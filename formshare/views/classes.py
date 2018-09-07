# -*- coding: utf-8 -*-
"""
    formshare.resources.resources
    ~~~~~~~~~~~~~~~~~~

    Provides the basic view classes for FormShare and
    the Digest Authorization for ODK

    :copyright: (c) 2017 by QLands Technology Consultants.
    :license: AGPL, see LICENSE for more details.
"""

from pyramid.security import authenticated_userid
from ..config.auth import getUserData, getCollaboratorData
from pyramid.httpexceptions import HTTPFound
from pyramid.session import check_csrf_token
from pyramid.httpexceptions import HTTPNotFound
from formencode.variabledecode import variable_decode
from pyramid.response import Response
import hashlib
from babel import Locale
import uuid
from ast import literal_eval
from formshare.processes import getProjectIDFromName,user_exists,get_user_details
import logging
log = logging.getLogger(__name__)

class odkView(object):
    def __init__(self, request):
        self.request = request
        self._ = self.request.translate
        self.nonce = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
        self.opaque = request.registry.settings['auth.opaque']
        self.realm = request.registry.settings['auth.realm']
        self.authHeader = {}
        self.user = ""

    def getAuthDict(self):
        authheader = self.request.headers["Authorization"].replace(", ", ",")
        authheader = authheader.replace('"', "")
        autharray = authheader.split(",")
        for e in autharray:
            t = e.split("=")
            if len(t) == 2:
                self.authHeader[t[0]] = t[1]
            else:
                self.authHeader[t[0]] = t[1] + "=" + t[2]

    def authorize(self,correctPassword):
        HA1 = ""
        HA2 = ""
        if self.authHeader["qop"] == 'auth':
            HA1 = hashlib.md5((self.user + ":" + self.realm + ":" + correctPassword).encode())
            HA2 = hashlib.md5((self.request.method + ":" + self.authHeader["uri"]).encode())
        if self.authHeader["qop"] == 'auth-int':
            HA1 = hashlib.md5((self.user + ":" + self.realm + ":" + correctPassword).encode())
            MD5Body = hashlib.md5(self.request.body).hexdigest()
            HA2 = hashlib.md5((self.request.method + ":" + self.authHeader["uri"] + ":" + MD5Body).encode())
        if HA1 == "":
            HA1 = hashlib.md5((self.user + ":" + self.realm + ":" + correctPassword).encode())
            HA2 = hashlib.md5(self.request.method + ":" + self.authHeader["uri"])

        authLine = ":".join(
            [HA1.hexdigest(), self.authHeader["nonce"], self.authHeader["nc"], self.authHeader["cnonce"], self.authHeader["qop"], HA2.hexdigest()])

        resp = hashlib.md5(authLine.encode())
        if resp.hexdigest() == self.authHeader["response"]:
            return True
        else:
            return False

    def askForCredentials(self):
        headers = [('WWW-Authenticate',
                    'Digest realm="' + self.realm + '",qop="auth,auth-int",nonce="' + self.nonce + '",opaque="' + self.opaque + '"')]
        reponse = Response(status=401, headerlist=headers)
        return reponse

    def createXMLResponse(self,XMLData):
        headers = [('Content-Type', 'text/xml; charset=utf-8'), ('X-OpenRosa-Accept-Content-Length', '10000000'),
                   ('Content-Language', self.request.locale_name), ('Vary', 'Accept-Language,Cookie,Accept-Encoding'),
                   ('X-OpenRosa-Version', '1.0'), ('Allow', 'GET, HEAD, OPTIONS')]
        response = Response(headerlist=headers, status=200)

        response.text = str(XMLData, "utf-8")
        return response


    def __call__(self):
        if "Authorization" in self.request.headers:
            self.getAuthDict()
            self.user = self.authHeader["Digest username"]
            return self.processView()
        else:
            headers = [('WWW-Authenticate',
                        'Digest realm="' + self.realm + '",qop="auth,auth-int",nonce="' + self.nonce + '",opaque="' + self.opaque + '"')]
            reponse = Response(status=401, headerlist=headers)
            return reponse

    def processView(self):
        #At this point children of odkView have:
        # self.user which us the user requesting ODK data
        # authorize(self,correctPassword) which checks if the password in the authorization is correct
        # askForCredentials(self) which return a response to ask again for the credentials
        # createXMLResponse(self,XMLData) that can be used to return XML data to ODK with the required headers
        return {}

#This is the most basic public view. Used for 404 and 500. But then used for others more advanced classes
class publicView(object):
    def __init__(self, request):
        self.request = request
        self._ = self.request.translate
        self.resultDict = {}
        self.errors = []
        locale = Locale(request.locale_name)
        if locale.character_order == "left-to-right":
            self.resultDict["rtl"] = False
        else:
            self.resultDict["rtl"] = True

    def __call__(self):
        self.resultDict["errors"] = self.errors
        processDict = self.processView()
        if type(processDict) == dict:
            self.resultDict.update(processDict)
            return self.resultDict
        else:
            return processDict

    def processView(self):
        return {}

    def getPostDict(self):
        dct = variable_decode(self.request.POST)
        return dct


