import uuid
import os
import shutil
import glob
from decimal import Decimal
from subprocess import Popen, PIPE, check_call, CalledProcessError
from formshare.processes.db import get_form_schema, get_form_directory, get_primary_key
from formshare.processes.odk import get_odk_path
import datetime
from formshare.processes.elasticsearch.repository_index import get_datasets_from_form, get_datasets_from_project
from formshare.processes.color_hash import ColorHash
import logging

__all__ = ['get_submission_media_files', 'json_to_csv', 'get_gps_points_from_form', 'generate_xlsx_file',
           'get_gps_points_from_project']

log = logging.getLogger(__name__)


def get_gps_points_from_project(request, user, project, query_from=None, query_size=None):
    total, datasets = get_datasets_from_project(request.registry.settings, user, project, query_from, query_size)
    data = []
    for dataset in datasets:
        if '_geopoint' in dataset.keys():
            parts = dataset['_geopoint'].split(" ")
            if len(parts) >= 2:
                color = ColorHash(dataset["_xform_id_string"])
                data.append(
                    {'key': dataset["_xform_id_string"], 'lati': parts[0], 'long': parts[1],
                     'options': {'iconShape': 'circle-dot', 'borderWidth': 5, 'borderColor': color.hex}})
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


def generate_xlsx_file(request, project, form, include_sensitive=False):
    odk_dir = get_odk_path(request)
    form_directory = get_form_directory(request, project, form)
    form_schema = get_form_schema(request, project, form)
    mysql_user = request.registry.settings['mysql.user']
    mysql_password = request.registry.settings['mysql.password']
    mysql_host = request.registry.settings['mysql.host']
    mysql_port = request.registry.settings['mysql.port']
    odk_tools_dir = request.registry.settings['odktools.path']

    paths = ['forms', form_directory, "repository", "create.xml"]
    create_xml = os.path.join(odk_dir, *paths)

    paths = [odk_tools_dir, "utilities", "MySQLToXLSX", "mysqltoxlsx"]
    mysql_to_xlsx = os.path.join(odk_dir, *paths)

    uid = str(uuid.uuid4())
    paths = ['tmp', uid + ".xlsx"]
    xlsx_file = os.path.join(odk_dir, *paths)

    paths = ['tmp', uid]
    temp_dir = os.path.join(odk_dir, *paths)
    os.makedirs(temp_dir)

    args = [mysql_to_xlsx, "-H " + mysql_host, "-P " + mysql_port, "-u " + mysql_user, "-p " + mysql_password,
            "-s " + form_schema, "-x " + create_xml, "-o " + xlsx_file, "-T " + temp_dir]

    if include_sensitive:
        args.append("-i")

    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        return True, xlsx_file
    else:
        log.error("MySQLToXLSX Error: " + stderr + "-" + stdout + ". Args: " + " ".join(args))
        error = stdout + stderr
        if error.find("Worksheet name is already in use") >= 0:
            return False, request.translate(
                'A worksheet name has been repeated. Excel only allow 30 characters in the worksheet name. '
                'You can fix this by editing the dictionary and change the description of the tables to a maximum of '
                '30 characters.\n Please report this error to support_for_cabi@qlands.com')
        else:
            return False, request.transalate('Unknown error while creating the XLSX. Sorry about this. '
                                             'Please report this error to support_for_ilri@qlands.com')
