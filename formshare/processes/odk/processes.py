import os
from lxml import etree
from formshare.models import Odkform as Form
from formshare.models import Collaborator, Septable, Sepsection, Sepitem, Submission, Jsonlog, Jsonhistory, \
    map_from_schema, Formacces, Collingroup, Formgrpacces
import datetime
import glob
import uuid
import zipfile
import re
from formshare.config.encdecdata import decode_data
from formshare.processes.db.form import get_assistant_forms
from formshare.processes.db.assistant import get_project_from_assistant
from sqlalchemy import and_, func
from sqlalchemy.sql import label
import logging

log = logging.getLogger(__name__)


def get_assistant_name(request, project, assistant):
    enum = request.dbsession.query(Collaborator).filter(Collaborator.project_id == project).filter(
        Collaborator.coll_id == assistant).first()
    if enum is not None:
        return enum.coll_name
    else:
        return ""


def is_assistant_active(request, project, assistant):
    enum = request.dbsession.query(Collaborator).filter(Collaborator.project_id == project).filter(
        Collaborator.coll_id == assistant).first()
    if enum is not None:
        if enum.coll_active == 1:
            return True
        else:
            return False
    else:
        return False


def get_assistant_password(request, project, assistant):
    enum = request.dbsession.query(Collaborator).filter(Collaborator.project_id == project).filter(
        Collaborator.coll_id == assistant).first()
    encoded_password = enum.coll_password
    decoded_password = decode_data(request, encoded_password)
    return decoded_password


def get_form_directory(request, project, form):
    form_data = request.dbsession.query(Form).filter(Form.project_id == project).filter(Form.form_id == form).one()
    return form_data.form_directory


def get_error_description_from_file(log_file):
    try:
        tree = etree.parse(log_file)
        root = tree.getroot()
        error = root.find(".//error")
        message = error.get("Error")
        if message.find("Duplicate entry") >= 0:
            return {"duplicated": True, "error": error.get("Error")}
        else:
            return {"duplicated": False, "error": error.get("Error")}
    except Exception as e:
        return {"duplicated": False, "error": str(e)}


def get_last_log_entry(request, user, project, form, submission_id):
    res = request.dbsession.query(Jsonhistory, Collaborator).filter(
        Jsonhistory.enum_project == Collaborator.project_id).filter(Jsonhistory.coll_id == Collaborator.coll_id).filter(
        Jsonhistory.project_id == project).filter(Jsonhistory.form_id == form).filter(
        Jsonhistory.log_id == submission_id).order_by(Jsonhistory.log_dtime.desc()).first()

    if res is not None:
        last_entry = map_from_schema(res)
        notes = last_entry['log_notes']
        if notes is not None:
            submissions = re.findall(r"[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12}", notes)
            if submissions:
                for submission in submissions:
                    if submission != submission_id:
                        if notes.find('[' + submission + ']') == -1:
                            project_code = request.matchdict['projcode']
                            url = request.route_url('comparesubmissions', userid=user, projcode=project_code,
                                                    formid=form, submissiona=submission_id, submissionb=submission)
                            notes = notes.replace(submission, '[' + submission + '](' + url + ")")

        return {'log_sequence': last_entry['log_sequence'], 'log_dtime': last_entry['log_dtime'],
                'log_action': last_entry['log_action'], 'log_commit': last_entry['log_commit'],
                'enum_id': last_entry['coll_id'], 'enum_name': last_entry['coll_name'],
                'log_notes': notes}
    else:
        return None


def get_submission_details(request, project, form, submission):
    res = request.dbsession.query(Submission, Collaborator).\
        filter(Submission.enum_project == Collaborator.project_id).\
        filter(Submission.coll_id == Collaborator.coll_id).\
        filter(Submission.project_id == project).filter(Submission.form_id == form).\
        filter(Submission.submission_id == submission).first()

    if res is not None:
        mapped_data = map_from_schema(res)
        return {'submission_dtime': mapped_data['submission_dtime'], 'submission_id': mapped_data['submission_id'],
                'enum_name': mapped_data['coll_name'], 'submission_status': mapped_data['submission_status']}
    else:
        return None


