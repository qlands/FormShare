"""The published-lists registry: the server core of native case management.

A published list is a real-time CSV (later GeoJSON) generated from a
repository table and served to devices as an ordinary form attachment. The
design record is docs/formshare_case_management/ -- read its README before
changing shapes here.

Two rules this module owns:

* **The key column of every list is rowuuid**, served as ``name``. It is not
  configurable, on purpose: rowuuid is the one identity every row of every
  table already has, which is what lets a list come from a maintable, a
  repeat table or another project's table without a special case anywhere.
* **Rows are ordered by rowuuid**, not by submission date, because a repeat
  table has no ``_submitted_date`` and because a stable order makes two
  generations of an unchanged table byte-identical -- which is what lets the
  manifest hash say "nothing changed".

The SQL builders are pure functions so the shape of a list can be asserted
without a database (tests/test_06_case_management.py); the wrappers around
them are thin.
"""

import csv
import datetime
import decimal
import logging
import re
from subprocess import Popen, PIPE
import tempfile
import shutil
import os
import uuid

from lxml import etree

from formshare.processes.list_filter import (
    resolve as resolve_filter,
    uses_properties as filter_uses_properties,
    referenced_properties,
)

from formshare.models import (
    PublishedList,
    PublishedListColumn,
    ListConsumer,
    MediaFile,
    TableProperty,
    Odkform,
    DictTable,
    DictField,
    map_from_schema,
)
from formshare.processes.logging.loggerclass import SecretLogger

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

__all__ = [
    "valid_list_filename",
    "build_list_select",
    "list_is_stale",
    "write_list_csv",
    "add_published_list",
    "update_published_list",
    "delete_published_list",
    "get_published_list",
    "get_project_published_lists",
    "set_list_columns",
    "get_list_columns",
    "get_list_source_schema",
    "get_form_data_tables",
    "get_table_columns",
    "detect_consumers",
    "sync_form_consumers",
    "get_form_consumers",
    "set_case_link",
    "get_case_link_consumer",
    "get_case_link_source",
    "get_consumer_sources",
    "apply_link_attributes",
    "source_form_has_consumers",
    "inherit_consumers",
    "project_is_longitudinal",
    "form_creates_cases",
    "form_consumes_cases",
    "list_has_active_consumers",
    "lists_fed_by_form",
    "project_has_workflow",
    "build_workflow_model",
    "get_project_workflow",
    "PROPERTY_TYPES",
    "property_type_label",
    "validate_property_default",
    "default_clause",
    "geometry_expression",
    "properties_table",
    "property_columns_ddl",
    "properties_ddl",
    "drop_property_ddl",
    "creation_trigger_sql",
    "backfill_sql",
    "get_list_source_tables",
    "get_table_properties",
    "get_form_properties",
    "properties_xml",
    "lists_xml",
    "property_is_served",
    "add_table_property",
    "delete_table_property",
    "inherit_properties",
    "generate_published_list_file",
    "project_has_lists",
]

# The file name is the entire coupling between the registry and the form
# designer's select_one_from_file, so it is kept boring on purpose: lower
# case, starts with a letter, csv or geojson.
_FILENAME = re.compile(r"^[a-z][a-z0-9_]*\.(csv|geojson)$")

# A column or table identifier as the dictionary writes them. Everything that
# reaches the SQL builders must have passed this or arrived from the
# dictionary itself; the builders quote with backticks either way.
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def valid_list_filename(file_name):
    """Whether a list file name is one the registry accepts."""
    return bool(_FILENAME.match(str(file_name or "")))


def _quoted(identifier):
    """Backtick-quotes an identifier, refusing anything that is not one.

    The registry UI only offers dictionary columns, so this is a backstop,
    not an escape mechanism: an identifier that fails here is a bug upstream.
    """
    if not _IDENTIFIER.match(str(identifier or "")):
        raise ValueError("Not an identifier: {}".format(identifier))
    return "`" + identifier + "`"


def build_list_select(
    schema,
    table,
    label_column,
    columns,
    filter_sql=None,
    limit=None,
    active=1,
    key_column=None,
    symbolic=False,
):
    """The SELECT that generates a published list.

    :param schema: the source repository schema
    :param table: maintable or a repeat table
    :param label_column: the column served as ``label``
    :param columns: [(column_name, column_as[, source]), ...] extra columns,
        in order; source is "table" (the default) or "property", a column of
        <table>_properties, joined 1:1 on rowuuid
    :param filter_sql: the list's filter, compiled from the owner's rule set
        by processes/list_filter.py, with {t} and {p} marking the aliases
    :param symbolic: spell the tables as ``{source.<table>}`` rather than
        ``schema.table`` -- the SELECT a device runs over its mirror
        (lists.xml, formshare.md 3.10); everything else is the same text,
        which SQLite accepts as written
    :return: (sql, headers) -- headers in CSV order

    ``name`` is always rowuuid and always first; ``label`` always second.
    """
    # A property column joins <table>_properties; the join and the aliases
    # appear only then, so a list without properties reads as before. A
    # filter that reads a property needs the join too, served or not.
    uses_properties = any(
        len(col) > 2 and col[2] == "property" for col in columns
    ) or filter_uses_properties(filter_sql)
    t = "t." if uses_properties else ""
    # A row list is keyed by the source row's rowuuid: one row per source row,
    # linkable as a case. A value list is keyed by a column -- a list of
    # districts pulled from a table of schools -- so name is that column's
    # value, DISTINCT collapses the repeats, and there is no rowuuid: it
    # cannot be a case link, there being nothing unique to foreign-key to.
    if key_column:
        select_parts = [
            "{}{} AS name".format(t, _quoted(key_column)),
            "{}{} AS label".format(t, _quoted(label_column)),
        ]
    else:
        select_parts = [
            "{}rowuuid AS name".format(t),
            "{}{} AS label".format(t, _quoted(label_column)),
        ]
    headers = ["name", "label"]
    for col in columns:
        column_name, column_as = col[0], col[1]
        prefix = "p." if len(col) > 2 and col[2] == "property" else t
        alias = column_as or column_name
        if alias in headers:
            # name and label are taken; a duplicate alias would shift the CSV.
            raise ValueError("Duplicated column: {}".format(alias))
        select_parts.append(
            "{}{} AS {}".format(prefix, _quoted(column_name), _quoted(alias))
        )
        headers.append(alias)
    if symbolic:
        source = "{source." + table + "}"
        props = "{source." + properties_table(table) + "}"
    else:
        source = "{}.{}".format(_quoted(schema), _quoted(table))
        props = "{}.{}".format(_quoted(schema), _quoted(properties_table(table)))
    if uses_properties:
        source += " AS t LEFT JOIN {} AS p ON p.rowuuid = t.rowuuid".format(props)
    sql = "SELECT {}{} FROM {}".format(
        "DISTINCT " if key_column else "",
        ",".join(select_parts),
        source,
    )
    # _active decides which rows the list carries. Every data table has it
    # (default 1), so a list serves active rows unless it was defined for the
    # inactive ones -- which is how one follow-up sees active cases while
    # another list sees the deactivated ones. active=None leaves it out
    # entirely, for the rare list that wants both.
    where = []
    if active is not None:
        where.append("{}_active = {}".format(t, int(active)))
    if filter_sql:
        # Compiled by processes/list_filter.py, with markers for the
        # aliases, which only this function knows.
        where.append(resolve_filter(filter_sql, t))
    if where:
        sql = sql + " WHERE " + " AND ".join(where)
    # A value list has no rowuuid to order by; its values order it instead.
    sql = sql + (" ORDER BY name" if key_column else " ORDER BY {}rowuuid".format(t))
    if limit is not None:
        # The sample download: enough rows to design a form against,
        # never the study.
        sql = sql + " LIMIT {}".format(int(limit))
    return sql, headers


def list_is_stale(lastgen, *change_dates):
    """Whether the stored file predates any change to its source.

    A list that was never generated is stale by definition. A change date the
    caller could not determine arrives as None and is ignored.
    """
    if lastgen is None:
        return True
    for a_date in change_dates:
        # Equal seconds count as a change: the stamps have one-second
        # resolution, and a change in the same second as the generation
        # would otherwise be served stale until the next one. The cost is
        # one regeneration of a file whose content may not have moved.
        if a_date is not None and a_date >= lastgen:
            return True
    return False


def write_list_csv(headers, rows, file_name):
    """Writes the generated rows as the CSV a device downloads.

    Every field is enclosed in double quotes (2026-09-13): data can carry
    commas, and always-quoting means no consumer -- device, spreadsheet, the
    Go generator that will replace this writer -- ever has to guess. An
    embedded quote is doubled, per RFC 4180. The Go generator must produce
    this byte for byte (rstools.md section 2.2), or the swap would churn
    every list's hash for nothing.
    """
    with open(file_name, "w", newline="") as outfile:
        writer = csv.writer(outfile, quoting=csv.QUOTE_ALL)
        writer.writerow(headers)
        for a_row in rows:
            writer.writerow(["" if a_value is None else a_value for a_value in a_row])


# ---------------------------------------------------------------------------
# Registry CRUD
# ---------------------------------------------------------------------------


