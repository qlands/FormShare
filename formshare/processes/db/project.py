from formshare.models import Project,Userproject,mapToSchema,mapFromSchema,\
    Submission,Odkform,Collaborator
import logging,datetime,sys,uuid
from sqlalchemy.exc import IntegrityError

__all__ = [
    'getProjectIDFromName','get_user_projects','get_active_project','add_project'
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
        Submission.submission_dtime.desc()).first()
    return mapFromSchema(res)

def get_user_projects(request,userID,loggedUserID,private=False):
    if private:
        if userID == loggedUserID:
            #The logged account is the user account = Seeing my projects

            # res = request.dbsession.query(Project, Userproject).filter(
            #     Project.project_id == Userproject.project_id).filter(
            #     Userproject.user_id == userID).column_descriptions
            #
            # print("*********************************99")

            res = request.dbsession.query(Project, Userproject).filter(Project.project_id == Userproject.project_id).filter(
                Userproject.user_id == userID).all()
            projects = mapFromSchema(res)
        else:
            projects = []
            #The logged account is different as the user account =  Seeing someone elses projects

            #Get all the private project from the user
            allUserProjects = request.dbsession.query(Project,Userproject).filter(
                Project.project_id == Userproject.project_id).filter(Userproject.user_id == userID).all()
            for project in allUserProjects:
                #Check each project to see if the logged user collaborate with it
                res = request.dbsession.query(Project, Userproject).filter(
                    Project.project_id == Userproject.project_id).filter(
                    Userproject.user_id == loggedUserID).filter(Userproject.project_id == project.project_id).first()
                collaborativeProject = mapFromSchema(res)
                if collaborativeProject:
                    collaborativeProject['collaborate'] = True
                    projects.append(collaborativeProject)
                else:
                    if project["project_public"] == 1:
                        collaborativeProject['collaborate'] = False
                        projects.append(collaborativeProject)
    else:
        res = request.dbsession.query(Project, Userproject).filter(Project.project_id == Userproject.project_id).filter(
            Userproject.user_id == userID).filter(Project.project_public == 1).all()
        projects = mapFromSchema(res)
    for project in projects:
        project['last_submission'] = get_last_submission(request,project['project_id'])
        project['total_submissions'] = get_project_submissions(request,project['project_id'])

    return projects

def get_active_project(request,userID):
    res = request.dbsession.query(Project, Userproject).filter(Project.project_id == Userproject.project_id).filter(
        Userproject.user_id == userID).filter(Userproject.project_active == 1).first()
    mappedRes = mapFromSchema(res)
    return mappedRes

def add_project(request,userID,projectData):
    res = request.dbsession.query(Project).filter(Project.project_id == Userproject.project_id).filter(
        Userproject.user_id == userID).filter(Userproject.access_type == 1).filter(
        Project.project_code == projectData["project_code"]).first()
    if res is None:
        projectData['project_id'] = str(uuid.uuid4())
        projectData['project_cdate'] = datetime.datetime.now()

        mappedData = mapToSchema(Project, projectData)
        newProject = Project(**mappedData)
        try:
            request.dbsession.add(newProject)
            request.dbsession.flush()
            newAccess = Userproject(user_id=userID,project_id=projectData['project_id'],access_type=1,access_date=projectData['project_cdate'],project_active=1)
            try:
                request.dbsession.add(newAccess)
                request.dbsession.flush()
            except IntegrityError as e:
                log.error("Duplicated access for user {} in project {}".format(userID,mappedData["project_id"]))
                return False, request.translate("Error allocating access")
            except:
                log.error("Error {} when allocating access for user {} in project {}".format(sys.exc_info()[0], userID, mappedData["project_id"]))
                return False, sys.exc_info()[0]
            return True, ""
        except IntegrityError as e:
            log.error("Duplicated project {}".format(mappedData["project_id"]))
            return False, request.translate("The project already exist")
        except:
            log.error("Error {} when inserting project {}".format(sys.exc_info()[0], mappedData["project_id"]))
            return False, sys.exc_info()[0]
    else:
        return False, request.translate("A project with name '{}' already exists in your account").format(projectData["project_code"])