def get_submission_error_details(request, project, form, submission):
    res = request.dbsession.query(Jsonlog, Collaborator).\
        filter(Jsonlog.enum_project == Collaborator.project_id).\
        filter(Jsonlog.coll_id == Collaborator.coll_id).\
        filter(Jsonlog.project_id == project).\
        filter(Jsonlog.form_id == form).filter(Jsonlog.log_id == submission).first()

    if res is not None:
        mapped_data = map_from_schema(res)
        return {'log_dtime': mapped_data['log_dtime'], 'json_file': mapped_data['json_file'],
                'enum_name': mapped_data['coll_name'], 'status': mapped_data['status'],
                'log_file': mapped_data['log_file']}
    else:
        return None


def get_errors_by_assistant(request, user, project, form, assistant):
    result = []

    if assistant is None:
        res = request.dbsession.query(Jsonlog, Collaborator). \
            filter(Jsonlog.enum_project == Collaborator.project_id). \
            filter(Jsonlog.coll_id == Collaborator.coll_id). \
            filter(Jsonlog.project_id == project). \
            filter(Jsonlog.form_id == form).order_by(Jsonlog.log_dtime.desc()).all()
    else:
        res = request.dbsession.query(Jsonlog, Collaborator). \
            filter(Jsonlog.enum_project == Collaborator.project_id). \
            filter(Jsonlog.coll_id == Collaborator.coll_id). \
            filter(Jsonlog.project_id == project). \
            filter(Jsonlog.coll_id == assistant). \
            filter(Jsonlog.form_id == form).order_by(Jsonlog.log_dtime.desc()).all()

    json_errors = map_from_schema(res)
    for error in json_errors:
        result.append({'log_id': error['log_id'], 'log_dtime': error['log_dtime'], 'json_file': error['json_file'],
                       'error': get_error_description_from_file(error['log_file']), 'status': error['status'],
                       'lastentry': get_last_log_entry(request, user, project, form, error['log_id']),
                       'enum_name': error['coll_name'], 'log_short': error['log_id'][-12:]})
    return result


def get_submissions_by_assistant(dbsession, project, form, assistant):
    total = dbsession.query(Submission).filter(Submission.project_id == project).filter(
        Submission.form_id == form).filter(Submission.coll_id == assistant).filter(Submission.sameas.is_(None)).count()

    in_db = dbsession.query(Submission).filter(Submission.project_id == project).filter(
        Submission.form_id == form).filter(Submission.coll_id == assistant).filter(
        Submission.submission_status == 0).filter(Submission.sameas.is_(None)).count()

    fixed = dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(Jsonlog.form_id == form).filter(
        Jsonlog.status == 0).filter(Jsonlog.coll_id == assistant).count()

    in_db_from_logs = dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
        Jsonlog.form_id == form).filter(Jsonlog.coll_id == assistant).count()

    in_error = dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(Jsonlog.form_id == form).filter(
        Jsonlog.coll_id == assistant).filter(Jsonlog.status != 0, Jsonlog.status != 4).count()

    res = dbsession.query(Submission).filter(Submission.project_id == project).filter(
        Submission.form_id == form).filter(Submission.coll_id == assistant).filter(
        Submission.sameas.is_(None)).order_by(Submission.submission_dtime.desc()).first()
    if res is not None:
        last = res.submission_dtime
    else:
        last = None

    result = {'total': total, 'totalInDB': in_db + fixed, 'totalInLogs': in_db_from_logs, 'totalInError': in_error,
              'last': last}
    return result


