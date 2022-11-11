import datetime
import logging
import secrets

from formshare.models import (
    map_to_schema,
    User,
    map_from_schema,
    Userproject,
    Odkform,
    Project,
    TimeZone,
)
from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

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
    "get_users",
    "get_user_timezone",
    "is_user_active",
    "get_query_user",
    "get_user_databases",
    "set_query_user",
    "get_query_password",
]

log = logging.getLogger("formshare")


def get_user_timezone(request, user):
    res = (
        request.dbsession.query(
            User.user_timezone, TimeZone.timezone_name, TimeZone.timezone_utc_offset
        )
        .filter(User.user_id == user)
        .filter(User.user_timezone == TimeZone.timezone_code)
        .first()
    )
    return map_from_schema(res)


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
        .filter(Userproject.project_id.in_(not_my_projects))
        .distinct(User.user_id)
        .all()
    )
    if len(my_collaborators) > 0 and len(collaborators) > 0:
        total_collaborators = my_collaborators
        t_total_collaborators = total_collaborators.copy()
        for c1 in collaborators:
            found = False
            for c2 in t_total_collaborators:
                if c1["user_id"] == c2["user_id"]:
                    found = True
            if not found:
                total_collaborators.append(c1)
    else:
        if len(my_collaborators) > 0:
            total_collaborators = my_collaborators
        else:
            total_collaborators = collaborators

    res["collaborators"] = total_collaborators
    return res


def register_user(request, user_data):
    _ = request.translate
    user_data.pop("user_password2", None)
    mapped_data = map_to_schema(User, user_data)
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
                "Error {} when inserting user {}".format(str(e), mapped_data["user_id"])
            )
            return False, str(e)
    else:
        log.error("Duplicated user with email {}".format(mapped_data["user_email"]))
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


def is_user_active(request, user_id):
    res = request.dbsession.query(User).filter(User.user_id == user_id).first()
    if res is not None:
        if res.user_active == 1:
            return True
    return False


def get_query_user(request, user_id):
    res = request.dbsession.query(User).filter(User.user_id == user_id).first()
    if res is not None:
        return res.user_query_user
    return None


def get_query_password(request, user_id):
    res = (
        request.dbsession.query(User)
        .filter(User.user_id == user_id)
        .filter(User.user_query_user.isnot(None))
        .first()
    )
    if res is not None:
        return res.user_query_password
    return None


def set_query_user(request, user_id, query_user, query_encrypted_password):
    try:
        request.dbsession.query(User).filter(User.user_id == user_id).update(
            {
                "user_query_user": query_user,
                "user_query_password": query_encrypted_password,
            }
        )
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} when setting query user details for user {}".format(
                str(e), user_id
            )
        )
        return False, str(e)


def get_user_databases(request, user_id):
    res = (
        request.dbsession.query(
            Project.project_id,
            Project.project_code,
            Project.project_name,
            Odkform.form_schema,
            Odkform.form_id,
            Odkform.form_name,
            Userproject.access_type,
        )
        .distinct(Odkform.form_schema)
        .filter(Odkform.project_id == Userproject.project_id)
        .filter(Odkform.project_id == Project.project_id)
        .filter(Userproject.project_accepted == 1)
        .filter(Userproject.user_id == user_id)
        .filter(Odkform.form_schema.isnot(None))
        .order_by(Project.project_name)
        .order_by(Odkform.form_name)
        .all()
    )
    if res is not None:
        databases = []
        for a_database in res:
            databases.append(
                {
                    "project_id": a_database.project_id,
                    "project_code": a_database.project_code,
                    "project_name": a_database.project_name,
                    "form_id": a_database.form_id,
                    "form_name": a_database.form_name,
                    "form_schema": a_database.form_schema,
                    "access_type": a_database.access_type,
                }
            )
        if databases:
            return databases
    return None


def get_users(request):
    res = request.dbsession.query(User).all()
    res = map_from_schema(res)
    return res


def get_user_details(request, user, just_active=True, get_stats=True):
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
        if get_stats:
            result["user_stats"] = get_user_stats(request, user)
        return result
    return {}


def email_exists(request, user, email):
    res = (
        request.dbsession.query(User)
        .filter(User.user_id != user)
        .filter(func.lower(User.user_email) == func.lower(email))
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
        .filter(func.lower(User.user_email) == func.lower(email))
        .filter(User.user_active == 1)
        .first()
    )
    if res is not None:
        return res.user_id
    else:
        return None


def update_profile(request, user, profile_data):
    if "api_changed" in profile_data.keys():
        if profile_data["api_changed"] == "1":
            profile_data["user_apitoken"] = (
                "invalid_" + secrets.token_hex(16) + "_invalid"
            )
        profile_data.pop("api_changed", None)
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
    engine = create_engine(
        request.registry.settings.get("sqlalchemy.url"), poolclass=NullPool
    )
    try:
        connection = engine.connect()
    except Exception as e:
        engine.dispose()
        log.error(
            "Error {} when updating last login for user {}. Cannot connect to MySQL".format(
                str(e), user
            )
        )
        return False, str(e)
    string_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = "UPDATE fsuser set user_llogin = '{}' WHERE user_id = '{}'".format(
        string_date, user
    )
    try:
        connection.execute(sql)
        connection.invalidate()
        engine.dispose()
        return True, ""
    except Exception as e:
        log.error("Error {} when updating last login for user {}".format(str(e), user))
        connection.invalidate()
        engine.dispose()
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
