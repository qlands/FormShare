# -*- coding: utf-8 -*-
"""
    formshare.resources.resources
    ~~~~~~~~~~~~~~~~~~

    Provides the basic view classes for FormShare and
    the Digest Authorization for ODK

    :copyright: (c) 2017 by QLands Technology Consultants.
    :license: AGPL, see LICENSE for more details.
"""

from ..config.auth import get_user_data, get_assistant_data
from pyramid.httpexceptions import HTTPFound
from pyramid.session import check_csrf_token
from pyramid.httpexceptions import HTTPNotFound
from formencode.variabledecode import variable_decode
from pyramid.response import Response
import hashlib
from babel import Locale
import uuid
from ast import literal_eval
from formshare.processes.db import (
    get_project_id_from_name,
    user_exists,
    get_user_details,
    get_active_project,
    get_user_projects,
    get_project_from_assistant,
    get_user_by_api_key,
)
import logging

log = logging.getLogger("formshare")


class ODKView(object):
    def __init__(self, request):
        self.request = request
        self._ = self.request.translate
        self.nonce = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
        self.opaque = request.registry.settings["auth.opaque"]
        self.realm = request.registry.settings["auth.realm"]
        self.authHeader = {}
        self.user = ""

    def get_auth_dict(self):
        authheader = self.request.headers["Authorization"].replace(", ", ",")
        authheader = authheader.replace('"', "")
        autharray = authheader.split(",")
        for e in autharray:
            t = e.split("=")
            if len(t) == 2:
                self.authHeader[t[0]] = t[1]
            else:
                self.authHeader[t[0]] = t[1] + "=" + t[2]

    def authorize(self, correct_password):
        ha1 = ""
        ha2 = ""
        if self.authHeader["qop"] == "auth":
            ha1 = hashlib.md5(
                (
                    self.user + ":" + self.realm + ":" + correct_password.decode()
                ).encode()
            )
            ha2 = hashlib.md5(
                (self.request.method + ":" + self.authHeader["uri"]).encode()
            )
        if self.authHeader["qop"] == "auth-int":
            ha1 = hashlib.md5(
                (
                    self.user + ":" + self.realm + ":" + correct_password.decode()
                ).encode()
            )
            md5_body = hashlib.md5(self.request.body).hexdigest()
            ha2 = hashlib.md5(
                (
                    self.request.method + ":" + self.authHeader["uri"] + ":" + md5_body
                ).encode()
            )
        if ha1 == "":
            ha1 = hashlib.md5(
                (
                    self.user + ":" + self.realm + ":" + correct_password.decode()
                ).encode()
            )
            ha2 = hashlib.md5(self.request.method + ":" + self.authHeader["uri"])

        auth_line = ":".join(
            [
                ha1.hexdigest(),
                self.authHeader["nonce"],
                self.authHeader["nc"],
                self.authHeader["cnonce"],
                self.authHeader["qop"],
                ha2.hexdigest(),
            ]
        )

        resp = hashlib.md5(auth_line.encode())
        if resp.hexdigest() == self.authHeader["response"]:
            return True
        else:
            return False

    def ask_for_credentials(self):
        headers = [
            (
                "WWW-Authenticate",
                'Digest realm="'
                + self.realm
                + '",qop="auth,auth-int",nonce="'
                + self.nonce
                + '",opaque="'
                + self.opaque
                + '"',
            )
        ]
        reponse = Response(status=401, headerlist=headers)
        return reponse

    def create_xmll_response(self, xml_data):
        headers = [
            ("Content-Type", "text/xml; charset=utf-8"),
            ("X-OpenRosa-Accept-Content-Length", "10000000"),
            ("Content-Language", self.request.locale_name),
            ("Vary", "Accept-Language,Cookie,Accept-Encoding"),
            ("X-OpenRosa-Version", "1.0"),
            ("Allow", "GET, HEAD, OPTIONS"),
        ]
        response = Response(headerlist=headers, status=200)

        response.text = str(xml_data, "utf-8")
        return response

    def __call__(self):
        if "Authorization" in self.request.headers:
            self.get_auth_dict()
            self.user = self.authHeader["Digest username"]
            return self.process_view()
        else:
            headers = [
                (
                    "WWW-Authenticate",
                    'Digest realm="'
                    + self.realm
                    + '",qop="auth,auth-int",nonce="'
                    + self.nonce
                    + '",opaque="'
                    + self.opaque
                    + '"',
                )
            ]
            reponse = Response(status=401, headerlist=headers)
            return reponse

    def process_view(self):
        # At this point children of odkView have:
        # self.user which us the user requesting ODK data
        # authorize(self,correctPassword) which checks if the password in the authorization is correct
        # askForCredentials(self) which return a response to ask again for the credentials
        # createXMLResponse(self,XMLData) that can be used to return XML data to ODK with the required headers
        raise NotImplementedError("process_view must be implemented in subclasses")


