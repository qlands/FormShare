from formshare.models import User as userModel
from formshare.models import Collaborator as collaboratorModel
from .encdecdata import decodeData
import urllib, hashlib
from ..models import mapFromSchema



#User class Used to store information about the user
class User(object):
    def __init__(self, userData):
        default = "identicon"
        size = 45
        self.email = userData["user_id"]
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(self.email.lower().encode('utf8')).hexdigest() + "?"
        gravatar_url += urllib.parse.urlencode({'d':default, 's':str(size)})
        self.userData = userData
        self.login = userData["user_id"]
        self.name = userData["user_name"]
        self.gravatarURL = gravatar_url
        if userData["user_about"] is None:
            self.about = ""
        else:
            self.about = userData["user_about"]

    def check_password(self, passwd,request):
        return checkLogin(self.login,passwd,request)

    def getGravatarUrl(self,size):
        default = "identicon"
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(self.email.lower()).hexdigest() + "?"
        gravatar_url += urllib.parse.urlencode({'d':default, 's':str(size)})
        return gravatar_url

    def updateGravatarURL(self):
        default = "identicon"
        size = 45
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(self.email.lower()).hexdigest() + "?"
        gravatar_url += urllib.parse.urlencode({'d':default, 's':str(size)})
        self.gravatarURL = gravatar_url

class Collaborator(object):
    def __init__(self, collData , project):
        default = "identicon"
        size = 45
        self.email = collData["coll_email"]
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(self.email.lower().encode('utf8')).hexdigest() + "?"
        gravatar_url += urllib.parse.urlencode({'d':default, 's':str(size)})
        self.userData = collData
        self.login = collData["coll_id"]
        self.projectID = project
        self.fullName = collData["coll_name"]
        self.gravatarURL = gravatar_url
        self.about = ""

    def check_password(self, passwd,request):
        return checkCollaboratorLogin(self.projectID,self.login,passwd,request)

    def getGravatarUrl(self,size):
        default = "identicon"
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(self.email.lower()).hexdigest() + "?"
        gravatar_url += urllib.parse.urlencode({'d':default, 's':str(size)})
        return gravatar_url

    def updateGravatarURL(self):
        default = "identicon"
        size = 45
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(self.email.lower()).hexdigest() + "?"
        gravatar_url += urllib.parse.urlencode({'d':default, 's':str(size)})
        self.gravatarURL = gravatar_url

def getUserData(email,request):
    result = mapFromSchema(request.dbsession.query(userModel).filter(userModel.user_email == email).filter(userModel.user_active == 1).first())
    if result:
        result["user_password"] = ""  # Remove the password form the result
        return User(result)
    return None

def getCollaboratorData(orgID,projectID, collaboratorID,request):
    result = mapFromSchema(request.dbsession.query(collaboratorModel).filter(collaboratorModel.org_id == orgID).filter(collaboratorModel.project_id == projectID).filter(collaboratorModel.coll_id == collaboratorID).first())
    if result:
        result["coll_password"] = ""  # Remove the password form the result
        return Collaborator(result,projectID)
    return None


def checkLogin(email,password, request):
    result = request.dbsession.query(userModel).filter(userModel.user_email == email).filter(userModel.user_active == 1).first()
    if result is None:
        return False
    else:
        cpass = decodeData(request,result.user_password.encode())
        if cpass == bytearray(password.encode()):
            return True
        else:
            return False

def checkCollaboratorLogin(projectID,collID,password, request):
    result = request.dbsession.query(collaboratorModel).filter(collaboratorModel.project_id == projectID).filter(collaboratorModel.coll_id == collID).filter(collaboratorModel.coll_active == 1).first()
    if result is None:
        return False
    else:
        cpass = decodeData(request,result.enum_password.encode())
        if cpass == bytearray(password.encode()):
            return True
        else:
            return False

