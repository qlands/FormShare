from formshare.models import Project
import logging

__all__ = [
    'getProjectIDFromName'
]

log = logging.getLogger(__name__)

def getProjectIDFromName(request,userID,projectName):
    res = request.dbsession.query(Project).filter(Project.user_id == userID).filter(Project.project_name == projectName).first()
    if res is not None:
        return res.project_id
    else:
        return None
