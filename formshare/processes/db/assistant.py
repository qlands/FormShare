import datetime
import logging
from formshare.processes.logging.loggerclass import SecretLogger
import secrets
from uuid import uuid4
import validators
import re
from formshare.config.encdecdata import decode_data
from formshare.config.encdecdata import encode_data
from formshare.models import (
    Collaborator,
    Project,
    map_from_schema,
    map_to_schema,
    Userproject,
    Formacces,
    Formgrpacces,
    Collingroup,
    TimeZone,
    User,
)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

__all__ = [
    "get_project_assistants",
    "delete_assistant",
    "add_assistant",
    "get_assistant_data",
    "modify_assistant",
    "change_assistant_password",
    "get_all_assistants",
    "is_assistant_active",
    "get_assistant_password",
    "get_assistant_login",
    "get_assistant_uuid_password",
    "get_project_from_assistant",
    "get_assigned_assistants",
    "get_assistant_by_api_key",
    "get_assistant_timezone",
    "get_one_assistant",
    "get_assistant_with_token",
    "assistant_exist",
    "get_assistant_uuid",
    "get_assistant_uuid_with_email",
    "get_global_assistant_with_user",
    "get_odk_assistant_uuid",
    "get_assistant_data_for_user",
    "get_assistant_data_with_uuid",
]

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


def get_one_assistant(request, project, form):
    res = (
        request.dbsession.query(Project.project_formlist_auth)
        .filter(Project.project_id == project)
        .first()
    )
    if res[0] == 0:
        return "public"
    res = (
        request.dbsession.query(Formacces)
        .filter(Formacces.form_project == project)
        .filter(Formacces.form_id == form)
        .filter(Formacces.coll_can_submit == 1)
        .first()
    )
    if res is not None:
        return res.coll_uuid
    else:
        res = (
            request.dbsession.query(Formgrpacces)
            .filter(Formgrpacces.form_project == project)
            .filter(Formgrpacces.form_id == form)
            .filter(Formgrpacces.group_can_submit == 1)
            .first()
        )
        if res is not None:
            project_id = res.project_id
            group_id = res.group_id
            res = (
                request.dbsession.query(Collingroup)
                .filter(Collingroup.project_id == project_id)
                .filter(Collingroup.group_id == group_id)
                .first()
            )
            if res is not None:
                return res.coll_uuid
            else:
                return None
        else:
            return None


def get_assistant_timezone(request, assistant_uuid):
    res = (
        request.dbsession.query(Collaborator.linked_user)
        .filter(Collaborator.coll_uuid == assistant_uuid)
        .first()
    )
    if res[0] is not None:
        res = (
            request.dbsession.query(
                User.user_timezone,
                TimeZone.timezone_name,
                TimeZone.timezone_utc_offset,
            )
            .filter(User.user_id == res[0])
            .filter(User.user_timezone == TimeZone.timezone_code)
            .first()
        )
        result = map_from_schema(res)
        result["coll_timezone"] = result["user_timezone"]
        return result

    res = (
        request.dbsession.query(
            Collaborator.coll_timezone,
            TimeZone.timezone_name,
            TimeZone.timezone_utc_offset,
        )
        .filter(Collaborator.coll_uuid == assistant_uuid)
        .filter(Collaborator.coll_timezone == TimeZone.timezone_code)
        .first()
    )
    return map_from_schema(res)


