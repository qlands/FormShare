import os
from lxml import etree
from formshare.models import Odkform as Form
from formshare.models import (
    Collaborator,
    Submission,
    Jsonlog,
    Jsonhistory,
    map_from_schema,
    Formacces,
    Collingroup,
    Formgrpacces,
)
import datetime
import glob
import uuid
import zipfile
import re
from formshare.config.encdecdata import decode_data
from formshare.processes.db.form import get_assistant_forms
from formshare.processes.db.assistant import get_project_from_assistant
import logging
from sqlalchemy.event import listen

log = logging.getLogger("formshare")


def get_assistant_name(request, project, assistant):
    enum = (
        request.dbsession.query(Collaborator)
        .filter(Collaborator.project_id == project)
        .filter(Collaborator.coll_id == assistant)
        .first()
    )
    if enum is not None:
        return enum.coll_name
    else:
        return ""


def is_assistant_active(request, project, assistant):
    enum = (
        request.dbsession.query(Collaborator)
        .filter(Collaborator.project_id == project)
        .filter(Collaborator.coll_id == assistant)
        .first()
    )
    if enum is not None:
        if enum.coll_active == 1:
            return True
        else:
            return False
    else:
        return False


def get_assistant_password(request, project, assistant):
    enum = (
        request.dbsession.query(Collaborator)
        .filter(Collaborator.project_id == project)
        .filter(Collaborator.coll_id == assistant)
        .first()
    )
    encoded_password = enum.coll_password
    decoded_password = decode_data(request, encoded_password)
    return decoded_password


def get_form_directory(request, project, form):
    form_data = (
        request.dbsession.query(Form)
        .filter(Form.project_id == project)
        .filter(Form.form_id == form)
        .one()
    )
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
    res = (
        request.dbsession.query(Jsonhistory, Collaborator)
        .filter(Jsonhistory.enum_project == Collaborator.project_id)
        .filter(Jsonhistory.coll_id == Collaborator.coll_id)
        .filter(Jsonhistory.project_id == project)
        .filter(Jsonhistory.form_id == form)
        .filter(Jsonhistory.log_id == submission_id)
        .order_by(Jsonhistory.log_dtime.desc())
        .first()
    )

    if res is not None:
        last_entry = map_from_schema(res)
        notes = last_entry["log_notes"]
        if notes is not None:
            submissions = re.findall(
                r"[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12}",
                notes,
            )
            if submissions:
                for submission in submissions:
                    if submission != submission_id:
                        if notes.find("[" + submission + "]") == -1:
                            project_code = request.matchdict["projcode"]
                            url = request.route_url(
                                "comparesubmissions",
                                userid=user,
                                projcode=project_code,
                                formid=form,
                                submissiona=submission_id,
                                submissionb=submission,
                            )
                            notes = notes.replace(
                                submission, "[" + submission + "](" + url + ")"
                            )

        return {
            "log_sequence": last_entry["log_sequence"],
            "log_dtime": last_entry["log_dtime"],
            "log_action": last_entry["log_action"],
            "log_commit": last_entry["log_commit"],
            "enum_id": last_entry["coll_id"],
            "enum_name": last_entry["coll_name"],
            "log_notes": notes,
        }
    else:
        return None


def get_submission_details(request, project, form, submission):
    res = (
        request.dbsession.query(Submission, Collaborator)
        .filter(Submission.enum_project == Collaborator.project_id)
        .filter(Submission.coll_id == Collaborator.coll_id)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.submission_id == submission)
        .first()
    )

    if res is not None:
        mapped_data = map_from_schema(res)
        return {
            "submission_dtime": mapped_data["submission_dtime"],
            "submission_id": mapped_data["submission_id"],
            "enum_name": mapped_data["coll_name"],
            "submission_status": mapped_data["submission_status"],
        }
    else:
        return None


def get_submission_error_details(request, project, form, submission):
    res = (
        request.dbsession.query(Jsonlog, Collaborator)
        .filter(Jsonlog.enum_project == Collaborator.project_id)
        .filter(Jsonlog.coll_id == Collaborator.coll_id)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.log_id == submission)
        .first()
    )

    if res is not None:
        mapped_data = map_from_schema(res)
        return {
            "log_dtime": mapped_data["log_dtime"],
            "json_file": mapped_data["json_file"],
            "enum_name": mapped_data["coll_name"],
            "status": mapped_data["status"],
            "log_file": mapped_data["log_file"],
        }
    else:
        return None


