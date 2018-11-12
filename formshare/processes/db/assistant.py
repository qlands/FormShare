from formshare.models import Collaborator, map_from_schema, map_to_schema
import logging
import sys
import datetime
from sqlalchemy.exc import IntegrityError

__all__ = ['get_project_assistants', 'delete_assistant', 'add_assistant', 'get_assistant_data',
           'modify_assistant']

log = logging.getLogger(__name__)


def get_project_assistants(request, project):
    res = request.dbsession.query(Collaborator).filter(Collaborator.project_id == project).all()
    mapped_data = map_from_schema(res)
    return mapped_data


def get_assistant_data(request, project, assistant):
    res = map_from_schema(request.dbsession.query(Collaborator).filter(Collaborator.project_id == project).filter(
        Collaborator.coll_id == assistant).first())
    return res


def delete_assistant(request, project, assistant):
    try:
        request.dbsession.query(Collaborator).filter(Collaborator.project_id == project).filter(
            Collaborator.coll_id == assistant).delete()
        request.dbsession.flush()
        return True, ""
    except RuntimeError:
        log.error(
            "Error {} while removing assistant {} from project {}".format(sys.exc_info()[0], assistant, project))
        request.dbsession.rollback()
        return False, sys.exc_info()[0]


def add_assistant(request, project, assistant_data):
    mapped_data = map_to_schema(Collaborator, assistant_data)
    mapped_data['coll_cdate'] = datetime.datetime.now()
    mapped_data['coll_active'] = 1
    mapped_data['project_id'] = project
    new_assistant = Collaborator(**mapped_data)
    try:
        request.dbsession.add(new_assistant)
        request.dbsession.flush()
        return True, ""
    except IntegrityError:
        request.dbsession.rollback()
        return False, request.translate("The collaborator is already part of this project")
    except RuntimeError:
        request.dbsession.rollback()
        log.error(
            "Error {} while adding collaborator {} in project {}".format(sys.exc_info()[0], assistant_data['coll_name'],
                                                                         project))
        return False, sys.exc_info()[0]


def modify_assistant(request, project, assistant, assistant_data):
    mapped_data = map_to_schema(Collaborator, assistant_data)
    try:
        request.dbsession.query(Collaborator).filter(Collaborator.project_id == project).filter(
            Collaborator.coll_id == assistant).update(mapped_data)
        request.dbsession.flush()
        return True, ''
    except IntegrityError:
        request.dbsession.rollback()
        return False, request.translate("The collaborator is already part of this project")
    except RuntimeError:
        request.dbsession.rollback()
        log.error(
            "Error {} while adding collaborator {} in project {}".format(sys.exc_info()[0], assistant_data['coll_name'],
                                                                         project))
        return False, sys.exc_info()[0]
