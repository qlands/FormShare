import logging
from formshare.processes.logging.loggerclass import SecretLogger
import os
import re
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from sqlalchemy.orm.session import Session
from formshare.models import DictTable, DictField, map_from_schema, map_to_schema
from formshare.processes.db.form import get_form_xml_create_file
from lxml import etree
import traceback
from sqlalchemy.exc import IntegrityError

__all__ = [
    "update_dictionary_tables",
    "get_dictionary_fields",
    "get_dictionary_table_desc",
    "get_dictionary_tables",
    "update_dictionary_table_desc",
    "update_dictionary_field_desc",
    "update_dictionary_field_sensitive",
    "is_file_a_lookup",
    "get_name_and_label_from_file",
    "update_lookup_from_csv",
    "get_references_from_file",
    "get_filter_columns_from_file",
    "get_lookup_merge_fields",
    "get_merge_columns",
    "get_identity_join",
    "merge_file_into_lookup",
    "update_insert_xml_from_lookup",
    "sql_column_type",
    "find_source_column",
    "fix_field_name",
    "bindable_value",
    "xml_attribute",
    "get_primary_keys",
    "get_lookup_relation_fields",
]

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


def fix_field_name(name):
    """
    The column name RSTools makes of a CSV header or a GeoJSON property.

    The authority is fixColumnName followed by fixField in
    JXFormToMysql/main.cpp: lowercased and trimmed, a colon or a dash turned
    into an underscore, then anything that is not a letter, a digit or an
    underscore dropped. Matching the same way is what lets a header written
    "Sub-Location" find the lookup column called sub_location.
    :param name: A column of a CSV file or a property of a GeoJSON feature
    :return: The name the column has in the lookup table
    """
    name = str(name).strip().lower().replace(":", "_").replace("-", "_")
    return re.sub(r"[^a-z0-9_]", "", name)


def find_source_column(lookup_column, available_columns):
    """
    The column of a replaced file that feeds one column of its lookup table
    :param lookup_column: Name of the column in the lookup table
    :param available_columns: The columns the file carries
    :return: The name of the column in the file, or None if it has none
    """
    for a_column in available_columns:
        if a_column == lookup_column:
            return a_column
    for a_column in available_columns:
        if fix_field_name(a_column) == lookup_column:
            return a_column
    return None


def sql_column_type(a_field):
    """
    The MySQL declaration of a lookup column, as RSTools writes it
    :param a_field: A field as returned by get_dictionary_fields
    :return: The type as it goes in a CREATE TABLE
    """
    field_type = a_field["field_type"]
    if field_type == "varchar" or field_type == "int":
        return "{}({})".format(field_type, a_field["field_size"])
    if field_type == "decimal":
        return "{}({},{})".format(
            field_type, a_field["field_size"], a_field["field_decsize"]
        )
    return field_type


def bindable_value(value):
    """
    A value read out of pandas or of JSON as something the driver can bind
    :param value: The value as the file gave it
    :return: The same value as a plain Python one
    """
    if isinstance(value, (dict, list)):
        # A nested JSON value has no column of its own to go in. RSTools stores
        # it as empty rather than as its text, so this does the same.
        return ""
    if hasattr(value, "item"):
        return value.item()
    return value