def get_number_of_errors_by_assistant(request, project, form, assistant, with_status):
    if assistant is None:
        if with_status is None:
            res = (
                request.dbsession.query(Jsonlog, Collaborator)
                .filter(Jsonlog.enum_project == Collaborator.project_id)
                .filter(Jsonlog.coll_id == Collaborator.coll_id)
                .filter(Jsonlog.project_id == project)
                .filter(Jsonlog.form_id == form)
                .order_by(Jsonlog.log_dtime.desc())
                .count()
            )
            return res
        else:
            res = (
                request.dbsession.query(Jsonlog, Collaborator)
                .filter(Jsonlog.enum_project == Collaborator.project_id)
                .filter(Jsonlog.coll_id == Collaborator.coll_id)
                .filter(Jsonlog.project_id == project)
                .filter(Jsonlog.form_id == form)
                .filter(Jsonlog.status == with_status)
                .order_by(Jsonlog.log_dtime.desc())
                .count()
            )
            return res
    else:
        if with_status is None:
            res = (
                request.dbsession.query(Jsonlog, Collaborator)
                .filter(Jsonlog.enum_project == Collaborator.project_id)
                .filter(Jsonlog.coll_id == Collaborator.coll_id)
                .filter(Jsonlog.project_id == project)
                .filter(Jsonlog.coll_id == assistant)
                .filter(Jsonlog.form_id == form)
                .order_by(Jsonlog.log_dtime.desc())
                .count()
            )
            return res
        else:
            res = (
                request.dbsession.query(Jsonlog, Collaborator)
                .filter(Jsonlog.enum_project == Collaborator.project_id)
                .filter(Jsonlog.coll_id == Collaborator.coll_id)
                .filter(Jsonlog.project_id == project)
                .filter(Jsonlog.coll_id == assistant)
                .filter(Jsonlog.form_id == form)
                .filter(Jsonlog.status == with_status)
                .order_by(Jsonlog.log_dtime.desc())
                .count()
            )
            return res


def apply_limit(start, page_size):
    def wrapped(query):
        query = query.limit(page_size)
        query = query.offset(start)
        return query

    return wrapped


def get_errors_by_assistant(
    request, user, project, form, assistant, start, page_size, with_status
):
    result = []
    if assistant is None:
        if with_status is None:
            query = (
                request.dbsession.query(Jsonlog, Collaborator)
                .filter(Jsonlog.enum_project == Collaborator.project_id)
                .filter(Jsonlog.coll_id == Collaborator.coll_id)
                .filter(Jsonlog.project_id == project)
                .filter(Jsonlog.form_id == form)
                .order_by(Jsonlog.log_dtime.desc())
            )
        else:
            query = (
                request.dbsession.query(Jsonlog, Collaborator)
                .filter(Jsonlog.enum_project == Collaborator.project_id)
                .filter(Jsonlog.coll_id == Collaborator.coll_id)
                .filter(Jsonlog.project_id == project)
                .filter(Jsonlog.form_id == form)
                .filter(Jsonlog.status == with_status)
                .order_by(Jsonlog.log_dtime.desc())
            )
        listen(query, "before_compile", apply_limit(start, page_size), retval=True)
        res = query.all()
    else:
        if with_status is None:
            query = (
                request.dbsession.query(Jsonlog, Collaborator)
                .filter(Jsonlog.enum_project == Collaborator.project_id)
                .filter(Jsonlog.coll_id == Collaborator.coll_id)
                .filter(Jsonlog.project_id == project)
                .filter(Jsonlog.coll_id == assistant)
                .filter(Jsonlog.form_id == form)
                .order_by(Jsonlog.log_dtime.desc())
                .all()
            )
        else:
            query = (
                request.dbsession.query(Jsonlog, Collaborator)
                .filter(Jsonlog.enum_project == Collaborator.project_id)
                .filter(Jsonlog.coll_id == Collaborator.coll_id)
                .filter(Jsonlog.project_id == project)
                .filter(Jsonlog.coll_id == assistant)
                .filter(Jsonlog.form_id == form)
                .filter(Jsonlog.status == with_status)
                .order_by(Jsonlog.log_dtime.desc())
                .all()
            )
        listen(query, "before_compile", apply_limit(start, page_size), retval=True)
        res = query.all()

    json_errors = map_from_schema(res)
    for error in json_errors:
        result.append(
            {
                "log_id": error["log_id"],
                "log_dtime": error["log_dtime"],
                "json_file": error["json_file"],
                "error": get_error_description_from_file(error["log_file"]),
                "status": error["status"],
                "lastentry": get_last_log_entry(
                    request, user, project, form, error["log_id"]
                ),
                "enum_name": error["coll_name"],
                "log_short": error["log_id"][-12:],
            }
        )
    return result