def get_assigned_assistants(request, project, form):
    assistants = []
    groups = (
        request.dbsession.query(Formgrpacces)
        .filter(Formgrpacces.form_project == project)
        .filter(Formgrpacces.form_id == form)
        .all()
    )
    for group in groups:
        res = (
            request.dbsession.query(Collaborator, Collingroup)
            .filter(Collingroup.coll_uuid == Collaborator.coll_uuid)
            .filter(Collingroup.project_id == group.project_id)
            .filter(Collingroup.group_id == group.group_id)
            .all()
        )
        group_assistants = map_from_schema(res)
        for assistant in group_assistants:
            assistants.append(
                {
                    "project": assistant["enum_project"],
                    "assistant": assistant["coll_id"],
                    "assistant_uuid": assistant["coll_uuid"],
                    "name": assistant["coll_name"],
                }
            )

    res = (
        request.dbsession.query(Formacces, Collaborator)
        .filter(Formacces.coll_uuid == Collaborator.coll_uuid)
        .filter(Formacces.form_project == project)
        .filter(Formacces.form_id == form)
        .all()
    )
    form_assistants = map_from_schema(res)
    for an_assistant in form_assistants:
        found = False
        for assistant in assistants:
            if (
                assistant["project"] == an_assistant["project_id"]
                and assistant["assistant"] == an_assistant["coll_id"]
            ):
                found = True
        if not found:
            assistants.append(
                {
                    "project": an_assistant["project_id"],
                    "assistant": an_assistant["coll_id"],
                    "assistant_uuid": an_assistant["coll_uuid"],
                    "name": an_assistant["coll_name"],
                }
            )
    return assistants


def get_all_assistants(request, project_user, project_id, tenant_id=None):
    res = (
        request.dbsession.query(Project, Collaborator)
        .filter(Project.project_id == Collaborator.project_id)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == project_user)
        .filter(Userproject.access_type == 1)
        .filter(Collaborator.coll_prjshare == 1)
        .filter(Project.project_archived == 0)
        .filter(Project.project_archiving == 0)
        .filter(Project.project_restoring == 0)
        .all()
    )
    all_assistants = map_from_schema(res)

    # Current project collaborators
    res = (
        request.dbsession.query(Project, Collaborator)
        .filter(Project.project_id == Collaborator.project_id)
        .filter(Project.project_id == project_id)
        .all()
    )
    this_project_assistants = map_from_schema(res)
    for an_assistant in this_project_assistants:
        found = False
        for item in all_assistants:
            if (
                item["project_id"] == an_assistant["project_id"]
                and item["coll_id"] == an_assistant["coll_id"]
            ):
                found = True
        if not found:
            all_assistants.append(an_assistant)

    assistants = []

    if tenant_id is not None:
        #  Get global Assistants
        res = (
            request.dbsession.query(User, Collaborator)
            .filter(Collaborator.linked_user == User.user_id)
            .filter(Collaborator.coll_tenant == tenant_id)
            .filter(Collaborator.coll_type == 2)
            .all()
        )
        global_assistants = map_from_schema(res)
        for a_global_assistant in global_assistants:
            assistants.append(
                {
                    "project_id": "global",
                    "project_desc": "Global assistants",
                    "assistants": [
                        {
                            "code": "||" + a_global_assistant["coll_uuid"],
                            "id": "global",
                            "name": a_global_assistant["user_name"],
                            "used": False,
                        }
                    ],
                }
            )

    for item in all_assistants:
        index = 0
        found = False
        if item["project_id"] is not None:
            for assistant in assistants:
                if assistant["project_id"] == item["project_id"]:
                    found = True
                    break
                index = index + 1
            if found:
                assistants[index]["assistants"].append(
                    {
                        "code": item["project_id"]
                        + "|"
                        + item["coll_id"]
                        + "|"
                        + item["coll_uuid"],
                        "uuid": item["coll_uuid"],
                        "id": item["coll_id"],
                        "name": item["coll_name"],
                        "used": False,
                    }
                )
            else:
                assistants.append(
                    {
                        "project_id": item["project_id"],
                        "project_desc": item["project_name"],
                        "assistants": [
                            {
                                "code": item["project_id"]
                                + "|"
                                + item["coll_id"]
                                + "|"
                                + item["coll_uuid"],
                                "id": item["coll_id"],
                                "name": item["coll_name"],
                                "used": False,
                            }
                        ],
                    }
                )

    return assistants


def get_project_assistants(request, project, return_max=0):
    res = (
        request.dbsession.query(Collaborator)
        .filter(Collaborator.project_id == project)
        .order_by(Collaborator.coll_cdate.desc())
        .all()
    )
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


