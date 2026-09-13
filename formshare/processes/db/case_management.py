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
import logging
import re
import uuid

from lxml import etree

from formshare.models import (
    PublishedList,
    PublishedListColumn,
    ListConsumer,
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
    "generate_published_list_file",
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
    schema, table, label_column, columns, filter_sql=None, limit=None, active=1
):
    """The SELECT that generates a published list.

    :param schema: the source repository schema
    :param table: maintable or a repeat table
    :param label_column: the column served as ``label``
    :param columns: [(column_name, column_as), ...] extra columns, in order
    :param filter_sql: optional membership WHERE fragment, UI-built
    :return: (sql, headers) -- headers in CSV order

    ``name`` is always rowuuid and always first; ``label`` always second.
    """
    select_parts = [
        "rowuuid AS name",
        "{} AS label".format(_quoted(label_column)),
    ]
    headers = ["name", "label"]
    for column_name, column_as in columns:
        alias = column_as or column_name
        if alias in headers:
            # name and label are taken; a duplicate alias would shift the CSV.
            raise ValueError("Duplicated column: {}".format(alias))
        select_parts.append("{} AS {}".format(_quoted(column_name), _quoted(alias)))
        headers.append(alias)
    sql = "SELECT {} FROM {}.{}".format(
        ",".join(select_parts), _quoted(schema), _quoted(table)
    )
    # _active decides which rows the list carries. Every data table has it
    # (default 1), so a list serves active rows unless it was defined for the
    # inactive ones -- which is how one follow-up sees active cases while
    # another list sees the deactivated ones. active=None leaves it out
    # entirely, for the rare list that wants both.
    where = []
    if active is not None:
        where.append("_active = {}".format(int(active)))
    if filter_sql:
        where.append(filter_sql)
    if where:
        sql = sql + " WHERE " + " AND ".join(where)
    sql = sql + " ORDER BY rowuuid"
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
        if a_date is not None and a_date > lastgen:
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


def get_project_published_lists(request, project_id):
    res = (
        request.dbsession.query(PublishedList)
        .filter(PublishedList.project_id == project_id)
        .order_by(PublishedList.list_createdate)
        .all()
    )
    return map_from_schema(res)


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
        (a_column["column_name"], a_column["column_as"])
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
    most one.
    """
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
        result.append(
            {
                "selector_field": consumer["selector_field"],
                "source_schema": res[0],
                "source_table": a_list["source_table"],
                "is_link": int(consumer["consumer_is_link"] or 0) == 1,
                "list_active": int(a_list.get("list_active", 1) or 0),
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


def apply_link_attributes(root, sources, key_types):
    """Wires a form's list consumers into its create.xml tree (pure).

    For every consumer: retype the selector to the source's rowuuid and add a
    foreign key to ``<source>.<table>(rowuuid)`` ON DELETE RESTRICT. For the
    one consumer that is the case link *and* serves active rows, also set the
    maintable attributes RSTools turns into a membership trigger -- it checks
    the selector exists in the source with ``_active = 1`` and refuses null.

    The active-rows condition matters: RSTools hardcodes ``_active = 1`` in
    that trigger, so a case link over an *inactive*-serving list would have
    every selection rejected. Such a link keeps the foreign key (existence)
    and skips the trigger until RSTools can take the active value as an
    argument (rstools.md).

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
        key = key_types.get(ref)
        if key is None:
            return False, "No key type for {}".format(ref)
        key_type, key_size = key
        field = root.find(".//field[@name='" + a_source["selector_field"] + "']")
        if field is None:
            return False, "The selector field {} was not found in create.xml".format(
                a_source["selector_field"]
            )
        field.set("type", key_type)
        field.set("size", str(key_size))
        field.set("rtable", ref)
        field.set("rfield", "rowuuid")
        field.set("rname", "fk_" + str(uuid.uuid4()).replace("-", "_"))
        field.set("rlookup", "false")
        field.set("on_delete", "RESTRICT")
        if a_source["is_link"] and int(a_source.get("list_active", 1)) == 1:
            table.set("case_followup", "true")
            table.set("creator_table", ref)
            table.set("creator_field", "rowuuid")
            table.set("selector_field", a_source["selector_field"])
            table.set("block_trigger", "T" + str(uuid.uuid4()).replace("-", "_"))
    return True, ""
