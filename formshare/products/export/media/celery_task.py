import datetime
import gettext
import glob
import logging
import os
import shutil
import traceback
import uuid
import zipfile
from decimal import Decimal

from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask
from formshare.models import get_engine
from formshare.processes.email.send_async_email import send_async_email
from formshare.processes.sse.messaging import send_task_status_to_form

log = logging.getLogger("formshare")


class BuildError(Exception):
    """
        Exception raised when there is an error while creating the repository.
    """


@celeryApp.task(base=CeleryTask)
def build_media_zip(
    settings,
    odk_dir,
    form_directories,
    form_schema,
    zip_file,
    primary_key,
    locale,
    test_task_id=None,
):

    parts = __file__.split("/products/")
    this_file_path = parts[0] + "/locale"
    es = gettext.translation("formshare", localedir=this_file_path, languages=[locale])
    es.install()
    _ = es.gettext
    try:
        if test_task_id is None:
            task_id = build_media_zip.request.id
        else:
            task_id = test_task_id

        created = False
        engine = get_engine(settings)
        sql = "SELECT count(surveyid) as total FROM " + form_schema + ".maintable"
        submissions = engine.execute(sql).fetchone()
        total = submissions.total

        sql = "SELECT surveyid," + primary_key + " FROM " + form_schema + ".maintable"
        submissions = engine.execute(sql).fetchall()
        uid = str(uuid.uuid4())
        repo_dir = settings["repository.path"]
        index = 0
        send_25 = True
        send_50 = True
        send_75 = True
        for submission in submissions:
            index = index + 1
            percentage = (index * 100) / total
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
            key_value = submission[primary_key]

            if (
                isinstance(key_value, datetime.datetime)
                or isinstance(key_value, datetime.date)
                or isinstance(key_value, datetime.time)
            ):
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
                        else:
                            if isinstance(key_value, int):
                                key_value = str(key_value)

            key_value = key_value.replace(
                "/", "_"
            )  # Replace invalid character for directory
            tmp_dir = os.path.join(repo_dir, *["tmp", uid, key_value])
            os.makedirs(tmp_dir)
            submission_id = submission.surveyid
            for form_directory in form_directories:
                submissions_dir = os.path.join(
                    odk_dir, *["forms", form_directory, "submissions", submission_id]
                )
                submissions_path = os.path.join(
                    odk_dir,
                    *["forms", form_directory, "submissions", submission_id, "*.*"]
                )
                if os.path.exists(submissions_dir):
                    files = glob.glob(submissions_path)
                    if files:
                        for file in files:
                            shutil.copy(file, tmp_dir)
                            created = True
        engine.dispose()
    except Exception as e:
        email_from = settings.get("mail.from", None)
        email_to = settings.get("mail.error", None)
        send_async_email(
            settings,
            email_from,
            email_to,
            "Build repository error",
            "\n\nError: {}\n\nTraceback: {}\n\n".format(str(e), traceback.format_exc()),
            None,
            locale,
        )
        raise BuildError(_("Error while zipping media files"))

    if created:
        tmp_dir = os.path.join(repo_dir, *["tmp", uid])
        send_task_status_to_form(settings, task_id, _("Creating zip file"))
        shutil.make_archive(zip_file.replace(".zip", ""), "zip", tmp_dir)
        shutil.rmtree(tmp_dir)
    else:
        # Write an empty zipFile
        send_task_status_to_form(settings, task_id, _("Creating empty zip file"))
        with zipfile.ZipFile(zip_file, "w") as file:
            file.writestr("empty.txt", _("There are no media files"))
