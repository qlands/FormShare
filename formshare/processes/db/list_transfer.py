"""Published lists as a document, to export and to import, in JSON or YAML.

A training manual, or a project set up again, needs the lists of a workflow
without an owner typing each one into the wizard, which is where the mistakes
come in. The document carries what the wizard and the edit page set -- the
file name, the source form and table, the label, the key, the rows to serve,
the served columns and the filter -- and the properties of each source table, which the
follow-up rules set. A list names its source by form_id, never by schema, so
an import resolves it in the importing project: the same form uploaded there
has a schema of its own, and the list follows it.

An import checks the whole document before it writes anything:

- the form exists in the project and has its repository;
- the table is one of that form's data tables;
- every column a list names is a column of that table;
- a property a list serves exists on the table or is defined in the document,
  and a property the document defines is valid and agrees with the table's.

Then the properties the tables lack are created, first, because each is DDL
that MySQL commits on its own, and then the lists, each with its columns.
"""

import datetime
import json
import re

import yaml

from formshare.processes.db.case_management import (
    PROPERTY_TYPES,
    add_published_list,
    add_table_property,
    delete_published_list,
    get_form_data_tables,
    get_list_columns,
    get_list_source_tables,
    get_project_published_lists,
    get_table_columns,
    get_table_properties,
    set_list_columns,
    valid_list_filename,
    validate_property_default,
)
from formshare.processes.db.form import get_form_data
from formshare.processes.list_filter import FilterError, compile_filter, filter_fields

__all__ = [
    "DOCUMENT",
    "VERSION",
    "MAX_BYTES",
    "list_document",
    "dump_document",
    "load_document",
    "import_lists",
]

DOCUMENT = "formshare-published-lists"
VERSION = 1
# A document is a few kilobytes; a file anywhere near this is not one.
MAX_BYTES = 1024 * 1024

# The wizard lower-cases a list's code, which is a path segment under
# /caselists, and keeps three words for its own segments there.
_CODE = re.compile(r"^[a-z0-9_-]{1,120}$")
_RESERVED_CODES = ("add", "tablesof", "fieldsof")
# A served name becomes a CSV header and a SQL alias (build_list_select).
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# add_table_property's own rules, checked here as well so that nothing is
# written before the whole document is known to be good.
_PROPERTY_NAME = re.compile(r"^[a-z][a-z0-9_]{0,60}$")
_PROPERTY_TYPES = [a_type[0] for a_type in PROPERTY_TYPES]
_LIST_KEYS = (
    "code",
    "file_name",
    "form_id",
    "table",
    "label_column",
    "key_column",
    "rows",
    "columns",
    "filter",
)


def list_document(request, project_id, list_ids=None):
    """The document of a project's lists: all of them, or those in list_ids.

    The properties of each source table travel with it, once, whether a list
    serves them or not: a rule of the follow-up may set a property that no
    list serves.
    """
    lists = []
    properties = []
    tables = []
    # In the order they were created, and by code within a second, which is
    # as finely as list_createdate tells them apart: an import creates several
    # in one.
    project_lists = sorted(
        get_project_published_lists(request, project_id),
        key=lambda a_list: (
            a_list.get("list_createdate") or datetime.datetime.min,
            a_list["list_id"],
        ),
    )
    for a_list in project_lists:
        if list_ids is not None and a_list["list_id"] not in list_ids:
            continue
        columns = []
        for a_column in get_list_columns(request, project_id, a_list["list_id"]):
            if (a_column.get("column_source") or "table") == "property":
                item = {"property": a_column["column_name"]}
            else:
                item = {"column": a_column["column_name"]}
            if a_column.get("column_as"):
                item["served_as"] = a_column["column_as"]
            columns.append(item)
        entry = {
            "code": a_list["list_id"],
            "file_name": a_list["list_filename"],
            "form_id": a_list["source_form"],
            "table": a_list["source_table"],
            "label_column": a_list["label_column"],
            "key_column": a_list.get("list_key_column") or None,
            "rows": "inactive" if a_list.get("list_active") == 0 else "active",
            "columns": columns,
        }
        rules = _stored_rules(a_list.get("filter_rules"))
        if rules:
            entry["filter"] = rules
        lists.append(entry)
        source = (
            a_list["source_project"],
            a_list["source_form"],
            a_list["source_table"],
        )
        if source not in tables:
            tables.append(source)
            for a_property in get_table_properties(request, *source):
                properties.append(
                    {
                        "form_id": a_list["source_form"],
                        "table": a_list["source_table"],
                        "name": a_property["property_name"],
                        "type": a_property["property_type"],
                        "default": a_property.get("property_default"),
                        "description": a_property.get("property_desc"),
                    }
                )
    return {
        "document": DOCUMENT,
        "version": VERSION,
        "properties": properties,
        "lists": lists,
    }