def get_submissions_by_form(dbsession, project, form):
    total = dbsession.query(Submission).filter(Submission.project_id == project).filter(
        Submission.form_id == form).filter(Submission.sameas.is_(None)).count()

    in_db = dbsession.query(Submission).filter(Submission.project_id == project).filter(
        Submission.form_id == form).filter(Submission.submission_status == 0).filter(
        Submission.sameas.is_(None)).count()

    in_db_from_logs = dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
        Jsonlog.form_id == form).count()

    fixed = dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(Jsonlog.form_id == form).filter(
        Jsonlog.status == 0).count()

    in_error = dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(Jsonlog.form_id == form).filter(
        Jsonlog.status != 0, Jsonlog.status != 4).count()

    res = dbsession.query(Submission).filter(Submission.project_id == project).filter(
        Submission.form_id == form).filter(Submission.sameas.is_(None)).order_by(
        Submission.submission_dtime.desc()).first()
    if res is not None:
        last = res.submission_dtime
    else:
        last = None

    result = {'total': total, 'totalInDB': in_db + fixed, 'totalInLogs': in_db_from_logs, 'totalInError': in_error,
              'last': last}
    return result


def get_forms_by_assistant(request, user, project, assistant):
    assistant_project = get_project_from_assistant(request, user, project, assistant)
    assistant_forms = get_assistant_forms(request, project, assistant_project, assistant)

    for a_form in assistant_forms:
        a_form['formstats'] = get_submissions_by_form(request.dbsession, a_form['project_id'], a_form['form_id'])
        a_form['enumstats'] = get_submissions_by_assistant(request.dbsession, a_form['project_id'], a_form['form_id'],
                                                           assistant)
    return assistant_forms


def get_assistant_permissions_on_a_form(request, user, requested_project, assistant, form):
    privileges = {'enum_cansubmit': 0, 'enum_canclean': 0}
    assistant_project = get_project_from_assistant(request, user, requested_project, assistant)
    # Get all the forms that the user can submit data to and are active
    assistant_access = request.dbsession.query(Formacces).filter(Formacces.project_id == assistant_project).filter(
        Formacces.coll_id == assistant).filter(Formacces.form_project == requested_project).filter(
        Formacces.form_id == form).first()
    if assistant_access is not None:
        if assistant_access.coll_privileges == 3:
            privileges = {'enum_cansubmit': 1, 'enum_canclean': 1}
        else:
            if assistant_access.coll_privileges == 1:
                privileges = {'enum_cansubmit': 1, 'enum_canclean': 0}
            else:
                privileges = {'enum_cansubmit': 0, 'enum_canclean': 1}

    # Select the groups that user belongs to
    groups = request.dbsession.query(Collingroup).filter(Collingroup.project_id == requested_project).filter(
        Collingroup.enum_project == assistant_project).filter(Collingroup.coll_id == assistant).all()

    for group in groups:
        res = request.dbsession.query(Formgrpacces).filter(Formgrpacces.project_id == group.project_id).filter(
            Formgrpacces.group_id == group.group_id).filter(Form.form_id == form).first()
        if res is not None:
            if res.group_privileges == 3:
                privileges = {'enum_cansubmit': 1, 'enum_canclean': 1}
            else:
                if res.group_privileges == 1:
                    privileges["enum_cansubmit"] = 1
                else:
                    privileges["enum_canclean"] = 2

    return privileges


# This update the stage information so he can come back
def update_form_stage(request, project, form, stage, primary_key, default_language, other_languages, yes_no_strings,
                      separation_file):
    request.dbsession.query(Form).filter(Form.project_id == project).filter(Form.form_id == form).update(
        {'form_stage': stage, 'form_pkey': primary_key, 'form_deflang': default_language,
         'form_othlangs': other_languages, 'form_yesno': yes_no_strings, 'form_sepfile': separation_file})


def update_form_stage_number(request, project, form, stage):
    request.dbsession.query(Form).filter(Form.project_id == project)\
        .filter(Form.form_id == form).update({'form_stage': stage})
    if stage == 1:
        # If the stage goes to 1 then reset the language and separation information
        request.dbsession.query(Septable).filter(Septable.project_id == project).filter(
            Septable.form_id == form).delete()
        request.dbsession.query(Form).filter(Form.project_id == project).filter(Form.form_id == form).update(
            {'form_deflang': None, 'form_othlangs': None, 'form_yesno': None, 'form_sepfile': None, 'form_pkey': None})


