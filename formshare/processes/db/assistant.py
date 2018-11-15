from formshare.models import Collaborator, Project, Userproject, map_from_schema, map_to_schema
import logging
import sys
import datetime
from sqlalchemy.exc import IntegrityError
from formshare.config.encdecdata import encode_data

__all__ = ['get_project_assistants', 'delete_assistant', 'add_assistant', 'get_assistant_data',
           'modify_assistant', 'change_assistant_password', 'get_all_assistants']

log = logging.getLogger(__name__)


def get_all_assistants(request, project, user):
    res = request.dbsession.query(Project, Collaborator).filter(Project.project_id == Collaborator.project_id).filter(
        Project.project_id == Userproject.project_id).filter(Userproject.user_id == user).filter(
        Collaborator.coll_prjshare == 1).filter(Project.project_id == project).all()
    project_assistants = map_from_schema(res)

    res = request.dbsession.query(Project, Collaborator).filter(Project.project_id == Collaborator.project_id).filter(
        Project.project_id == Userproject.project_id).filter(Userproject.user_id == user).filter(
        Collaborator.coll_prjshare == 1).filter(Project.project_id != project).all()
    other_assistants = map_from_schema(res)

    all_assistants = project_assistants + other_assistants

    assistants = []
    for item in all_assistants:
        index = 0
        found = False
        for assistant in assistants:
            if assistant["project_id"] == item["project_id"]:
                found = True
                break
            index = index + 1
        if found:
            assistants[index]["assistants"].append(
                {'code': item["project_id"] + "|" + item['coll_id'], 'name': item["coll_name"]})
        else:
            assistants.append({'project_id': item["project_id"], 'project_desc': item['project_name'], 'assistants': [
                {'code': item["project_id"] + "|" + item['coll_id'], 'name': item["coll_name"]}]})

    return assistants


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
    mapped_data['coll_password'] = encode_data(request, mapped_data['coll_password'])
    new_assistant = Collaborator(**mapped_data)
    try:
        request.dbsession.add(new_assistant)
        request.dbsession.flush()
        return True, ""
    except IntegrityError:
        request.dbsession.rollback()
        return False, request.translate("The assistant is already part of this project")
    except RuntimeError:
        request.dbsession.rollback()
        log.error(
            "Error {} while adding assistant {} in project {}".format(sys.exc_info()[0], assistant_data['coll_name'],
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
        return False, request.translate("The assistant is already part of this project")
    except RuntimeError:
        request.dbsession.rollback()
        log.error(
            "Error {} while adding assistant {} in project {}".format(sys.exc_info()[0], assistant_data['coll_name'],
                                                                      project))
        return False, sys.exc_info()[0]


def change_assistant_password(request, project, assistant, password):
    try:
        encrypted_password = encode_data(request, password)
        request.dbsession.query(Collaborator).filter(Collaborator.project_id == project).filter(
            Collaborator.coll_id == assistant).update({'coll_password': encrypted_password})
        request.dbsession.flush()
        return True, ''
    except RuntimeError:
        request.dbsession.rollback()
        log.error(
            "Error {} while adding assistant {} in project {}".format(sys.exc_info()[0], assistant, project))
        return False, sys.exc_info()[0]
