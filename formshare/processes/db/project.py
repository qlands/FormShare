from formshare.models import (
    Project,
    Userproject,
    map_to_schema,
    map_from_schema,
    Submission,
    Odkform,
    Collaborator,
    ProjectFile,
)
import logging
import datetime
import uuid
from sqlalchemy.exc import IntegrityError
from formshare.processes.elasticsearch.repository_index import (
    get_dataset_stats_for_project,
)
from formshare.processes.db.form import get_by_details, get_form_data
import dateutil.parser

__all__ = [
    "get_project_id_from_name",
    "get_user_projects",
    "get_active_project",
    "add_project",
    "modify_project",
    "delete_project",
    "is_collaborator",
    "add_file_to_project",
    "get_project_files",
    "remove_file_from_project",
    "get_project_code_from_id",
    "get_project_details",
    "set_project_as_active",
    "get_project_owner",
]

log = logging.getLogger("formshare")


def get_project_id_from_name(request, user, project_code):
    res = (
        request.dbsession.query(Project)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Project.project_code == project_code)
        .filter(Userproject.access_type == 1)
        .filter(Userproject.project_accepted == 1)
        .first()
    )
    if res is not None:
        return res.project_id
    return None


def get_project_code_from_id(request, user, project_id):
    res = (
        request.dbsession.query(Project)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Project.project_id == project_id)
        .filter(Userproject.access_type == 1)
        .filter(Userproject.project_accepted == 1)
        .first()
    )
    if res is not None:
        return res.project_code
    return None


def get_forms_number(request, project):
    total = (
        request.dbsession.query(Odkform).filter(Odkform.project_id == project).count()
    )
    return total


def get_project_submissions(request, project):
    total = (
        request.dbsession.query(Submission)
        .filter(Submission.project_id == project)
        .count()
    )
    return total


def get_last_submission(request, project):
    res = (
        request.dbsession.query(
            Submission.submission_dtime,
            Odkform.form_name,
            Collaborator.coll_name,
            Project.project_id,
            Project.project_name,
        )
        .filter(
            Submission.project_id == Odkform.project_id,
            Submission.form_id == Odkform.form_id,
        )
        .filter(
            Submission.enum_project == Collaborator.project_id,
            Submission.coll_id == Collaborator.coll_id,
        )
        .filter(Collaborator.project_id == Project.project_id)
        .filter(Submission.project_id == project)
        .order_by(Submission.submission_dtime.desc())
        .first()
    )
    return map_from_schema(res)


def get_project_owner(request, project):
    res = (
        request.dbsession.query(Userproject.user_id)
        .filter(Userproject.project_id == project)
        .filter(Userproject.access_type == 1)
        .filter(Userproject.project_accepted == 1)
        .first()
    )
    if res is not None:
        return res.user_id
    else:
        return None


def is_collaborator(request, user, project, accepted_status=1):
    res = (
        request.dbsession.query(Userproject.user_id)
        .filter(Userproject.project_id == project)
        .filter(Userproject.user_id == user)
        .filter(Userproject.project_accepted == accepted_status)
        .first()
    )
    if res is not None:
        return True
    else:
        return False


