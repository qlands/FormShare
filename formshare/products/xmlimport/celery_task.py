from requests.auth import HTTPDigestAuth
import gettext
import glob
import requests
import os
from celery.utils.log import get_task_logger

from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
from formshare.processes.sse.messaging import send_task_status_to_form

log = get_task_logger(__name__)


def internal_import_xml_files(
    settings,
    user,
    project_code,
    assistant,
    assistant_password,
    path_to_files,
    locale,
    task_id=None,
    task_object=None,
):
    parts = __file__.split("/products/")
    this_file_path = parts[0] + "/locale"
    es = gettext.translation("formshare", localedir=this_file_path, languages=[locale])
    es.install()
    _ = es.gettext
    if settings["server:main:root"] == "/":
        url_to_project = "http://{}:{}/user/{}/project/{}".format(
            settings["server:main:host"],
            settings["server:main:port"],
            user,
            project_code,
        )
    else:
        url_to_project = "http://{}:{}{}/user/{}/project/{}".format(
            settings["server:main:host"],
            settings["server:main:port"],
            settings["root"],
            user,
            project_code,
        )

    paths = ["report.txt"]
    report_file = os.path.join(path_to_files, *paths)

    path_to_submissions = path_to_files + "/*/"
    index = 0
    for a_directory in glob.iglob(path_to_submissions):
        index = index + 1
    total_files = index
    index = 1
    send_25 = True
    send_50 = True
    send_75 = True
    messages = []
    for a_directory in glob.iglob(path_to_submissions):
        if task_object is not None:
            if task_object.is_aborted():
                return
        files = {}
        files_array = []
        has_xml_file = False
        for a_file in glob.iglob(a_directory + "*"):
            if not os.path.isdir(a_file):
                if a_file.lower().find(".xml") >= 0:
                    has_xml_file = True
                files_array.append(a_file)
                file_name = os.path.basename(a_file)
                files[file_name] = open(a_file, "rb")
        if files and has_xml_file:
            # We post them internally
            try:  # pragma: no cover
                r = requests.post(
                    url_to_project + "/push",
                    auth=HTTPDigestAuth(assistant, assistant_password),
                    files=files,
                )
                if r.status_code != 201:
                    message = _(
                        "-Error {} while pushing submission {} to URL {}. Error \n\n{}\n\n"
                    ).format(
                        r.status_code, a_directory, url_to_project + "/push", r.text
                    )
                    log.error(message)
                    messages.append(message)
                else:
                    messages.append(
                        _("-Submission {} imported successfully").format(a_directory)
                    )
            except Exception as e:
                message = _(
                    "-Error while pushing submission {} to URL {}. Error \n\n{}\n\n"
                ).format(a_directory, url_to_project + "/push", str(e))
                log.error(message)
                messages.append(message)
        else:
            message = _(
                "-The directory {} does not have any submission files or it does not have an xml data file"
            ).format(a_directory)
            log.error(message)
            messages.append(message)
        percentage = (index * 100) / total_files
        # We report chucks to not overload the messaging system
        if 25 <= percentage <= 50:
            if send_25:
                send_task_status_to_form(settings, task_id, _("25% processed"))
                send_25 = False
        if 50 <= percentage <= 75:
            if send_50:
                send_task_status_to_form(settings, task_id, _("50% processed"))
                send_50 = False
        if 75 <= percentage <= 100:
            if send_75:
                send_task_status_to_form(settings, task_id, _("75% processed"))
                send_75 = False
        index = index + 1

    send_task_status_to_form(settings, task_id, _("Writing report"))
    with open(report_file, "w") as f:
        for a_message in messages:
            f.write(a_message + "\n")


@celeryApp.task(bind=True, base=CeleryTask)
def import_xml_files(
    self,
    settings,
    user,
    project_code,
    assistant,
    assistant_password,
    path_to_files,
    locale,
    test_task_id=None,
):
    if test_task_id is None:
        task_id = import_xml_files.request.id
    else:
        task_id = test_task_id
    internal_import_xml_files(
        settings,
        user,
        project_code,
        assistant,
        assistant_password,
        path_to_files,
        locale,
        task_id,
        self,
    )