def _stored_rules(text):
    """A list's stored filter as the rule set it is, or None.

    filter_rules is the stored truth of a filter, QueryBuilder's JSON; its
    compiled filter_sql names the source's columns and is compiled again
    against the importing table's.
    """
    if not text:
        return None
    try:
        rules = json.loads(text)
    except ValueError:
        return None
    return rules if isinstance(rules, dict) else None


def dump_document(document, file_format):
    """The document as the text of a JSON or a YAML file."""
    if file_format == "yaml":
        return yaml.safe_dump(
            document, sort_keys=False, allow_unicode=True, default_flow_style=False
        )
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def load_document(content, translate=None):
    """The document in the content of a JSON or YAML file: (document, error).

    JSON is tried first and YAML second; safe_load builds no objects, only
    mappings, lists and scalars.
    """
    _ = translate or (lambda s: s)
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return None, _("The file is not UTF-8 text")
    try:
        document = json.loads(content)
    except ValueError:
        try:
            document = yaml.safe_load(content)
        except yaml.YAMLError as e:
            return None, _("The file is neither JSON nor YAML: {}").format(
                str(e).split("\n")[0]
            )
    if not isinstance(document, dict) or document.get("document") != DOCUMENT:
        return None, _("The file is not a list export of FormShare")
    if document.get("version") != VERSION:
        return None, _(
            "The file is version {} of the export, and this FormShare reads version {}"
        ).format(document.get("version"), VERSION)
    return document, ""


def _text(value):
    """A scalar of the document as text: (text, ok).

    YAML reads 2026-03-01 as a date and 12 as a number; both are text here.
    A mapping, a list, or a yes or no that YAML turned into a boolean is not
    a scalar of this document, and gives ok False.
    """
    if value is None:
        return None, True
    if isinstance(value, (bool, dict, list)):
        return None, False
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S"), True
    return str(value).strip(), True


def _source(request, project_id, form_id, table, sources, _):
    """(columns, properties, error) of a form's table in the project, read
    once per table: the column names, the existing properties by name with
    their type, or the reason the table cannot be a source."""
    key = (form_id, table)
    if key not in sources:
        form_data = get_form_data(request, project_id, form_id) if form_id else None
        if form_data is None:
            sources[key] = (
                None,
                None,
                _('The form "{}" does not exist in this project').format(form_id),
            )
        elif not form_data.get("form_schema"):
            sources[key] = (
                None,
                None,
                _(
                    'The form "{}" has no repository yet. Create it before '
                    "importing its lists"
                ).format(form_id),
            )
        elif table not in [
            a_table["table_name"]
            for a_table in get_form_data_tables(request, project_id, form_id)
        ]:
            sources[key] = (
                None,
                None,
                _('The form "{}" has no table "{}"').format(form_id, table),
            )
        else:
            sources[key] = (
                {
                    a_column["field_name"]
                    for a_column in get_table_columns(
                        request, project_id, form_id, table
                    )
                },
                {
                    a_property["property_name"]: a_property["property_type"]
                    for a_property in get_table_properties(
                        request, project_id, form_id, table
                    )
                },
                None,
            )
    return sources[key]


