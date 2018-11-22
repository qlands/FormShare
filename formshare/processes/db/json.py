from formshare.models import Jsonlog, Jsonhistory
import logging
import datetime
from sqlalchemy.exc import IntegrityError
import sys

__all__ = ['add_json_log', 'update_json_status', 'add_json_history']

log = logging.getLogger(__name__)


def add_json_log(request, project, form, submission, json_file, log_file, status, assistant):
    new_json_log = Jsonlog(project_id=project, form_id=form, log_id=submission,
                           json_file=json_file, log_file=log_file, status=status,
                           enum_project=project, coll_id=assistant,
                           log_dtime=datetime.datetime.now())
    try:
        request.dbsession.add(new_json_log)
        request.dbsession.flush()
        return True, ""
    except IntegrityError as e:
        request.dbsession.rollback()
        log.debug(str(e))
        return False, str(e)
    except RuntimeError:
        request.dbsession.rollback()
        log.debug(sys.exc_info()[0])
        return False, sys.exc_info()[0]


def update_json_status(request, project, form, submission, status):
    try:
        request.dbsession.query(Jsonlog).filter(Jsonlog.project_id == project).\
            filter(Jsonlog.form_id == form, Jsonlog.log_id == submission).update({'status': status})
        request.dbsession.flush()
    except IntegrityError as e:
        request.dbsession.rollback()
        log.debug(str(e))
        return False, str(e)
    except RuntimeError:
        request.dbsession.rollback()
        log.debug(sys.exc_info()[0])
        return False, sys.exc_info()[0]


def add_json_history(request, project, form, submission, sequence, status, assistant, notes):
    new_record = Jsonhistory(project_id=project, form_id=form, log_id=submission, log_sequence=sequence,
                             log_dtime=datetime.datetime.now(), log_action=status, enum_project=project,
                             coll_id=assistant, log_commit=sequence, log_notes=notes)
    try:
        request.dbsession.add(new_record)
        request.dbsession.flush()
        return True, ""
    except IntegrityError as e:
        request.dbsession.rollback()
        log.debug(str(e))
        return False, str(e)
    except RuntimeError:
        request.dbsession.rollback()
        log.debug(sys.exc_info()[0])
        return True, sys.exc_info()[0]