def get_assistant_data_for_user(request, tenant_id, user_email):
    res = (
        request.dbsession.query(User)
        .filter(User.user_email == user_email)
        .filter(User.user_tenant == tenant_id)
        .first()
    )
    return {
        "coll_name": res.user_name,
        "coll_id": user_email,
        "coll_email": user_email,
        "project_id": "global",
    }


def get_assistant_data_with_uuid(request, assistant_uuid):
    res = map_from_schema(
        request.dbsession.query(Collaborator)
        .filter(Collaborator.coll_uuid == assistant_uuid)
        .first()
    )
    if res["linked_user"] is None:
        return res
    else:
        linked_user = res["linked_user"]
        res = request.dbsession.query(User).filter(User.user_id == linked_user).first()
        return {
            "coll_name": res.user_name,
            "coll_id": res.user_id,
            "coll_email": res.user_email,
            "project_id": "global",
        }


def get_assistant_data(request, project, assistant):
    res = map_from_schema(
        request.dbsession.query(Collaborator)
        .filter(Collaborator.project_id == project)
        .filter(Collaborator.coll_id == assistant)
        .first()
    )
    return res


def get_assistant_by_api_key(request, api_key):
    res = map_from_schema(
        request.dbsession.query(Collaborator)
        .filter(Collaborator.coll_apikey == api_key)
        .first()
    )
    return res


def delete_assistant(request, assistant_uuid):
    try:
        request.dbsession.query(Collaborator).filter(
            Collaborator.coll_uuid == assistant_uuid
        ).delete()
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while removing assistant {}".format(str(e), assistant_uuid))
        return False, str(e)


def assistant_exist(request, user, project, assistant_data):
    if assistant_data["coll_type"] == 1:
        res = (
            request.dbsession.query(func.count(Collaborator.coll_uuid))
            .filter(Collaborator.project_id == Userproject.project_id)
            .filter(Userproject.project_id == Project.project_id)
            .filter(Userproject.user_id == user)
            .filter(Userproject.access_type == 1)
            .filter(Project.project_archived == 0)
            .filter(Project.project_archiving == 0)
            .filter(Project.project_restoring == 0)
            .filter(Collaborator.coll_id == assistant_data["coll_id"])
            .filter(Collaborator.project_id != project)
            .first()
        )
        if res[0] != 0:
            return True
    else:
        res = (
            request.dbsession.query(func.count(Collaborator.coll_uuid))
            .filter(Collaborator.coll_email == assistant_data["coll_email"])
            .filter(Collaborator.coll_tenant == assistant_data["coll_tenant"])
            .first()
        )
        if res[0] != 0:
            return True
    return False


def add_assistant(request, user, project, assistant_data, flush=True, check_exist=True):
    _ = request.translate
    if check_exist:
        if assistant_exist(request, user, project, assistant_data):
            return (
                False,
                _(
                    "The assistant already exists in your account. "
                    "You do not need to duplicate assistants, "
                    'just mark them as "Share among projects" to use them across projects.'
                ),
            )
    mapped_data = map_to_schema(Collaborator, assistant_data)
    mapped_data["coll_cdate"] = datetime.datetime.now()
    mapped_data["coll_active"] = 1
    mapped_data["project_id"] = project
    mapped_data["coll_apikey"] = str(uuid4())
    mapped_data["coll_apisecret"] = encode_data(request, secrets.token_hex(16))
    mapped_data["coll_password"] = encode_data(request, mapped_data["coll_password"])
    new_assistant = Collaborator(**mapped_data)
    try:
        request.dbsession.add(new_assistant)
        if flush:
            request.dbsession.commit()
        return True, ""
    except IntegrityError:
        if flush:
            request.dbsession.rollback()
        return False, _("The assistant is already part of this project")
    except Exception as e:
        if flush:
            request.dbsession.rollback()
        log.error(
            "Error {} while adding assistant {} in project {}".format(
                str(e), assistant_data["coll_name"], project
            )
        )
        return False, str(e)


