from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
import logging
import os
import gettext
import uuid
from subprocess import Popen, PIPE, check_call
import glob
from formshare.processes.sse.messaging import send_task_status_to_form

log = logging.getLogger(__name__)
gettext.bindtextdomain('formshare', 'formshare:locate')
gettext.textdomain('formshare')
_ = gettext.gettext


class EmptyFileError(Exception):
    """
        Exception raised when there is an error while creating the CSV.
    """

    def __str__(self):
        return _('The ODK form does not contain any submissions')


class JQError(Exception):
    """
        Exception raised when there is an error while creating the CSV.
    """

    def __str__(self):
        return _('Error calling JQ')


class MySQLDenormalizeError(Exception):
    """
        Exception raised when there is an error while creating the CSV.
    """

    def __str__(self):
        return _('Error calling MySQLDenormalize')


@celeryApp.task(base=CeleryTask)
def build_csv(settings, form_directory, form_schema, csv_file):
    task_id = build_csv.request.id

    paths = ['odk', 'forms', form_directory, "submissions", 'maps']
    maps_path = os.path.join(settings['repository.path'], *paths)

    paths = ["utilities", "MySQLDenormalize", "mysqldenormalize"]
    mysql_denormalize = os.path.join(settings['odktools.path'], *paths)

    uid = str(uuid.uuid4())
    paths = ['tmp', uid]
    temp_path = os.path.join(settings['repository.path'], *paths)
    os.makedirs(temp_path)

    uid = str(uuid.uuid4())
    paths = ['tmp', uid]
    out_path = os.path.join(settings['repository.path'], *paths)
    os.makedirs(out_path)

    args = [mysql_denormalize, "-H " + settings['mysql.host'], "-P " + settings['mysql.port'],
            "-u " + settings['mysql.user'], "-p " + settings['mysql.password'], "-s " + form_schema, "-t maintable",
            "-m " + maps_path, "-o " + out_path, "-T " + temp_path, "-i"]

    send_task_status_to_form(settings, task_id, "Denormalizing database")
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        paths = ["*.json"]
        out_path = os.path.join(out_path, *paths)
        files = glob.glob(out_path)
        if files:
            # Join The files with JQ
            args = ["jq", "-s", "."]
            for file in files:
                args.append(file)
            send_task_status_to_form(settings, task_id, "Joining JSON files")
            p = Popen(args, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            if p.returncode == 0:
                uid = str(uuid.uuid4())
                paths = ['tmp', uid + ".json"]
                json_file = os.path.join(settings['repository.path'], *paths)
                file = open(json_file, "w")
                file.write(stdout.decode())
                file.close()
                # Convert the file to CSV
                args = ["json2csv", json_file, csv_file]
                send_task_status_to_form(settings, task_id, "Building CSV")
                check_call(args)

            else:
                log.error("JQ error: " + stderr.decode('utf-8') + "-" + stdout.decode('utf-8') + ":" + " ".join(args))
                raise JQError("JQ error: " + stderr.decode('utf-8') + "-" + stdout.decode('utf-8'))

        else:
            raise EmptyFileError(_('The ODK form does not contain any submissions'))
    else:
        log.error("MySQLDenormalize Error: " + stderr.decode('utf-8') + "-" + stdout.decode('utf-8') + ":"
                  + " ".join(args))
        raise MySQLDenormalizeError("MySQLDenormalize Error: " + stderr.decode('utf-8') + "-" +
                                    stdout.decode('utf-8'))