def add_published_list(request, project_id, list_data):
    """Adds a list to the registry. list_data mirrors PublishedList columns."""
    _ = request.translate
    if not valid_list_filename(list_data.get("list_filename")):
        return False, _(
            "The file name must be lower case, start with a letter, and end "
            "in .csv or .geojson"
        )
    mapped_data = dict(list_data)
    mapped_data["project_id"] = project_id
    mapped_data["list_createdate"] = datetime.datetime.now()
    new_list = PublishedList(**mapped_data)
    try:
        request.dbsession.add(new_list)
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while adding list {} to project {}".format(
                str(e), list_data.get("list_id"), project_id
            )
        )
        return False, str(e)


def update_published_list(request, project_id, list_id, list_data):
    try:
        mapped_data = dict(list_data)
        mapped_data.pop("project_id", None)
        mapped_data.pop("list_id", None)
        request.dbsession.query(PublishedList).filter(
            PublishedList.project_id == project_id
        ).filter(PublishedList.list_id == list_id).update(mapped_data)
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while updating list {} of project {}".format(
                str(e), list_id, project_id
            )
        )
        return False, str(e)


def delete_published_list(request, project_id, list_id):
    try:
        request.dbsession.query(PublishedList).filter(
            PublishedList.project_id == project_id
        ).filter(PublishedList.list_id == list_id).delete()
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while deleting list {} of project {}".format(
                str(e), list_id, project_id
            )
        )
        return False, str(e)


def get_published_list(request, project_id, list_id):
    res = (
        request.dbsession.query(PublishedList)
        .filter(PublishedList.project_id == project_id)
        .filter(PublishedList.list_id == list_id)
        .first()
    )
    if res is None:
        return None
    return map_from_schema(res)


def project_has_lists(request, project_id):
    res = (
        request.dbsession.query(PublishedList)
        .filter(PublishedList.project_id == project_id)
        .order_by(PublishedList.list_createdate)
        .first()
    )
    if res is None:
        return False
    return True


def get_project_published_lists(request, project_id):
    res = (
        request.dbsession.query(PublishedList)
        .filter(PublishedList.project_id == project_id)
        .order_by(PublishedList.list_createdate)
        .all()
    )
    res = map_from_schema(res)
    for a_list in res:
        a_list["has_active_consumers"] = list_has_active_consumers(
            request, project_id, a_list["list_id"]
        )
    return res


def set_list_columns(request, project_id, list_id, columns):
    """Replaces the served columns of a list. columns = [(name, as, source)]."""
    try:
        request.dbsession.query(PublishedListColumn).filter(
            PublishedListColumn.project_id == project_id
        ).filter(PublishedListColumn.list_id == list_id).delete()
        for an_index, (column_name, column_as, column_source) in enumerate(columns):
            request.dbsession.add(
                PublishedListColumn(
                    project_id=project_id,
                    list_id=list_id,
                    column_name=column_name,
                    column_as=column_as,
                    column_source=column_source,
                    column_order=an_index,
                )
            )
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while setting columns of list {} of project {}".format(
                str(e), list_id, project_id
            )
        )
        return False, str(e)


def invalidate_list_copies(request, project_id, list_id):
    """Marks every served copy of a list as never generated.

    A form's copy is regenerated at manifest time only when it is stale, and
    stale is decided against the source's data (refresh_published_lists in
    processes/odk/api.py: the copy's file_lastgen against the source's last
    submission and last clean edit). A change to the list's own definition --
    a column added or removed, another label, filter, key or active flag --
    did not count, so every consuming form kept serving the old columns until
    the source next received data, which on a settled roster can be never.

    Clearing the copies' file_lastgen is what that gate already reads as
    "never generated by us", so the next pull of each form regenerates the
    file and stamps the new edition; the list's own list_lastgen and list_seq
    move then, not here, because they mark a generation that happened. The
    copies are the media files named after the list in its project, which is
    also how the gate finds them: a form that attached the file by name is
    served the regenerated list whether or not it has a ListConsumer row, so
    it is invalidated the same way.
    """
    list_data = get_published_list(request, project_id, list_id)
    if list_data is None:
        return False, "The list does not exist"
    try:
        request.dbsession.query(MediaFile).filter(
            MediaFile.project_id == project_id
        ).filter(MediaFile.file_name == list_data["list_filename"]).update(
            {"file_lastgen": None}, synchronize_session=False
        )
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while invalidating the copies of list {} of project {}".format(
                str(e), list_id, project_id
            )
        )
        return False, str(e)


def get_list_columns(request, project_id, list_id):
    res = (
        request.dbsession.query(PublishedListColumn)
        .filter(PublishedListColumn.project_id == project_id)
        .filter(PublishedListColumn.list_id == list_id)
        .order_by(PublishedListColumn.column_order)
        .all()
    )
    return map_from_schema(res)


def get_form_data_tables(request, project_id, form_id):
    """The tables of a form a list can be published from: maintable and the
    repeat tables -- never the lookups, whose rows are choices, not cases."""
    res = (
        request.dbsession.query(DictTable)
        .filter(DictTable.project_id == project_id)
        .filter(DictTable.form_id == form_id)
        .filter(DictTable.table_lkp == 0)
        .order_by(DictTable.table_index)
        .all()
    )
    return map_from_schema(res)


def get_table_columns(request, project_id, form_id, table_name):
    """The columns of a source table an owner may serve or label with.

    rowuuid is excluded because it is always served, as name, and offering
    it would invite serving it twice.
    """
    res = (
        request.dbsession.query(DictField)
        .filter(DictField.project_id == project_id)
        .filter(DictField.form_id == form_id)
        .filter(DictField.table_name == table_name)
        .filter(DictField.field_name != "rowuuid")
        .all()
    )
    return map_from_schema(res)


def get_list_source_schema(request, list_data):
    """The repository schema of a list's source form, or None if unbuilt."""
    res = (
        request.dbsession.query(Odkform.form_schema)
        .filter(Odkform.project_id == list_data["source_project"])
        .filter(Odkform.form_id == list_data["source_form"])
        .first()
    )
    if res is None:
        return None
    return res[0]


def generate_published_list_file(request, list_data, out_path):
    """Generates the list's file and stamps the edition.

    Bumps list_seq and list_lastgen only when generation succeeded, so a
    failed generation leaves the previous edition current.
    """
    schema = get_list_source_schema(request, list_data)
    if schema is None or schema == "":
        return False, "The source form has no repository"
    columns = [
        (
            a_column["column_name"],
            a_column["column_as"],
            a_column.get("column_source") or "table",
        )
        for a_column in get_list_columns(
            request, list_data["project_id"], list_data["list_id"]
        )
    ]
    try:
        sql, headers = build_list_select(
            schema,
            list_data["source_table"],
            list_data["label_column"],
            columns,
            list_data.get("filter_sql"),
            active=list_data.get("list_active", 1),
            key_column=list_data.get("list_key_column"),
        )
        rows = request.dbsession.execute(sql).fetchall()
        write_list_csv(headers, rows, out_path)
        request.dbsession.query(PublishedList).filter(
            PublishedList.project_id == list_data["project_id"]
        ).filter(PublishedList.list_id == list_data["list_id"]).update(
            {
                "list_seq": PublishedList.list_seq + 1,
                "list_lastgen": datetime.datetime.now(),
            }
        )
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        log.error(
            "Error {} while generating list {} of project {}".format(
                str(e), list_data["list_id"], list_data["project_id"]
            )
        )
        return False, str(e)


# ---------------------------------------------------------------------------
# Consumers: the forms that read a list, and which reference is the case link
# ---------------------------------------------------------------------------


def detect_consumers(maintable_fields, published_lists):
    """Which registry lists a form consumes, from its maintable fields.

    A form consumes a list when one of its ``select_one_from_file`` fields
    (``selecttype`` 3 in create.xml) names that list's file. The match is by
    file name, which is the whole coupling between a form and a list.

    :param maintable_fields: get_fields_from_table_in_file(create_file, "maintable")
    :param published_lists: get_project_published_lists(...)
    :return: [{list_id, list_filename, selector_field}, ...]
    """
    by_filename = {a_list["list_filename"]: a_list for a_list in published_lists}
    consumers = []
    for a_field in maintable_fields:
        if a_field.get("selecttype") != "3":
            continue
        a_list = by_filename.get(a_field.get("externalfilename", ""))
        if a_list is None:
            continue
        consumers.append(
            {
                "list_id": a_list["list_id"],
                "list_filename": a_list["list_filename"],
                "selector_field": a_field["name"],
            }
        )
    return consumers


