import datetime
import logging

from formshare.models import Jsonlog, Jsonhistory
from sqlalchemy.exc import IntegrityError

__all__ = ["add_json_log", "update_json_status", "add_json_history"]

log = logging.getLogger("formshare")


def add_json_log(
    request,
    project,
    form,
    submission,
    json_file,
    log_file,
    status,
    project_of_assistant,
    assistant,
    command_executed,
):
    res = (
        request.dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.log_id == submission)
        .first()
    )
    save_point = request.tm.savepoint()
    try:
        if res is None:
            new_json_log = Jsonlog(
                project_id=project,
                form_id=form,
                log_id=submission,
                json_file=json_file,
                log_file=log_file,
                status=status,
                enum_project=project_of_assistant,
                coll_id=assistant,
                log_dtime=datetime.datetime.now(),
                command_executed=command_executed,
            )
            request.dbsession.add(new_json_log)
            request.dbsession.flush()
            return True, ""
        else:
            # This might not happen. Left here just in case
            request.dbsession.query(Jsonlog).filter(
                Jsonlog.project_id == project
            ).filter(Jsonlog.form_id == form).filter(
                Jsonlog.log_id == submission
            ).update(
                {
                    "json_file": json_file,
                    "log_file": log_file,
                    "status": status,
                    "enum_project": project_of_assistant,
                    "coll_id": assistant,
                    "log_dtime": datetime.datetime.now(),
                    "command_executed": command_executed,
                }
            )
            request.dbsession.flush()
            return True, ""
    except Exception as e:
        save_point.rollback()
        log.debug(str(e))
        return False, str(e)


def update_json_status(request, project, form, submission, status):
    save_point = request.tm.savepoint()
    try:
        request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
            Jsonlog.form_id == form, Jsonlog.log_id == submission
        ).update({"status": status})
        request.dbsession.flush()
    except Exception as e:
        save_point.rollback()
        log.debug(str(e))
        return False, str(e)


def add_json_history(
    request,
    project,
    form,
    submission,
    sequence,
    status,
    project_of_assistant,
    assistant,
    notes,
):
    new_record = Jsonhistory(
        project_id=project,
        form_id=form,
        log_id=submission,
        log_sequence=sequence,
        log_dtime=datetime.datetime.now(),
        log_action=status,
        enum_project=project_of_assistant,
        coll_id=assistant,
        log_commit=sequence,
        log_notes=notes,
    )
    save_point = request.tm.savepoint()
    try:
        request.dbsession.add(new_record)
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        save_point.rollback()
        log.debug(str(e))
        return True, str(e)
