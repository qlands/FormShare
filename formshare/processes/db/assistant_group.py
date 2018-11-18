from formshare.models import Collgroup, Collingroup, Collaborator, map_from_schema, map_to_schema
import logging
import sys
import datetime
import uuid
from sqlalchemy.exc import IntegrityError

__all__ = ['get_project_groups', 'delete_group', 'add_group', 'get_group_data',
           'modify_group', 'get_members', 'add_assistant_to_group', 'remove_assistant_from_group']

log = logging.getLogger(__name__)


def get_members(request, project, group):
    res = request.dbsession.query(Collaborator, Collingroup).filter(
        Collaborator.project_id == Collingroup.enum_project).filter(Collaborator.coll_id == Collingroup.coll_id).filter(
        Collingroup.project_id == project).filter(Collingroup.group_id == group).all()
    return map_from_schema(res)


def get_members_count(request, project, group):
    return request.dbsession.query(Collingroup).filter(Collingroup.project_id == project).filter(
        Collingroup.group_id == group).count()


def get_project_groups(request, project):
    res = request.dbsession.query(Collgroup).filter(Collgroup.project_id == project).order_by(
        Collgroup.group_cdate.desc()).all()
    mapped_data = map_from_schema(res)
    for group in mapped_data:
        group["members"] = get_members_count(request, project, group["group_id"])
    return mapped_data


def get_group_data(request, project, group):
    res = map_from_schema(request.dbsession.query(Collgroup).filter(Collgroup.project_id == project).filter(
        Collgroup.group_id == group).first())
    return res


def delete_group(request, project, group):
    try:
        request.dbsession.query(Collgroup).filter(Collgroup.project_id == project).filter(
            Collgroup.group_id == group).delete()
        request.dbsession.flush()
        return True, ""
    except RuntimeError:
        log.error(
            "Error {} while removing group {} from project {}".format(sys.exc_info()[0], group, project))
        request.dbsession.rollback()
        return False, sys.exc_info()[0]


def add_group(request, project, group_data):
    mapped_data = map_to_schema(Collgroup, group_data)
    group_id = str(uuid.uuid4())
    group_id = group_id[-12:]
    mapped_data['group_id'] = group_id
    mapped_data['group_cdate'] = datetime.datetime.now()
    mapped_data['group_active'] = 1
    mapped_data['project_id'] = project
    group_desc = " ".join(group_data['group_desc'].split())
    res = request.dbsession.query(Collgroup).filter(Collgroup.project_id == project).filter(
        Collgroup.group_desc == group_desc).first()
    if res is None:
        mapped_data['group_desc'] = group_desc
        new_group = Collgroup(**mapped_data)
        try:
            request.dbsession.add(new_group)
            request.dbsession.flush()
            return True, ""
        except IntegrityError:
            request.dbsession.rollback()
            log.error("The group code {} already exists in project {}".format(group_id, project))
            return False, request.translate("The group is already part of this project")
        except RuntimeError:
            request.dbsession.rollback()
            log.error("Error {} while adding group {} in project {}".format(sys.exc_info()[0], group_data['group_desc'],
                                                                            project))
            return False, sys.exc_info()[0]
    else:
        return False, request.translate("Such group already exists in this project")


def modify_group(request, project, group, group_data):
    mapped_data = map_to_schema(Collgroup, group_data)
    group_desc = " ".join(group_data['group_desc'].split())
    res = request.dbsession.query(Collgroup).filter(Collgroup.project_id == project).filter(
        Collgroup.group_id != group).filter(Collgroup.group_desc == group_desc).first()
    if res is None:
        try:
            mapped_data['group_desc'] = group_desc
            request.dbsession.query(Collgroup).filter(Collgroup.project_id == project).filter(
                Collgroup.group_id == group).update(mapped_data)
            request.dbsession.flush()
            return True, ''
        except IntegrityError:
            request.dbsession.rollback()
            return False, request.translate("The group is already part of this project")
        except RuntimeError:
            request.dbsession.rollback()
            log.error("Error {} while editing collaborator {} in project {}".format(sys.exc_info()[0],
                                                                                    group_data['group_desc'], project))
            return False, sys.exc_info()[0]
    else:
        return False, request.translate("Such group already exists in this project")


def add_assistant_to_group(request, project, group, assistant_project, assistant):
    new_member = Collingroup(project_id=project, group_id=group, enum_project=assistant_project, coll_id=assistant,
                             coll_privileges=1, join_date=datetime.datetime.now())
    try:
        request.dbsession.add(new_member)
        request.dbsession.flush()
        return True, ""
    except IntegrityError:
        request.dbsession.rollback()
        log.error("The group member {} already exists in group {} of project {}".format(assistant, group, project))
        return False, request.translate("The member is already part of this group")
    except RuntimeError:
        request.dbsession.rollback()
        log.error(
            "Error {} while adding member {} in group {} of project {}".format(sys.exc_info()[0], assistant, group,
                                                                               project))
        return False, sys.exc_info()[0]


def remove_assistant_from_group(request, project, group, assistant_project, assistant):
    try:
        request.dbsession.query(Collingroup).filter(Collingroup.project_id == project).filter(
            Collingroup.group_id == group).filter(Collingroup.enum_project == assistant_project).filter(
            Collingroup.coll_id == assistant).delete()
        request.dbsession.flush()
        return True, ""
    except IntegrityError:
        request.dbsession.rollback()
        log.error("Cannot remove member {} from group {} of project {}".format(assistant, group, project))
        return False, request.translate("Cannot remove the member")
    except RuntimeError:
        request.dbsession.rollback()
        log.error(
            "Error {} while removing member {} in group {} of project {}".format(sys.exc_info()[0], assistant, group,
                                                                                 project))
