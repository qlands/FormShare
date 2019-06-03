import uuid
import os
import shutil
import glob
from subprocess import Popen, PIPE, check_call, CalledProcessError
from formshare.processes.db import get_form_schema, get_form_directory, get_project_form_colors
from formshare.processes.odk import get_odk_path
from formshare.processes.elasticsearch.repository_index import get_datasets_from_form, get_datasets_from_project
from formshare.processes.color_hash import ColorHash
from formshare.models.formshare import Submission, Jsonlog
import logging
from sqlalchemy import exc
from decimal import Decimal
from zope.sqlalchemy import mark_changed
from lxml import etree
import datetime
import re
import paginate
from sqlalchemy import create_engine
from formshare.processes.elasticsearch.repository_index import delete_dataset_index, delete_from_dataset_index
from formshare.processes.elasticsearch.record_index import delete_record_index, delete_from_record_index

__all__ = ['get_submission_media_files', 'json_to_csv', 'get_gps_points_from_form',
           'get_gps_points_from_project', 'get_tables_from_form', 'update_table_desc', 'update_field_desc',
           'update_field_sensitive', 'get_fields_from_table', 'get_table_desc', 'is_field_key', 'get_request_data',
           'update_data', 'get_request_data_jqgrid', 'delete_submission', 'delete_all_submission']

log = logging.getLogger(__name__)


def get_gps_points_from_project(request, user, project, project_id, query_from=None, query_size=None):
    total, datasets = get_datasets_from_project(request.registry.settings, user, project, query_from, query_size)
    data = []
    colors = get_project_form_colors(request, project_id)
    for dataset in datasets:
        if '_geopoint' in dataset.keys():
            parts = dataset['_geopoint'].split(" ")
            if len(parts) >= 2:
                if dataset["_xform_id_string"] not in colors.keys():
                    color = ColorHash(dataset["_xform_id_string"]).hex
                else:
                    color = colors[dataset["_xform_id_string"]]
                data.append(
                    {'key': dataset["_xform_id_string"], 'lati': parts[0], 'long': parts[1],
                     'options': {'iconShape': 'circle-dot', 'borderWidth': 5, 'borderColor': color}})
    return True, {'points': data}


def get_gps_points_from_form(request, user, project, form, query_from=None, query_size=None):
    total, datasets = get_datasets_from_form(request.registry.settings, user, project, form, query_from, query_size)
    data = []
    for dataset in datasets:
        if '_geopoint' in dataset.keys():
            parts = dataset['_geopoint'].split(" ")
            if len(parts) >= 2:
                data.append({'key': dataset["_submission_id"], 'lati': parts[0], 'long': parts[1]})
    return True, {'points': data}


def get_submission_media_files(request, project, form):
    uid = str(uuid.uuid4())
    form_directory = get_form_directory(request, project, form)
    odk_dir = get_odk_path(request)

    submissions_path = os.path.join(odk_dir, *['forms', form_directory, "submissions", '*.json'])
    submissions = glob.glob(submissions_path)
    if submissions:
        created = False
        for submission in submissions:
            submission_id = os.path.basename(submission).replace(".json", "")
            tmp_dir = os.path.join(odk_dir, *['tmp', uid, submission_id])
            os.makedirs(tmp_dir)
            submissions_path = os.path.join(odk_dir,
                                            *['forms', form_directory, "submissions", submission_id, '*.*'])
            files = glob.glob(submissions_path)
            if files:
                for file in files:
                    shutil.copy(file, tmp_dir)
                    created = True
        if created:
            tmp_dir = os.path.join(odk_dir, *['tmp', uid])
            zip_file = os.path.join(odk_dir, *['tmp', uid])
            shutil.make_archive(zip_file, 'zip', tmp_dir)
            return True, zip_file + ".zip"

    return False, request.translate("There are no media files to download")