def xml_attribute(value):
    """
    A value read from a lookup table as it goes into the insert XML file
    :param value: The value as MySQL returned it
    :return: The value as a string, empty when there is none
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def get_lookup_merge_fields(request, project_id, form_id, rel_table, code_column):
    """
    The fields of a lookup table that a replaced file is allowed to write.

    Three kinds are left out. The surrogate key, which MySQL assigns and which
    exists precisely so that the code does not have to be unique. rowuuid,
    which a trigger mints. And any generated column: a GeoJSON lookup derives
    its geometry from geometry_json, and MySQL raises 3105 if anything gives
    that column a value.

    :param request: Pyramid request object
    :param project_id: Project ID
    :param form_id: Form ID
    :param rel_table: Lookup table
    :param code_column: The column holding the code of a choice
    :return: Array of dict fields
    """
    fields = []
    for a_field in get_dictionary_fields(request, project_id, form_id, rel_table):
        if a_field["field_name"] == "rowuuid":
            continue
        if a_field.get("field_generatedas"):
            continue
        if a_field.get("field_autoincrement") == 1:
            continue
        if a_field["field_key"] == 1 and a_field["field_name"] != code_column:
            continue
        fields.append(a_field)
    return fields


def get_filter_columns_from_file(request, project_id, form_id, file_name):
    """
    The lookup columns that identify a choice, beyond its code.

    Since schema format 3.0 a lookup is keyed by a surrogate and the index on
    its code is not unique, so the code alone no longer names a row: "v001"
    under one sub location and "v001" under another are two choices. What tells
    them apart is the choice_filter, which RSTools records on the referencing
    field as rfilter, in "lookupColumn:dataColumn" pairs separated by commas.
    Only the lookup side of each pair matters here.

    A list whose codes do not repeat has no filter and no extra columns, and
    the code names the row on its own.

    :param request: Pyramid request object
    :param project_id: Project ID
    :param form_id: Form ID
    :param file_name: CSV or GeoJSON file
    :return: Array of column names, empty when the code names the choice
    """
    res = (
        request.dbsession.query(DictField.field_rfilter)
        .filter(DictField.project_id == project_id)
        .filter(DictField.form_id == form_id)
        .filter(DictField.field_externalfilename == file_name)
        .filter(DictField.field_rlookup == 1)
        .first()
    )
    if res is None:
        # Check if the file is linked to a multi_select
        res = (
            request.dbsession.query(DictField.table_name, DictField.field_name)
            .filter(DictField.project_id == project_id)
            .filter(DictField.form_id == form_id)
            .filter(DictField.field_externalfilename == file_name)
            .filter(DictField.field_odktype == "select all that apply")
            .first()
        )
        if res is not None:
            res = (
                request.dbsession.query(DictField.field_rfilter)
                .filter(DictField.project_id == project_id)
                .filter(DictField.form_id == form_id)
                .filter(
                    DictField.table_name
                    == "{}_msel_{}".format(res.table_name, res.field_name)
                )
                .filter(DictField.field_rlookup == 1)
                .first()
            )
    if res is None or not res.field_rfilter:
        return []
    return [a_pair.split(":")[0] for a_pair in res.field_rfilter.split(",")]


def get_identity_join(identity):
    """
    The condition that says a row of the file and a row of the lookup are the
    same choice.

    "<=>" rather than "=" so that a NULL matches a NULL, which is what a column
    no file has ever filled looks like on both sides.

    :param identity: The columns that name a choice
    :return: The condition, with the lookup as TA and the file as TB
    """
    return " AND ".join("TA.{0} <=> TB.{0}".format(a_column) for a_column in identity)


def get_merge_columns(
    request, project_id, form_id, rel_table, rel_field, identity, file_columns, sources
):
    """
    Work out which column of a replaced file feeds which column of its lookup.

    Every column of the lookup is carried, not only the code and the
    description: the columns a choice_filter names are what tell two choices
    sharing a code apart, and a row inserted without them cannot be chosen in a
    submission or resolved in an export.

    :param request: Pyramid request object
    :param project_id: Project ID
    :param form_id: Form ID
    :param rel_table: Lookup table
    :param rel_field: The column holding the code of a choice
    :param identity: The columns that name a choice
    :param file_columns: The columns the file carries
    :param sources: Mapping of lookup column to file column, already holding
                    the ones the dictionary names rather than the file
    :return: (fields, error message). fields is None when there is a message
    """
    fields = []
    carried = []
    for a_field in get_lookup_merge_fields(
        request, project_id, form_id, rel_table, rel_field
    ):
        field_name = a_field["field_name"]
        if field_name not in sources:
            source = find_source_column(field_name, file_columns)
            if source is None:
                if a_field.get("field_notnull") == 1:
                    # Left out, a row would reach a column that has no default
                    # and cannot have one, and MySQL would discard the row and
                    # report a warning rather than an error.
                    return None, (
                        "The file does not have the column '{}', which every "
                        "option has to have".format(field_name)
                    )
                # A column the file no longer carries is left as it stands
                # rather than overwritten with nothing. Unless it names the
                # choice, in which case there is nothing safe to do but stop.
                continue
            sources[field_name] = source
        fields.append(a_field)
        carried.append(field_name)
    for a_column in identity:
        if a_column not in carried:
            return None, (
                "The file does not have the column '{}', which tells its "
                "repeated options apart".format(a_column)
            )
    return fields, ""


def merge_file_into_lookup(
    session, user_id, form_schema, rel_table, columns, identity, rows
):
    """
    Put the rows of a replaced CSV or GeoJSON into its lookup table.

    Keyed on identity throughout. The code alone stopped naming a row when 3.0
    made the key of a lookup a surrogate and left the index on its code
    without UNIQUE, so joining on the code would carry one option's values onto
    another option's row and INSERT IGNORE would append the whole file again.

    A choice the file no longer carries stays where it is. Submissions may
    already reference it, and since 3.0 the referential integrity guard raises
    1451 for the whole delete rather than skipping the rows that are in use.

    :param session: An open SQLAlchemy session
    :param user_id: The user doing the upload, for the audit triggers
    :param form_schema: Schema of the repository
    :param rel_table: Lookup table
    :param columns: The fields of the lookup this file may write
    :param identity: The columns that name a choice
    :param rows: One dict per row of the file, keyed by lookup column
    """
    uid = str(uuid.uuid4())
    uid = "TMP_" + uid.replace("-", "_")
    column_names = [a_field["field_name"] for a_field in columns]
    session.execute(
        "CREATE TABLE {}.{} ({})".format(
            form_schema,
            uid,
            ",".join(
                "{} {}".format(a_field["field_name"], sql_column_type(a_field))
                for a_field in columns
            ),
        )
    )
    try:
        session.execute(
            "CREATE INDEX code_index ON {}.{} ({})".format(
                form_schema, uid, identity[0]
            )
        )
        insert = text(
            "INSERT INTO {}.{} ({}) VALUES ({})".format(
                form_schema,
                uid,
                ",".join(column_names),
                ",".join(":" + a_column for a_column in column_names),
            )
        )
        for a_row in rows:
            session.execute(insert, a_row)

        session.execute("SET @odktools_current_user = '" + user_id + "'")
        join = get_identity_join(identity)

        # Update the columns that do not name the choice, on the rows the file
        # and the lookup agree are the same choice.
        updatable = [a_column for a_column in column_names if a_column not in identity]
        if updatable:
            session.execute(
                "UPDATE {}.{} TA, {}.{} TB SET {} WHERE {}".format(
                    form_schema,
                    rel_table,
                    form_schema,
                    uid,
                    ",".join(
                        "TA.{0} = TB.{0}".format(a_column) for a_column in updatable
                    ),
                    join,
                )
            )

        # Insert the choices the lookup does not have yet, with every column
        # the file gives them. Not INSERT IGNORE: there is no unique index left
        # for it to skip anything on, and it is what turned a row MySQL refused
        # into a silent success.
        session.execute(
            "INSERT INTO {}.{} ({}) SELECT {} FROM {}.{} TB"
            " WHERE NOT EXISTS (SELECT 1 FROM {}.{} TA WHERE {})".format(
                form_schema,
                rel_table,
                ",".join(column_names),
                ",".join("TB." + a_column for a_column in column_names),
                form_schema,
                uid,
                form_schema,
                rel_table,
                join,
            )
        )
    except Exception:
        # Rolled back here rather than by the caller, because the DROP below is
        # DDL and MySQL commits the open transaction before running it. Left to
        # the caller, an update that got as far as the UPDATE and then failed on
        # the INSERT would be committed on the way out.
        session.rollback()
        raise
    finally:
        try:
            session.execute("DROP TABLE {}.{}".format(form_schema, uid))
        except Exception as e:
            log.error(
                "Unable to drop the temporary table {}.{}. Error: {}".format(
                    form_schema, uid, str(e)
                )
            )


def update_insert_xml_from_lookup(
    session, form_insert_file, form_schema, rel_table, columns, identity, desc_column
):
    """
    Bring the insert XML file back in step with the lookup table.

    The file is what a repository is seeded from when it is built again, so a
    choice that only ever reached the table would come back missing. A value is
    matched the way the merge matches a row - on the code and on every column
    the choice_filter names - and carries every column of the lookup, which is
    what RSTools writes into it: the description under "description", and each
    remaining column, geometry_json included, under its own name.

    The merge is already committed by the time this runs, because creating and
    dropping the temporary table it uses is DDL and MySQL commits around it. So
    a failure here leaves the file a step behind the table rather than undoing
    anything, and the next upload that succeeds puts it right.

    :param session: An open SQLAlchemy session
    :param form_insert_file: Path of the insert XML file
    :param form_schema: Schema of the repository
    :param rel_table: Lookup table
    :param columns: The fields of the lookup this file may write
    :param identity: The columns that name a choice
    :param desc_column: The column holding the description of a choice
    """
    column_names = [a_field["field_name"] for a_field in columns]
    lookup_rows = session.execute(
        "SELECT {} FROM {}.{}".format(",".join(column_names), form_schema, rel_table)
    ).fetchall()

    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(form_insert_file, parser)

    tables = tree.xpath('//table[@name="{}"]'.format(rel_table))
    for a_table in tables:
        curren_values = a_table.findall(".//value")
        for a_lookup_row in lookup_rows:
            values = dict(zip(column_names, a_lookup_row))
            attributes = {"code": xml_attribute(values[identity[0]])}
            for a_column in identity[1:]:
                attributes[a_column] = xml_attribute(values[a_column])
            others = {}
            for a_column in column_names:
                if a_column in identity:
                    continue
                if a_column == desc_column:
                    others["description"] = xml_attribute(values[a_column])
                else:
                    others[a_column] = xml_attribute(values[a_column])
            new_value_found = False
            for a_current_value in curren_values:
                matches = True
                for an_attribute, a_value in attributes.items():
                    if a_current_value.get(an_attribute, None) != a_value:
                        matches = False
                        break
                if matches:
                    new_value_found = True
                    for an_attribute, a_value in others.items():
                        a_current_value.set(an_attribute, a_value)
            if not new_value_found:
                new_element = etree.Element("value", attributes)
                for an_attribute, a_value in others.items():
                    new_element.set(an_attribute, a_value)
                a_table.append(new_element)
    tree.write(
        form_insert_file, pretty_print=True, encoding="UTF-8", xml_declaration=True
    )


def update_lookup_from_csv(
    request,
    user_id,
    project_id,
    form_id,
    form_schema,
    form_insert_file,
    file_name,
    dataframe,
    lookup_type,
):
    rel_table, rel_field = get_references_from_file(
        request, project_id, form_id, file_name
    )
    rel_field_desc = rel_field.replace("_cod", "_des")
    filter_columns = get_filter_columns_from_file(
        request, project_id, form_id, file_name
    )
    identity = [rel_field] + filter_columns
    name, label = get_name_and_label_from_file(request, project_id, form_id, file_name)

    # The code and the description are named on the field itself. Every other
    # column of the lookup was made out of a column of the file and carries its
    # name, so it is looked for there.
    sources = {rel_field: name}
    if rel_field_desc != rel_field:
        sources[rel_field_desc] = label
    columns, message = get_merge_columns(
        request,
        project_id,
        form_id,
        rel_table,
        rel_field,
        identity,
        dataframe.columns,
        sources,
    )
    if columns is None:
        return False, "{}. {}".format(file_name, message)

    rows = []
    seen = set()
    for ind in dataframe.index:
        a_row = {}
        for a_field in columns:
            a_column = a_field["field_name"]
            a_row[a_column] = bindable_value(dataframe[sources[a_column]][ind])
        code = a_row[rel_field]
        if isinstance(code, str):
            # RSTools stores a code with its apostrophes turned into backticks,
            # so the lookup holds it that way and this has to ask for it that
            # way.
            code = code.replace("'", "`").replace('"', "")
            a_row[rel_field] = code
            if lookup_type == 2:
                if code.find(" ") >= 0:
                    return (
                        False,
                        '{} is used by a multi-select but it has spaces in the column "name"'.format(
                            file_name
                        ),
                    )
        if isinstance(a_row.get(rel_field_desc), str):
            a_row[rel_field_desc] = a_row[rel_field_desc].replace('"', "")

        # Two rows of a file naming the same choice cannot both be meant, and
        # one of them would win the merge without saying so. A code repeating
        # under different filter values is a different matter: that is what
        # allow_choice_duplicates is for, and it is what the file is expected
        # to hold.
        key = tuple(str(a_row[a_column]) for a_column in identity)
        if key in seen:
            return False, "You have a duplicated option in {}: '{}'".format(
                file_name, code
            )
        seen.add(key)
        rows.append(a_row)

    sql_url = request.registry.settings.get("sqlalchemy.url")
    engine = create_engine(sql_url, poolclass=NullPool)
    session = Session(bind=engine)
    try:
        merge_file_into_lookup(
            session, user_id, form_schema, rel_table, columns, identity, rows
        )
        update_insert_xml_from_lookup(
            session,
            form_insert_file,
            form_schema,
            rel_table,
            columns,
            identity,
            rel_field_desc,
        )
        session.commit()
        engine.dispose()
        return True, ""
    except Exception as e:
        session.rollback()
        engine.dispose()
        log.error(
            "Unable to upload lookup connected to {}. Error: {}".format(
                file_name, str(e)
            )
        )
        log.error(traceback.format_exc())
        return False, str(e)


def is_file_a_lookup(request, project_id, form_id, file_name):
    """
    Returns whether a CSV files is linked to a lookup table
    :param request: Pyramid request object
    :param project_id: Project ID
    :param form_id: Form ID
    :param file_name: CSV file
    """
    res = (
        request.dbsession.query(DictField)
        .filter(DictField.project_id == project_id)
        .filter(DictField.form_id == form_id)
        .filter(DictField.field_externalfilename == file_name)
        .filter(DictField.field_rlookup == 1)
        .first()
    )
    if res is None:
        # Check if the CSV is used in a multi select
        res = (
            request.dbsession.query(DictField)
            .filter(DictField.project_id == project_id)
            .filter(DictField.form_id == form_id)
            .filter(DictField.field_externalfilename == file_name)
            .filter(DictField.field_odktype == "select all that apply")
            .first()
        )
    if res is not None:
        if res.field_odktype == "select all that apply":
            return 2
        return 1
    else:
        return 0


def get_references_from_file(request, project_id, form_id, file_name):
    """
    Return the size of the code column of a CSV file used by a form
    :param request: Pyramid request object
    :param project_id: Project ID
    :param form_id: Form ID
    :param file_name: CSV file
    """
    res = (
        request.dbsession.query(DictField.field_rtable, DictField.field_rfield)
        .filter(DictField.project_id == project_id)
        .filter(DictField.form_id == form_id)
        .filter(DictField.field_externalfilename == file_name)
        .filter(DictField.field_rlookup == 1)
        .first()
    )
    if res is None:
        # Check if the csv is linked to a multi_select
        res = (
            request.dbsession.query(DictField.table_name, DictField.field_name)
            .filter(DictField.project_id == project_id)
            .filter(DictField.form_id == form_id)
            .filter(DictField.field_externalfilename == file_name)
            .filter(DictField.field_odktype == "select all that apply")
            .first()
        )
        if res is not None:
            res = (
                request.dbsession.query(DictField.field_rtable, DictField.field_rfield)
                .filter(DictField.project_id == project_id)
                .filter(DictField.form_id == form_id)
                .filter(
                    DictField.table_name
                    == "{}_msel_{}".format(res.table_name, res.field_name)
                )
                .filter(DictField.field_rlookup == 1)
                .first()
            )
            return res.field_rtable, res.field_rfield
    return res.field_rtable, res.field_rfield


def get_name_and_label_from_file(request, project_id, form_id, file_name):
    """
    Return the name and label column of a CSV file used by a form
    :param request: Pyramid request object
    :param project_id: Project ID
    :param form_id: Form ID
    :param file_name: CSV file
    """
    res = (
        request.dbsession.query(DictField.field_codecolumn, DictField.field_desccolumn)
        .filter(DictField.project_id == project_id)
        .filter(DictField.form_id == form_id)
        .filter(DictField.field_externalfilename == file_name)
        .filter(DictField.field_rlookup == 1)
        .first()
    )
    if res is None:
        # Check if the file is multiselect
        res = (
            request.dbsession.query(
                DictField.field_codecolumn, DictField.field_desccolumn
            )
            .filter(DictField.project_id == project_id)
            .filter(DictField.form_id == form_id)
            .filter(DictField.field_externalfilename == file_name)
            .filter(DictField.field_odktype == "select all that apply")
            .first()
        )
    return res.field_codecolumn, res.field_desccolumn


def update_dictionary_field_sensitive(
    request, project, form, table, field, sensitive, protection
):
    """
    Update the sensitivity of a field in the database
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :param table: Table name
    :param field: Field Name
    :param sensitive: New sensitivity
    :param protection: New type of protection
    :return: True or False
    """
    try:
        update_dict = {"field_sensitive": sensitive}
        if sensitive == 1:
            update_dict["field_protection"] = protection
        else:
            update_dict["field_protection"] = "None"
        request.dbsession.query(DictField).filter(
            DictField.project_id == project
        ).filter(DictField.form_id == form).filter(
            DictField.table_name == table
        ).filter(
            DictField.field_name == field
        ).update(
            update_dict
        )
        request.dbsession.commit()
        return True
    except Exception as e:
        log.error(
            "Error {} while updating description "
            "for field {} in table {} in form {} of project {}".format(
                str(e), field, table, form, project
            )
        )
        request.dbsession.rollback()
        return False


def update_dictionary_field_desc(request, project, form, table, field, new_metadata):
    """
    Update the description of a Field
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :param table: Table name
    :param field: Field Name
    :param new_metadata: New metadata
    :return: True or False
    """
    try:
        mapped_data = map_to_schema(DictField, new_metadata)
        request.dbsession.query(DictField).filter(
            DictField.project_id == project
        ).filter(DictField.form_id == form).filter(
            DictField.table_name == table
        ).filter(
            DictField.field_name == field
        ).update(
            mapped_data
        )
        request.dbsession.commit()
        return True
    except Exception as e:
        log.error(
            "Error {} while updating description "
            "for field {} in table {} in form {} of project {}".format(
                str(e), field, table, form, project
            )
        )
        request.dbsession.rollback()
        return False


def update_dictionary_table_desc(request, project, form, table, description):
    """
    Update the description of a table
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :param table: Table name
    :param description: New description
    :return: True or False
    """
    try:
        request.dbsession.query(DictTable).filter(
            DictTable.project_id == project
        ).filter(DictTable.form_id == form).filter(
            DictTable.table_name == table
        ).update(
            {"table_desc": description}
        )
        request.dbsession.commit()
        return True
    except Exception as e:
        log.error(
            "Error {} while updating description "
            "for table {} in form {} of project {}".format(str(e), table, form, project)
        )
        request.dbsession.rollback()
        return False


def get_dictionary_tables(request, project, form, table_type):
    """
    Returns all tables as an array with their information
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :param table_type: Type of table to return: None=All, 1= Data tables, 2= Lookup tables
    :return: Array of dict elements or empty array
    """
    if table_type is None:
        res = (
            request.dbsession.query(DictTable)
            .filter(DictTable.project_id == project)
            .filter(DictTable.form_id == form)
            .order_by(DictTable.table_index)
            .all()
        )
        return map_from_schema(res)
    if table_type == 1:
        res = (
            request.dbsession.query(DictTable)
            .filter(DictTable.project_id == project)
            .filter(DictTable.form_id == form)
            .filter(DictTable.table_lkp == 0)
            .order_by(DictTable.table_index)
            .all()
        )
        return map_from_schema(res)
    if table_type == 2:
        res = (
            request.dbsession.query(DictTable)
            .filter(DictTable.project_id == project)
            .filter(DictTable.form_id == form)
            .filter(DictTable.table_lkp == 1)
            .order_by(DictTable.table_index)
            .all()
        )
        return map_from_schema(res)
    return []


def get_dictionary_table_desc(request, project, form, table):
    """
    Return the description of a table in the DB
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :param table: Table name
    :return: Table description or None
    """
    return (
        request.dbsession.query(DictTable.table_desc)
        .filter(DictTable.project_id == project)
        .filter(DictTable.form_id == form)
        .filter(DictTable.table_name == table)
        .first()
    )


def get_lookup_relation_fields(request, project, form, multiselect_table):
    """
    Get the relational fields on a multiselect table
    """
    res = (
        request.dbsession.query(
            DictField.field_name, DictField.field_rtable, DictField.field_rfield
        )
        .filter(DictField.project_id == project)
        .filter(DictField.form_id == form)
        .filter(DictField.table_name == multiselect_table)
        .filter(DictField.field_rlookup == 1)
        .first()
    )
    if res is not None:
        return res[0], res[1], res[2]


def get_primary_keys(request, project, form, table):
    """
    Get the primary keys of a table
    """

    res = (
        request.dbsession.query(DictField.field_name)
        .filter(DictField.project_id == project)
        .filter(DictField.form_id == form)
        .filter(DictField.table_name == table)
        .filter(DictField.field_key == 1)
        .all()
    )
    if res is not None:
        primary_keys = []
        for a_key in res:
            primary_keys.append(a_key[0])
        return primary_keys


def get_dictionary_fields(request, project, form, table):
    """
    Get the fields of a table from the DB as a array of dict
    :param request: Pyramid request
    :param project: Project ID
    :param form: Form ID
    :param table: Table name
    :return: Array of dict fields
    """
    res = (
        request.dbsession.query(DictField)
        .filter(DictField.project_id == project)
        .filter(DictField.form_id == form)
        .filter(DictField.table_name == table)
        .order_by(DictField.field_index)
        .all()
    )
    return map_from_schema(res)


def update_dictionary_tables(request, project, form):  # pragma: no cover
    """
    Update the dictionary tables in the DB using a create XML file.
    This function has no coverage because it is used by old version of FormShare
    to move the dictionary tables from XML files to database
    :param request: Pyramid request object
    :param project: Project ID
    :param form: Form ID
    :return: True if update happened, False if error
    """

    def create_new_field_dict(a_table, a_field):
        field_desc = a_field.get("desc", "")
        field_rlookup = a_field.get("rlookup", "false")
        if field_rlookup == "true":
            field_rlookup = 1
        else:
            field_rlookup = 0
        field_key = a_field.get("key", "false")
        if field_key == "true":
            field_key = 1
        else:
            field_key = 0
        # Schema format 3.0. A lookup whose form declares allow_choice_duplicates
        # is keyed by an autoincrement surrogate rather than by its code, and a
        # GeoJSON lookup carries a geometry MySQL derives for itself. Neither may
        # be written by a file update, so both are recorded here rather than
        # guessed at later.
        field_autoincrement = a_field.get("autoincrement", "false")
        if field_autoincrement == "true":
            field_autoincrement = 1
        else:
            field_autoincrement = 0
        field_notnull = a_field.get("notnull", "false")
        if field_notnull == "true":
            field_notnull = 1
        else:
            field_notnull = 0
        field_sensitive = a_field.get("sensitive", "false")
        if field_sensitive == "true":
            field_sensitive = 1
        else:
            field_sensitive = 0
        new_field_dict = {
            "project_id": project,
            "form_id": form,
            "table_name": a_table.get("name"),
            "field_name": a_field.get("name"),
            "field_desc": field_desc,
            "field_key": field_key,
            "field_xmlcode": a_field.get("xmlcode"),
            "field_type": a_field.get("type"),
            "field_odktype": a_field.get("odktype"),
            "field_rtable": a_field.get("rtable"),
            "field_rfield": a_field.get("rfield"),
            "field_rlookup": field_rlookup,
            "field_rname": a_field.get("rname"),
            "field_selecttype": a_field.get("selecttype"),
            "field_externalfilename": a_field.get("externalfilename"),
            "field_codecolumn": a_field.get("codeColumn"),
            "field_desccolumn": a_field.get("descColumn"),
            "field_size": a_field.get("size", 0),
            "field_decsize": a_field.get("decsize", 0),
            "field_sensitive": field_sensitive,
            "field_protection": a_field.get("protection"),
            "field_rfilter": a_field.get("rfilter"),
            "field_generatedas": a_field.get("generatedas"),
            "field_autoincrement": field_autoincrement,
            "field_notnull": field_notnull,
            "field_srid": a_field.get("srid"),
        }
        if a_field.get("selecttype") == "2":
            if new_field_dict["field_externalfilename"].upper().find(".CSV") == -1:
                new_field_dict["field_externalfilename"] = (
                    new_field_dict["field_externalfilename"] + ".csv"
                )
        return new_field_dict

    def store_tables(element, lookup):
        # Process tables
        tables = element.findall(".//table")
        if tables:
            for table in tables:
                res = (
                    request.dbsession.query(DictTable.table_name)
                    .filter(DictTable.project_id == project)
                    .filter(DictTable.form_id == form)
                    .filter(DictTable.table_name == table.get("name"))
                    .count()
                )
                if res == 0:
                    new_table_dict = {
                        "project_id": project,
                        "form_id": form,
                        "table_name": table.get("name"),
                        "table_desc": table.get("desc"),
                        "table_lkp": lookup,
                        "table_inserttrigger": table.get("inserttrigger"),
                        "table_xmlcode": table.get("xmlcode"),
                    }
                    parent = table.getparent()
                    if parent.tag == "table":
                        new_table_dict["parent_project"] = project
                        new_table_dict["parent_form"] = form
                        new_table_dict["parent_table"] = parent.get("name")
                    new_table = DictTable(**new_table_dict)
                    try:
                        request.dbsession.add(new_table)
                        error_in_fields = False
                        for field in table.getchildren():
                            if field.tag == "field":
                                res = (
                                    request.dbsession.query(DictField.field_name)
                                    .filter(DictField.project_id == project)
                                    .filter(DictField.form_id == form)
                                    .filter(DictField.table_name == table.get("name"))
                                    .filter(DictField.field_name == field.get("name"))
                                    .count()
                                )
                                if res == 0:
                                    new_field_dict = create_new_field_dict(table, field)
                                    new_field = DictField(**new_field_dict)
                                    try:
                                        request.dbsession.add(new_field)
                                    except IntegrityError:
                                        request.dbsession.rollback()
                                        log.error(
                                            "Duplicated field {} in table {} in project {} form {}".format(
                                                field.get("name"),
                                                table.get("name"),
                                                project,
                                                form,
                                            )
                                        )
                                        error_in_fields = True
                                    except Exception as e:
                                        request.dbsession.rollback()
                                        log.error(
                                            "Error adding field {} in table {} in project {} form {}. Error: {}".format(
                                                field.get("name"),
                                                table.get("name"),
                                                project,
                                                form,
                                                str(e),
                                            )
                                        )
                                        error_in_fields = True
                        if not error_in_fields:
                            request.dbsession.commit()
                        else:
                            return False
                    except IntegrityError:
                        request.dbsession.rollback()
                        log.error(
                            "Duplicated table {} in project {} form {}".format(
                                table.get("name"), project, form
                            )
                        )
                        return False
                    except Exception as e:
                        request.dbsession.rollback()
                        log.error(
                            "Error adding table {} in project {} form {}. Error: {}".format(
                                table.get("name"), project, form, str(e)
                            )
                        )
                        return False
                else:
                    error_in_fields = False
                    for field in table.getchildren():
                        if field.tag == "field":
                            res = (
                                request.dbsession.query(DictField.field_name)
                                .filter(DictField.project_id == project)
                                .filter(DictField.form_id == form)
                                .filter(DictField.table_name == table.get("name"))
                                .filter(DictField.field_name == field.get("name"))
                                .count()
                            )
                            if res == 0:
                                new_field_dict = create_new_field_dict(table, field)
                                new_field = DictField(**new_field_dict)
                                try:
                                    request.dbsession.add(new_field)
                                except IntegrityError:
                                    request.dbsession.rollback()
                                    log.error(
                                        "Duplicated field {} in table {} in project {} form {}".format(
                                            field.get("name"),
                                            table.get("name"),
                                            project,
                                            form,
                                        )
                                    )
                                    error_in_fields = True
                                except Exception as e:
                                    request.dbsession.rollback()
                                    log.error(
                                        "Error adding field {} in table {} in project {} form {}. Error: {}".format(
                                            field.get("name"),
                                            table.get("name"),
                                            project,
                                            form,
                                            str(e),
                                        )
                                    )
                                    error_in_fields = True
                    if not error_in_fields:
                        try:
                            request.dbsession.commit()
                        except Exception as e:
                            request.dbsession.rollback()
                            log.error(
                                "Eroror {} inserting fileds in table {} in project {} form {}".format(
                                    str(e),
                                    table.get("name"),
                                    project,
                                    form,
                                )
                            )
        return True

    create_file = get_form_xml_create_file(request, project, form)
    if not os.path.isfile(create_file):
        return False
    tree = etree.parse(create_file)
    root = tree.getroot()
    element_lkp_tables = root.find(".//lkptables")
    element_tables = root.find(".//tables")
    lkp_stored = store_tables(element_lkp_tables, 1)
    non_lkp_stored = store_tables(element_tables, 0)
    if lkp_stored and non_lkp_stored:
        return True
    else:
        return False