def modify_assistant(request, assistant_uuid, assistant_data):
    if (
        "coll_apikey" in assistant_data.keys()
        and "coll_apisecret" in assistant_data.keys()
    ):
        assistant_data["coll_apitoken"] = (
            "invalid_" + secrets.token_hex(16) + "_invalid"
        )
    _ = request.translate
    mapped_data = map_to_schema(Collaborator, assistant_data)
    try:
        request.dbsession.query(Collaborator).filter(
            Collaborator.coll_uuid == assistant_uuid
        ).update(mapped_data)
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while adding assistant {}.".format(str(e), assistant_uuid))
        return False, str(e)


def change_assistant_password(request, assistant_uuid, password):
    encrypted_password = encode_data(request, password)
    try:
        request.dbsession.query(Collaborator).filter(
            Collaborator.coll_uuid == assistant_uuid
        ).update({"coll_password": encrypted_password})
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while changing password for assistant {}".format(
                str(e),
                assistant_uuid,
            )
        )
        return False, str(e)


def _get_project_tenant(request, project_id):
    res = (
        request.dbsession.query(Project)
        .filter(Project.project_id == project_id)
        .first()
    )
    if res is not None:
        return res.project_tenant
    return None


def get_odk_assistant_uuid(request, user, project, assistant):
    if validators.email(assistant) and re.match(r"^[A-Za-z0-9._@-]+$", assistant):
        project_tenant = _get_project_tenant(request, project)
        return get_assistant_uuid_with_email(request, project_tenant, assistant)
    else:
        project_of_assistant = get_project_from_assistant(
            request, user, project, assistant
        )
        return get_assistant_uuid(request, project_of_assistant, assistant)


def get_assistant_uuid_with_email(request, tenant, assistant_email):
    res = (
        request.dbsession.query(User, Collaborator)
        .filter(Collaborator.linked_user == User.user_id)
        .filter(Collaborator.coll_tenant == tenant)
        .filter(User.user_email == assistant_email)
        .first()
    )
    res = map_from_schema(res)
    if res is not None:
        return res["coll_uuid"]
    else:
        return None


def get_assistant_uuid(request, project, assistant):
    res = (
        request.dbsession.query(Collaborator.coll_uuid)
        .filter(Collaborator.project_id == project)
        .filter(Collaborator.coll_id == assistant)
        .first()
    )
    if res is not None:
        return res[0]
    else:
        return None


def get_global_assistant_with_user(request, tenant_id, user_id):
    res = (
        request.dbsession.query(Collaborator)
        .filter(Collaborator.coll_tenant == tenant_id)
        .filter(Collaborator.linked_user == user_id)
        .first()
    )
    if res is not None:
        return res.coll_uuid
    return None


def get_project_from_assistant(request, user, requested_project, assistant):
    # Get all the assistants the user has with that name across projects
    num_assistants = (
        request.dbsession.query(Userproject, Collaborator)
        .filter(Userproject.project_id == Collaborator.project_id)
        .filter(Userproject.project_id == Project.project_id)
        .filter(Userproject.user_id == user)
        .filter(Userproject.access_type == 1)
        .filter(Project.project_archived == 0)
        .filter(Project.project_archiving == 0)
        .filter(Project.project_restoring == 0)
        .filter(Collaborator.coll_id == assistant)
        .count()
    )
    if num_assistants > 0:
        if num_assistants == 1:
            # If the user has just one assistant with that name then gets his data
            assistant_data = (
                request.dbsession.query(Collaborator)
                .filter(Userproject.project_id == Collaborator.project_id)
                .filter(Userproject.project_id == Project.project_id)
                .filter(Userproject.user_id == user)
                .filter(Userproject.access_type == 1)
                .filter(Project.project_archived == 0)
                .filter(Project.project_archiving == 0)
                .filter(Project.project_restoring == 0)
                .filter(Collaborator.coll_id == assistant)
                .first()
            )
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


