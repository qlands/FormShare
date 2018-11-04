from ...models import map_to_schema, User, map_from_schema, Userproject, Odkform, Project
import sys
from sqlalchemy.exc import IntegrityError
import logging
from validate_email import validate_email

__all__ = [
    'register_user', 'user_exists', 'get_user_details', 'update_profile'
]

log = logging.getLogger(__name__)


def get_user_stats(request, user):
    res = {}
    res["num_projects"] = request.dbsession.query(Userproject).filter(Userproject.user_id == user).count()
    res["num_forms"] = request.dbsession.query(Odkform).filter(Odkform.project_id == Userproject.project_id).filter(
        Userproject.user_id == user).count()
    last_project = request.dbsession.query(Project.project_cdate).filter(
        Project.project_id == Userproject.project_id).filter(Userproject.user_id == user).order_by(
        Project.project_cdate.desc()).first()
    if last_project is not None:
        res["last_project"] = last_project.project_cdate
    else:
        res["last_project"] = None
    not_my_projects = request.dbsession.query(Userproject.project_id).filter(Userproject.user_id == user).filter(
        Userproject.access_type != 1)
    collaborators = map_from_schema(request.dbsession.query(User).filter(Userproject.user_id == User.user_id).filter(
        Userproject.access_type == 1).filter(Userproject.project_id.in_(not_my_projects)).distinct(User.user_id).all())
    res["collaborators"] = collaborators
    return res


def register_user(request, user_data):
    user_data.pop('user_password2', None)
    mapped_data = map_to_schema(User, user_data)
    email_valid = validate_email(mapped_data["user_email"])
    if email_valid:
        res = request.dbsession.query(User).filter(User.user_email == mapped_data["user_email"]).first()
        if res is None:
            new_user = User(**mapped_data)
            try:
                request.dbsession.add(new_user)
                request.dbsession.flush()
                return True, ""
            except IntegrityError:
                log.error("Duplicated user {}".format(mapped_data["user_id"]))
                return False, request.translate("Username is already taken")
            except RuntimeError:
                log.error("Error {} when inserting user {}".format(sys.exc_info()[0], mapped_data["user_id"]))
                return False, sys.exc_info()[0]
        else:
            log.error("Duplicated user with email {}".format(mapped_data["user_email"]))
            return False, request.translate("Email already taken")
    else:
        log.error("Email {} is not valid".format(mapped_data["user_email"]))
        return False, request.translate("Email is invalid")


def user_exists(request, user):
    res = request.dbsession.query(User).filter(User.user_id == user).filter(User.user_active == 1).first()
    if res is None:
        return False
    return True


def get_user_details(request, user):
    res = request.dbsession.query(User).filter(User.user_id == user).filter(User.user_active == 1).first()
    if res is not None:
        result = map_from_schema(res)
        result["user_stats"] = get_user_stats(request, user)
        return result
    return {}


def update_profile(request, user, profile_data):
    mapped_data = map_to_schema(User, profile_data)
    try:
        request.dbsession.query(User).filter(User.user_id == user).update(mapped_data)
        request.dbsession.flush()
        return True, ""
    except RuntimeError:
        log.error("Error {} when updating user user {}".format(sys.exc_info()[0], user))
        return False, sys.exc_info()[0]