def get_submissions_by_assistant(dbsession, project, form, assistant):
    total = (
        dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.coll_id == assistant)
        .filter(Submission.sameas.is_(None))
        .count()
    )

    in_db = (
        dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.coll_id == assistant)
        .filter(Submission.submission_status == 0)
        .filter(Submission.sameas.is_(None))
        .count()
    )

    fixed = (
        dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.status == 0)
        .filter(Jsonlog.coll_id == assistant)
        .count()
    )

    in_db_from_logs = (
        dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.coll_id == assistant)
        .count()
    )

    in_error = (
        dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.coll_id == assistant)
        .filter(Jsonlog.status != 0, Jsonlog.status != 4)
        .count()
    )

    res = (
        dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.coll_id == assistant)
        .filter(Submission.sameas.is_(None))
        .order_by(Submission.submission_dtime.desc())
        .first()
    )
    if res is not None:
        last = res.submission_dtime
    else:
        last = None

    result = {
        "total": total,
        "totalInDB": in_db + fixed,
        "totalInLogs": in_db_from_logs,
        "totalInError": in_error,
        "last": last,
    }
    return result


def get_submissions_by_form(dbsession, project, form):
    total = (
        dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.sameas.is_(None))
        .count()
    )

    in_db = (
        dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.submission_status == 0)
        .filter(Submission.sameas.is_(None))
        .count()
    )

    in_db_from_logs = (
        dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .count()
    )

    fixed = (
        dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.status == 0)
        .count()
    )

    in_error = (
        dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.status != 0, Jsonlog.status != 4)
        .count()
    )

    res = (
        dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.sameas.is_(None))
        .order_by(Submission.submission_dtime.desc())
        .first()
    )
    if res is not None:
        last = res.submission_dtime
    else:
        last = None

    result = {
        "total": total,
        "totalInDB": in_db + fixed,
        "totalInLogs": in_db_from_logs,
        "totalInError": in_error,
        "last": last,
    }
    return result


def get_forms_by_assistant(request, user, project, assistant):
    assistant_project = get_project_from_assistant(request, user, project, assistant)
    assistant_forms = get_assistant_forms(
        request, project, assistant_project, assistant
    )

    for a_form in assistant_forms:
        a_form["formstats"] = get_submissions_by_form(
            request.dbsession, a_form["project_id"], a_form["form_id"]
        )
        a_form["enumstats"] = get_submissions_by_assistant(
            request.dbsession, a_form["project_id"], a_form["form_id"], assistant
        )
    return assistant_forms


def get_assistant_permissions_on_a_form(
    request, user, requested_project, assistant, form
):
    privileges = {"enum_cansubmit": 0, "enum_canclean": 0}
    assistant_project = get_project_from_assistant(
        request, user, requested_project, assistant
    )
    # Get all the forms that the user can submit data to and are active
    assistant_access = (
        request.dbsession.query(Formacces)
        .filter(Formacces.project_id == assistant_project)
        .filter(Formacces.coll_id == assistant)
        .filter(Formacces.form_project == requested_project)
        .filter(Formacces.form_id == form)
        .first()
    )
    if assistant_access is not None:
        if assistant_access.coll_privileges == 3:
            privileges = {"enum_cansubmit": 1, "enum_canclean": 1}
        else:
            if assistant_access.coll_privileges == 1:
                privileges = {"enum_cansubmit": 1, "enum_canclean": 0}
            else:
                privileges = {"enum_cansubmit": 0, "enum_canclean": 1}

    # Select the groups that user belongs to
    groups = (
        request.dbsession.query(Collingroup)
        .filter(Collingroup.project_id == requested_project)
        .filter(Collingroup.enum_project == assistant_project)
        .filter(Collingroup.coll_id == assistant)
        .all()
    )

    for group in groups:
        res = (
            request.dbsession.query(Formgrpacces)
            .filter(Formgrpacces.project_id == group.project_id)
            .filter(Formgrpacces.group_id == group.group_id)
            .filter(Form.form_id == form)
            .first()
        )
        if res is not None:
            if res.group_privileges == 3:
                privileges = {"enum_cansubmit": 1, "enum_canclean": 1}
            else:
                if res.group_privileges == 1:
                    privileges["enum_cansubmit"] = 1
                else:
                    privileges["enum_canclean"] = 2

    return privileges


# This update the stage information so he can come back
def update_form_repository_info(request, project, form, data):
    request.dbsession.query(Form).filter(Form.project_id == project).filter(
        Form.form_id == form
    ).update(data)


def get_form_data(project, form, request):
    res = {}
    data = (
        request.dbsession.query(Form)
        .filter(Form.project_id == project)
        .filter(Form.form_id == form)
        .first()
    )
    if data:
        res["id"] = data.form_id
        res["name"] = data.form_name
        res["directory"] = data.form_directory
        res["schema"] = data.form_schema
        res["form_pkey"] = data.form_pkey
        res["form_deflang"] = data.form_deflang
        res["form_othlangs"] = data.form_othlangs
        res["form_stage"] = data.form_stage
        res["form_abletomerge"] = data.form_abletomerge
        res["parent_form"] = data.parent_form
    return res