# Reconstruct the separation tables
def update_form_separation_file(request, project, form, separation_file):
    request.dbsession.query(Septable).filter(Septable.project_id == project) \
        .filter(Septable.form_id == form).delete()

    request.dbsession.query(Form).filter(Form.project_id == project)\
        .filter(Form.form_id == form).update({'form_sepfile': separation_file})
    tree = etree.parse(separation_file)
    root = tree.getroot()
    xml_tables = root.findall(".//table")
    for table in xml_tables:
        table_name = table.get("name")
        new_table = Septable(project_id=project, form_id=form, table_name=table_name, table_desc='')
        request.dbsession.add(new_table)
        xml_groups = table.findall(".//group")
        group_order = 1
        for group in xml_groups:
            section_id = str(uuid.uuid4())
            section_id = section_id[-12:]
            new_group = Sepsection(project_id=project, form_id=form, table_name=table_name, section_id=section_id,
                                   section_name=group.get("name"), section_desc=group.get("description"),
                                   section_order=group_order)

            request.dbsession.add(new_group)
            group_order = group_order + 1
            xml_items = group.findall(".//field")
            item_order = 1
            for item in xml_items:
                if item.get("notmove") == 'true':
                    not_display = 1
                else:
                    not_display = 0
                new_item = Sepitem(project_id=project, form_id=form, table_name=table_name, item_name=item.get("name"),
                                   item_desc=item.get("description"), item_xmlcode=item.get("xmlcode"),
                                   item_notdisplay=not_display, item_order=item_order, section_project=project,
                                   section_form=form, section_table=table_name, section_id=section_id)
                request.dbsession.add(new_item)
                item_order = item_order + 1


def table_belongs_to_form(request, project, form, table_name):
    data = request.dbsession.query(Septable).filter(Septable.project_id == project) \
        .filter(Septable.form_id == form).filter(Septable.table_name == table_name).first()
    if data is None:
        return False
    else:
        return True


def get_table_items(request, project, form, table_name, just_main=False):
    # if just_main:
    #     items = request.dbsession.query(Sepsection, Sepitem).outerjoin((Sepitem, and_(
    #         Sepitem.section_project == Sepsection.project_id, Sepitem.section_form == Sepsection.form_id,
    #         Sepitem.section_table == Sepsection.table_name, Sepitem.section_id == Sepsection.section_id))).filter(
    #         Sepsection.project_id == project).filter(Sepsection.form_id == form).filter(
    #         Sepsection.table_name == table_name).filter(Sepsection.section_name == 'main').\
    #         order_by(Sepsection.section_order.asc(), Sepitem.item_order.asc()).all()
    # else:
    #     items = request.dbsession.query(Sepsection, Sepitem).outerjoin((Sepitem, and_(
    #         Sepitem.section_project == Sepsection.project_id, Sepitem.section_form == Sepsection.form_id,
    #         Sepitem.section_table == Sepsection.table_name, Sepitem.section_id == Sepsection.section_id))).filter(
    #         Sepsection.project_id == project).filter(Sepsection.form_id == form).filter(
    #         Sepsection.table_name == table_name).filter(Sepsection.section_name != 'main'). \
    #         order_by(Sepsection.section_order.asc(), Sepitem.item_order.asc()).all()

    sql = "SELECT sepsection.section_id,sepsection.section_name,sepsection.section_desc," \
          "sepsection.section_order, sepitems.item_name,sepitems.item_desc," \
          "IFNULL(sepitems.item_order,0) as item_order, sepitems.item_notdisplay " \
          "FROM sepsection " \
          "LEFT JOIN sepitems " \
          "ON sepitems.section_project = sepsection.project_id " \
          "AND sepitems.section_form = sepsection.form_id " \
          "AND sepitems.section_table = sepsection.table_name " \
          "AND sepitems.section_id = sepsection.section_id " \
          "WHERE sepsection.project_id = '" + project + "' " \
          "AND sepsection.form_id = '" + form + "' " \
          "AND sepsection.table_name = '" + table_name + "' "
    if just_main:
        sql = sql + "AND sepsection.section_name = 'main' "
    else:
        sql = sql + "AND sepsection.section_name != 'main' "
    sql = sql + "ORDER BY sepsection.section_order,item_order"
    items = request.dbsession.execute(sql).fetchall()

    result = []
    for qst in items:
        dct = (dict(qst))
        for key, value in dct.items():
            dct[key] = value
        result.append(dct)

    return result
    # if items is not None:
    #     return map_from_schema(items)
    # else:
    #     return None


