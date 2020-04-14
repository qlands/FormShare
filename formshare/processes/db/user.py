from ...models import (
    map_to_schema,
    User,
    map_from_schema,
    Userproject,
    Odkform,
    Project,
)
from sqlalchemy.exc import IntegrityError
import logging
import validators
import datetime

__all__ = [
    "register_user",
    "user_exists",
    "get_user_details",
    "update_profile",
    "get_user_name",
    "get_user_by_api_key",
    "update_password",
    "email_exists",
    "update_last_login",
    "get_user_id_with_email",
]

log = logging.getLogger("formshare")


def get_user_stats(request, user):
    res = {
        "num_projects": request.dbsession.query(Userproject)
        .filter(Userproject.user_id == user)
        .filter(Userproject.project_accepted == 1)
        .count(),
        "num_forms": request.dbsession.query(Odkform)
        .filter(Odkform.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Userproject.project_accepted == 1)
        .count(),
    }

    last_project = (
        request.dbsession.query(Project.project_cdate)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .order_by(Project.project_cdate.desc())
        .first()
    )
    if last_project is not None:
        res["last_project"] = last_project.project_cdate
    else:
        res["last_project"] = None

    my_projects = (
        request.dbsession.query(Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Userproject.access_type == 1)
    )
    my_collaborators = map_from_schema(
        request.dbsession.query(User)
        .filter(Userproject.user_id == User.user_id)
        .filter(Userproject.access_type != 1)
        .filter(Userproject.project_accepted == 1)
        .filter(Userproject.project_id.in_(my_projects))
        .distinct(User.user_id)
        .all()
    )

    not_my_projects = (
        request.dbsession.query(Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Userproject.access_type != 1)
        .filter(Userproject.project_accepted == 1)
    )
    collaborators = map_from_schema(
        request.dbsession.query(User)
        .filter(Userproject.user_id == User.user_id)
        .filter(Userproject.access_type == 1)
        .filter(Userproject.project_accepted == 1)
        .filter(Userproject.project_id.in_(not_my_projects))
        .distinct(User.user_id)
        .all()
    )

    if len(my_collaborators) > 0:
        total_collaborators = my_collaborators
    else:
        total_collaborators = collaborators

    for c1 in total_collaborators:
        found = False
        searched = False
        for c2 in collaborators:
            searched = True
            if c1["user_id"] == c2["user_id"]:
                found = True
        if not found and searched:
            total_collaborators.append(c1)

    for c1 in total_collaborators:
        found = False
        searched = False
        for c2 in my_collaborators:
            searched = True
            if c1["user_id"] == c2["user_id"]:
                found = True
        if not found and searched:
            total_collaborators.append(c1)

    res["collaborators"] = total_collaborators
    return res


def register_user(request, user_data):
    _ = request.translate
    user_data.pop("user_password2", None)
    mapped_data = map_to_schema(User, user_data)
    email_valid = validators.email(mapped_data["user_email"])
    if email_valid:
        res = (
            request.dbsession.query(User)
            .filter(User.user_email == mapped_data["user_email"])
            .first()
        )
        if res is None:
            new_user = User(**mapped_data)
            try:
                request.dbsession.add(new_user)
                request.dbsession.flush()
                return True, ""
            except IntegrityError:
                request.dbsession.rollback()
                log.error("Duplicated user {}".format(mapped_data["user_id"]))
                return False, _("Username is already taken")
            except Exception as e:
                request.dbsession.rollback()
                log.error(
                    "Error {} when inserting user {}".format(
                        str(e), mapped_data["user_id"]
                    )
                )
                return False, str(e)
        else:
            log.error("Duplicated user with email {}".format(mapped_data["user_email"]))
            return False, _("Email is invalid")
    else:
        log.error("Email {} is not valid".format(mapped_data["user_email"]))
        return False, _("Email is invalid")


def user_exists(request, user, just_active=True):
    if just_active:
        res = (
            request.dbsession.query(User)
            .filter(User.user_id == user)
            .filter(User.user_active == 1)
            .first()
        )
    else:
        res = request.dbsession.query(User).filter(User.user_id == user).first()
    if res is None:
        return False
    return True


def get_user_details(request, user, just_active=True):
    if just_active:
        res = (
            request.dbsession.query(User)
            .filter(User.user_id == user)
            .filter(User.user_active == 1)
            .first()
        )
    else:
        res = request.dbsession.query(User).filter(User.user_id == user).first()
    if res is not None:
        result = map_from_schema(res)
        result["user_stats"] = get_user_stats(request, user)
        return result
    return {}


def email_exists(request, user, email):
    res = (
        request.dbsession.query(User)
        .filter(User.user_id != user)
        .filter(User.user_email == email)
        .first()
    )
    if res is None:
        return False
    else:
        return True


def get_user_name(request, user):
    res = (
        request.dbsession.query(User)
        .filter(User.user_id == user)
        .filter(User.user_active == 1)
        .first()
    )
    if res is not None:
        return res.user_name
    else:
        return None


def get_user_id_with_email(request, email):
    res = (
        request.dbsession.query(User)
        .filter(User.user_email == email)
        .filter(User.user_active == 1)
        .first()
    )
    if res is not None:
        return res.user_id
    else:
        return None


def update_profile(request, user, profile_data):
    mapped_data = map_to_schema(User, profile_data)
    try:
        request.dbsession.query(User).filter(User.user_id == user).update(mapped_data)
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} when updating user {}".format(str(e), user))
        return False, str(e)


def update_last_login(request, user):
    try:
        request.dbsession.query(User).filter(User.user_id == user).update(
            {"user_llogin": datetime.datetime.now()}
        )
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} when updating last login for user {}".format(str(e), user))
        return False, str(e)


def get_user_by_api_key(request, api_key):
    res = (
        request.dbsession.query(User)
        .filter(User.user_apikey == api_key)
        .filter(User.user_active == 1)
        .first()
    )
    if res is not None:
        result = map_from_schema(res)
        result["user_stats"] = get_user_stats(request, result["user_id"])
        return result
    return None


def update_password(request, user, password):
    try:
        request.dbsession.query(User).filter(User.user_id == user).update(
            {"user_password": password}
        )
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} when changing password for user {}".format(str(e), user))
        return False, str(e)