def _check_properties(request, project_id, document, list_sources, sources, errors, _):
    """The properties to create, and those the document defines, by table.

    A property belongs on a table a list draws from, a list of the document
    or one the project has, as on the Properties page. A property the table
    has already is kept as it is when the document gives it the same type,
    and refused when it gives another.
    """
    to_create = []
    defined = {}
    entries = document.get("properties") or []
    if not isinstance(entries, list):
        errors.append(_("The properties of the file are not a list"))
        return to_create, defined
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            errors.append(_("Property {} is not a mapping").format(index))
            continue
        form_id, ok_form = _text(entry.get("form_id"))
        table, ok_table = _text(entry.get("table"))
        name, ok_name = _text(entry.get("name"))
        property_type, ok_type = _text(entry.get("type"))
        default, ok_default = _text(entry.get("default"))
        description, ok_description = _text(entry.get("description"))
        if not (form_id and table and name and property_type):
            errors.append(
                _("Property {} needs a form_id, a table, a name and a type").format(
                    index
                )
            )
            continue
        where = '{} "{}" ({}, {})'.format(_("Property"), name, form_id, table)
        if (form_id, table) not in list_sources:
            errors.append("{}: {}".format(where, _("no list draws from its table")))
            continue
        columns, existing, error = _source(
            request, project_id, form_id, table, sources, _
        )
        if error:
            errors.append("{}: {}".format(where, error))
            continue
        problems = []
        if not _PROPERTY_NAME.match(name) or name in ("rowuuid", "name", "label"):
            problems.append(
                _(
                    "a property name is lower case, starts with a letter, and "
                    "uses letters, digits and underscores"
                )
            )
        elif name in columns or name.endswith("_geom"):
            problems.append(_("the table has a column of that name"))
        if property_type not in _PROPERTY_TYPES:
            problems.append(
                _("its type must be one of {}").format(", ".join(_PROPERTY_TYPES))
            )
        if not (ok_default and ok_description):
            problems.append(_("write its default and its description in quotes"))
        if problems:
            errors.append("{}: {}".format(where, "; ".join(problems)))
            continue
        valid, default, message = validate_property_default(
            property_type, default or "", _
        )
        if not valid:
            errors.append("{}: {}".format(where, message))
            continue
        key = (form_id, table, name)
        if key in defined:
            if defined[key] != (property_type, default):
                errors.append(
                    "{}: {}".format(where, _("the file defines it twice, differently"))
                )
            continue
        defined[key] = (property_type, default)
        if name in existing:
            if existing[name] != property_type:
                errors.append(
                    "{}: {}".format(
                        where,
                        _("the table has it already, as {}").format(existing[name]),
                    )
                )
            continue
        to_create.append(
            (form_id, table, name, property_type, default, description or "")
        )
    return to_create, defined


def _check_lists(request, project_id, document, sources, defined, errors, warnings, _):
    """The lists to add, each with its columns, ready for add_published_list."""
    to_add = []
    entries = document.get("lists")
    if not isinstance(entries, list) or not entries:
        errors.append(_("The file has no lists"))
        return to_add
    taken_codes = set()
    taken_files = set()
    for a_list in get_project_published_lists(request, project_id):
        taken_codes.add(a_list["list_id"])
        taken_files.add(a_list["list_filename"])
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            errors.append(_("List {} is not a mapping").format(index))
            continue
        code = (_text(entry.get("code"))[0] or "").lower()
        file_name = _text(entry.get("file_name"))[0] or ""
        form_id = _text(entry.get("form_id"))[0] or ""
        table = _text(entry.get("table"))[0] or ""
        label_column = _text(entry.get("label_column"))[0] or ""
        key_column = _text(entry.get("key_column"))[0] or None
        rows = _text(entry.get("rows"))[0] or "active"
        where = '{} "{}"'.format(_("List"), code or index)
        problems = []
        if not _CODE.match(code) or code in _RESERVED_CODES:
            problems.append(
                _("its code is lower case letters, digits, hyphens and underscores")
            )
        elif code in taken_codes:
            problems.append(
                _("its code is in use, in the project or earlier in the file")
            )
        if not valid_list_filename(file_name) or not file_name.endswith(".csv"):
            problems.append(
                _(
                    "its file name must be lower case, start with a letter, and "
                    "end in .csv"
                )
            )
        elif file_name in taken_files:
            problems.append(
                _(
                    'its file "{}" is in use, in the project or earlier in the file'
                ).format(file_name)
            )
        taken_codes.add(code)
        taken_files.add(file_name)
        if rows not in ("active", "inactive"):
            problems.append(_("its rows are active or inactive"))
        unknown = sorted(str(a_key) for a_key in entry if a_key not in _LIST_KEYS)
        if unknown:
            warnings.append(
                "{}: {}".format(where, _("not imported: {}").format(", ".join(unknown)))
            )
        columns, properties, error = _source(
            request, project_id, form_id, table, sources, _
        )
        if error:
            problems.append(error)
            errors.append("{}: {}".format(where, "; ".join(problems)))
            continue
        if label_column not in columns:
            problems.append(
                _('the table has no column "{}" to label with').format(label_column)
            )
        if key_column is not None and key_column not in columns:
            problems.append(
                _('the table has no column "{}" to key with').format(key_column)
            )
        served = []
        served_names = {"name", "label"}
        for position, a_column in enumerate(entry.get("columns") or [], start=1):
            if not isinstance(a_column, dict) or (
                ("column" in a_column) == ("property" in a_column)
            ):
                problems.append(
                    _("its column {} names one column or one property").format(position)
                )
                continue
            if "property" in a_column:
                name = _text(a_column.get("property"))[0] or ""
                source = "property"
                if name not in properties and (form_id, table, name) not in defined:
                    problems.append(
                        _(
                            'it serves the property "{}", which the table does '
                            "not have and the file does not define"
                        ).format(name)
                    )
            else:
                name = _text(a_column.get("column"))[0] or ""
                source = "table"
                if name not in columns:
                    problems.append(_('the table has no column "{}"').format(name))
            served_as = _text(a_column.get("served_as"))[0] or None
            if served_as is not None and not _IDENTIFIER.match(served_as):
                problems.append(
                    _(
                        '"{}" cannot be a served name: use letters, digits and '
                        "underscores"
                    ).format(served_as)
                )
            alias = served_as or name
            if alias in served_names:
                problems.append(
                    _(
                        'two served columns are called "{}" (name and label are '
                        "taken)"
                    ).format(alias)
                )
            served_names.add(alias)
            served.append((name, served_as, source))
        if len({a_column[0] for a_column in served}) != len(served):
            problems.append(_("it serves a column twice"))
        # The filter is compiled against the importing table, whose fields a
        # property of the document is about to join.
        filter_rules = None
        filter_sql = None
        rules = entry.get("filter")
        if rules not in (None, "", {}):
            if not isinstance(rules, dict):
                problems.append(_("its filter is not a rule set"))
            else:
                pending = [
                    {"property_name": key[2], "property_type": value[0]}
                    for key, value in defined.items()
                    if key[:2] == (form_id, table) and key[2] not in properties
                ]
                fields = filter_fields(
                    get_table_columns(request, project_id, form_id, table),
                    get_table_properties(request, project_id, form_id, table) + pending,
                )
                try:
                    filter_sql = compile_filter(rules, fields)
                except FilterError as e:
                    problems.append(_("its filter: {}").format(str(e)))
                if filter_sql:
                    filter_rules = json.dumps(rules)
        if problems:
            errors.append("{}: {}".format(where, "; ".join(problems)))
            continue
        to_add.append(
            (
                {
                    "list_id": code,
                    "list_filename": file_name,
                    "list_format": "csv",
                    "source_project": project_id,
                    "source_form": form_id,
                    "source_table": table,
                    "label_column": label_column,
                    "list_active": 0 if rows == "inactive" else 1,
                    "list_key_column": key_column,
                    "filter_rules": filter_rules,
                    "filter_sql": filter_sql,
                },
                served,
            )
        )
    return to_add


