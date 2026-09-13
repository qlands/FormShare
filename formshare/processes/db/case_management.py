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

from formshare.models import (
    PublishedList,
    PublishedListColumn,
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


def build_list_select(schema, table, label_column, columns, filter_sql=None):
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
    if filter_sql:
        sql = sql + " WHERE " + filter_sql
    sql = sql + " ORDER BY rowuuid"
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
    """Writes the generated rows as the CSV a device downloads."""
    with open(file_name, "w", newline="") as outfile:
        writer = csv.writer(outfile)
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
        request.dbsession.flush()
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
        request.dbsession.flush()
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
        request.dbsession.flush()
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
        request.dbsession.flush()
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
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        log.error(
            "Error {} while generating list {} of project {}".format(
                str(e), list_data["list_id"], list_data["project_id"]
            )
        )
        return False, str(e)