def modification_date(filename):
    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)


def get_number_of_submissions(odk_dir, directory):
    paths = ["forms", directory, "submissions", "*.json"]
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
                ziph.write(
                    os.path.join(root, file), os.path.basename(os.path.join(root, file))
                )


def zip_json_files(odk_dir, form):
    try:
        uid = str(uuid.uuid4())
        paths = ["tmp", uid + ".zip"]
        path = os.path.join(odk_dir, *paths)
        zipf = zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED)
        paths = ["forms", form, "submissions"]
        source_path = os.path.join(odk_dir, *paths)
        zipdir(source_path, zipf)
        zipf.close()
        return True, path
    except Exception as e:
        return False, str(e)


def handle_uploaded_file(f, target_file):
    max_size = 100
    tmp_filepath = target_file + "~"
    output_file = open(tmp_filepath, "wb")
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
            print("File upload too large")

    output_file.close()
    os.rename(tmp_filepath, target_file)


def checkout_submission(
    request, project, form, submission, project_of_assistant, assistant
):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
        Jsonlog.form_id == form, Jsonlog.log_id == submission
    ).update({"status": 2})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(
        project_id=project,
        form_id=form,
        log_id=submission,
        log_sequence=sequence,
        log_dtime=datetime.datetime.now(),
        log_action=2,
        enum_project=project_of_assistant,
        coll_id=assistant,
    )
    request.dbsession.add(new_record)


def cancel_checkout(
    request, project, form, submission, project_of_assistant, assistant
):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
        Jsonlog.form_id == form, Jsonlog.log_id == submission
    ).update({"status": 1})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(
        project_id=project,
        form_id=form,
        log_id=submission,
        log_sequence=sequence,
        log_dtime=datetime.datetime.now(),
        log_action=5,
        enum_project=project_of_assistant,
        coll_id=assistant,
    )
    request.dbsession.add(new_record)


def cancel_revision(
    request, project, form, submission, project_of_assistant, assistant, revision
):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
        Jsonlog.form_id == form, Jsonlog.log_id == submission
    ).update({"status": 1})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(
        project_id=project,
        form_id=form,
        log_id=submission,
        log_sequence=sequence,
        log_dtime=datetime.datetime.now(),
        log_action=6,
        enum_project=project_of_assistant,
        coll_id=assistant,
        log_commit=revision,
    )
    request.dbsession.add(new_record)


def fix_revision(
    request, project, form, submission, project_of_assistant, assistant, revision
):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
        Jsonlog.form_id == form, Jsonlog.log_id == submission
    ).update({"status": 0})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(
        project_id=project,
        form_id=form,
        log_id=submission,
        log_sequence=sequence,
        log_dtime=datetime.datetime.now(),
        log_action=0,
        enum_project=project_of_assistant,
        coll_id=assistant,
        log_commit=revision,
    )
    request.dbsession.add(new_record)


def fail_revision(
    request, project, form, submission, project_of_assistant, assistant, revision
):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
        Jsonlog.form_id == form, Jsonlog.log_id == submission
    ).update({"status": 1})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(
        project_id=project,
        form_id=form,
        log_id=submission,
        log_sequence=sequence,
        log_dtime=datetime.datetime.now(),
        log_action=7,
        enum_project=project_of_assistant,
        coll_id=assistant,
        log_commit=revision,
    )
    request.dbsession.add(new_record)


def disregard_revision(
    request, project, form, submission, project_of_assistant, assistant, notes
):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
        Jsonlog.form_id == form, Jsonlog.log_id == submission
    ).update({"status": 4})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(
        project_id=project,
        form_id=form,
        log_id=submission,
        log_sequence=sequence,
        log_dtime=datetime.datetime.now(),
        log_action=4,
        enum_project=project_of_assistant,
        coll_id=assistant,
        log_notes=notes,
    )
    request.dbsession.add(new_record)


def cancel_disregard_revision(
    request, project, form, submission, project_of_assistant, assistant, notes
):
    request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
        Jsonlog.form_id == form, Jsonlog.log_id == submission
    ).update({"status": 1})
    sequence = str(uuid.uuid4())
    sequence = sequence[-12:]
    new_record = Jsonhistory(
        project_id=project,
        form_id=form,
        log_id=submission,
        log_sequence=sequence,
        log_dtime=datetime.datetime.now(),
        log_action=8,
        enum_project=project_of_assistant,
        coll_id=assistant,
        log_notes=notes,
    )
    request.dbsession.add(new_record)