def import_lists(request, project_id, document, user):
    """Imports the lists and properties of a document into a project.

    Returns (done, errors, warnings). done holds what was written -- "lists",
    "properties" created, and "kept", the properties the tables had already.
    When the document has errors, nothing is written. An error while writing,
    which the checks should have made impossible, stops the import there, and
    done says how far it got.
    """
    _ = request.translate
    errors = []
    warnings = []
    sources = {}
    done = {"lists": [], "properties": [], "kept": []}
    list_sources = {
        (form_id, table)
        for form_id, tables in get_list_source_tables(request, project_id).items()
        for table in tables
    }
    for entry in document.get("lists") or []:
        if isinstance(entry, dict):
            list_sources.add(
                (_text(entry.get("form_id"))[0], _text(entry.get("table"))[0])
            )
    to_create, defined = _check_properties(
        request, project_id, document, list_sources, sources, errors, _
    )
    to_add = _check_lists(
        request, project_id, document, sources, defined, errors, warnings, _
    )
    if errors:
        return done, errors, warnings
    created = {(a[0], a[1], a[2]) for a in to_create}
    done["kept"] = sorted({key[2] for key in defined if key not in created})
    for form_id, table, name, property_type, default, description in to_create:
        added, message = add_table_property(
            request,
            project_id,
            form_id,
            table,
            name,
            property_type,
            default or "",
            description,
            user,
        )
        if not added:
            errors.append(
                '{} "{}" ({}, {}): {}'.format(
                    _("Property"), name, form_id, table, message
                )
            )
            return done, errors, warnings
        done["properties"].append(name)
    for list_data, served in to_add:
        added, message = add_published_list(request, project_id, list_data)
        if added:
            added, message = set_list_columns(
                request, project_id, list_data["list_id"], served
            )
            if not added:
                delete_published_list(request, project_id, list_data["list_id"])
        if not added:
            errors.append(
                '{} "{}": {}'.format(_("List"), list_data["list_id"], message)
            )
            return done, errors, warnings
        done["lists"].append(list_data["list_id"])
    return done, errors, warnings
