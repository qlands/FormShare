from formshare.models import DictTable, DictField, map_from_schema
from formshare.processes.db.form import get_form_xml_create_file
import logging
import os
from lxml import etree
from sqlalchemy.exc import IntegrityError

__all__ = [
    "update_dictionary_tables",
    "get_dictionary_fields",
    "get_dictionary_table_desc",
]

log = logging.getLogger("formshare")


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
        .all()
    )
    return map_from_schema(res)


def update_dictionary_tables(request, project, form):
    """
    Update the dictionary tables in the DB using a create XML file
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
            "field_size": a_field.get("size", 0),
            "field_decsize": a_field.get("decsize", 0),
            "field_sensitive": field_sensitive,
            "field_protection": a_field.get("protection"),
        }
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
                        request.dbsession.flush()
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
                                        request.dbsession.flush()
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
                                        return False
                    except IntegrityError:
                        request.dbsession.rollback()
                        log.error(
                            "Duplicated table {} in project {} form {}".format(
                                table.get("name"), project, form
                            )
                        )
                        return False
                else:
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
                                    request.dbsession.flush()
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
                                    return False
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
