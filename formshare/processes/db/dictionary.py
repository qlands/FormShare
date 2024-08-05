import logging
import os
import uuid
from sqlalchemy import create_engine
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
    "get_primary_keys",
    "get_lookup_relation_fields",
]

log = logging.getLogger("formshare")


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
    uid = str(uuid.uuid4())
    uid = "TMP_" + uid.replace("-", "_")
    field_type, field_size = get_type_and_size_from_file(
        request, project_id, form_id, file_name
    )
    if field_type == "varchar":
        sql = "CREATE TABLE {}.{} (var_code {}({}) PRIMARY KEY, var_label text)".format(
            form_schema, uid, field_type, field_size
        )
    else:
        sql = "CREATE TABLE {}.{} (var_code {} PRIMARY KEY, var_label text)".format(
            form_schema, uid, field_type
        )

    sql_url = request.registry.settings.get("sqlalchemy.url")
    engine = create_engine(sql_url, poolclass=NullPool)
    session = Session(bind=engine)
    temp_table_created = False
    try:
        session.execute(sql)
        temp_table_created = True
        name, label = get_name_and_label_from_file(
            request, project_id, form_id, file_name
        )
        for ind in dataframe.index:
            code = dataframe[name][ind]
            if isinstance(code, str):
                code = code.replace("'", "`").replace('"', "")
                if lookup_type == 2:
                    if code.find(" ") >= 0:
                        sql = "DROP TABLE {}.{}".format(form_schema, uid)
                        session.execute(sql)
                        return (
                            False,
                            '{} is used by a multi-select but it has spaces in the column "name"'.format(
                                file_name
                            ),
                        )

            value = dataframe[label][ind]
            if isinstance(value, str):
                value = value.replace('"', "")
            sql = (
                "INSERT INTO {}.{} (var_code, var_label) VALUES ('{}', \"{}\")".format(
                    form_schema,
                    uid,
                    code,
                    value,
                )
            )
            session.execute(sql)

        rel_table, rel_field = get_references_from_file(
            request, project_id, form_id, file_name
        )
        rel_field_desc = rel_field.replace("_cod", "_des")

        # Update the descriptions
        session.execute("SET @odktools_current_user = '" + user_id + "'")
        sql = "UPDATE {}.{} TA, {}.{} TB SET TA.{} = TB.var_label WHERE TA.{} = TB.var_code".format(
            form_schema, rel_table, form_schema, uid, rel_field_desc, rel_field
        )
        session.execute(sql)

        # Insert new items
        sql = "INSERT IGNORE INTO {}.{} ({},{}) SELECT var_code, var_label FROM {}.{}".format(
            form_schema, rel_table, rel_field, rel_field_desc, form_schema, uid
        )
        session.execute(sql)

        sql = "DROP TABLE {}.{}".format(form_schema, uid)
        session.execute(sql)
        temp_table_created = False

        sql = "SELECT {},{} FROM {}.{}".format(
            rel_field, rel_field_desc, form_schema, rel_table
        )
        new_values = session.execute(sql).fetchall()

        # Now we update the Insert XML file based on the values of the Lookup table
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(form_insert_file, parser)

        tables = tree.xpath('//table[@name="{}"]'.format(rel_table))
        for a_table in tables:
            curren_values = a_table.findall(".//value")
            for a_new_value in new_values:
                new_value_found = False
                new_value = a_new_value[0]
                if isinstance(new_value, int):
                    new_value = str(new_value)
                for a_current_value in curren_values:
                    if a_current_value.get("code", None) == new_value:
                        new_value_found = True
                        a_current_value.set("description", a_new_value[1])
                if not new_value_found:
                    new_element = etree.Element(
                        "value", code=new_value, description=a_new_value[1]
                    )
                    a_table.append(new_element)
        tree.write(
            form_insert_file, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )

        session.commit()
        engine.dispose()

        return True, ""
    except IntegrityError:
        if temp_table_created:
            sql = "DROP TABLE {}.{}".format(form_schema, uid)
            session.execute(sql)
        session.commit()
        engine.dispose()
        return False, "You have a duplicated option in {}".format(file_name)
    except Exception as e:
        if temp_table_created:
            sql = "DROP TABLE {}.{}".format(form_schema, uid)
            session.execute(sql)
        session.commit()
        engine.dispose()
        log.error(
            "Unable to upload lookup connected to {}. Error: {}".format(
                file_name, str(e)
            )
        )
        print(traceback.format_exc())
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


def get_type_and_size_from_file(request, project_id, form_id, file_name):
    """
    Return the size of the code column of a CSV file used by a form
    :param request: Pyramid request object
    :param project_id: Project ID
    :param form_id: Form ID
    :param file_name: CSV file
    """
    res = (
        request.dbsession.query(DictField.field_type, DictField.field_size)
        .filter(DictField.project_id == project_id)
        .filter(DictField.form_id == form_id)
        .filter(DictField.field_externalfilename == file_name)
        .filter(DictField.field_rlookup == 1)
        .first()
    )
    if res is None:
        # Look for type and size in LookUp table
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
                request.dbsession.query(DictField.field_type, DictField.field_size)
                .filter(DictField.project_id == project_id)
                .filter(DictField.form_id == form_id)
                .filter(
                    DictField.table_name
                    == "{}_msel_{}".format(res.table_name, res.field_name)
                )
                .filter(DictField.field_rlookup == 1)
                .first()
            )
            return res.field_type, res.field_size
    return res.field_type, res.field_size


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
    save_point = request.tm.savepoint()
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
        request.dbsession.flush()
        return True
    except Exception as e:
        log.error(
            "Error {} while updating description "
            "for field {} in table {} in form {} of project {}".format(
                str(e), field, table, form, project
            )
        )
        save_point.rollback()
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
    save_point = request.tm.savepoint()
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
        request.dbsession.flush()
        return True
    except Exception as e:
        log.error(
            "Error {} while updating description "
            "for field {} in table {} in form {} of project {}".format(
                str(e), field, table, form, project
            )
        )
        save_point.rollback()
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
    save_point = request.tm.savepoint()
    try:
        request.dbsession.query(DictTable).filter(
            DictTable.project_id == project
        ).filter(DictTable.form_id == form).filter(
            DictTable.table_name == table
        ).update(
            {"table_desc": description}
        )
        request.dbsession.flush()
        return True
    except Exception as e:
        log.error(
            "Error {} while updating description "
            "for table {} in form {} of project {}".format(str(e), table, form, project)
        )
        save_point.rollback()
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
                    save_point = request.tm.savepoint()
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
                                        save_point.rollback()
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
                                        save_point.rollback()
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
                            request.dbsession.flush()
                        else:
                            return False
                    except IntegrityError:
                        save_point.rollback()
                        log.error(
                            "Duplicated table {} in project {} form {}".format(
                                table.get("name"), project, form
                            )
                        )
                        return False
                    except Exception as e:
                        save_point.rollback()
                        log.error(
                            "Error adding table {} in project {} form {}. Error: {}".format(
                                table.get("name"), project, form, str(e)
                            )
                        )
                        return False
                else:
                    error_in_fields = False
                    save_point = request.tm.savepoint()
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
                                    save_point.rollback()
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
                                    save_point.rollback()
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
                            request.dbsession.flush()
                        except Exception as e:
                            save_point.rollback()
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
