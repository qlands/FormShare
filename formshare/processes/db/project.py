from formshare.models import Project, Userproject, map_to_schema, map_from_schema,\
    Submission, Odkform, Collaborator
import logging
import datetime
import sys
import uuid
from sqlalchemy.exc import IntegrityError

__all__ = [
    'get_project_id_from_name', 'get_user_projects', 'get_active_project', 'add_project'
]

log = logging.getLogger(__name__)


def get_project_id_from_name(request, user, project_name):
    res = request.dbsession.query(Project).filter(Project.project_id == Userproject.project_id).filter(
        Userproject.user_id == user).filter(Project.project_name == project_name).first()
    if res is not None:
        return res.project_id
    return None


def get_forms_number(request, project):
    total = request.dbsession.query(Odkform).filter(Odkform.project_id == project).count()
    return total


def get_project_submissions(request, project):
    total = request.dbsession.query(Submission).filter(Submission.project_id == project).count()
    return total


def get_last_submission(request, project):
    res = request.dbsession.query(Submission.submission_dtime, Odkform.form_name, Collaborator.coll_name,
                                  Project.project_id, Project.project_name).filter(
        Submission.project_id == Odkform.project_id, Submission.form_id == Odkform.form_id).filter(
        Submission.enum_project == Collaborator.project_id, Submission.coll_id == Collaborator.coll_id).filter(
        Collaborator.project_id == Project.project_id).filter(Submission.project_id == project).order_by(
        Submission.submission_dtime.desc()).first()
    return map_from_schema(res)


def get_project_owner(request, project):
    res = request.dbsession.query(Userproject.user_id).filter(Userproject.project_id == project).filter(
        Userproject.access_type == 1).first()
    if res is not None:
        return res.user_id
    else:
        return None


def get_user_projects(request, user, logged_user, private=False):
    if private:
        if user == logged_user:
            # The logged account is the user account = Seeing my projects
            res = request.dbsession.query(Project, Userproject).filter(
                Project.project_id == Userproject.project_id).filter(Userproject.user_id == user).all()
            projects = map_from_schema(res)
        else:
            projects = []
            # The logged account is different as the user account =  Seeing someone else projects

            # Get all the projects of that user
            all_user_projects = request.dbsession.query(Project).filter(
                Project.project_id == Userproject.project_id).filter(Userproject.user_id == user).all()
            for project in all_user_projects:
                # Check each project to see if the logged user collaborate with it
                res = request.dbsession.query(Project, Userproject).filter(
                    Project.project_id == Userproject.project_id).filter(
                    Userproject.user_id == logged_user).filter(Userproject.project_id == project.project_id).first()
                collaborative_project = map_from_schema(res)
                if collaborative_project:
                    collaborative_project['collaborate'] = True
                    collaborative_project['user_id'] = user
                    projects.append(collaborative_project)
                else:
                    if project["project_public"] == 1:
                        collaborative_project['collaborate'] = False
                        collaborative_project['user_id'] = user
                        projects.append(collaborative_project)
    else:
        res = request.dbsession.query(Project, Userproject).filter(Project.project_id == Userproject.project_id).filter(
            Userproject.user_id == user).filter(Project.project_public == 1).all()
        projects = map_from_schema(res)
    for project in projects:
        project['last_submission'] = get_last_submission(request, project['project_id'])
        project['total_submissions'] = get_project_submissions(request, project['project_id'])
        project['total_forms'] = get_forms_number(request, project['project_id'])
        if private:
            if project['access_type'] == 1:
                project['owner'] = user
            else:
                project['owner'] = get_project_owner(request, project['project_id'])
        else:
            project['owner'] = get_project_owner(request, project['project_id'])
            project['access_type'] = 4
    projects = sorted(projects, key=lambda prj: project["project_cdate"], reverse=True)
    return projects


def get_active_project(request, user):
    res = request.dbsession.query(Project, Userproject).filter(Project.project_id == Userproject.project_id).filter(
        Userproject.user_id == user).filter(Userproject.project_active == 1).first()
    mapped_data = map_from_schema(res)
    return mapped_data


def add_project(request, user, project_data):
    res = request.dbsession.query(Project).filter(Project.project_id == Userproject.project_id).filter(
        Userproject.user_id == user).filter(Userproject.access_type == 1).filter(
        Project.project_code == project_data["project_code"]).first()
    if res is None:
        project_data['project_id'] = str(uuid.uuid4())
        project_data['project_cdate'] = datetime.datetime.now()

        mapped_data = map_to_schema(Project, project_data)
        new_project = Project(**mapped_data)
        try:
            request.dbsession.add(new_project)
            request.dbsession.flush()
            new_access = Userproject(user_id=user, project_id=project_data['project_id'], access_type=1,
                                     access_date=project_data['project_cdate'], project_active=1)
            try:
                request.dbsession.add(new_access)
                request.dbsession.flush()
            except IntegrityError:
                log.error("Duplicated access for user {} in project {}".format(user, mapped_data["project_id"]))
                return False, request.translate("Error allocating access")
            except RuntimeError:
                log.error("Error {} when allocating access for user {} in project {}".format(sys.exc_info()[0], user,
                                                                                             mapped_data["project_id"]))
                return False, sys.exc_info()[0]
            return True, ""
        except IntegrityError:
            log.error("Duplicated project {}".format(mapped_data["project_id"]))
            return False, request.translate("The project already exist")
        except RuntimeError:
            log.error("Error {} when inserting project {}".format(sys.exc_info()[0], mapped_data["project_id"]))
            return False, sys.exc_info()[0]
    else:
        return False, request.translate("A project with name '{}' already exists in your account").format(
            project_data["project_code"])