def is_separation_ok(request, project, form, table_name):
    items = request.dbsession.query(Sepitem.section_id, label('totitems', func.count(Sepitem.section_id))).filter(
        Sepitem.project_id == project).filter(Sepitem.form_id == form).filter(
        Sepitem.table_name == table_name).group_by(Sepitem.section_id).all()

    # sql = "select section_id,count(*) as totitems " \
    #       "from sepitems " \
    #       "where project_id = '" + projectID + "' " \
    #       "and form_id = '" + formID + "' " \
    #       "and table_name = '" + tableName + "' " \
    #       "group by section_id;"
    # items = request.dbsession.execute(sql).fetchall()
    fine = True
    for item in items:
        if item.totitems >= 60:
            fine = False
    return fine


def save_separation_order(request, project, form, table_name, order, order2):
    # Delete all items that are not in main
    request.dbsession.query(Sepitem).filter(Sepitem.project_id == project).filter(Sepitem.form_id == form).filter(
        Sepitem.table_name == table_name).delete()

    # Update the group order will start in 1
    pos = 1
    for item in order:
        if item["type"] == "group":
            pos = pos + 1
            request.dbsession.query(Sepsection).filter(Sepsection.project_id == project).filter(
                Sepsection.form_id == form).filter(Sepsection.table_name == table_name).filter(
                Sepsection.section_id == item["id"].replace("GRP", "")).update({"section_order": pos})

    for item in order2:
        if item["type"] == "group":
            pos = pos + 1
            request.dbsession.query(Sepsection).filter(Sepsection.project_id == project).filter(
                Sepsection.form_id == form).filter(Sepsection.table_name == table_name).filter(
                Sepsection.section_id == item["id"].replace("GRP", "")).update({"section_order": pos})

    # Add question to the list
    pos = 0
    for item in order:
        if item["type"] == "group":
            if "children" in item.keys():
                for child in item["children"]:
                    pos = pos + 1
                    new_item = Sepitem(project_id=project, form_id=form, table_name=table_name,
                                       item_name=child["id"].replace("QST", ''), item_desc=child["desc"],
                                       item_notdisplay=child["display"], section_project=project, section_form=form,
                                       section_table=table_name, section_id=item["id"].replace("GRP", ""),
                                       item_order=pos)
                    request.dbsession.add(new_item)
        if item["type"] == "question":
            return False, request.translate("One item is outside a group!")

    for item in order2:
        if item["type"] == "group":
            if "children" in item.keys():
                for child in item["children"]:
                    pos = pos + 1
                    new_item = Sepitem(project_id=project, form_id=form, table_name=table_name,
                                       item_name=child["id"].replace("QST", ''), item_desc=child["desc"],
                                       item_notdisplay=child["display"], section_project=project, section_form=form,
                                       section_table=table_name, section_id=item["id"].replace("GRP", ""),
                                       item_order=pos)
                    request.dbsession.add(new_item)
        if item["type"] == "question":
            return False, request.translate("One item is outside a group!")

    try:
        request.dbsession.flush()
    except Exception as e:
        log.error(str(e))
        request.dbsession.rollback()
    return True, ""


def get_group_number_of_items(request, project, form, table_name, section_id):
    res = request.dbsession.query(Sepitem).filter(Sepitem.project_id == project).filter(Sepitem.form_id == form).filter(
        Sepitem.table_name == table_name).filter(Sepitem.section_id == section_id).count()
    return res


