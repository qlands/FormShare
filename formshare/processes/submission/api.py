import uuid
import os
import shutil
import glob
from decimal import Decimal
from subprocess import Popen, PIPE, check_call, CalledProcessError
from formshare.processes.db import get_form_schema, get_form_directory, get_primary_key, get_project_id_from_name
from formshare.processes.odk import get_odk_path
import datetime
from lxml import etree
from formshare.processes.elasticsearch.repository_index import get_datasets_from_form

__all__ = ['get_submission_media_files', 'json_to_csv', 'get_gps_points_from_form']


def get_gps_points_from_form(request, user, project, form):
    project_id = get_project_id_from_name(request, user, project)
    schema = get_form_schema(request, project_id, form)
    form_directory = get_form_directory(request, project_id, form)
    odk_dir = get_odk_path(request)
    paths = ['forms', form_directory, "repository", "create.xml"]
    if schema is not None:
        create_xml = os.path.join(odk_dir, *paths)
        data = []
        if os.path.exists(create_xml):
            tree = etree.parse(create_xml)
            root = tree.getroot()
            tables = root.find(".//tables")
            field = tables.find(".//field[@odktype='geopoint']")
            if field is not None:
                table = field.getparent()
                if table is not None:
                    s_field = field.get("name")
                    s_table = table.get("name")
                    key_fields = []
                    for tField in table.getchildren():
                        if tField.get("key") == "true":
                            key_fields.append(tField.get("name"))

                    sql = "SELECT concat(" + ",".join(
                        key_fields) + ") as rowkey," + s_field + " FROM " + schema + "." + s_table
                    points = request.dbsession.execute(sql).fetchall()
                    for point in points:
                        s_point = point[s_field]
                        if s_point is not None:
                            parts = s_point.split(" ")
                            if len(parts) >= 2:
                                data.append({'key': point["rowkey"], 'lati': parts[0], 'long': parts[1]})
                    return True, {'points': data}

            return False, {'points': data}
        else:
            return False, {'points': data}
    else:
        total, datasets = get_datasets_from_form(request, user, project, form)
        data = []
        for dataset in datasets:
            if '_geopoint' in dataset.keys():
                parts = dataset['_geopoint'].split(" ")
                if len(parts) >= 2:
                    data.append({'key': dataset["_submission_id"], 'lati': parts[0], 'long': parts[1]})
        return True, {'points': data}


def get_submission_media_files(request, project, form):
    uid = str(uuid.uuid4())
    schema = get_form_schema(request, project, form)
    form_directory = get_form_directory(request, project, form)
    odk_dir = get_odk_path(request)
    if schema is None:
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
    else:
        primary_key = get_primary_key(request, project, form)
        sql = "SELECT surveyid," + primary_key + " FROM " + schema + ".maintable"
        submissions = request.dbsession.execute(sql).fetchall()
        created = False
        for submission in submissions:
            key_value = submission[primary_key]

            if isinstance(key_value, datetime.datetime) or \
                    isinstance(key_value, datetime.date) or \
                    isinstance(key_value, datetime.time):
                key_value = key_value.isoformat().replace("T", " ")
            else:
                if isinstance(key_value, float):
                    key_value = str(key_value)
                else:
                    if isinstance(key_value, Decimal):
                        key_value = str(key_value)
                    else:
                        if isinstance(key_value, datetime.timedelta):
                            key_value = str(key_value)

            key_value = key_value.replace("/", "_")  # Replace invalid character for directory
            tmp_dir = os.path.join(odk_dir, *['tmp', uid, key_value])
            os.makedirs(tmp_dir)
            submission_id = submission.surveyid
            submissions_path = os.path.join(odk_dir, *['forms', form_directory, "submissions", submission_id, '*.*'])
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
    return False, ''


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
            return False, ""
    else:
        return False, ""