def sync_form_consumers(request, project_id, form_id, maintable_fields):
    """Reconciles the stored consumers of a form with what it now references.

    Adds newly referenced lists, drops references the form no longer makes,
    and updates the detected selector column, all without disturbing a
    case-link choice already made. When the form consumes exactly one list
    and none is marked the case link, that one is marked automatically -- the
    common single-list follow-up needs no decision.
    """
    published = get_project_published_lists(request, project_id)
    detected = detect_consumers(maintable_fields, published)
    detected_ids = {a_consumer["list_id"] for a_consumer in detected}
    existing = {
        a_row["list_id"]: a_row
        for a_row in get_form_consumers(request, project_id, form_id)
    }
    try:
        # Drop references the form no longer makes.
        for list_id in existing:
            if list_id not in detected_ids:
                request.dbsession.query(ListConsumer).filter(
                    ListConsumer.list_project == project_id
                ).filter(ListConsumer.list_id == list_id).filter(
                    ListConsumer.consumer_project == project_id
                ).filter(
                    ListConsumer.consumer_form == form_id
                ).delete()
        # Add or update the ones it makes.
        for a_consumer in detected:
            if a_consumer["list_id"] in existing:
                request.dbsession.query(ListConsumer).filter(
                    ListConsumer.list_project == project_id
                ).filter(ListConsumer.list_id == a_consumer["list_id"]).filter(
                    ListConsumer.consumer_project == project_id
                ).filter(
                    ListConsumer.consumer_form == form_id
                ).update(
                    {"selector_field": a_consumer["selector_field"]}
                )
            else:
                request.dbsession.add(
                    ListConsumer(
                        list_project=project_id,
                        list_id=a_consumer["list_id"],
                        consumer_project=project_id,
                        consumer_form=form_id,
                        consumer_role="reads",
                        selector_field=a_consumer["selector_field"],
                        consumer_is_link=0,
                    )
                )
        request.dbsession.commit()
        # Auto-mark the case link when there is exactly one consumer and no
        # choice has been made.
        current = get_form_consumers(request, project_id, form_id)
        if len(current) == 1 and not any(
            int(a_row["consumer_is_link"] or 0) == 1 for a_row in current
        ):
            # A lone value-list consumer (a district filter) is not a follow-up
            # of anything; set_case_link refuses it, quietly here.
            set_case_link(request, project_id, form_id, current[0]["list_id"])
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while syncing consumers of form {} in project {}".format(
                str(e), form_id, project_id
            )
        )
        return False, str(e)


def get_form_consumers(request, project_id, form_id):
    res = (
        request.dbsession.query(ListConsumer)
        .filter(ListConsumer.consumer_project == project_id)
        .filter(ListConsumer.consumer_form == form_id)
        .all()
    )
    return map_from_schema(res)


def set_case_link(request, project_id, form_id, list_id):
    """Marks one consumer as the case link and clears the others.

    The case link is the list whose rows the form is about: it gets the
    foreign key and the membership trigger at repository build. A form has at
    most one, and it must be a row list -- a value list (distinct districts
    from a table of schools) has no rowuuid to link to.
    """
    a_list = get_published_list(request, project_id, list_id)
    if a_list is not None and a_list.get("list_key_column"):
        return False, "A value list cannot be the case link: it has no row identity"
    try:
        request.dbsession.query(ListConsumer).filter(
            ListConsumer.consumer_project == project_id
        ).filter(ListConsumer.consumer_form == form_id).update({"consumer_is_link": 0})
        request.dbsession.query(ListConsumer).filter(
            ListConsumer.consumer_project == project_id
        ).filter(ListConsumer.consumer_form == form_id).filter(
            ListConsumer.list_id == list_id
        ).update(
            {"consumer_is_link": 1, "consumer_role": "updates"}
        )
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while setting the case link of form {} in project {}".format(
                str(e), form_id, project_id
            )
        )
        return False, str(e)


def get_case_link_consumer(request, project_id, form_id):
    """The consumer marked as the case link, or None."""
    res = (
        request.dbsession.query(ListConsumer)
        .filter(ListConsumer.consumer_project == project_id)
        .filter(ListConsumer.consumer_form == form_id)
        .filter(ListConsumer.consumer_is_link == 1)
        .first()
    )
    if res is None:
        return None
    return map_from_schema(res)


def get_case_link_source(request, project_id, form_id):
    """The (schema, table) a form's case link points at, or None.

    Resolves the case-link consumer to its list, the list to its source form,
    and that form to its built repository schema. None when there is no case
    link or the source repository is not built.
    """
    consumer = get_case_link_consumer(request, project_id, form_id)
    if consumer is None:
        return None
    a_list = get_published_list(request, consumer["list_project"], consumer["list_id"])
    if a_list is None:
        return None
    res = (
        request.dbsession.query(Odkform.form_schema)
        .filter(Odkform.project_id == a_list["source_project"])
        .filter(Odkform.form_id == a_list["source_form"])
        .first()
    )
    if res is None or res[0] is None or res[0] == "":
        return None
    return res[0], a_list["source_table"]


def get_consumer_sources(request, project_id, form_id):
    """Every list a form consumes, resolved to its source table and role.

    Returns [{selector_field, source_schema, source_table, is_link}], one per
    consumer whose source repository is built. The repository build retypes
    each selector to the source key and adds a foreign key; the case link one
    additionally gets the membership trigger.
    """
    result = []
    for consumer in get_form_consumers(request, project_id, form_id):
        a_list = get_published_list(
            request, consumer["list_project"], consumer["list_id"]
        )
        if a_list is None:
            continue
        res = (
            request.dbsession.query(Odkform.form_schema)
            .filter(Odkform.project_id == a_list["source_project"])
            .filter(Odkform.form_id == a_list["source_form"])
            .first()
        )
        if res is None or res[0] is None or res[0] == "":
            continue
        if not consumer["selector_field"]:
            continue
        key_column = a_list.get("list_key_column") or None
        result.append(
            {
                "selector_field": consumer["selector_field"],
                "source_schema": res[0],
                "source_table": a_list["source_table"],
                # A value list has no rowuuid to link to, whatever was stored.
                "is_link": int(consumer["consumer_is_link"] or 0) == 1
                and not key_column,
                "list_active": int(a_list.get("list_active", 1) or 0),
                "key_column": key_column,
            }
        )
    return result


def source_form_has_consumers(request, source_project, source_form):
    """Whether any list sourced from this form is consumed by a form.

    The delete guard reads this: a source form cannot be deleted while a
    follow-up links to a list it feeds, the same reason its foreign key uses
    ON DELETE RESTRICT.
    """
    res = (
        request.dbsession.query(ListConsumer)
        .join(
            PublishedList,
            (ListConsumer.list_project == PublishedList.project_id)
            & (ListConsumer.list_id == PublishedList.list_id),
        )
        .filter(PublishedList.source_project == source_project)
        .filter(PublishedList.source_form == source_form)
        .all()
    )
    return len(res) > 0


def lists_fed_by_form(request, source_project, source_form):
    """The published lists, in any project, whose source is this form.

    The delete guard reads this after source_form_has_consumers: a form that
    feeds a list cannot be deleted even while nothing consumes the list yet,
    because the registry's foreign key on the source (fk_publishedlist_
    source_odkform, no cascade) refuses it -- the lists go first.
    """
    res = (
        request.dbsession.query(
            PublishedList.project_id, PublishedList.list_id, PublishedList.list_filename
        )
        .filter(PublishedList.source_project == source_project)
        .filter(PublishedList.source_form == source_form)
        .order_by(PublishedList.list_id)
        .all()
    )
    return [{"project_id": r[0], "list_id": r[1], "list_filename": r[2]} for r in res]


def inherit_consumers(request, project_id, parent_form, child_form):
    """Gives a new version the list links of the version it will replace.

    A merge child keeps its parent's consumers -- the same lists, the same
    case link -- because the repository it will merge into was built on them:
    the foreign keys and the membership trigger already exist on the parent's
    selectors, and mergeversions has to see the same shape on both sides.
    Rows the child already has are left alone; the selector column is taken
    from the parent and refreshed by the next sync against the child's own
    create.xml, which is where a renamed selector shows up.
    """
    existing = {
        a_row["list_id"]
        for a_row in get_form_consumers(request, project_id, child_form)
    }
    try:
        for a_row in get_form_consumers(request, project_id, parent_form):
            if a_row["list_id"] in existing:
                continue
            request.dbsession.add(
                ListConsumer(
                    list_project=a_row["list_project"],
                    list_id=a_row["list_id"],
                    consumer_project=project_id,
                    consumer_form=child_form,
                    consumer_role=a_row["consumer_role"],
                    selector_field=a_row["selector_field"],
                    consumer_is_link=a_row["consumer_is_link"],
                )
            )
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while inheriting consumers from {} to {} in project {}".format(
                str(e), parent_form, child_form, project_id
            )
        )
        return False, str(e)


def project_is_longitudinal(request, project_id):
    """Whether a project runs a longitudinal workflow: it publishes a list
    that some form uses.

    "Used" means a form references the list; whether that form's repository is
    built ("consumed") or not does not matter. A list nobody references does
    not make the project longitudinal.
    """
    return (
        request.dbsession.query(ListConsumer.list_id)
        .join(
            PublishedList,
            (ListConsumer.list_project == PublishedList.project_id)
            & (ListConsumer.list_id == PublishedList.list_id),
        )
        .filter(PublishedList.project_id == project_id)
        .first()
        is not None
    )