def get_group_name_from_id(request, project, form, table_name, section_id):
    res = request.dbsession.query(Sepsection).filter(Sepsection.project_id == project).filter(
        Sepsection.form_id == form).filter(Sepsection.table_name == table_name).filter(
        Sepsection.section_id == section_id).first()
    if res is not None:
        return res.section_desc
    else:
        return None


def generate_separation_file(request, project, form):

    form_data = request.dbsession.query(Form).filter(Form.project_id == project).filter(Form.form_id == form).first()
    separation_file = form_data.form_sepfile

    if separation_file.find("-separated") >= 0:
        if os.path.exists(separation_file):
            return separation_file

    file_name = os.path.basename(separation_file)
    file_path = os.path.dirname(separation_file)
    file_name, file_extension = os.path.splitext(file_name)

    new_file = os.path.join(file_path, file_name+'-separated' + file_extension)

    page = etree.Element('ODKSeparationXML', version="1.0")
    root = etree.ElementTree(page)
    tables = request.dbsession.query(Septable).filter(Septable.project_id == project).filter(
        Septable.form_id == form).all()
    for aTable in tables:
        e_table = etree.SubElement(page, 'table', name=aTable.table_name)
        groups = request.dbsession.query(Sepsection).filter(Sepsection.project_id == project).filter(
            Sepsection.form_id == form).filter(Sepsection.table_name == aTable.table_name).all()
        for aGroup in groups:
            e_group = etree.SubElement(e_table, 'group', name=aGroup.section_name, description=aGroup.section_desc)
            items = request.dbsession.query(Sepitem).filter(Sepitem.section_project == project).filter(
                Sepitem.section_form == form).filter(Sepitem.section_table == aTable.table_name).filter(
                Sepitem.section_id == aGroup.section_id).all()
            for item in items:
                if item.item_notdisplay == 1:
                    not_move = "true"
                else:
                    not_move = "false"
                if item.item_xmlcode is None:
                    xml_code = "NONE"
                else:
                    xml_code = item.item_xmlcode
                etree.SubElement(e_group, 'field', name=item.item_name, description=item.item_desc, notmove=not_move,
                                 xmlcode=xml_code)

    out_file = open(new_file, 'wb')
    root.write(out_file, xml_declaration=True, encoding='UTF-8', pretty_print=True)
    out_file.close()

    request.dbsession.query(Form).filter(Form.project_id == project).filter(Form.form_id == form).update(
        {'form_sepfile': new_file})

    return new_file


def get_tables_to_separate(request, project, form):
    tables = request.dbsession.query(Sepitem.section_table, Sepitem.section_id,
                                     label('totitems', func.count(Sepitem.item_name))).filter(
        Sepitem.project_id == project).filter(Sepitem.form_id == form).group_by(Sepitem.section_table,
                                                                                Sepitem.section_id).all()

    # sql = "SELECT section_table,section_id,count(item_name) AS totitems " \
    #       "FROM sepitems " \
    #       "WHERE project_id = '" + projectID + "' " \
    #       "AND form_id = '" + formID + "' " \
    #       "GROUP BY section_table,section_id ORDER BY totitems DESC"
    # tables = request.dbsession.execute(sql).fetchall()
    result = []
    has_tables_to_separate = False
    for table in tables:
        separate = False
        if table.totitems >= 60:
            separate = True
            has_tables_to_separate = True
        found = False
        for aTable in result:
            if aTable["name"] == table.section_table:
                found = True
        if not found:
            result.append({'name': table.section_table, 'separate': separate})
    return has_tables_to_separate, result


def delete_group(request, project, form, table_name, section_id):
    try:
        request.dbsession.query(Sepsection).filter(Sepsection.project_id == project).filter(
            Sepsection.form_id == form).filter(Sepsection.table_name == table_name).filter(
            Sepsection.section_id == section_id).delete()
        return True, ""
    except Exception as e:
        return False, str(e)


