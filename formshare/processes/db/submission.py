import datetime
import logging
from formshare.processes.logging.loggerclass import SecretLogger

from formshare.models import Submission
from sqlalchemy.exc import IntegrityError

__all__ = ["get_submission_data", "add_submission", "add_submission_same_as"]

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


def get_submission_data(request, project, form, original_md5sum):
    res = (
        request.dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .filter(Submission.form_id == form)
        .filter(Submission.original_md5sum == original_md5sum)
        .order_by(Submission.submission_dtime.asc())
        .first()
    )
    return res


def add_submission(
    request,
    project,
    form,
    project_of_assistant,
    assistant,
    submission,
    md5sum,
    original_md5sum,
    status,
):
    new_submission = Submission(
        submission_id=submission,
        submission_dtime=datetime.datetime.now(),
        submission_status=status,
        project_id=project,
        form_id=form,
        enum_project=project_of_assistant,
        coll_id=assistant,
        md5sum=md5sum,
        original_md5sum=original_md5sum,
    )
    save_point = request.tm.savepoint()
    try:
        request.dbsession.add(new_submission)
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        save_point.rollback()
        log.error(str(e))
        return False, str(e)


def add_submission_same_as(
    request,
    project,
    form,
    project_of_assistant,
    assistant,
    submission,
    md5sum,
    status,
    same_as,
):
    new_submission = Submission(
        submission_id=submission,
        submission_dtime=datetime.datetime.now(),
        submission_status=status,
        project_id=project,
        form_id=form,
        enum_project=project_of_assistant,
        coll_id=assistant,
        md5sum=md5sum,
        sameas=same_as,
    )
    save_point = request.tm.savepoint()
    try:
        request.dbsession.add(new_submission)
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        save_point.rollback()
        log.error(str(e))
        return False, str(e)