def form_creates_cases(request, project_id, form_id):
    """Whether a form produces a published list that some form uses.

    The form is the source of a list, and a form references that list --
    whether that consumer's repository is built or not. A list published from
    this form that nobody references does not count.
    """
    return (
        request.dbsession.query(ListConsumer.list_id)
        .join(
            PublishedList,
            (ListConsumer.list_project == PublishedList.project_id)
            & (ListConsumer.list_id == PublishedList.list_id),
        )
        .filter(PublishedList.source_project == project_id)
        .filter(PublishedList.source_form == form_id)
        .first()
        is not None
    )


def form_consumes_cases(request, project_id, form_id):
    """Whether a form consumes a published list -- it uses cases.

    True if the form references any published list, whether that reference is
    the case link or an auxiliary read, and whether or not its repository is
    built.
    """
    return (
        request.dbsession.query(ListConsumer.list_id)
        .filter(ListConsumer.consumer_project == project_id)
        .filter(ListConsumer.consumer_form == form_id)
        .first()
        is not None
    )


def list_has_active_consumers(request, project_id, list_id):
    """Whether a list has a consumer whose repository is built.

    An "active" consumer is one that is actually wired into the schema: its
    form has a repository, so the foreign key (and, for the case link, the
    membership trigger) to this list's source exist. A consumer detected at
    upload but not yet built does not count -- nothing depends on the list in
    the database yet. This is what makes a list's source risky to change.
    """
    return (
        request.dbsession.query(ListConsumer.consumer_form)
        .join(
            Odkform,
            (ListConsumer.consumer_project == Odkform.project_id)
            & (ListConsumer.consumer_form == Odkform.form_id),
        )
        .filter(ListConsumer.list_project == project_id)
        .filter(ListConsumer.list_id == list_id)
        .filter(Odkform.form_schema.isnot(None))
        .filter(Odkform.form_schema != "")
        .first()
        is not None
    )


def apply_link_attributes(root, sources, key_types):
    """Wires a form's list consumers into its create.xml tree (pure).

    For every consumer: retype the selector to the source's rowuuid and add a
    foreign key to ``<source>.<table>(rowuuid)`` ON DELETE RESTRICT. For the
    one consumer that is the case link, also set the maintable attributes
    RSTools turns into a membership trigger: it checks the selector exists in
    the source with the ``_active`` the list serves, and refuses null.

    Which ``_active`` the trigger checks is chosen by ``case_action_type``
    (rstools.md 6.5, 2026-09-19): ``follow`` asks for 1, ``activate`` for 0.
    So a link over an active-serving list checks "exists and is active" and
    one over an inactive-serving list "exists and is inactive" (the message
    then reads "is already active or does not exist"). ``case_action`` is
    ``false`` either way: the trigger is a check, never a write -- what a
    follow-up does to a case is an action (section 3.3), not a side effect
    of selecting it.

    :param root: the parsed create.xml root
    :param sources: get_consumer_sources(...) output
    :param key_types: {"schema.table": (type, size)} for each source
    :return: (True, "") or (False, message)
    """
    table = root.find(".//table[@name='maintable']")
    if table is None:
        return False, "Main table was not found in create.xml"
    for a_source in sources:
        ref = a_source["source_schema"] + "." + a_source["source_table"]
        key_column = a_source.get("key_column") or "rowuuid"
        key = key_types.get(ref + "." + key_column)
        if key is None:
            return False, "No key type for {}.{}".format(ref, key_column)
        key_type, key_size = key
        # Scoped to the maintable on purpose. A registry-served CSV can carry a
        # column named after the selector (the tosin roster serves one called
        # worker_id), and if RSTools has frozen that CSV into a lookup table the
        # lookup carries a same-named field that comes first in document
        # order; an unscoped find stamped the foreign key on it and the build
        # failed with 1452 inserting the lookup rows.
        field = table.find("field[@name='" + a_source["selector_field"] + "']")
        if field is None:
            return False, "The selector field {} was not found in create.xml".format(
                a_source["selector_field"]
            )
        field.set("type", key_type)
        field.set("size", str(key_size))
        if a_source.get("key_column"):
            # A value list: the selector holds a value (a district name), so it
            # only needs the key column's type -- RSTools emits int for an
            # external select -- and no foreign key: the key is neither unique
            # nor a rowuuid, and the list is a filter driver, not a case.
            continue
        field.set("rtable", ref)
        field.set("rfield", "rowuuid")
        field.set("rname", "fk_" + str(uuid.uuid4()).replace("-", "_"))
        field.set("rlookup", "false")
        field.set("on_delete", "RESTRICT")
        if a_source["is_link"]:
            table.set("case_followup", "true")
            table.set("creator_table", ref)
            table.set("creator_field", "rowuuid")
            table.set("selector_field", a_source["selector_field"])
            table.set("block_trigger", "T" + str(uuid.uuid4()).replace("-", "_"))
            table.set(
                "case_action_type",
                "follow" if int(a_source.get("list_active", 1)) == 1 else "activate",
            )
            table.set("case_action", "false")
    return True, ""


# ---------------------------------------------------------------------------
# The workflow diagram: what the registry and the schemas say about a project,
# as one model a page can draw (docs/formshare_case_management/formshare.md
# section 3.9).


def project_has_workflow(request, project_id):
    """Whether a workflow is in place: a list of the project has a consumer
    whose repository is built, so at least two schemas are linked and the
    list can no longer be deleted (list_has_active_consumers, per list)."""
    return (
        request.dbsession.query(ListConsumer.consumer_form)
        .join(
            Odkform,
            (ListConsumer.consumer_project == Odkform.project_id)
            & (ListConsumer.consumer_form == Odkform.form_id),
        )
        .filter(ListConsumer.list_project == project_id)
        .filter(Odkform.form_schema.isnot(None))
        .filter(Odkform.form_schema != "")
        .first()
        is not None
    )