def set_group_desc(request, project, form, table_name, section_id, section_desc):
    try:
        request.dbsession.query(Sepsection).filter(Sepsection.project_id == project).filter(
            Sepsection.form_id == form).filter(Sepsection.table_name == table_name).filter(
            Sepsection.section_id == section_id).update({'section_desc': section_desc})
        return True, ""
    except Exception as e:
        return False, str(e)


def add_group(request, project, form, table_name, section_name, section_desc):
    exist = request.dbsession.query(Sepsection).filter(Sepsection.project_id == project).filter(
        Sepsection.form_id == form).filter(Sepsection.table_name == table_name).filter(
        Sepsection.section_name == section_name).first()
    if exist is None:
        res = request.dbsession.query(label('maxorder', func.max(Sepsection.section_order))).filter(
            Sepsection.project_id == project).filter(Sepsection.form_id == form).filter(
            Sepsection.table_name == table_name).one()
        # sql = "SELECT max(section_order) as maxorder " \
        #       "FROM sepsection " \
        #       "WHERE project_id = '" + projectID + "' " \
        #       "AND form_id = '" + formID + "' " \
        #       "AND table_name = '" + tableName + "'"
        # res = request.dbsession.execute(sql).fetchone()
        max_order = res.maxorder + 1
        section_id = str(uuid.uuid4())
        section_id = section_id[-12:]
        new_section = Sepsection(project_id=project, form_id=form, table_name=table_name, section_id=section_id,
                                 section_name=section_name, section_desc=section_desc, section_order=max_order)
        request.dbsession.add(new_section)
        return True, ""
    else:
        return False, request.translate("Section name ") + section_name + request.translate(" already exist")


def get_stage_info_from_form(request, project, form):
    stage = 1
    primary_key = ""
    deflanguage = ""
    languages = []
    yesvalue = ''
    novalue = ''
    other_languages = ""
    yes_no_strings = ""
    default_language = ""
    separation_file = None
    data = request.dbsession.query(Form).filter(Form.project_id == project).filter(Form.form_id == form).first()
    if data.form_stage is not None:
        stage = data.form_stage
    if data.form_pkey is not None:
        primary_key = data.form_pkey
    if data.form_deflang is not None:
        default_language = data.form_deflang
        parts = default_language.split(")")
        deflanguage = parts[1]
    if data.form_othlangs is not None:
        other_languages = data.form_othlangs
        lst_langs = other_languages.split(',')
        for lang in lst_langs:
            parts = lang.split(")")
            lang_code = parts[0].replace("(", "")
            lang_desc = parts[1]
            languages.append({'code': lang_code, 'name': lang_desc})
    if data.form_yesno is not None:
        yes_no_strings = data.form_yesno
        if yes_no_strings != "":
            if yes_no_strings != "|":
                parts = yes_no_strings.split("|")
                yesvalue = parts[0]
                novalue = parts[1]

    if data.form_sepfile is not None:
        separation_file = data.form_sepfile

    return stage, primary_key, deflanguage, languages, yesvalue, \
        novalue, other_languages, yes_no_strings, default_language, separation_file


def get_form_data(project, form, request):
    res = {}
    data = request.dbsession.query(Form).filter(Form.project_id == project).filter(Form.form_id == form).first()
    if data:
        res["id"] = data.form_id
        res["name"] = data.form_name
        res["directory"] = data.form_directory
        res["schema"] = data.form_schema
    return res


def modification_date(filename):
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)


def get_number_of_submissions(odk_dir, directory):
    paths = ['forms', directory, 'submissions', '*.json']
    path = os.path.join(odk_dir, *paths)
    files = glob.glob(path)
    if files:
        files.sort(key=os.path.getmtime)
        return len(files), modification_date(files[0])
    else:
        return 0, None


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.find(".json") >= 0:
                ziph.write(os.path.join(root, file), os.path.basename(os.path.join(root, file)))


