import datetime
import logging
from formshare.processes.logging.loggerclass import SecretLogger

from formshare.models import Jsonlog, Jsonhistory
from sqlalchemy.exc import IntegrityError

__all__ = ["add_json_log", "update_json_status", "add_json_history"]

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


def add_json_log(
    request,
    project,
    form,
    submission,
    json_file,
    log_file,
    status,
    assistant_uuid,
    command_executed,
):
    res = (
        request.dbsession.query(Jsonlog)
        .filter(Jsonlog.project_id == project)
        .filter(Jsonlog.form_id == form)
        .filter(Jsonlog.log_id == submission)
        .first()
    )
    try:
        if res is None:
            new_json_log = Jsonlog(
                project_id=project,
                form_id=form,
                log_id=submission,
                json_file=json_file,
                log_file=log_file,
                status=status,
                coll_uuid=assistant_uuid,
                log_dtime=datetime.datetime.now(),
                command_executed=command_executed,
            )
            request.dbsession.add(new_json_log)
            request.dbsession.commit()
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
                    "coll_uuid": assistant_uuid,
                    "log_dtime": datetime.datetime.now(),
                    "command_executed": command_executed,
                }
            )
            request.dbsession.commit()
            return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.debug(str(e))
        return False, str(e)


def update_json_status(request, project, form, submission, status):
    try:
        request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
            Jsonlog.form_id == form, Jsonlog.log_id == submission
        ).update({"status": status})
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        log.debug(str(e))
        return False, str(e)


def add_json_history(
    request,
    project,
    form,
    submission,
    sequence,
    status,
    assistant_uuid,
    notes,
):
    new_record = Jsonhistory(
        project_id=project,
        form_id=form,
        log_id=submission,
        log_sequence=sequence,
        log_dtime=datetime.datetime.now(),
        log_action=status,
        coll_uuid=assistant_uuid,
        log_commit=sequence,
        log_notes=notes,
    )
    try:
        request.dbsession.add(new_record)
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.debug(str(e))
        return True, str(e)
