from formshare.models import Userproject, User, map_from_schema
import logging
import sys
import datetime
from sqlalchemy.exc import IntegrityError

__all__ = ['get_project_collaborators', 'remove_collaborator_from_project', 'set_collaborator_role',
           'add_collaborator_to_project']

log = logging.getLogger(__name__)


def get_project_collaborators(request, project):
    res = request.dbsession.query(User, Userproject).filter(Userproject.user_id == User.user_id).filter(
        Userproject.project_id == project).filter(Userproject.access_type != 1).order_by(
        Userproject.access_date.desc()).all()
    mapped_data = map_from_schema(res)
    return mapped_data


def remove_collaborator_from_project(request, project, collaborator):
    try:
        request.dbsession.query(Userproject).filter(Userproject.project_id == project).filter(
            Userproject.user_id == collaborator).delete()
        request.dbsession.flush()
        return True, ""
    except RuntimeError:
        log.error(
            "Error {} while removing collaborator {} from project {}".format(sys.exc_info()[0], collaborator, project))
        return False, sys.exc_info()[0]


def set_collaborator_role(request, project, collaborator, role):
    try:
        request.dbsession.query(Userproject).filter(Userproject.project_id == project).filter(
            Userproject.user_id == collaborator).update({'access_type': role})
        request.dbsession.flush()
        return True, ""
    except RuntimeError:
        request.dbsession.rollback()
        log.error(
            "Error {} while changing role to collaborator {} in project {}".format(sys.exc_info()[0], collaborator,
                                                                                   project))
        return False, sys.exc_info()[0]


def add_collaborator_to_project(request, project, collaborator):
    new_collaborator = Userproject(user_id=collaborator, project_id=project, access_type=4,
                                   access_date=datetime.datetime.now(), project_active=1)
    try:
        request.dbsession.add(new_collaborator)
        request.dbsession.flush()
        return True, ""
    except IntegrityError:
        request.dbsession.rollback()
        return False, request.translate("The collaborator is already part of this project")
    except RuntimeError:
        request.dbsession.rollback()
        log.error(
            "Error {} while adding collaborator {} in project {}".format(sys.exc_info()[0], collaborator, project))
        return False, sys.exc_info()[0]
