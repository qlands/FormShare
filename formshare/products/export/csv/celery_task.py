from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
import logging
import os
import gettext
import uuid
from subprocess import Popen, PIPE
import glob
from formshare.processes.sse.messaging import send_task_status_to_form
import json
from pandas.io.json import json_normalize
from collections import OrderedDict
import pandas as pd

log = logging.getLogger(__name__)


class EmptyFileError(Exception):
    """
        Exception raised when there is an error while creating the CSV.
    """


class DummyError(Exception):
    """
        Exception raised when there is an error while creating the CSV.
    """


class MySQLDenormalizeError(Exception):
    """
        Exception raised when there is an error while creating the CSV.
    """


def flatten_json(y):
    out = OrderedDict()

    def flatten(x, name=''):
        if type(x) is OrderedDict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 1
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out


def gather_array_sizes(data, array_dict):
    for key, value in data.items():
        if type(value) is list:
            current_size = array_dict.get(key, 0)
            if len(value) > current_size:
                array_dict[key] = len(value)
            for an_item in value:
                gather_array_sizes(an_item, array_dict)


@celeryApp.task(base=CeleryTask)
def build_csv(settings, form_directory, form_schema, csv_file, locale):
    parts = __file__.split('/products/')
    this_file_path = parts[0] + "/locale"
    es = gettext.translation('formshare',
                             localedir=this_file_path,
                             languages=[locale])
    es.install()
    _ = es.gettext
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

    send_task_status_to_form(settings, task_id, _("Denormalizing database"))
    log.error(" ".join(args))
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:

        paths = ["*.json"]
        out_path2 = os.path.join(out_path, *paths)
        files = glob.glob(out_path2)
        if files:
            send_task_status_to_form(settings, task_id, _("Calculating the number of columns"))
            array_dict = {}
            for aFile in files:
                with open(aFile) as json_file:
                    data = json.load(json_file)
                    gather_array_sizes(data, array_dict)
            array_sizes = []
            for key, value in array_dict.items():
                array_sizes.append(key + ":" + str(value))

            paths = ["utilities", "createDummyJSON", "createdummyjson"]
            create_dummy_json = os.path.join(settings['odktools.path'], *paths)

            manifest_file = os.path.join(settings['repository.path'], *["odk", "forms", form_directory,
                                                                        "repository", "manifest.xml"])
            paths = ["dummy.djson"]
            dummy_json = os.path.join(out_path, *paths)

            args = [create_dummy_json, "-i " + manifest_file, "-o " + dummy_json, "-r"]
            if len(array_sizes) > 0:
                args.append("-a " + ",".join(array_sizes))
            p = Popen(args, stdout=PIPE, stderr=PIPE)

            p.communicate()
            if p.returncode == 0:
                dataframe_array = []

                # Adds the dummy
                with open(dummy_json) as json_file:
                    data = json.load(json_file, object_pairs_hook=OrderedDict)
                flat = flatten_json(data)
                temp = json_normalize(flat)
                cols = []
                for col in temp.columns:
                    cols.append(col.replace(".", ""))
                temp.columns = cols
                dataframe_array.append(temp)
                send_task_status_to_form(settings, task_id, _("Flattening the JSON files"))
                for file in files:
                    with open(file) as json_file:
                        data = json.load(json_file, object_pairs_hook=OrderedDict)
                    flat = flatten_json(data)
                    temp = json_normalize(flat)
                    cols = []
                    for col in temp.columns:
                        cols.append(col.replace(".", ""))
                    temp.columns = cols
                    dataframe_array.append(temp)
                send_task_status_to_form(settings, task_id, _("Concatenating submissions"))
                join = pd.concat(dataframe_array, sort=False)
                join = join.iloc[1:]
                send_task_status_to_form(settings, task_id, _("Saving CSV"))
                join.to_csv(csv_file, index=False, encoding='utf-8')

            else:
                raise DummyError(_('Error while creating the dummy JSON file'))

        else:
            raise EmptyFileError(_('The ODK form does not contain any submissions'))
    else:
        log.error("MySQLDenormalize Error: " + stderr.decode('utf-8') + "-" + stdout.decode('utf-8') + ":"
                  + " ".join(args))
        raise MySQLDenormalizeError("MySQLDenormalize Error: " + stderr.decode('utf-8') + "-"
                                    + stdout.decode('utf-8'))