class PublicView(object):
    """
    This is the most basic public view. Used for 404 and 500. But then used for others more advanced classes
    """

    def __init__(self, request):
        self.request = request
        self._ = self.request.translate
        self.resultDict = {"errors": []}
        self.errors = []
        self.returnRawViewResult = False
        locale = Locale(request.locale_name)
        if locale.character_order == "left-to-right":
            self.resultDict["rtl"] = False
        else:
            self.resultDict["rtl"] = True

    def __call__(self):
        self.resultDict["errors"] = self.errors
        process_dict = self.process_view()
        if not self.returnRawViewResult:
            self.resultDict.update(process_dict)
            return self.resultDict
        else:
            return process_dict

    def process_view(self):
        raise NotImplementedError("process_view must be implemented in subclasses")

    def get_post_dict(self):
        dct = variable_decode(self.request.POST)
        return dct


class PrivateView(object):
    def __init__(self, request):
        self.request = request
        self.user = None
        self._ = self.request.translate
        self.errors = []
        self.userID = ""
        self.classResult = {"activeUser": None, "userProjects": [], "activeProject": {}}
        self.viewResult = {}
        self.returnRawViewResult = False
        self.privateOnly = True
        self.guestAccess = False
        self.viewingSelfAccount = True
        self.showWelcome = False
        self.checkCrossPost = True
        self.queryProjects = True
        self.user_projects = []
        self.activeProject = {}
        locale = Locale(request.locale_name)
        if locale.character_order == "left-to-right":
            self.classResult["rtl"] = False
        else:
            self.classResult["rtl"] = True
        self.classResult["activeMenu"] = ""

    def get_policy(self, policy_name):
        policies = self.request.policies()
        for policy in policies:
            if policy["name"] == policy_name:
                return policy["policy"]
        return None

    def __call__(self):
        error = self.request.session.pop_flash(queue="error")
        if len(error) > 0:
            self.errors.append(error[0].replace("|error", ""))

        # login_data = authenticated_userid(self.request)
        policy = self.get_policy("main")
        login_data = policy.authenticated_userid(self.request)

        if login_data is not None:
            login_data = literal_eval(login_data)
        self.guestAccess = False
        self.userID = self.request.matchdict["userid"]
        if not user_exists(self.request, self.userID):
            raise HTTPNotFound()
        self.classResult["userDetails"] = get_user_details(self.request, self.userID)
        if (
            self.request.method == "POST"
            or self.request.method == "PUT"
            or self.request.method == "DELETE"
        ):
            if login_data is not None:
                if login_data["group"] == "mainApp":
                    self.user = get_user_data(login_data["login"], self.request)
                    if self.user is not None:
                        safe = check_csrf_token(self.request, raises=False)
                        if not safe:
                            self.request.session.pop_flash()
                            log.error(
                                "SECURITY-CSRF error at {} ".format(self.request.url)
                            )
                            raise HTTPFound(self.request.route_url("refresh"))
                        else:
                            if self.checkCrossPost:
                                if self.request.referer != self.request.url:
                                    self.request.session.pop_flash()
                                    log.error(
                                        "SECURITY-CrossPost error. Posting at {} from {} ".format(
                                            self.request.url, self.request.referer
                                        )
                                    )
                                    raise HTTPNotFound()
                    else:
                        raise HTTPFound(location=self.request.route_url("login"))
                else:
                    raise HTTPFound(location=self.request.route_url("login"))
            else:
                raise HTTPFound(location=self.request.route_url("login"))

        if login_data is not None:
            if login_data["group"] == "mainApp":
                self.user = get_user_data(login_data["login"], self.request)
                if self.user is None:
                    if (
                        self.request.registry.settings["auth.allow_guest_access"]
                        == "false"
                        or self.privateOnly
                    ):
                        raise HTTPFound(
                            location=self.request.route_url(
                                "login", _query={"next": self.request.url}
                            )
                        )
                    else:
                        self.guestAccess = True
            else:
                if (
                    self.request.registry.settings["auth.allow_guest_access"] == "false"
                    or self.privateOnly
                ):
                    raise HTTPFound(
                        location=self.request.route_url(
                            "login", _query={"next": self.request.url}
                        )
                    )
                else:
                    self.guestAccess = True
        else:
            if (
                self.request.registry.settings["auth.allow_guest_access"] == "false"
                or self.privateOnly
            ):
                raise HTTPFound(
                    location=self.request.route_url(
                        "login", _query={"next": self.request.url}
                    )
                )
            else:
                self.guestAccess = True
        if not self.guestAccess:
            self.classResult["activeUser"] = self.user
            if self.user.login != self.userID:
                self.viewingSelfAccount = False
        else:
            self.classResult["activeUser"] = None
            self.viewingSelfAccount = False

        if self.queryProjects:
            if self.user is not None:
                if self.userID == self.user.login:
                    self.user_projects = get_user_projects(
                        self.request, self.userID, self.userID, True
                    )
                else:
                    self.user_projects = get_user_projects(
                        self.request, self.userID, self.user.login, True
                    )
            else:
                self.user_projects = get_user_projects(self.request, self.userID, None)
            self.classResult["userProjects"] = self.user_projects
        else:
            self.classResult["userProjects"] = []

        if self.user is not None:
            self.activeProject = get_active_project(self.request, self.user.login)
            self.classResult["activeProject"] = self.activeProject
        else:
            self.classResult["activeProject"] = {}

        self.classResult["viewingSelfAccount"] = self.viewingSelfAccount
        self.classResult["errors"] = self.errors
        self.classResult["showWelcome"] = self.showWelcome
        self.viewResult = self.process_view()
        if not self.returnRawViewResult:
            self.classResult.update(self.viewResult)
            return self.classResult
        else:
            return self.viewResult

    def process_view(self):
        return {"activeUser": self.user}

    def set_active_menu(self, menu_name):
        self.classResult["activeMenu"] = menu_name

    def get_post_dict(self):
        dct = variable_decode(self.request.POST)
        return dct

    def reload_user_details(self):
        self.classResult["userDetails"] = get_user_details(self.request, self.userID)

    def add_error(self, message):
        self.request.session.flash("{}|error".format(message), queue="error")