def get_user_projects(request, user, logged_user, private=False):
    if private:
        if user == logged_user:
            # The logged account is the user account = Seeing my projects
            res = (
                request.dbsession.query(Project, Userproject)
                .filter(Project.project_id == Userproject.project_id)
                .filter(Userproject.user_id == user)
                .filter(Userproject.project_accepted == 1)
                .all()
            )
            projects = map_from_schema(res)
        else:
            projects = []
            # The logged account is different as the user account =  Seeing someone else projects

            # Get all the projects of that user
            all_user_projects = (
                request.dbsession.query(Project)
                .filter(Project.project_id == Userproject.project_id)
                .filter(Userproject.user_id == user)
                .filter(Userproject.project_accepted == 1)
                .all()
            )
            all_user_projects = map_from_schema(all_user_projects)
            for project in all_user_projects:
                # Check each project to see if the logged user collaborate with it
                res = (
                    request.dbsession.query(Project, Userproject)
                    .filter(Project.project_id == Userproject.project_id)
                    .filter(Userproject.user_id == logged_user)
                    .filter(Userproject.project_id == project["project_id"])
                    .filter(Userproject.project_accepted == 1)
                    .first()
                )
                collaborative_project = map_from_schema(res)
                if collaborative_project:
                    collaborative_project["collaborate"] = True
                    collaborative_project["user_id"] = user
                    projects.append(collaborative_project)
                else:
                    if project["project_public"] == 1:
                        project["collaborate"] = False
                        project["access_type"] = 5
                        projects.append(project)
    else:
        res = (
            request.dbsession.query(Project, Userproject)
            .filter(Project.project_id == Userproject.project_id)
            .filter(Userproject.user_id == user)
            .filter(Project.project_public == 1)
            .filter(Userproject.project_accepted == 1)
            .all()
        )
        projects = map_from_schema(res)

    for project in projects:
        submissions, last, by, form = get_dataset_stats_for_project(
            request.registry.settings, user, project["project_code"]
        )
        if last is not None:
            project["last_submission"] = dateutil.parser.parse(last)
        else:
            project["last_submission"] = None
        project["total_submissions"] = submissions
        project["last_submission_by"] = by
        project["last_submission_by_details"] = get_by_details(
            request, user, project["project_id"], by
        )
        project["last_submission_form"] = form
        project["last_submission_form_details"] = get_form_data(
            request, project["project_id"], form
        )
        project["total_forms"] = get_forms_number(request, project["project_id"])
        if private:
            project["owner"] = get_project_owner(request, project["project_id"])
        else:
            project["owner"] = get_project_owner(request, project["project_id"])
            project["access_type"] = 5
    projects = sorted(projects, key=lambda prj: project["project_cdate"], reverse=True)
    return projects


def get_active_project(request, user):
    res = (
        request.dbsession.query(Project, Userproject)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Userproject.project_active == 1)
        .filter(Userproject.project_accepted == 1)
        .first()
    )
    mapped_data = map_from_schema(res)
    user_projects = get_user_projects(request, user, user, True)
    if res is not None:
        for project in user_projects:
            if project["project_id"] == mapped_data["project_id"]:
                mapped_data["access_type"] = project["access_type"]
                mapped_data["owner"] = project["owner"]
    else:
        if len(user_projects) > 0:
            last_project = (
                request.dbsession.query(Userproject)
                .filter(Userproject.user_id == user)
                .filter(Userproject.project_accepted == 1)
                .order_by(Userproject.access_date.desc())
                .first()
            )
            if last_project is not None:
                last_project_id = last_project.project_id
                request.dbsession.query(Userproject).filter(
                    Userproject.user_id == user
                ).filter(Userproject.project_id == last_project_id).update(
                    {"project_active": 1}
                )
                try:
                    request.dbsession.flush()
                except Exception as e:
                    request.dbsession.rollback()
                    log.error("Error {} while getting an active project".format(str(e)))

                res = (
                    request.dbsession.query(Project, Userproject)
                    .filter(Project.project_id == Userproject.project_id)
                    .filter(Userproject.user_id == user)
                    .filter(Userproject.project_active == 1)
                    .filter(Userproject.project_accepted == 1)
                    .first()
                )
                mapped_data = map_from_schema(res)
                if res is not None:
                    for project in user_projects:
                        if project["project_id"] == mapped_data["project_id"]:
                            mapped_data["access_type"] = project["access_type"]
                            mapped_data["owner"] = project["owner"]

    return mapped_data


def add_project(request, user, project_data):
    _ = request.translate
    res = (
        request.dbsession.query(Project)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Userproject.access_type == 1)
        .filter(Project.project_code == project_data["project_code"])
        .first()
    )
    if res is None:
        project_data["project_id"] = str(uuid.uuid4())
        project_data["project_cdate"] = datetime.datetime.now()

        mapped_data = map_to_schema(Project, project_data)
        new_project = Project(**mapped_data)
        try:
            request.dbsession.add(new_project)
            request.dbsession.flush()

            request.dbsession.query(Userproject).filter(
                Userproject.user_id == user
            ).update({"project_active": 0})

            new_access = Userproject(
                user_id=user,
                project_id=project_data["project_id"],
                access_type=1,
                access_date=project_data["project_cdate"],
                project_active=1,
                project_accepted=1,
                project_accepted_date=project_data["project_cdate"],
            )
            try:
                request.dbsession.add(new_access)
                request.dbsession.flush()
            except IntegrityError:
                request.dbsession.rollback()
                log.error(
                    "Duplicated access for user {} in project {}".format(
                        user, mapped_data["project_id"]
                    )
                )
                return False, _("Error allocating access")
            except Exception as e:
                request.dbsession.rollback()
                log.error(
                    "Error {} while allocating access for user {} in project {}".format(
                        str(e), user, mapped_data["project_id"]
                    )
                )
                return False, str(e)
            return True, project_data["project_id"]
        except IntegrityError:
            request.dbsession.rollback()
            log.error("Duplicated project {}".format(mapped_data["project_id"]))
            return False, _("The project already exist")
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while inserting project {}".format(
                    str(e), mapped_data["project_id"]
                )
            )
            return False, str(e)
    else:
        return (
            False,
            _("A project with name '{}' already exists in your account").format(
                project_data["project_code"]
            ),
        )