def build_workflow_model(
    project,
    forms,
    lists,
    list_columns,
    consumers,
    tables,
    fks,
    triggers,
    translate=None,
):
    """The longitudinal workflow of a project, as data for a page to draw.

    Pure: every input is a list of dicts the caller read, so it can be checked
    without a database. The shape is what the page's script expects:

    forms   the current version of each form (a merged-away version is folded
            into the one that owns its schema, and so are its consumers) with
            the tables that take part -- a table that publishes a list or
            holds a selector; the main table alone when none does -- and their
            fields: rowuuid, a repeat's parent_rowuuid, the primary key, the
            selectors with their role. "rank" is the form's column: 0 for a
            form that consumes nothing, else one more than the forms whose
            lists it consumes, which lays the chain out left to right.
    lists   a published list with what it serves; "rank" is source + 0.5.
    edges   publishes (table field -> list), reads and link (list -> selector,
            labelled from the schema: the foreign key rule and the membership
            trigger, read from the built schema rather than the registry) and
            repeat (a repeat's parent_rowuuid -> its parent's rowuuid).
    """
    _ = translate or (lambda s: s)
    schema_owner = {}
    for f in forms:
        if f["form_schema"]:
            schema_owner[f["form_schema"]] = f["form_id"]  # the newest version
    form_by_id = {f["form_id"]: f for f in forms}

    def current_of(form_id):
        f = form_by_id.get(form_id)
        if f and f["form_schema"]:
            return schema_owner[f["form_schema"]]
        return form_id

    fk_by_field = {(fk["s"], fk["t"], fk["c"]): fk for fk in fks}
    trigger_by_field = {}
    for t in triggers:
        # RSTools quotes the identifiers since 378c792 (2026-09-19) and wrote
        # them bare before; both shapes are read. The _active it checks is 1
        # for a follow-up over active rows and 0 over inactive ones.
        m = re.search(
            r"FROM `?(\w+)`?\.`?(\w+)`? WHERE `?_active`? = (\d) "
            r"AND `?(\w+)`? = new\.`?(\w+)`?",
            t["body"],
        )
        if m:
            trigger_by_field[(t["s"], t["t"], m.group(5))] = {
                "rt": m.group(2),
                "rc": m.group(4),
                "active": m.group(3),
            }
    consumers_of = {}
    for c in consumers:
        mine = consumers_of.setdefault(current_of(c["consumer_form"]), [])
        if not any(
            m["list_id"] == c["list_id"] and m["selector_field"] == c["selector_field"]
            for m in mine
        ):
            mine.append(c)
    list_by_id = {l["list_id"]: l for l in lists}
    published_by = {}
    for l in lists:
        published_by.setdefault(current_of(l["source_form"]), []).append(l)
    columns_of = {}
    for c in list_columns:
        columns_of.setdefault(c["list_id"], []).append(
            c["column_name"] + (" → " + c["column_as"] if c["column_as"] else "")
        )

    rank = {}

    def rank_of(form_id, seen=()):
        if form_id in rank:
            return rank[form_id]
        if form_id in seen:
            return 0
        sources = [
            current_of(list_by_id[c["list_id"]]["source_form"])
            for c in consumers_of.get(form_id, [])
            if c["list_id"] in list_by_id
        ]
        sources = [s for s in sources if s != form_id]
        rank[form_id] = (
            0
            if not sources
            else 1 + max(rank_of(s, seen + (form_id,)) for s in sources)
        )
        return rank[form_id]

    model = {"project": project, "forms": [], "lists": [], "edges": []}
    current_forms = [
        f
        for f in forms
        if not f["form_schema"] or schema_owner[f["form_schema"]] == f["form_id"]
    ]
    for f in current_forms:
        fid = f["form_id"]
        published = published_by.get(fid, [])
        my_consumers = consumers_of.get(fid, [])
        form_tables = [t for t in tables if t["form_id"] == fid] or [
            {
                "form_id": fid,
                "table_name": "maintable",
                "parent_table": None,
                "table_desc": "",
            }
        ]
        taking_part = {l["source_table"] for l in published}
        if my_consumers:
            taking_part.add("maintable")
        form_tables = [t for t in form_tables if t["table_name"] in taking_part] or [
            t for t in form_tables if t["table_name"] == "maintable"
        ]
        shown = {t["table_name"] for t in form_tables}
        form_tables.sort(
            key=lambda t: (
                t["parent_table"] is not None,
                t["table_name"] != "maintable",
                t["table_name"],
            )
        )
        out_tables = []
        for t in form_tables:
            name = t["table_name"]
            fields = [
                {"name": "rowuuid", "desc": _("identity of a row"), "kind": "identity"}
            ]
            if t["parent_table"]:
                fields.append(
                    {
                        "name": "parent_rowuuid",
                        "desc": _("the {} row it belongs to").format(t["parent_table"]),
                        "kind": "parent",
                    }
                )
            if name == "maintable" and f.get("form_pkey"):
                fields.append(
                    {"name": f["form_pkey"], "desc": _("primary key"), "kind": "pkey"}
                )
            if name == "maintable":
                for c in my_consumers:
                    fields.append(
                        {
                            "name": c["selector_field"],
                            "desc": (
                                _("case link")
                                if c["consumer_is_link"]
                                else _(c["consumer_role"])
                            )
                            + " ← "
                            + c["list_id"],
                            "kind": "link" if c["consumer_is_link"] else "reads",
                        }
                    )
            parent = t["parent_table"] if t["parent_table"] in shown else None
            out_tables.append(
                {
                    "name": name,
                    "desc": t.get("table_desc") or "",
                    "parent": parent,
                    "fields": fields,
                }
            )
            if parent:
                model["edges"].append(
                    {
                        "kind": "repeat",
                        "label": _("repeat of"),
                        "from": {"form": fid, "table": name, "field": "parent_rowuuid"},
                        "to": {"form": fid, "table": parent, "field": "rowuuid"},
                    }
                )
        model["forms"].append(
            {
                "id": fid,
                "name": f["form_name"],
                "version": f["form_version"],
                "schema": f["form_schema"][3:11] if f["form_schema"] else None,
                "rank": rank_of(fid),
                "tables": out_tables,
            }
        )
        for c in my_consumers:
            key = (f["form_schema"], "maintable", c["selector_field"])
            fk, trig = fk_by_field.get(key), trigger_by_field.get(key)
            if c["consumer_is_link"]:
                parts = [_("case link")]
                if fk:
                    parts.append(_("FK ON DELETE {}").format(fk["rule"]))
                if trig:
                    parts.append(
                        (
                            _("trigger: {}.{} must be _active")
                            if trig["active"] == "1"
                            else _("trigger: {}.{} must be inactive")
                        ).format(trig["rt"], trig["rc"])
                    )
            else:
                parts = [_(c["consumer_role"])]
                if fk:
                    parts.append(_("FK ON DELETE {}").format(fk["rule"]))
                elif f["form_schema"]:
                    parts.append(_("value only, no FK"))
            model["edges"].append(
                {
                    "kind": "link" if c["consumer_is_link"] else "reads",
                    "label": "\n".join(parts),
                    "from": {"list": c["list_id"]},
                    "to": {
                        "form": fid,
                        "table": "maintable",
                        "field": c["selector_field"],
                    },
                }
            )
    for l in lists:
        source = current_of(l["source_form"])
        model["lists"].append(
            {
                "id": l["list_id"],
                "filename": l["list_filename"],
                "source_form": l["source_form"],
                "source_table": l["source_table"],
                "value_list": bool(l.get("list_key_column")),
                "kind": (
                    _("value list: DISTINCT {}").format(l["list_key_column"])
                    if l.get("list_key_column")
                    else _("row list: name = rowuuid")
                ),
                "label": l["label_column"],
                "columns": columns_of.get(l["list_id"], []),
                "rank": rank_of(source) + 0.5,
            }
        )
        model["edges"].append(
            {
                "kind": "publishes",
                "label": _("publishes"),
                "from": {
                    "form": source,
                    "table": l["source_table"],
                    "field": "rowuuid",
                },
                "to": {"list": l["list_id"]},
            }
        )
    return model


def get_project_workflow(request, project_id, project):
    """Reads what build_workflow_model needs and builds the model."""
    forms = [
        {
            "form_id": r.form_id,
            "form_name": r.form_name,
            "form_version": r.form_version,
            "form_schema": r.form_schema,
            "parent_form": r.parent_form,
            "form_pkey": r.form_pkey,
        }
        for r in request.dbsession.query(
            Odkform.form_id,
            Odkform.form_name,
            Odkform.form_version,
            Odkform.form_schema,
            Odkform.parent_form,
            Odkform.form_pkey,
        )
        .filter(Odkform.project_id == project_id)
        .order_by(Odkform.form_cdate)
        .all()
    ]
    lists = [
        {
            "list_id": r.list_id,
            "list_filename": r.list_filename,
            "source_form": r.source_form,
            "source_table": r.source_table,
            "label_column": r.label_column,
            "list_key_column": r.list_key_column,
        }
        for r in request.dbsession.query(
            PublishedList.list_id,
            PublishedList.list_filename,
            PublishedList.source_form,
            PublishedList.source_table,
            PublishedList.label_column,
            PublishedList.list_key_column,
        )
        .filter(PublishedList.project_id == project_id)
        .order_by(PublishedList.list_createdate)
        .all()
    ]
    list_columns = [
        {"list_id": r.list_id, "column_name": r.column_name, "column_as": r.column_as}
        for r in request.dbsession.query(
            PublishedListColumn.list_id,
            PublishedListColumn.column_name,
            PublishedListColumn.column_as,
        )
        .filter(PublishedListColumn.project_id == project_id)
        .order_by(PublishedListColumn.list_id, PublishedListColumn.column_order)
        .all()
    ]
    consumers = [
        {
            "list_id": r.list_id,
            "consumer_form": r.consumer_form,
            "consumer_role": r.consumer_role,
            "selector_field": r.selector_field,
            "consumer_is_link": r.consumer_is_link,
        }
        for r in request.dbsession.query(
            ListConsumer.list_id,
            ListConsumer.consumer_form,
            ListConsumer.consumer_role,
            ListConsumer.selector_field,
            ListConsumer.consumer_is_link,
        )
        .filter(ListConsumer.list_project == project_id)
        .all()
    ]
    tables = [
        {
            "form_id": r.form_id,
            "table_name": r.table_name,
            "parent_table": r.parent_table,
            "table_desc": r.table_desc,
        }
        for r in request.dbsession.query(
            DictTable.form_id,
            DictTable.table_name,
            DictTable.parent_table,
            DictTable.table_desc,
        )
        .filter(DictTable.project_id == project_id)
        .filter(~DictTable.table_name.like("lkp%"))
        .filter(~DictTable.table_name.like("%\\_msel\\_%"))
        .order_by(DictTable.form_id, DictTable.table_name)
        .all()
    ]
    schemas = sorted({f["form_schema"] for f in forms if f["form_schema"]})
    fks, triggers = [], []
    if schemas:
        params = {"s{}".format(i): s for i, s in enumerate(schemas)}
        in_list = ", ".join(":" + k for k in params)
        fks = [
            {
                "s": r[0],
                "t": r[1],
                "c": r[2],
                "rs": r[3],
                "rt": r[4],
                "rc": r[5],
                "rule": r[6],
            }
            for r in request.dbsession.execute(
                "SELECT k.constraint_schema, k.table_name, k.column_name, "
                "k.referenced_table_schema, k.referenced_table_name, "
                "k.referenced_column_name, r.delete_rule "
                "FROM information_schema.key_column_usage k "
                "JOIN information_schema.referential_constraints r "
                "ON r.constraint_schema = k.constraint_schema "
                "AND r.constraint_name = k.constraint_name "
                "WHERE k.referenced_table_schema IN ({}) "
                "AND k.constraint_schema <> k.referenced_table_schema".format(in_list),
                params,
            ).fetchall()
        ]
        # "is inactive or does not exist" for a follow-up over active rows,
        # "is already active or does not exist" over inactive ones.
        trigger_params = dict(params, pattern="%or does not exist%")
        triggers = [
            {"s": r[0], "t": r[1], "body": r[2]}
            for r in request.dbsession.execute(
                "SELECT trigger_schema, event_object_table, action_statement "
                "FROM information_schema.triggers "
                "WHERE trigger_schema IN ({}) AND action_statement LIKE :pattern".format(
                    in_list
                ),
                trigger_params,
            ).fetchall()
        ]
    return build_workflow_model(
        project,
        forms,
        lists,
        list_columns,
        consumers,
        tables,
        fks,
        triggers,
        request.translate,
    )


