from formshare.models import Project,Userproject,mapToSchema,mapFromSchema,\
    Submission,Odkform,Collaborator
import logging

__all__ = [
    'getProjectIDFromName','get_user_projects'
]

log = logging.getLogger(__name__)

def getProjectIDFromName(request,userID,projectName):
    res = request.dbsession.query(Project).filter(Project.user_id == userID).filter(Project.project_name == projectName).first()
    if res is not None:
        return res.project_id
    else:
        return None

def get_project_submissions(request,projectID):
    total = request.dbsession.query(Submission).filter(Submission.project_id == projectID).count()
    return total

def get_last_submission(request,projectID):
    res = request.dbsession.query(Submission.submission_dtime, Odkform.form_name, Collaborator.coll_name,
                                  Project.project_id, Project.project_name).filter(
        Submission.project_id == Odkform.project_id, Submission.form_id == Odkform.form_id).filter(
        Submission.enum_project == Collaborator.project_id, Submission.coll_id == Collaborator.coll_id).filter(
        Collaborator.project_id == Project.project_id).filter(Submission.project_id == projectID).order_by(
        Submission.submission_dtime).last()


def get_user_projects(request,userID,private=False):
    if private:
        res = request.dbsession.query(Project, Userproject).filter(Project.project_id == Userproject.project_id).filter(
            Userproject.user_id == userID).all()
        projects = mapFromSchema(res)
    else:
        res = request.dbsession.query(Project, Userproject).filter(Project.project_id == Userproject.project_id).filter(
            Userproject.user_id == userID).filter(Project.project_public == 1).all()
        projects = mapFromSchema(res)
    # for project in projects:

    return projects