def modify_project(request, project, project_data):
    if project_data.get("project_code", None) is not None:
        project_data.pop("project_code")
    mapped_data = map_to_schema(Project, project_data)
    try:
        request.dbsession.query(Project).filter(Project.project_id == project).update(
            mapped_data
        )
        request.dbsession.flush()
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while updating project {}".format(str(e), project))
        return False, str(e)
    return True, ""


def delete_project(request, user, project):
    _ = request.translate
    try:
        request.dbsession.query(Project).filter(Project.project_id == project).delete()
        request.dbsession.flush()
        res = (
            request.dbsession.query(Userproject)
            .filter(Userproject.user_id == user)
            .filter(Userproject.project_active == 1)
            .first()
        )
        if res is None:
            res = (
                request.dbsession.query(Userproject)
                .filter(Userproject.user_id == user)
                .order_by(Userproject.access_date.desc())
                .first()
            )
            if res is not None:
                new_active_project = res.project_id
                request.dbsession.query(Userproject).filter(
                    Userproject.user_id == user
                ).filter(Userproject.project_id == new_active_project).update(
                    {"project_active": 1}
                )
                request.dbsession.flush()
    except IntegrityError as e:
        request.dbsession.rollback()
        log.error("Error {} while deleting project {}".format(str(e), project))
        return (
            False,
            _(
                "If you have forms with submissions. First you need to delete such forms"
            ),
        )
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while deleting project {}".format(str(e), project))
        return False, str(e)
    return True, ""


def set_project_as_active(request, user, project):
    try:
        request.dbsession.query(Userproject).filter(Userproject.user_id == user).update(
            {"project_active": 0}
        )
        request.dbsession.flush()
        request.dbsession.query(Userproject).filter(Userproject.user_id == user).filter(
            Userproject.project_id == project
        ).update({"project_active": 1})
        request.dbsession.flush()
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while setting project {} as active".format(str(e), project))
        return False, str(e)
    return True, ""


def add_file_to_project(request, project, file_name, overwrite=False):
    _ = request.translate
    res = (
        request.dbsession.query(ProjectFile)
        .filter(ProjectFile.project_id == project)
        .filter(ProjectFile.file_name == file_name)
        .first()
    )
    if res is None:
        new_file_id = str(uuid.uuid4())
        new_file = ProjectFile(
            file_id=new_file_id,
            project_id=project,
            file_name=file_name,
            file_udate=datetime.datetime.now(),
        )
        try:
            request.dbsession.add(new_file)
            request.dbsession.flush()
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while adding file {} in project {}".format(
                    str(e), file_name, project
                )
            )
            return False, str(e)
        return True, new_file_id
    else:
        if not overwrite:
            return False, _("The file {} already exist").format(file_name)
        else:
            return True, res.file_id


def get_project_files(request, project):
    res = (
        request.dbsession.query(ProjectFile)
        .filter(ProjectFile.project_id == project)
        .all()
    )
    return map_from_schema(res)


def remove_file_from_project(request, project, file_name):
    try:
        request.dbsession.query(ProjectFile).filter(
            ProjectFile.project_id == project
        ).filter(ProjectFile.file_name == file_name).delete()
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while removing file {} in project {}".format(
                str(e), file_name, project
            )
        )
        return False, str(e)


def get_project_details(request, project):
    res = request.dbsession.query(Project).filter(Project.project_id == project).first()
    if res is not None:
        return map_from_schema(res)
    else:
        return None