# ---------------------------------------------------------------------------
# Properties (feature 2): a typed column beside the source table, born with
# the row at its default, set by the workflow, served by any list of the
# table. docs/formshare_case_management/formshare.md sections 2.3 and 3.1.

_PROPERTY_NAME = re.compile(r"^[a-z][a-z0-9_]{0,60}$")

# The types a property can have and the MySQL column each becomes. The three
# geo types are stored as RSTools stores the matching ODK answers: a geopoint
# as its "lat lon alt acc" text, a trace or a shape as text with a geometry
# MySQL derives beside it (JXFormToMySQL's appendAnswerGeometry), so a value a
# follow-up copies from its own geo variable always fits.
PROPERTY_TYPES = [
    ("string", "String", "varchar(255)"),
    ("integer", "Integer", "int"),
    ("decimal", "Decimal", "decimal(10,3)"),
    ("date", "Date", "date"),
    ("datetime", "DateTime", "datetime"),
    ("geopoint", "GeoPoint", "varchar(80)"),
    ("geotrace", "GeoTrace", "text"),
    ("geoshape", "GeoShape", "text"),
]
_COLUMN_TYPE = {code: column for code, _, column in PROPERTY_TYPES}
_GEO_TWIN = ("geotrace", "geoshape")


def property_type_label(code):
    return {c: label for c, label, _ in PROPERTY_TYPES}.get(code, code)


_COORDINATE = re.compile(r"-?[0-9]+(\.[0-9]+)?")


def _valid_point(text):
    """A point the geometry can read: latitude and longitude, or those with
    altitude and accuracy, each a plain decimal in ASCII digits.

    geometry_expression reads coordinates as [-0-9.] and drops altitude and
    accuracy only when both are there, so anything float() takes beyond that
    -- 1e1, +1, 1_0, other scripts' digits, a point of three numbers -- would
    keep its text and get a NULL geometry beside it, silently
    (rstools.md 15.4 d)."""
    parts = text.split()
    if len(parts) not in (2, 4):
        return False
    if not all(_COORDINATE.fullmatch(part) for part in parts):
        return False
    numbers = [float(part) for part in parts]
    return -90 <= numbers[0] <= 90 and -180 <= numbers[1] <= 180


def validate_property_default(property_type, value, translate=None):
    """Checks a default against its type; returns (ok, value, message).

    Empty is NULL. A number must be one; a date is YYYY-MM-DD and a datetime
    YYYY-MM-DD HH:MM:SS, both real dates (so 0, AAA and 2026-02-30 are
    refused); a geopoint is "latitude longitude [altitude [accuracy]]", a
    geotrace at least two such points joined by semicolons, a geoshape at
    least four, closing on its first. The value comes back normalised.
    """
    _ = translate or (lambda s: s)
    value = (value or "").strip()
    if value == "":
        return True, None, ""
    if property_type == "string":
        if len(value) > 255:
            return False, None, _("A string default holds at most 255 characters")
        return True, value, ""
    if property_type == "integer":
        if (
            not re.match(r"^[+-]?\d+$", value)
            or not -2147483648 <= int(value) <= 2147483647
        ):
            return False, None, _("{} is not an integer").format(value)
        return True, str(int(value)), ""
    if property_type == "decimal":
        m = re.match(r"^([+-]?\d+)(?:\.(\d+))?$", value)
        if m is None:
            return False, None, _("{} is not a decimal number").format(value)
        if len(m.group(2) or "") > 3 or len(m.group(1).lstrip("+-")) > 7:
            return (
                False,
                None,
                _(
                    "A decimal default has at most 7 digits before the point and 3 after"
                ),
            )
        return (
            True,
            (
                str(decimal.Decimal(value).normalize())
                if "." in value
                else str(int(value))
            ),
            "",
        )
    if property_type == "date":
        try:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                raise ValueError
            datetime.date.fromisoformat(value)
        except ValueError:
            return False, None, _("{} is not a date: use YYYY-MM-DD").format(value)
        return True, value, ""
    if property_type == "datetime":
        try:
            datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return (
                False,
                None,
                _("{} is not a date and time: use YYYY-MM-DD HH:MM:SS").format(value),
            )
        return True, value, ""
    if property_type == "geopoint":
        if not _valid_point(value):
            return (
                False,
                None,
                _(
                    "A geopoint is latitude, longitude, altitude and accuracy separated by spaces"
                ),
            )
        return True, " ".join(value.split()), ""
    if property_type in _GEO_TWIN:
        points = [p.strip() for p in value.split(";") if p.strip()]
        if len(points) < 2 or not all(_valid_point(p) for p in points):
            return (
                False,
                None,
                _("A trace or shape is at least two geopoints separated by semicolons"),
            )
        if property_type == "geoshape" and (
            len(points) < 4 or points[0].split()[:2] != points[-1].split()[:2]
        ):
            return (
                False,
                None,
                _("A shape is at least four geopoints, the last repeating the first"),
            )
        return True, ";".join(" ".join(p.split()) for p in points), ""
    return False, None, _("Unknown property type {}").format(property_type)


