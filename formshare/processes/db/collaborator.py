from formshare.models import Userproject, User, map_from_schema
import logging
import datetime
from sqlalchemy.exc import IntegrityError

__all__ = [
    "get_project_collaborators",
    "remove_collaborator_from_project",
    "set_collaborator_role",
    "add_collaborator_to_project",
    "accept_collaboration",
    "decline_collaboration",
]

log = logging.getLogger("formshare")


def get_project_collaborators(
    request, project, current_user=None, retrieve_max=0, accepted_only=False
):
    if not accepted_only:
        if current_user is not None:
            res = (
                request.dbsession.query(User, Userproject)
                .filter(Userproject.user_id == User.user_id)
                .filter(Userproject.project_id == project)
                .filter(Userproject.user_id != current_user)
                .order_by(Userproject.access_date.desc())
                .all()
            )
        else:
            res = (
                request.dbsession.query(User, Userproject)
                .filter(Userproject.user_id == User.user_id)
                .filter(Userproject.project_id == project)
                .filter(Userproject.access_type != 1)
                .order_by(Userproject.access_date.desc())
                .all()
            )
    else:
        if current_user is not None:
            res = (
                request.dbsession.query(User, Userproject)
                .filter(Userproject.user_id == User.user_id)
                .filter(Userproject.project_id == project)
                .filter(Userproject.user_id != current_user)
                .filter(Userproject.project_accepted == 1)
                .order_by(Userproject.access_date.desc())
                .all()
            )
        else:
            res = (
                request.dbsession.query(User, Userproject)
                .filter(Userproject.user_id == User.user_id)
                .filter(Userproject.project_id == project)
                .filter(Userproject.access_type != 1)
                .filter(Userproject.project_accepted == 1)
                .order_by(Userproject.access_date.desc())
                .all()
            )

    mapped_data = map_from_schema(res)
    if retrieve_max <= 0:
        return mapped_data, 0
    else:
        more = len(mapped_data) - retrieve_max
        if more > 0:
            result = []
            index = 1
            for item in mapped_data:
                if index <= retrieve_max:
                    result.append(item)
                    index = index + 1
                else:
                    break
            return result, more
        else:
            return mapped_data, 0


def remove_collaborator_from_project(request, project, collaborator):
    try:
        request.dbsession.query(Userproject).filter(
            Userproject.project_id == project
        ).filter(Userproject.user_id == collaborator).delete()
        request.dbsession.flush()

        active_project = (
            request.dbsession.query(Userproject)
            .filter(Userproject.user_id == collaborator)
            .filter(Userproject.project_active == 1)
            .first()
        )
        if active_project is None:
            last_project = (
                request.dbsession.query(Userproject)
                .filter(Userproject.user_id == collaborator)
                .order_by(Userproject.access_date.desc())
                .first()
            )
            if last_project is not None:
                last_project_id = last_project.project_id
                request.dbsession.query(Userproject).filter(
                    Userproject.user_id == collaborator
                ).filter(Userproject.project_id == last_project_id).update(
                    {"project_active": 1}
                )

        return True, ""
    except Exception as e:
        log.error(
            "Error {} while removing collaborator {} from project {}".format(
                str(e), collaborator, project
            )
        )
        return False, str(e)


def set_collaborator_role(request, project, collaborator, role):
    try:
        request.dbsession.query(Userproject).filter(
            Userproject.project_id == project
        ).filter(Userproject.user_id == collaborator).update({"access_type": role})
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        log.error(
            "Error {} while changing role to collaborator {} in project {}".format(
                str(e), collaborator, project
            )
        )
        return False, str(e)


def add_collaborator_to_project(request, project, collaborator):
    _ = request.translate
    active_projects = (
        request.dbsession.query(Userproject.user_id == collaborator)
        .filter(Userproject.project_active == 1)
        .first()
    )
    if active_projects is not None:
        project_active = 0
    else:
        project_active = 1
    auto_accept_collaboration = request.registry.settings.get(
        "auth.auto_accept_collaboration", "false"
    )
    if auto_accept_collaboration == "true":
        project_accepted = 1
        project_accepted_date = datetime.datetime.now()
    else:
        project_accepted = 0
        project_active = 0
        project_accepted_date = None
    new_collaborator = Userproject(
        user_id=collaborator,
        project_id=project,
        access_type=4,
        access_date=datetime.datetime.now(),
        project_active=project_active,
        project_accepted=project_accepted,
        project_accepted_date=project_accepted_date,
    )
    try:
        request.dbsession.add(new_collaborator)
        request.dbsession.flush()
        return True, ""
    except IntegrityError:
        return False, _("The collaborator is already part of this project")
    except Exception as e:
        log.error(
            "Error {} while adding collaborator {} in project {}".format(
                str(e), collaborator, project
            )
        )
        return False, str(e)


def accept_collaboration(request, user, project):
    _ = request.translate
    request.dbsession.query(Userproject).filter(Userproject.user_id == user).update(
        {"project_active": 0}
    )
    request.dbsession.query(Userproject).filter(Userproject.user_id == user).filter(
        Userproject.project_id == project
    ).filter(Userproject.project_accepted == 0).update(
        {
            "project_accepted": 1,
            "project_accepted_date": datetime.datetime.now(),
            "project_active": 1,
        }
    )
    try:
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        log.error(
            "Error {} while accepting collaboration for user {} in project {}".format(
                str(e), user, project
            )
        )
        return False, str(e)


def decline_collaboration(request, user, project):
    _ = request.translate
    request.dbsession.query(Userproject).filter(Userproject.user_id == user).filter(
        Userproject.project_id == project
    ).filter(Userproject.project_accepted == 0).delete()
    try:
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        log.error(
            "Error {} while declining collaboration for user {} in project {}".format(
                str(e), user, project
            )
        )
        return False, str(e)