class DashboardView(PrivateView):
    def __call__(self):
        self.set_active_menu("dashboard")
        self.showWelcome = True
        # We need to set here relevant information for the dashboard
        PrivateView.__call__(self)
        if not self.returnRawViewResult:
            self.classResult.update(self.viewResult)
            return self.classResult
        else:
            return self.viewResult


class ProfileView(PrivateView):
    def __call__(self):
        policy = self.get_policy("main")
        login_data = policy.authenticated_userid(self.request)
        # login_data = authenticated_userid(self.request)
        if login_data is not None:
            self.set_active_menu("profile")
            PrivateView.__call__(self)
            if not self.returnRawViewResult:
                self.classResult.update(self.viewResult)
                return self.classResult
            else:
                return self.viewResult
        else:
            raise HTTPNotFound()


class ProjectsView(PrivateView):
    def __call__(self):
        self.set_active_menu("projects")
        # We need to set here relevant information for the dashboard
        PrivateView.__call__(self)
        if not self.returnRawViewResult:
            self.classResult.update(self.viewResult)
            return self.classResult
        else:
            return self.viewResult


class AssistantView(object):
    def __init__(self, request):
        self.request = request
        self.projectID = ""
        self.userID = ""
        self.projectCode = ""
        self.assistant = None
        self._ = self.request.translate
        self.errors = []
        self.resultDict = {"errors": []}
        locale = Locale(request.locale_name)
        if locale.character_order == "left-to-right":
            self.resultDict["rtl"] = False
        else:
            self.resultDict["rtl"] = True
        self.returnRawViewResult = False
        self.project_assistant = None
        self.checkCrossPost = True

    def get_policy(self, policy_name):
        policies = self.request.policies()
        for policy in policies:
            if policy["name"] == policy_name:
                return policy["policy"]
        return None

    def __call__(self):
        error = self.request.session.pop_flash(queue="error")
        if len(error) > 0:
            self.errors.append(error[0])

        self.userID = self.request.matchdict["userid"]
        self.projectCode = self.request.matchdict["projcode"]
        self.projectID = get_project_id_from_name(
            self.request, self.userID, self.projectCode
        )
        if self.projectID is None:
            raise HTTPNotFound()

        policy = self.get_policy("assistant")
        login_data = policy.authenticated_userid(self.request)
        if login_data is not None:
            login_data = literal_eval(login_data)
            if login_data["group"] == "collaborators":
                self.project_assistant = get_project_from_assistant(
                    self.request, self.userID, self.projectID, login_data["login"]
                )
                self.assistant = get_assistant_data(
                    self.project_assistant, login_data["login"], self.request
                )
                if self.assistant is None:
                    return HTTPFound(
                        location=self.request.route_url(
                            "assistant_login",
                            userid=self.userID,
                            projcode=self.projectCode,
                            _query={"next": self.request.url},
                        )
                    )
            else:
                return HTTPFound(
                    location=self.request.route_url(
                        "assistant_login",
                        userid=self.userID,
                        projcode=self.projectCode,
                        _query={"next": self.request.url},
                    )
                )
        else:
            return HTTPFound(
                location=self.request.route_url(
                    "assistant_login",
                    userid=self.userID,
                    projcode=self.projectCode,
                    _query={"next": self.request.url},
                )
            )

        if self.request.method == "POST":
            safe = check_csrf_token(self.request, raises=False)
            if not safe:
                self.request.session.pop_flash()
                log.error("SECURITY-CSRF error at {} ".format(self.request.url))
                raise HTTPFound(self.request.route_url("refresh"))
            else:
                if self.checkCrossPost:
                    if self.request.referer != self.request.url:
                        self.request.session.pop_flash()
                        log.error(
                            "SECURITY-CrossPost error. Posting at {} from {} ".format(
                                self.request.url, self.request.referer
                            )
                        )
                        raise HTTPNotFound()

        self.assistantID = self.assistant.login
        self.resultDict["activeAssistant"] = self.assistant
        self.resultDict["userid"] = self.userID
        self.resultDict["projcode"] = self.projectCode
        self.resultDict["posterrors"] = self.errors
        process_dict = self.process_view()
        if not self.returnRawViewResult:
            self.resultDict.update(process_dict)
            return self.resultDict
        else:
            return process_dict

    def process_view(self):
        return {"activeAssistant": self.assistant}

    def get_post_dict(self):
        dct = variable_decode(self.request.POST)
        return dct

    def add_error(self, message):
        self.request.session.flash(message, queue="error")


class APIView(object):
    def __init__(self, request):
        self.request = request
        self.user = None
        self.body = None
        self.api_key = ""
        self._ = self.request.translate

    def __call__(self):
        self.api_key = self.request.params.get("apikey", None)
        if self.api_key is not None:
            self.user = get_user_by_api_key(self.request, self.api_key)
            if self.user is None:
                response = Response(
                    status=401,
                    body={
                        "error": self._("This API key does not exist or is inactive.")
                    },
                )
                return response

            if self.request.method == "POST":
                self.body = self.request.params.get("Body", None)
                if self.body is None:
                    response = Response(
                        status=401, body={"error": self._("Body non-existent")}
                    )
                    return response
        else:
            response = Response(
                status=401, body={"error": self._("You need to specify an API key")}
            )
            return response

        return self.process_view()

    def process_view(self):
        return {"key": self.api_key}
