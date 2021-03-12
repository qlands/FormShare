import datetime
import logging
import re
import uuid

from lxml import etree
from sqlalchemy.event import listen

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
from formshare.models import Odkform as Form
from formshare.processes.db.assistant import get_project_from_assistant

log = logging.getLogger("formshare")


def get_form_schema(request, project, form):
    form_data = (
        request.dbsession.query(Form)
        .filter(Form.project_id == project)
        .filter(Form.form_id == form)
        .one()
    )
    return form_data.form_schema


def get_form_primary_key(request, project, form):
    form_data = (
        request.dbsession.query(Form)
        .filter(Form.project_id == project)
        .filter(Form.form_id == form)
        .one()
    )
    return form_data.form_pkey


def get_form_case_params(request, project, form):
    form_data = (
        request.dbsession.query(Form)
        .filter(Form.project_id == project)
        .filter(Form.form_id == form)
        .one()
    )
    return (
        form_data.form_casetype,
        form_data.form_caselabel,
        form_data.form_caseselector,
    )


def get_error_description_from_file(request, project, form, log_file):
    try:
        tree = etree.parse(log_file)
        root = tree.getroot()
        error = root.find(".//error")
        message = error.get("Error")
        table_name = error.get("Table")
        if message.find("Duplicate entry") >= 0:
            if table_name == "maintable":
                message = message.replace("Duplicate entry ", "")
                message = message.replace("'", "")
                message_parts = message.split(" for key ")
                if len(message_parts) == 2:
                    schema = get_form_schema(request, project, form)
                    primary_key = get_form_primary_key(request, project, form)
                    sql = "SELECT surveyid from {}.maintable WHERE {} = '{}'".format(
                        schema, primary_key, message_parts[0]
                    )
                    res = request.dbsession.execute(sql).fetchone()
                    if res is not None:
                        return {
                            "duplicated": True,
                            "error": error.get("Error"),
                            "maintable": True,
                            "survey_id": res[0],
                            "primary_key": primary_key,
                            "duplicated_value": message_parts[0],
                            "duplicated_exists": True,
                            "moved": False,
                        }
                    else:
                        return {
                            "duplicated": True,
                            "error": error.get("Error"),
                            "maintable": True,
                            "survey_id": None,
                            "primary_key": primary_key,
                            "duplicated_value": message_parts[0],
                            "duplicated_exists": False,
                            "moved": False,
                        }

            return {
                "duplicated": True,
                "error": error.get("Error"),
                "maintable": False,
                "moved": False,
            }
        else:
            if message.find("Moved to logs by") >= 0:
                return {"duplicated": False, "error": error.get("Error"), "moved": True}
            else:
                return {
                    "duplicated": False,
                    "error": error.get("Error"),
                    "moved": False,
                }
    except Exception as e:
        return {"duplicated": False, "error": str(e), "moved": False}


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
                "error": get_error_description_from_file(
                    request, project, form, error["log_file"]
                ),
                "status": error["status"],
                "lastentry": get_last_log_entry(
                    request, user, project, form, error["log_id"]
                ),
                "enum_name": error["coll_name"],
                "log_short": error["log_id"][-12:],
            }
        )
    return result


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
                    privileges = {"enum_cansubmit": 1, "enum_canclean": 0}
                else:
                    privileges = {"enum_cansubmit": 0, "enum_canclean": 1}

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
        res["form_createxmlfile"] = data.form_createxmlfile
        res["form_insertxmlfile"] = data.form_insertxmlfile
        res["form_hexcolor"] = data.form_hexcolor
    return res


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


def fix_submission(request, project, form, submission, project_of_assistant, assistant):
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