def zip_json_files(odk_dir, form):
    try:
        uid = str(uuid.uuid4())
        paths = ['tmp', uid+".zip"]
        path = os.path.join(odk_dir, *paths)
        zipf = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
        paths = ['forms', form, "submissions"]
        source_path = os.path.join(odk_dir, *paths)
        zipdir(source_path, zipf)
        zipf.close()
        return True, path
    except Exception as e:
        return False, str(e)


def handle_uploaded_file(f, target_file):
    max_size = 100
    tmp_filepath = target_file + "~"
    output_file = open(tmp_filepath, 'wb')
    current_size = 0
    while True:
        current_size = current_size + 1
        # MB chunks
        data = f.read(2 ** 20)
        if not data:
            break
        output_file.write(data)
        if current_size > max_size:
            os.remove(tmp_filepath)
            print('File upload too large')

    output_file.close()
    os.rename(tmp_filepath, target_file)


def checkout_submission(request, project, form, submission, project_of_assistant, assistant):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(Jsonlog.form_id == form,
                                                                                  Jsonlog.log_id == submission).update(
        {'status': 2})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(project_id=project, form_id=form, log_id=submission, log_sequence=sequence,
                             log_dtime=datetime.datetime.now(), log_action=2, enum_project=project_of_assistant,
                             coll_id=assistant)
    request.dbsession.add(new_record)


def cancel_checkout(request, project, form, submission, project_of_assistant, assistant):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(Jsonlog.form_id == form,
                                                                                  Jsonlog.log_id == submission).update(
        {'status': 1})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(project_id=project, form_id=form, log_id=submission, log_sequence=sequence,
                             log_dtime=datetime.datetime.now(), log_action=5, enum_project=project_of_assistant,
                             coll_id=assistant)
    request.dbsession.add(new_record)


def cancel_revision(request, project, form, submission, project_of_assistant, assistant, revision):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(Jsonlog.form_id == form,
                                                                                  Jsonlog.log_id == submission).update(
        {'status': 1})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(project_id=project, form_id=form, log_id=submission, log_sequence=sequence,
                             log_dtime=datetime.datetime.now(), log_action=6, enum_project=project_of_assistant,
                             coll_id=assistant, log_commit=revision)
    request.dbsession.add(new_record)


def fix_revision(request, project, form, submission, project_of_assistant, assistant, revision):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(Jsonlog.form_id == form,
                                                                                  Jsonlog.log_id == submission).update(
        {'status': 0})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(project_id=project, form_id=form, log_id=submission, log_sequence=sequence,
                             log_dtime=datetime.datetime.now(), log_action=0, enum_project=project_of_assistant,
                             coll_id=assistant, log_commit=revision)
    request.dbsession.add(new_record)


def fail_revision(request, project, form, submission, project_of_assistant, assistant, revision):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(Jsonlog.form_id == form,
                                                                                  Jsonlog.log_id == submission).update(
        {'status': 1})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(project_id=project, form_id=form, log_id=submission, log_sequence=sequence,
                             log_dtime=datetime.datetime.now(), log_action=7, enum_project=project_of_assistant,
                             coll_id=assistant, log_commit=revision)
    request.dbsession.add(new_record)


def disregard_revision(request, project, form, submission, project_of_assistant, assistant, notes):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(Jsonlog.form_id == form,
                                                                                  Jsonlog.log_id == submission).update(
        {'status': 4})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(project_id=project, form_id=form, log_id=submission, log_sequence=sequence,
                             log_dtime=datetime.datetime.now(), log_action=4, enum_project=project_of_assistant,
                             coll_id=assistant, log_notes=notes)
    request.dbsession.add(new_record)


def cancel_disregard_revision(request, project, form, submission, project_of_assistant, assistant, notes):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(Jsonlog.form_id == form,
                                                                                  Jsonlog.log_id == submission).update(
        {'status': 1})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(project_id=project, form_id=form, log_id=submission, log_sequence=sequence,
                             log_dtime=datetime.datetime.now(), log_action=8, enum_project=project_of_assistant,
                             coll_id=assistant, log_notes=notes)
    request.dbsession.add(new_record)
