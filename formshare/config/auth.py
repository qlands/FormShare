from ..models import User as userModel
from encdecdata import decodeData
import urllib, hashlib, arrow


#User class Used to store information about the user
class User(object):
    def __init__(self, userData ,groups=None):

        default = "identicon"
        size = 45
        self.email = userData.user_email
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(self.email.lower()).hexdigest() + "?"
        gravatar_url += urllib.urlencode({'d':default, 's':str(size)})

        self.userData = userData
        self.login = userData.user_name
        self.password = ""
        self.groups = groups or []
        self.fullName = userData.user_fullname
        self.organization = userData.user_organization


        self.gravatarURL = gravatar_url
        if userData.user_about is None:
            self.about = ""
        else:
            self.about = userData.user_about

    def check_password(self, passwd,request):
        return checkLogin(self.login,passwd,request)

    def getGravatarUrl(self,size):
        default = "identicon"
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(self.email.lower()).hexdigest() + "?"
        gravatar_url += urllib.urlencode({'d':default, 's':str(size)})
        return gravatar_url
    def getAPIKey(self,request):
        key = ""
        result = request.dbsession.query(userModel).filter_by(user_name = self.login).first()
        if not result is None:
            key = result.user_apikey
        return key
    def getJoinDate(self,request):
        result = request.dbsession.query(userModel).filter_by(user_name = self.login).first()
        ar = arrow.get(result.user_joindate)
        joindate = ar.format('dddd Do of MMMM, YYYY')
        return joindate
    def updateGravatarURL(self):
        default = "identicon"
        size = 45
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(self.email.lower()).hexdigest() + "?"
        gravatar_url += urllib.urlencode({'d':default, 's':str(size)})
        self.gravatarURL = gravatar_url

def getUserData(user,request):
    res = None
    result = request.dbsession.query(userModel).filter_by(user_name = user).filter_by(user_active = 1).first()
    if not result is None:
        res = User(result)

    return res

def checkLogin(user,password, request):
    result = request.dbsession.query(userModel).filter_by(user_name = user).filter_by(user_active = 1).first()
    if result is None:
        return False
    else:
        cpass = decodeData(result.user_password)
        if cpass == password:
            return True
        else:
            return False