def json_to_csv(request, project, form):
    uid = str(uuid.uuid4())
    form_directory = get_form_directory(request, project, form)
    odk_dir = get_odk_path(request)
    # Create temporary directory
    tmp_dir = os.path.join(odk_dir, *['tmp', uid])
    os.makedirs(tmp_dir)
    # Copy all submissions to the temporary directory
    paths = ['forms', form_directory, "submissions", "*.json"]
    path = os.path.join(odk_dir, *paths)
    files = glob.glob(path)
    if files:
        for aFile in files:
            shutil.copy(aFile, tmp_dir)
    # Get all submissions
    paths = ['tmp', uid, "*.json"]
    path = os.path.join(odk_dir, *paths)
    files = glob.glob(path)
    if files:
        # Join The files with JQ
        args = ["jq", "-s", "."]
        for file in files:
            args.append(file)
        p = Popen(args, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if p.returncode == 0:
            uid = str(uuid.uuid4())
            paths = ['tmp', uid + ".json"]
            json_file = os.path.join(odk_dir, *paths)
            file = open(json_file, "w")
            file.write(stdout.decode())
            file.close()
            # Convert the file to CSV
            paths = ['tmp', uid + ".csv"]
            csv_file = os.path.join(odk_dir, *paths)
            args = ["json2csv", json_file, csv_file]
            try:
                check_call(args)
            except CalledProcessError as e:
                msg = "Error creating CSV files \n"
                msg = msg + "Command: " + " ".join(args) + "\n"
                msg = msg + "Error: \n"
                msg = msg + str(e)
                return False, msg
            return True, csv_file
        else:
            return False, stderr
    else:
        return False, request.translate("There are not submissions to download")


def get_tables_from_form(request, project, form):
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    create_file = os.path.join(odk_dir, *['forms', form_directory, 'repository', 'create.xml'])
    tree = etree.parse(create_file)
    root = tree.getroot()
    element_lkp_tables = root.find(".//lkptables")
    element_tables = root.find(".//tables")
    # Append all tables
    tables = element_tables.findall(".//table")
    result = []
    if tables:
        for table in tables:
            fields = []
            sfields = []
            num_sensitive = 0
            for field in table.getchildren():
                if field.tag == "field":
                    desc = field.get('name', '')
                    if desc == "":
                        desc = request.translate("Without description")
                    fields.append({'name': field.get('name'), 'desc': desc})
                    sfields.append(field.get('name') + "-" + desc)
                    sensitive = field.get('sensitive', 'false')
                    if sensitive == 'true':
                        num_sensitive = num_sensitive + 1
            if table.get('name').find('_msel_') >= 0:
                multi = True
            else:
                multi = False
            result.append({'name': table.get('name'), 'desc': table.get('desc'), 'fields': fields, 'lookup': False,
                           'multi': multi, 'sfields': ",".join(sfields), 'numsensitive': num_sensitive})
    # Append all lookup tables
    tables = element_lkp_tables.findall(".//table")
    if tables:
        for table in tables:
            fields = []
            sfields = []
            num_sensitive = 0
            for field in table.getchildren():
                if field.tag == "field":
                    desc = field.get('name', '')
                    if desc == "":
                        desc = request.translate("Without description")
                    fields.append({'name': field.get('name'), 'desc': desc})
                    sfields.append(field.get('name') + "-" + desc)
                    sensitive = field.get('sensitive', 'false')
                    if sensitive == 'true':
                        num_sensitive = num_sensitive + 1
            result.append({'name': table.get('name'), 'desc': table.get('desc'), 'fields': fields, 'lookup': True,
                           'multi': False, 'sfields': ",".join(sfields), 'numsensitive': num_sensitive})

    return result


def update_table_desc(request, project, form, table_name, description):
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    create_file = os.path.join(odk_dir, *['forms', form_directory, 'repository', 'create.xml'])
    if os.path.exists(create_file):
        tree = etree.parse(create_file)
        root = tree.getroot()
        table = root.find(".//table[@name='" + table_name + "']")
        if table is not None:
            table.set("desc", description)
        else:
            log.error("updateTables. Cannot find table " + table_name)
            return False

        try:
            # Crete a backup the first time the file is edited
            if not os.path.exists(create_file + ".bk"):
                shutil.copy(create_file, create_file + ".bk")
            tree.write(create_file, pretty_print=True, xml_declaration=True, encoding="utf-8")
            return True
        except Exception as e:
            log.error("updateTables. Error updating create XML. Error:" + str(e))
        return False
    else:
        return False


def update_field_desc(request, project, form, table_name, field_name, description):
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    create_file = os.path.join(odk_dir, *['forms', form_directory, 'repository', 'create.xml'])
    if os.path.exists(create_file):
        tree = etree.parse(create_file)
        root = tree.getroot()
        table = root.find(".//table[@name='" + table_name + "']")
        if table is not None:
            field = table.find(".//field[@name='" + field_name + "']")
            if field is not None:
                field.set("desc", description)
            try:
                # Crete a backup the first time the file is edited
                if not os.path.exists(create_file + ".bk"):
                    shutil.copy(create_file, create_file + ".bk")
                tree.write(create_file, pretty_print=True, xml_declaration=True, encoding="utf-8")
                return True
            except Exception as e:
                log.error("updateField. Error updating create XML. Error:" + str(e))
            return False
        else:
            return False
    else:
        return False


def update_field_sensitive(request, project, form, table_name, field_name, sensitive, protection="None"):
    if sensitive:
        sensitive = "true"
    else:
        sensitive = "false"
        protection = "None"
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    create_file = os.path.join(odk_dir, *['forms', form_directory, 'repository', 'create.xml'])
    if os.path.exists(create_file):
        tree = etree.parse(create_file)
        root = tree.getroot()
        table = root.find(".//table[@name='" + table_name + "']")
        if table is not None:
            field = table.find(".//field[@name='" + field_name + "']")
            if field is not None:
                field.set("sensitive", sensitive)
                field.set("protection", protection)
            try:
                # Crete a backup the first time the file is edited
                if not os.path.exists(create_file + ".bk"):
                    shutil.copy(create_file, create_file + ".bk")
                tree.write(create_file, pretty_print=True, xml_declaration=True, encoding="utf-8")
                return True
            except Exception as e:
                log.error("updateField. Error updating create XML. Error:" + str(e))
            return False
        else:
            return False
    else:
        return False


def get_fields_from_table(request, project, form, table_name, current_fields, with_rowuuid=False):
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    create_file = os.path.join(odk_dir, *['forms', form_directory, 'repository', 'create.xml'])
    tree = etree.parse(create_file)
    root = tree.getroot()
    table = root.find(".//table[@name='" + table_name + "']")
    result = []
    checked = 0
    if table is not None:
        for field in table.getchildren():
            if field.tag == "field":
                if field.get('name') != 'rowuuid' or with_rowuuid:
                    found = False
                    for cfield in current_fields:
                        if field.get('name') == cfield:
                            found = True
                            checked = checked + 1
                    desc = field.get('desc')
                    if desc == "" or desc == 'Without label':
                        desc = field.get('name') + " - Without description"
                    result.append({'name': field.get('name'), 'desc': desc,
                                   'type': field.get('type'), 'size': field.get('size'),
                                   'decsize': field.get('decsize'), 'checked': found,
                                   'sensitive': field.get('sensitive'), 'protection': field.get('protection', 'None'),
                                   'key': field.get('key', 'false'), 'rlookup': field.get('rlookup', 'false'),
                                   'rtable': field.get('rtable', 'None')})
            else:
                break
    return result, checked


def get_table_desc(request, project, form, table_name):
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    create_file = os.path.join(odk_dir, *['forms', form_directory, 'repository', 'create.xml'])
    tree = etree.parse(create_file)
    root = tree.getroot()
    table = root.find(".//table[@name='" + table_name + "']")
    if table is not None:
        return table.get("desc")
    return ""


def is_field_key(request, project, form, table_name, field_name):
    if table_name == "maintable" and field_name == "surveyid":
        return True
    if table_name == "maintable" and field_name == "originid":
        return True
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    create_file = os.path.join(odk_dir, *['forms', form_directory, 'repository', 'create.xml'])
    tree = etree.parse(create_file)
    root = tree.getroot()
    table = root.find(".//table[@name='" + table_name + "']")
    if table is not None:
        for field in table.getchildren():
            if field.tag == "field":
                if field.get("name") == field_name:
                    if field.get("key") == "true":
                        return True
                    if field.get("odktype") == "geopoint":
                        return True
            else:
                break
    return False


def get_request_data(request, project, form, table_name, draw, fields, start, length, order_index, order_direction,
                     search_value):
    schema = get_form_schema(request, project, form)
    sql_fields = ','.join(fields)
    not_null_fields_array = []
    for a_field in fields:
        not_null_fields_array.append("IFNULL(" + a_field + ",'')")
    not_null_fields = ','.join(not_null_fields_array)
    table_order = fields[order_index]

    if search_value == "":
        sql = "SELECT " + sql_fields + " FROM " + schema + "." + table_name
        where_clause = ''
    else:
        sql = "SELECT " + sql_fields + " FROM " + schema + "." + table_name
        sql = sql + " WHERE LOWER(CONCAT(" + not_null_fields + ")) like '%" + search_value.lower() + "%'"
        where_clause = " WHERE LOWER(CONCAT(" + not_null_fields + ")) like '%" + search_value.lower() + "%'"

    sql = sql + " ORDER BY " + table_order + " " + order_direction
    sql = sql + " LIMIT " + str(start) + "," + str(length)
    count_sql = "SELECT count(*) as total FROM " + schema + "." + table_name + where_clause
    mark_changed(request.dbsession)
    records = request.dbsession.execute(sql).fetchall()
    data = []
    if records is not None:
        for record in records:
            a_record = {'DT_RowId': record.rowuuid}
            for field in fields:
                try:
                    if isinstance(record[field], datetime.datetime) or isinstance(record[field],
                                                                                  datetime.date) or isinstance(
                            record[field], datetime.time):
                        a_record[field] = record[field].isoformat().replace("T", " ")
                    else:
                        if isinstance(record[field], float):
                            a_record[field] = str(record[field])
                        else:
                            if isinstance(record[field], Decimal):
                                a_record[field] = str(record[field])
                            else:
                                if isinstance(record[field], datetime.timedelta):
                                    a_record[field] = str(record[field])
                                else:
                                    if field != "rowuuid":
                                        a_record[field] = record[field]
                                    else:
                                        a_record[field] = record[field][-12:]
                except Exception as e:
                    a_record[field] = "AJAX Data error. Report this error to support_for_cabi@qlands.com"
                    log.error("AJAX Error in field " + field + ". Error: " + str(e))
            data.append(a_record)

    records = request.dbsession.execute(count_sql).fetchone()
    total = records.total

    result = {'draw': draw, 'recordsTotal': total, 'recordsFiltered': total, 'data': data}
    return result


def get_request_data_jqgrid(request, project, form, table_name, fields, current_page, length, table_order,
                            order_direction, search_field, search_string, search_operator):
    schema = get_form_schema(request, project, form)
    sql_fields = ','.join(fields)

    if search_field is None or search_string == "":
        sql = "SELECT " + sql_fields + " FROM " + schema + "." + table_name
        where_clause = ''
    else:
        sql = "SELECT " + sql_fields + " FROM " + schema + "." + table_name
        if search_operator == 'like':
            sql = sql + " WHERE LOWER(" + search_field + ") like '%" + search_string.lower() + "%'"
            where_clause = " WHERE LOWER(" + search_field + ") like '%" + search_string.lower() + "%'"
        else:
            sql = sql + " WHERE LOWER(" + search_field + ") not like '%" + search_string.lower() + "%'"
            where_clause = " WHERE LOWER(" + search_field + ") not like '%" + search_string.lower() + "%'"

    count_sql = "SELECT count(*) as total FROM " + schema + "." + table_name + where_clause
    records = request.dbsession.execute(count_sql).fetchone()
    total = records.total

    collection = list(range(total))
    page = paginate.Page(collection, current_page, length)
    if page.first_item is not None:
        start = page.first_item-1
    else:
        start = 0

    if table_order is not None:
        sql = sql + " ORDER BY " + table_order + " " + order_direction
    sql = sql + " LIMIT " + str(start) + "," + str(length)

    mark_changed(request.dbsession)
    records = request.dbsession.execute(sql).fetchall()
    data = []
    if records is not None:
        for record in records:
            a_record = {}
            for field in fields:
                try:
                    if isinstance(record[field], datetime.datetime) or isinstance(record[field],
                                                                                  datetime.date) or isinstance(
                            record[field], datetime.time):
                        a_record[field] = record[field].isoformat().replace("T", " ")
                    else:
                        if isinstance(record[field], float):
                            a_record[field] = str(record[field])
                        else:
                            if isinstance(record[field], Decimal):
                                a_record[field] = str(record[field])
                            else:
                                if isinstance(record[field], datetime.timedelta):
                                    a_record[field] = str(record[field])
                                else:
                                    a_record[field] = record[field]

                except Exception as e:
                    a_record[field] = "AJAX Data error. Report this error to support_for_cabi@qlands.com"
                    log.error("AJAX Error in field " + field + ". Error: " + str(e))
            data.append(a_record)

    result = {'records': total, 'page': current_page, 'total': page.page_count, 'rows': data}
    return result


def update_data(request, project, form, table_name, row_uuid, field, value):
    schema = get_form_schema(request, project, form)
    sql = "UPDATE " + schema + "." + table_name + " SET " + field + " = '" + value + "'"
    sql = sql + " WHERE rowuuid = '" + row_uuid + "'"
    try:
        request.dbsession.execute(sql)
        mark_changed(request.dbsession)
        res = {"data": {field: value}}
        return res
    except exc.IntegrityError as e:
        p1 = re.compile(r'`(\w+)`')
        m1 = p1.findall(str(e))
        if m1:
            if len(m1) == 6:
                lookup = get_table_desc(request, project, form, m1[4])
                return {"fieldErrors": [{'name': field,
                                         'status': 'Cannot update value. Check the valid values in lookup table "' +
                                                   lookup + '"'}]}
        return {
            "fieldErrors": [{'name': field, 'status': 'Cannot update value. Check the valid values in lookup table'}]}
    except Exception as ex:
        log.error(str(ex))
        return {"fieldErrors": [{'name': field, 'status': 'Unknown error'}]}


def delete_submission(request, user, project, form, row_uuid, project_code):
    schema = get_form_schema(request, project, form)
    sql = "SELECT surveyid FROM " + schema + ".maintable WHERE rowuuid = '" + row_uuid + "'"
    records = request.dbsession.execute(sql).fetchone()
    submission_id = records.surveyid
    try:
        odk_dir = get_odk_path(request)
        form_directory = get_form_directory(request, project, form)

        # Remove the submissions from the submission DB created by ODK Tools
        paths = ['forms', form_directory, 'submissions', "logs", "imported.sqlite"]
        imported_db = os.path.join(odk_dir, *paths)
        sqlite_engine = 'sqlite:///{}'.format(imported_db)
        engine = create_engine(sqlite_engine)
        try:
            engine.execute("DELETE FROM submissions WHERE submission_id ='{}'".format(submission_id))
        except Exception as e:
            log.error("Error {} removing submission {} from {}").format(str(e), submission_id, imported_db)
        engine.dispose()

        # Remove the submission from the database
        request.dbsession.query(Submission).filter(Submission.project_id == project).\
            filter(Submission.form_id == form).filter(Submission.submission_id == submission_id).delete()
        mark_changed(request.dbsession)

        # Try to remove all associated files
        try:
            paths = ['forms', form_directory, 'submissions', submission_id]
            submissions_dir = os.path.join(odk_dir, *paths)
            shutil.rmtree(submissions_dir)
        except Exception as e:
            log.error("Error deleting submission directory for id {}. Error: {}".format(submission_id, str(e)))
        try:
            paths = ['forms', form_directory, 'submissions', submission_id + ".xml"]
            xml_file = os.path.join(odk_dir, *paths)
            os.remove(xml_file)
        except Exception as e:
            log.error("Error deleting submission xml file for id {}. Error: {}".format(submission_id, str(e)))
        try:
            paths = ['forms', form_directory, 'submissions', submission_id + ".json"]
            json_file = os.path.join(odk_dir, *paths)
            os.remove(json_file)
        except Exception as e:
            log.error("Error deleting submission json file for id {}. Error: {}".format(submission_id, str(e)))
        try:
            paths = ['forms', form_directory, 'submissions', submission_id + ".ordered.json"]
            json_file = os.path.join(odk_dir, *paths)
            os.remove(json_file)
        except Exception as e:
            log.error("Error deleting ordered submission json file for id {}. Error: {}".format(submission_id, str(e)))
        try:
            paths = ['forms', form_directory, 'submissions', submission_id + ".log"]
            log_file = os.path.join(odk_dir, *paths)

            with open(log_file) as f:
                lines = f.readlines()
                for line in lines:
                    parts = line.split(",")
                    delete_from_record_index(request.registry.settings, user, project_code, form, schema, parts[1])

            os.remove(log_file)
        except Exception as e:
            log.error("Error deleting submission row logging file for id {}. Error: {}".format(submission_id, str(e)))

        delete_from_dataset_index(request.registry.settings, user, project_code, form, submission_id)

        # Finally remove the submission from the repository database
        sql = "DELETE FROM " + schema + ".maintable WHERE rowuuid = '" + row_uuid + "'"
        request.dbsession.execute(sql)
        mark_changed(request.dbsession)
        return True
    except Exception as e:
        log.error("Unable to remove submission {} using rowuuid {}. Error {}".format(submission_id, row_uuid, str(e)))
    return False


def delete_all_submission(request, user, project, form, project_code):
    schema = get_form_schema(request, project, form)
    try:
        request.dbsession.query(Submission).filter(Submission.project_id == project).\
            filter(Submission.form_id == form).delete()
        request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project). \
            filter(Jsonlog.form_id == form).delete()
        mark_changed(request.dbsession)

        odk_dir = get_odk_path(request)
        form_directory = get_form_directory(request, project, form)
        paths = ['forms', form_directory, 'submissions']
        submissions_dir = os.path.join(odk_dir, *paths)
        shutil.rmtree(submissions_dir)
        paths = ['forms', form_directory, 'submissions']
        os.makedirs(os.path.join(odk_dir, *paths))
        paths = ['forms', form_directory, 'submissions', 'logs']
        os.makedirs(os.path.join(odk_dir, *paths))
        paths = ['forms', form_directory, 'submissions', 'maps']
        os.makedirs(os.path.join(odk_dir, *paths))

        sql = "DELETE FROM " + schema + ".maintable"
        request.dbsession.execute(sql)
        mark_changed(request.dbsession)

        delete_dataset_index(request.registry.settings, user, project_code, form)
        delete_record_index(request.registry.settings, user, project_code, form)

        return True, ""
    except Exception as e:
        log.error("Unable to remove submissions. Error {}".format(str(e)))
        return False, str(e)