def _sql_literal(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def default_clause(property_type, value):
    """The DEFAULT of a property column. A text column takes its default as
    an expression, in parentheses, which MySQL allows from 8.0.13."""
    if value is None:
        return "DEFAULT NULL"
    if property_type in ("integer", "decimal"):
        return "DEFAULT " + value
    if property_type in _GEO_TWIN:
        return "DEFAULT (" + _sql_literal(value) + ")"
    return "DEFAULT " + _sql_literal(value)


def _points_to_wkt(column):
    # JXFormToMySQL's odkPointsToWkt, verbatim: the ODK text -- points of
    # "lat lon alt acc" joined by semicolons, or pipes once stored -- as the
    # coordinate list WKT wants.
    return (
        "REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(" + _quoted(column) + ","
        "'^[[:space:];|]+|[[:space:];|]+$',''),"
        "'([-0-9.]+)[[:space:]]+([-0-9.]+)[[:space:]]+[-0-9.]+[[:space:]]+[-0-9.]+','$1 $2'),"
        "'[[:space:]]*[;|][[:space:]]*',',')"
    )


def geometry_expression(column, closed):
    """JXFormToMySQL's odkGeometryExpression, verbatim: the guarded expression
    a trace's or shape's geometry column is derived from -- NULL for anything
    ST_GeomFromText could not read, the text itself kept beside it."""
    wkt = _points_to_wkt(column)
    shaped = (
        wkt
        + " REGEXP '^[-0-9.]+ [-0-9.]+(,[-0-9.]+ [-0-9.]+)"
        + ("{3,}" if closed else "+")
        + "$'"
    )
    if closed:
        shaped += (
            " AND SUBSTRING_INDEX("
            + wkt
            + ",',',1) = SUBSTRING_INDEX("
            + wkt
            + ",',',-1)"
        )
    body = (
        "ST_GeomFromText(CONCAT('POLYGON((', " + wkt + ", '))'),4326)"
        if closed
        else "ST_GeomFromText(CONCAT('LINESTRING(', " + wkt + ", ')'),4326)"
    )
    return "CASE WHEN " + shaped + " THEN " + body + " ELSE NULL END"


def properties_table(table_name):
    return table_name + "_properties"


def property_columns_ddl(property_name, property_type, default):
    """The column definitions a property adds: one, or two for a trace or a
    shape, whose geometry MySQL derives and nothing ever writes."""
    columns = [
        "{} {} {}".format(
            _quoted(property_name),
            _COLUMN_TYPE[property_type],
            default_clause(property_type, default),
        )
    ]
    if property_type in _GEO_TWIN:
        columns.append(
            "{} geometry GENERATED ALWAYS AS ({}) STORED SRID 4326".format(
                _quoted(property_name + "_geom"),
                geometry_expression(property_name, property_type == "geoshape"),
            )
        )
    return columns


def properties_ddl(
    schema,
    table_name,
    property_name,
    property_type,
    default,
    create_table,
    key_charset,
    key_collation,
):
    """CREATE <table>_properties with its first property, or ADD COLUMN.

    FormShare's own table, outside the RSTools contract: not in create.xml,
    unknown to mergeversions and the exporters, and that boundary is the
    point. rowuuid is both the key and a foreign key to the source row, ON
    DELETE CASCADE, so a property row never outlives its case; it is
    declared with the source column's charset and collation because InnoDB
    refuses a key between strings that differ in either. _lastupdate is there
    because RSTools' audit triggers set it on every update, as on every data
    table, and it doubles as the row's change stamp. The property's DEFAULT
    is what every row, existing or new, starts with.
    """
    props = "{}.{}".format(_quoted(schema), _quoted(properties_table(table_name)))
    columns = property_columns_ddl(property_name, property_type, default)
    if create_table:
        return (
            "CREATE TABLE {} (rowuuid VARCHAR(80) CHARACTER SET {} COLLATE {} NOT NULL, "
            "{}, _lastupdate DATETIME NULL, PRIMARY KEY (rowuuid), "
            "CONSTRAINT {} FOREIGN KEY (rowuuid) "
            "REFERENCES {}.{} (rowuuid) ON DELETE CASCADE) ENGINE=InnoDB"
        ).format(
            props,
            key_charset,
            key_collation,
            ", ".join(columns),
            _quoted("fk_" + properties_table(table_name)),
            _quoted(schema),
            _quoted(table_name),
        )
    return "ALTER TABLE {} {}".format(
        props, ", ".join("ADD COLUMN " + column for column in columns)
    )


def drop_property_ddl(schema, table_name, property_name, property_type):
    props = "{}.{}".format(_quoted(schema), _quoted(properties_table(table_name)))
    drops = []
    if property_type in _GEO_TWIN:
        drops.append("DROP COLUMN " + _quoted(property_name + "_geom"))
    drops.append("DROP COLUMN " + _quoted(property_name))
    return "ALTER TABLE {} {}".format(props, ", ".join(drops))


def creation_trigger_sql(schema, table_name):
    """The AFTER INSERT trigger that gives a new source row its property row,
    at the defaults. One statement, so it loads through the driver; named
    deterministically (fs_cm_<table>_properties) and with its schema, or
    MySQL refuses it (1435) when the session's database is another."""
    name = "fs_cm_{}_properties".format(table_name)
    sql = (
        "CREATE TRIGGER {}.{} AFTER INSERT ON {}.{} FOR EACH ROW "
        "INSERT IGNORE INTO {}.{} (rowuuid) VALUES (NEW.rowuuid)"
    ).format(
        _quoted(schema),
        _quoted(name),
        _quoted(schema),
        _quoted(table_name),
        _quoted(schema),
        _quoted(properties_table(table_name)),
    )
    return name, sql


def backfill_sql(schema, table_name):
    """The rows that exist already get their property row, at the defaults."""
    return "INSERT IGNORE INTO {}.{} (rowuuid) SELECT rowuuid FROM {}.{}".format(
        _quoted(schema),
        _quoted(properties_table(table_name)),
        _quoted(schema),
        _quoted(table_name),
    )


def get_table_properties(request, project_id, form_id, table_name):
    res = (
        request.dbsession.query(TableProperty)
        .filter(TableProperty.project_id == project_id)
        .filter(TableProperty.form_id == form_id)
        .filter(TableProperty.table_name == table_name)
        .order_by(TableProperty.property_cdate)
        .all()
    )
    return map_from_schema(res)


def get_list_source_tables(request, project_id):
    """The tables of this project's forms that a published list draws from:
    {form_id: [table_name, ...]}, each list once.

    A property exists to steer a workflow -- a patient's risk factor set by
    each follow-up -- so it belongs only on a table that a list serves; a
    table no list draws from has no follow-up to feed it or read it. A list
    whose source is another project's form is left to that project.
    """
    result = {}
    for r in (
        request.dbsession.query(PublishedList.source_form, PublishedList.source_table)
        .filter(PublishedList.project_id == project_id)
        .filter(PublishedList.source_project == project_id)
        .distinct()
        .order_by(PublishedList.source_form, PublishedList.source_table)
        .all()
    ):
        result.setdefault(r[0], []).append(r[1])
    return result


def property_is_served(request, project_id, form_id, table_name, property_name):
    """Whether a published list of the table serves the property."""
    return (
        request.dbsession.query(PublishedListColumn.list_id)
        .join(
            PublishedList,
            (PublishedList.project_id == PublishedListColumn.project_id)
            & (PublishedList.list_id == PublishedListColumn.list_id),
        )
        .filter(PublishedList.source_project == project_id)
        .filter(PublishedList.source_form == form_id)
        .filter(PublishedList.source_table == table_name)
        .filter(PublishedListColumn.column_source == "property")
        .filter(PublishedListColumn.column_name == property_name)
        .first()
        is not None
    )


def property_filters_a_list(request, project_id, form_id, table_name, property_name):
    """The id of a published list of the table whose filter reads the
    property, or None. Its SELECT would fail once the property is gone."""
    lists = (
        request.dbsession.query(PublishedList.list_id, PublishedList.filter_rules)
        .filter(PublishedList.source_project == project_id)
        .filter(PublishedList.source_form == form_id)
        .filter(PublishedList.source_table == table_name)
        .all()
    )
    for list_id, rules in lists:
        if property_name in referenced_properties(rules):
            return list_id
    return None


def _form_schema(request, project_id, form_id):
    res = (
        request.dbsession.query(Odkform.form_schema)
        .filter(Odkform.project_id == project_id)
        .filter(Odkform.form_id == form_id)
        .first()
    )
    return res[0] if res else None


def _properties_table_exists(request, schema, table_name):
    return (
        request.dbsession.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = :s AND table_name = :t",
            {"s": schema, "t": properties_table(table_name)},
        ).fetchone()[0]
        > 0
    )


def _install_creation_trigger(request, schema, table_name, install):
    name, sql = creation_trigger_sql(schema, table_name)
    request.dbsession.execute(
        "DROP TRIGGER IF EXISTS {}.{}".format(_quoted(schema), _quoted(name))
    )
    if install:
        request.dbsession.execute(sql)


def regenerate_properties_audit(request, schema, table_name):
    """Audit triggers on <table>_properties, in RSTools' own shape.

    The repository's audit triggers come from createaudittriggers at build
    time and know nothing of a table created later, so a property's history
    would be missing and README decision 3 (history = audit + submissions)
    false. The same utility is re-run scoped to the properties table (-t),
    into a scratch directory so the build's mysql_create_audit.sql is left
    alone; its previous triggers on that table (audit_* and the TLU_ one that
    stamps _lastupdate) are dropped first, because their names are random
    and a re-run would add a second set. Returns (ok, message).
    """
    props = properties_table(table_name)
    for (name,) in request.dbsession.execute(
        "SELECT trigger_name FROM information_schema.triggers "
        "WHERE trigger_schema = :s AND event_object_table = :t "
        "AND (trigger_name LIKE :a OR trigger_name LIKE :l)",
        {"s": schema, "t": props, "a": "audit\\_%", "l": "TLU\\_%"},
    ).fetchall():
        request.dbsession.execute(
            "DROP TRIGGER IF EXISTS {}.{}".format(_quoted(schema), _quoted(name))
        )
    settings = request.registry.settings
    tool = os.path.join(
        settings["odktools.path"],
        *["utilities", "createAuditTriggers", "createaudittriggers"]
    )
    out_dir = tempfile.mkdtemp(prefix="fs_properties_")
    try:
        args = [
            tool,
            "-H " + settings["mysql.host"],
            "-P " + settings["mysql.port"],
            "-u " + settings["mysql.user"],
            "-p " + settings["mysql.password"],
            "-s " + schema,
            "-o " + out_dir,
            "-t " + props,
        ]
        p = Popen(args, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            return False, "createaudittriggers failed: {}".format(
                stderr.decode() or stdout.decode()
            )
        audit_file = os.path.join(out_dir, "mysql_create_audit.sql")
        with open(audit_file) as sql_file:
            proc = Popen(
                ["mysql", "--defaults-file=" + settings["mysql.cnf"], schema],
                stdin=sql_file,
                stdout=PIPE,
                stderr=PIPE,
            )
            output, error = proc.communicate()
        if proc.returncode != 0:
            return False, "Loading the audit triggers failed: {}".format(error.decode())
        return True, ""
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def add_table_property(
    request,
    project_id,
    form_id,
    table_name,
    property_name,
    property_type,
    default,
    desc,
    user,
):
    """Defines a property of a table: a type, a default, a description.

    In this order, because MySQL commits around DDL: the column (and the
    table, the first time), the audit triggers, the property rows of the
    rows that exist -- at the defaults, under the owner's name -- the
    creation trigger, and only then the registry row. Returns (ok, message).
    """
    _ = request.translate
    property_name = str(property_name or "").strip().lower()
    property_type = str(property_type or "").strip().lower()
    if not _PROPERTY_NAME.match(property_name) or property_name in (
        "rowuuid",
        "name",
        "label",
    ):
        return False, _(
            "A property name is lower case, starts with a letter, and uses "
            "letters, digits and underscores"
        )
    if property_type not in _COLUMN_TYPE:
        return False, _("Select the type of the property")
    valid, default, message = validate_property_default(property_type, default, _)
    if not valid:
        return False, message
    schema = _form_schema(request, project_id, form_id)
    if not schema:
        return False, _("The form has no repository")
    existing = get_table_properties(request, project_id, form_id, table_name)
    if any(p["property_name"] == property_name for p in existing):
        return False, _("There is already a property with that name")
    if property_name in {
        c["field_name"]
        for c in get_table_columns(request, project_id, form_id, table_name)
    } or property_name.endswith("_geom"):
        # The served CSV would carry two columns of one name, and a filter
        # naming it could mean either; _geom is the geometry twin's suffix.
        return False, _("A property cannot be named like a column of the table")
    key = request.dbsession.execute(
        "SELECT CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.columns "
        "WHERE table_schema = :s AND table_name = :t AND column_name = 'rowuuid'",
        {"s": schema, "t": table_name},
    ).fetchone()
    if key is None:
        return False, _("The table has no rowuuid column")
    try:
        request.dbsession.execute(
            properties_ddl(
                schema,
                table_name,
                property_name,
                property_type,
                default,
                not _properties_table_exists(request, schema, table_name),
                key[0],
                key[1],
            )
        )
        # Audit first, so the backfill is recorded under the owner who
        # defined the property, like any office edit.
        audited, message = regenerate_properties_audit(request, schema, table_name)
        if not audited:
            return False, message
        request.dbsession.execute("SET @odktools_current_user = :u", {"u": user})
        request.dbsession.execute(backfill_sql(schema, table_name))
        request.dbsession.execute("SET @odktools_current_user = NULL")
        _install_creation_trigger(request, schema, table_name, True)
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while adding property {} to {}.{} of form {} in project {}".format(
                str(e), property_name, schema, table_name, form_id, project_id
            )
        )
        return False, str(e)
    try:
        request.dbsession.add(
            TableProperty(
                project_id=project_id,
                form_id=form_id,
                table_name=table_name,
                property_name=property_name,
                property_type=property_type,
                property_default=default,
                property_desc=(desc or "")[:500] or None,
                property_cdate=datetime.datetime.now(),
            )
        )
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while recording property {} of {}.{}".format(
                str(e), property_name, form_id, table_name
            )
        )
        return False, str(e)