class privateView(object):
    def __init__(self, request):
        self.request = request
        self.user = None
        self._ = self.request.translate
        self.errors = []
        self.userID = ''
        self.classResult = {}
        self.viewResult = {}
        self.returnRawViewResult = False
        self.privateOnly = False
        self.guestAccess = False
        self.viewingSelfAccount = True
        self.showWelcome = False
        self.checkCrossPost = True
        locale = Locale(request.locale_name)
        if locale.character_order == "left-to-right":
            self.classResult["rtl"] = False
        else:
            self.classResult["rtl"] = True
        self.classResult['activeMenu'] = ""

    def __call__(self):
        loginData = authenticated_userid(self.request)
        if loginData is not None:
            loginData = literal_eval(loginData)
        self.guestAccess = False
        self.userID = self.request.matchdict['userid']
        if not user_exists(self.request,self.userID):
            raise HTTPNotFound()
        self.classResult["userDetails"] = get_user_details(self.request,self.userID)
        if self.request.method == 'POST' or self.request.method == 'PUT' or self.request.method == 'DELETE':
            if loginData is not None:
                if loginData["group"] == "mainApp":
                    self.user = getUserData(loginData["login"], self.request)
                    if self.user is not None:
                        safe = check_csrf_token(self.request,raises=False)
                        if not safe:
                            self.request.session.pop_flash()
                            log.error("SECURITY-CSRF error at {} ".format(self.request.url))
                            raise HTTPNotFound()
                        else:
                            if self.checkCrossPost:
                                if self.request.referer != self.request.url:
                                    self.request.session.pop_flash()
                                    log.error("SECURITY-CrossPost error. Posting at {} from {} ".format(self.request.url,self.request.referer))
                                    raise HTTPNotFound()
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()

        if loginData is not None:
            if loginData["group"] == "mainApp":
                self.user = getUserData(loginData["login"],self.request)
                if self.user is None:
                    if self.request.registry.settings['auth.allow_guest_access'] == 'false' or self.privateOnly:
                        raise HTTPFound(location=self.request.route_url('login',_query={'next':self.request.url}))
                    else:
                        self.guestAccess = True
            else:
                if self.request.registry.settings['auth.allow_guest_access'] == 'false' or self.privateOnly:
                    raise HTTPFound(location=self.request.route_url('login', _query={'next': self.request.url}))
                else:
                    self.guestAccess = True
        else:
            if self.request.registry.settings['auth.allow_guest_access'] == 'false' or self.privateOnly:
                raise HTTPFound(location=self.request.route_url('login', _query={'next': self.request.url}))
            else:
                self.guestAccess = True
        if not self.guestAccess:
            self.classResult["activeUser"] = self.user
            if self.user.login != self.userID:
                self.viewingSelfAccount = False
        else:
            self.classResult["activeUser"] = None
            self.viewingSelfAccount = False
        self.classResult["viewingSelfAccount"] = self.viewingSelfAccount
        self.classResult["errors"] = self.errors
        self.classResult["showWelcome"] = self.showWelcome
        self.viewResult = self.processView()
        if not self.returnRawViewResult:
            self.classResult.update(self.viewResult)
            return self.classResult
        else:
            return self.viewResult

    def processView(self):
        return {'activeUser': self.user}

    def setActiveMenu(self,menuName):
        self.classResult['activeMenu'] = menuName

    def getPostDict(self):
        dct = variable_decode(self.request.POST)
        return dct

    def reloadUserDetails(self):
        self.classResult["userDetails"] = get_user_details(self.request, self.userID)

class dashboardView(privateView):
    def __call__(self):
        self.setActiveMenu('dashboard')
        self.showWelcome = True
        # We need to set here relevant information for the dashboard
        privateView.__call__(self)
        if not self.returnRawViewResult:
            self.classResult.update(self.viewResult)
            return self.classResult
        else:
            return self.viewResult

class profileView(privateView):
    def __call__(self):
        loginData = authenticated_userid(self.request)
        if loginData is not None:
            loginData = literal_eval(loginData)
            self.setActiveMenu('profile')
            userID = self.request.matchdict['userid']
            privateView.__call__(self)
            if not self.returnRawViewResult:
                self.classResult.update(self.viewResult)
                return self.classResult
            else:
                return self.viewResult
        else:
            raise HTTPNotFound()

class projectsView(privateView):
    def __call__(self):
        self.setActiveMenu('projects')
        # We need to set here relevant information for the dashboard
        privateView.__call__(self)
        if not self.returnRawViewResult:
            self.classResult.update(self.viewResult)
            return self.classResult
        else:
            return self.viewResult


class collaboratorView(object):
    def __init__(self, request):
        self.request = request
        self.projectID = ""
        self.collaborator = None
        self._ = self.request.translate
        self.errors = []
        self.resultDict = {}
        locale = Locale(request.locale_name)
        if locale.character_order == "left-to-right":
            self.resultDict["rtl"] = False
        else:
            self.resultDict["rtl"] = True

    def __call__(self):
        projectName = self.request.matchdict['pname']
        userID = self.request.matchdict['userid']
        self.projectID = getProjectIDFromName(self.request, userID, projectName)
        if self.projectID is None:
            raise HTTPNotFound()

        loginData = authenticated_userid(self.request)
        if loginData is not None:
            loginData = literal_eval(loginData)
            if loginData["group"] == "collaborators":
                self.collaborator = getCollaboratorData(self.projectID,loginData["login"],self.request)
                if self.collaborator is None:
                    return HTTPFound(location=self.request.route_url('login',_query={'next':self.request.url}))
            else:
                return HTTPFound(location=self.request.route_url('login', _query={'next': self.request.url}))
        else:
            return HTTPFound(location=self.request.route_url('login', _query={'next': self.request.url}))

        if self.request.method == 'POST':
            safe = check_csrf_token(self.request,raises=False)
            if not safe:
                raise HTTPNotFound()

        self.resultDict["activeCollaborator"] = self.collaborator
        self.resultDict["errors"] = self.errors
        processDict = self.processView()
        if type(processDict) == dict:
            self.resultDict.update(processDict)
            return self.resultDict
        else:
            return processDict

    def processView(self):
        return {'activeCollaborator': self.collaborator}

    def getPostDict(self):
        dct = variable_decode(self.request.POST)
        return dct