def is_assistant_active(request, assistant_uuid):
    if assistant_uuid is None:
        return False
    enum = (
        request.dbsession.query(Collaborator)
        .filter(Collaborator.coll_uuid == assistant_uuid)
        .first()
    )
    if enum is not None:
        if enum.coll_active == 1:
            return True
    return False

    # # Get all the assistants the user has with that name across projects
    # num_assistants = (
    #     request.dbsession.query(Userproject, Collaborator)
    #     .filter(Userproject.project_id == Collaborator.project_id)
    #     .filter(Userproject.user_id == user)
    #     .filter(Userproject.access_type == 1)
    #     .filter(Collaborator.coll_id == assistant)
    #     .count()
    # )
    # if num_assistants > 0:
    #     if num_assistants == 1:
    #         # If the user has just one assistant with that name then gets his data
    #         assistant_data = (
    #             request.dbsession.query(Collaborator)
    #             .filter(Userproject.project_id == Collaborator.project_id)
    #             .filter(Userproject.user_id == user)
    #             .filter(Userproject.access_type == 1)
    #             .filter(Collaborator.coll_id == assistant)
    #             .first()
    #         )
    #         # Is the assistant from the same project?
    #         if assistant_data.project_id == project:
    #             enum = (
    #                 request.dbsession.query(Collaborator)
    #                 .filter(Collaborator.project_id == assistant_data.project_id)
    #                 .filter(Collaborator.coll_id == assistant)
    #                 .first()
    #             )
    #             if enum is not None:
    #                 if enum.coll_active == 1:
    #                     return True
    #                 else:
    #                     return False
    #             else:
    #                 return False
    #         else:
    #             # Is the assistant shareable across projects?
    #             if assistant_data.coll_prjshare == 1:
    #                 enum = (
    #                     request.dbsession.query(Collaborator)
    #                     .filter(Collaborator.project_id == assistant_data.project_id)
    #                     .filter(Collaborator.coll_id == assistant)
    #                     .first()
    #                 )
    #                 if enum is not None:
    #                     if enum.coll_active == 1:
    #                         return True
    #                     else:
    #                         return False
    #                 else:
    #                     return False
    #             else:
    #                 return False
    #     else:
    #         # If there are more than one assistant then use the project in the URL
    #         enum = (
    #             request.dbsession.query(Collaborator)
    #             .filter(Collaborator.project_id == project)
    #             .filter(Collaborator.coll_id == assistant)
    #             .first()
    #         )
    #         if enum is not None:
    #             if enum.coll_active == 1:
    #                 return True
    #             else:
    #                 return False
    #         else:
    #             return False
    # else:
    #     return False


def get_assistant_login(request, assistant_uuid):
    if assistant_uuid == "public":
        return "public"
    assistant_data = (
        request.dbsession.query(Collaborator)
        .filter(Collaborator.coll_uuid == assistant_uuid)
        .first()
    )
    if assistant_data.linked_user is not None:
        res = (
            request.dbsession.query(User)
            .filter(User.user_id == assistant_data.linked_user)
            .first()
        )
        return res.user_email

    else:
        return assistant_data.coll_id


def get_assistant_password(request, assistant_uuid):

    assistant_data = (
        request.dbsession.query(Collaborator)
        .filter(Collaborator.coll_uuid == assistant_uuid)
        .first()
    )
    if assistant_data.linked_user is not None:
        res = (
            request.dbsession.query(User)
            .filter(User.user_id == assistant_data.linked_user)
            .first()
        )
        decrypted = decode_data(request, res.user_assistant_password.encode())
        return decrypted

    else:
        decrypted = decode_data(request, assistant_data.coll_password.encode())
        return decrypted


def get_assistant_uuid_password(request, assistant_uuid, decrypt=True):
    enum = (
        request.dbsession.query(Collaborator)
        .filter(Collaborator.coll_uuid == assistant_uuid)
        .first()
    )
    if decrypt:
        decrypted = decode_data(request, enum.coll_password.encode())
        return decrypted
    else:
        return enum.coll_password


def get_assistant_with_token(request, token):
    res = (
        request.dbsession.query(Collaborator)
        .filter(Collaborator.coll_apitoken == token)
        .filter(Collaborator.coll_apitoken_expires_on >= datetime.datetime.now())
        .first()
    )
    if res is not None:
        return res.coll_id
    return None
