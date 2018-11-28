from formshare.models import Collaborator, Project, map_from_schema, map_to_schema, Userproject
import logging
import sys
import datetime
from sqlalchemy.exc import IntegrityError
from formshare.config.encdecdata import encode_data
from formshare.config.encdecdata import decode_data

__all__ = ['get_project_assistants', 'delete_assistant', 'add_assistant', 'get_assistant_data',
           'modify_assistant', 'change_assistant_password', 'get_all_assistants', 'is_assistant_active',
           'get_assistant_password', 'get_project_from_assistant']

log = logging.getLogger(__name__)


def get_all_assistants(request, project, user):
    res = request.dbsession.query(Project, Collaborator).filter(Project.project_id == Collaborator.project_id).filter(
        Project.project_id == Userproject.project_id).filter(Userproject.user_id == user).filter(
        Project.project_id == project).all()
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


def get_project_assistants(request, project, return_max=0):
    res = request.dbsession.query(Collaborator).filter(Collaborator.project_id == project).order_by(
        Collaborator.coll_cdate.desc()).all()
    mapped_data = map_from_schema(res)
    if return_max <= 0:
        return mapped_data, 0
    else:
        more = len(mapped_data) - return_max
        if more < 0:
            more = 0
        result = []
        count = 1
        for item in mapped_data:
            if count <= return_max:
                result.append(item)
                count = count + 1
            else:
                break
        return result, more


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


def get_project_from_assistant(request, user, requested_project, assistant):
    # Get all the assistants the user has with that name across projects
    num_assistants = request.dbsession.query(Userproject, Collaborator).filter(
        Userproject.project_id == Collaborator.project_id).filter(Userproject.user_id == user).filter(
        Userproject.access_type <= 3).filter(Collaborator.coll_id == assistant).count()
    if num_assistants > 0:
        if num_assistants == 1:
            # If the user has just one assistant with that name then gets his data
            assistant_data = request.dbsession.query(Collaborator).filter(
                Userproject.project_id == Collaborator.project_id).filter(Userproject.user_id == user).filter(
                Userproject.access_type <= 3).filter(Collaborator.coll_id == assistant).first()
            # Is the assistant from the same project?
            if assistant_data.project_id == requested_project:
                return requested_project
            else:
                # Is the assistant shareable across projects?
                if assistant_data.coll_prjshare == 1:
                    return assistant_data.project_id
                else:
                    return None
        else:
            # If there are more than one assistant then return the requested_project
            return requested_project
    else:
        return None


def is_assistant_active(request, user, project, assistant):
    # Get all the assistants the user has with that name across projects
    num_assistants = request.dbsession.query(Userproject, Collaborator).filter(
        Userproject.project_id == Collaborator.project_id).filter(Userproject.user_id == user).filter(
        Userproject.access_type <= 3).filter(Collaborator.coll_id == assistant).count()
    if num_assistants > 0:
        if num_assistants == 1:
            # If the user has just one assistant with that name then gets his data
            assistant_data = request.dbsession.query(Collaborator).filter(
                Userproject.project_id == Collaborator.project_id).filter(Userproject.user_id == user).filter(
                Userproject.access_type <= 3).filter(Collaborator.coll_id == assistant).first()
            # Is the assistant from the same project?
            if assistant_data.project_id == project:
                enum = request.dbsession.query(Collaborator).filter(
                    Collaborator.project_id == assistant_data.project_id).filter(
                    Collaborator.coll_id == assistant).first()
                if enum is not None:
                    if enum.coll_active == 1:
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                # Is the assistant shareable across projects?
                if assistant_data.coll_prjshare == 1:
                    enum = request.dbsession.query(Collaborator).filter(
                        Collaborator.project_id == assistant_data.project_id).filter(
                        Collaborator.coll_id == assistant).first()
                    if enum is not None:
                        if enum.coll_active == 1:
                            return True
                        else:
                            return False
                    else:
                        return False
                else:
                    return False
        else:
            # If there are more than one assistant then use the project in the URL
            enum = request.dbsession.query(Collaborator).filter(Collaborator.project_id == project).filter(
                Collaborator.coll_id == assistant).first()
            if enum is not None:
                if enum.coll_active == 1:
                    return True
                else:
                    return False
            else:
                return False
    else:
        return False


def get_assistant_password(request, user, project, assistant):
    project_assistant = get_project_from_assistant(request, user, project, assistant)
    enum = request.dbsession.query(Collaborator).filter(Collaborator.project_id == project_assistant).filter(
        Collaborator.coll_id == assistant).first()
    decrypted = decode_data(request, enum.coll_password.encode())
    return decrypted
