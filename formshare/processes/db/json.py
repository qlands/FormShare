from formshare.models import Jsonlog, Jsonhistory
import logging
import datetime
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
):
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
    )
    try:
        request.dbsession.add(new_json_log)
        request.dbsession.flush()
        return True, ""
    except IntegrityError as e:
        log.debug(str(e))
        return False, str(e)
    except Exception as e:
        log.debug(str(e))
        return False, str(e)


def update_json_status(request, project, form, submission, status):
    try:
        request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).filter(
            Jsonlog.form_id == form, Jsonlog.log_id == submission
        ).update({"status": status})
        request.dbsession.flush()
    except IntegrityError as e:
        log.debug(str(e))
        return False, str(e)
    except Exception as e:
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
    try:
        request.dbsession.add(new_record)
        request.dbsession.flush()
        return True, ""
    except IntegrityError as e:
        log.debug(str(e))
        return False, str(e)
    except Exception as e:
        log.debug(str(e))
        return True, str(e)
