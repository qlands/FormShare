from formshare.models import Submission
import logging
import datetime
from sqlalchemy.exc import IntegrityError
import sys


__all__ = ['get_submission_data', 'add_submission']

log = logging.getLogger(__name__)


def get_submission_data(request, project, form, md5sum):
    res = request.dbsession.query(Submission).filter(Submission.project_id == project).filter(
        Submission.form_id == form).filter(Submission.md5sum == md5sum).order_by(
        Submission.submission_dtime.asc()).first()
    return res


def add_submission(request, project, form, assistant, submission, md5sum, status):
    new_submission = Submission(submission_id=submission,
                                submission_dtime=datetime.datetime.now(),
                                submission_status=status, project_id=project,
                                form_id=form, enum_project=project, coll_id=assistant,
                                md5sum=md5sum)
    try:
        request.dbsession.add(new_submission)
        request.dbsession.flush()
        return True, ""
    except IntegrityError as e:
        request.dbsession.rollback()
        log.error(str(e))
        return False, str(e)
    except RuntimeError:
        request.dbsession.rollback()
        log.error(sys.exc_info()[0])
        return False, sys.exc_info()[0]