def delete_table_property(request, project_id, form_id, table_name, property_name):
    """Removes a property: refused while a list serves it; otherwise the
    column goes, and with the last property the table and its triggers."""
    _ = request.translate
    if property_is_served(request, project_id, form_id, table_name, property_name):
        return False, _(
            "A published list serves this property. Remove it from the list first."
        )
    filtering = property_filters_a_list(
        request, project_id, form_id, table_name, property_name
    )
    if filtering:
        return False, _(
            'The filter of the published list "{}" reads this property. '
            "Change the filter first."
        ).format(filtering)
    schema = _form_schema(request, project_id, form_id)
    if not schema:
        return False, _("The form has no repository")
    properties = get_table_properties(request, project_id, form_id, table_name)
    this_one = next(
        (p for p in properties if p["property_name"] == property_name), None
    )
    if this_one is None:
        return False, _("The property does not exist")
    remaining = [p for p in properties if p["property_name"] != property_name]
    props = "{}.{}".format(_quoted(schema), _quoted(properties_table(table_name)))
    try:
        if remaining:
            request.dbsession.execute(
                drop_property_ddl(
                    schema, table_name, property_name, this_one["property_type"]
                )
            )
            audited, message = regenerate_properties_audit(request, schema, table_name)
            if not audited:
                return False, message
        else:
            _install_creation_trigger(request, schema, table_name, False)
            request.dbsession.execute("DROP TABLE IF EXISTS {}".format(props))
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while deleting property {} of {}.{}".format(
                str(e), property_name, schema, table_name
            )
        )
        return False, str(e)
    try:
        request.dbsession.query(TableProperty).filter(
            TableProperty.project_id == project_id
        ).filter(TableProperty.form_id == form_id).filter(
            TableProperty.table_name == table_name
        ).filter(
            TableProperty.property_name == property_name
        ).delete()
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        return False, str(e)


def inherit_properties(request, project_id, parent_form, child_form):
    """A new version keeps its parent's property definitions: the table and
    the trigger live in the schema it will own, and the definitions must
    follow. Copies the parent's rows to the child, skipping any it has."""
    existing = {
        (p.table_name, p.property_name)
        for p in request.dbsession.query(
            TableProperty.table_name, TableProperty.property_name
        )
        .filter(TableProperty.project_id == project_id)
        .filter(TableProperty.form_id == child_form)
        .all()
    }
    for p in (
        request.dbsession.query(TableProperty)
        .filter(TableProperty.project_id == project_id)
        .filter(TableProperty.form_id == parent_form)
        .all()
    ):
        if (p.table_name, p.property_name) in existing:
            continue
        request.dbsession.add(
            TableProperty(
                project_id=project_id,
                form_id=child_form,
                table_name=p.table_name,
                property_name=p.property_name,
                property_type=p.property_type,
                property_default=p.property_default,
                property_desc=p.property_desc,
                property_cdate=p.property_cdate,
            )
        )
    request.dbsession.commit()


# ---------------------------------------------------------------------------
# properties.xml: the <table>_properties tables for the device mirror, in
# create.xml's own vocabulary (rstools.md 5.3 and 6.8). Served in the manifest
# beside create.xml (formshare.md 3.10).

# The type each property kind takes in the file, as the library reads it: the
# same shapes the server columns have (PROPERTY_TYPES), spelled the way
# JXFormToMySQL spells a field.
_PROPERTIES_XML_TYPES = {
    "string": ("varchar", "255", "0"),
    "integer": ("int", "9", "0"),
    "decimal": ("decimal", "10", "3"),
    "date": ("date", "0", "0"),
    "datetime": ("datetime", "0", "0"),
    "geopoint": ("varchar", "80", "0"),
    "geotrace": ("text", "0", "0"),
    "geoshape": ("text", "0", "0"),
}


def get_form_properties(request, project_id, form_id):
    """{table_name: [property, ...]} for every table of the form that has
    properties, each list in definition order."""
    result = {}
    for p in (
        request.dbsession.query(TableProperty)
        .filter(TableProperty.project_id == project_id)
        .filter(TableProperty.form_id == form_id)
        .order_by(TableProperty.table_name, TableProperty.property_cdate)
        .all()
    ):
        result.setdefault(p.table_name, []).append(
            {
                "property_name": p.property_name,
                "property_type": p.property_type,
                "property_default": p.property_default,
                "property_desc": p.property_desc,
            }
        )
    return result


def properties_xml(properties_by_table):
    """The properties.xml a device builds <table>_properties from (pure).

    An XMLSchemaStructure like create.xml's, one table per source table that
    has properties, properties="true" on it so the loader knows to give every
    new source row a property row; rowuuid as the key field, one field per
    property with its type and, when it has one, its default; _lastupdate
    listed, never written by the device. Always a complete document: a form
    with no properties serves an empty <tables/>, so the contract is one
    file and not a file that may be missing.
    """
    root = etree.Element("XMLSchemaStructure", version="3.0")
    tables = etree.SubElement(root, "tables")
    for table_name in sorted(properties_by_table):
        table = etree.SubElement(
            tables,
            "table",
            name=properties_table(table_name),
            properties="true",
            desc="Properties of {}".format(table_name),
        )
        etree.SubElement(
            table,
            "field",
            name="rowuuid",
            type="varchar",
            size="80",
            decsize="0",
            key="true",
        )
        for p in properties_by_table[table_name]:
            xml_type, size, decsize = _PROPERTIES_XML_TYPES.get(
                p["property_type"], ("varchar", "255", "0")
            )
            # The property's own type, in create.xml's attribute for it: the
            # column type alone cannot tell a trace from a shape (both text),
            # and the device checks a geopoint, trace or shape as its default
            # is only when odktype says so (rstools.md 15.2).
            field = etree.SubElement(
                table,
                "field",
                name=p["property_name"],
                type=xml_type,
                size=size,
                decsize=decsize,
                odktype=p["property_type"],
            )
            if p.get("property_default") is not None:
                field.set("default", p["property_default"])
            if p.get("property_desc"):
                field.set("desc", p["property_desc"])
        etree.SubElement(
            table, "field", name="_lastupdate", type="datetime", size="0", decsize="0"
        )
    return etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    )


# ---------------------------------------------------------------------------
# lists.xml: the rule behind each list a form attaches, for the device
# (formshare.md 3.10, kotlincollect.md 4). Served beside create.xml.


def lists_xml(definitions):
    """The lists.xml of a consuming form (pure).

    One list element per published list the form is part of, in either
    role: role="feeds" for a list drawn from one of this form's tables --
    what the device runs at the form's finalize to put the rows it produced
    into the SQLite Collect made from the CSV, for every form that attaches
    the file -- and role="reads" or "updates" for a list this form attaches,
    with the field that selects from it (selector) and whether that
    selection is the case link (link), which is what a follow-up's device
    reads to know which case a submission is about. Either way: the list's
    identity, the repository, form and table it draws from, its kind (a row
    list keyed by rowuuid, or a value list with its key), its label column,
    the _active it serves, and the SELECT that generates it with the tables
    spelled symbolically. No column map: a device never reads a CSV back
    (README decision 14). A form in neither role serves an empty document.
    """
    root = etree.Element("XMLLists", version="1.0")
    for d in definitions:
        a_list = etree.SubElement(
            root,
            "list",
            id=d["list_id"],
            file=d["filename"],
            role=d.get("role") or "feeds",
            kind="value" if d.get("key_column") else "row",
            repository=d["repository"],
            form=d["source_form"],
            table=d["source_table"],
            label=d["label_column"],
            active="" if d.get("active") is None else str(int(d["active"])),
        )
        if d.get("key_column"):
            a_list.set("key", d["key_column"])
        if d.get("selector"):
            a_list.set("selector", d["selector"])
            a_list.set("link", "true" if d.get("link") else "false")
        etree.SubElement(a_list, "select").text = d["select"]
    return etree.tostring(
        root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    )
