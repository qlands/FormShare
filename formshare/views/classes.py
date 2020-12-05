# -*- coding: utf-8 -*-
"""
    formshare.resources.resources
    ~~~~~~~~~~~~~~~~~~

    Provides the basic view classes for FormShare and
    the Digest Authorization for ODK

    :copyright: (c) 2017 by QLands Technology Consultants.
    :license: AGPL, see LICENSE for more details.
"""

import hashlib
import json
import logging
import uuid
from ast import literal_eval

from babel import Locale
from formencode.variabledecode import variable_decode
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound, exception_response
from pyramid.response import Response
from pyramid.session import check_csrf_token

from formshare.processes.db import (
    get_project_id_from_name,
    user_exists,
    get_user_details,
    get_active_project,
    get_user_projects,
    get_project_from_assistant,
    get_user_by_api_key,
    get_assistant_by_api_key,
)
from formshare import plugins as p
from formshare.config.auth import get_user_data, get_assistant_data

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
        if self.request.encget("FS_for_testing", default="false") == "false":
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
                        self.request.method
                        + ":"
                        + self.authHeader["uri"]
                        + ":"
                        + md5_body
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
        else:
            return True

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
        testing_calls = self.request.encget("FS_for_testing", default="false")
        if "Authorization" in self.request.headers or testing_calls == "true":
            if testing_calls == "false":
                if self.request.headers["Authorization"].find("Basic ") == -1:
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
                    response = Response(status=401, headerlist=headers)
                    return response
            else:
                self.user = self.request.encget("FS_user_for_testing", default="None")
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

        i_public_view_implementations = p.PluginImplementations(p.IPublicView)
        for plugin in i_public_view_implementations:
            plugin.before_processing(self.request)

        process_dict = self.process_view()

        for plugin in i_public_view_implementations:
            process_dict = plugin.after_processing(self.request, process_dict)

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

    def append_to_errors(self, error):
        self.request.response.headers["FS_error"] = "true"
        self.errors.append(error)


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

    def append_to_errors(self, error):
        self.request.response.headers["FS_error"] = "true"
        self.errors.append(error)

    def get_policy(self, policy_name):
        policies = self.request.policies()
        for policy in policies:
            if policy["name"] == policy_name:
                return policy["policy"]
        return None

    def check_post_put_delete(self):
        if (
            self.request.method == "POST"
            or self.request.method == "PUT"
            or self.request.method == "DELETE"
        ):
            if (
                self.request.registry.settings.get("perform_post_checks", "true")
                == "true"
            ):
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

    def check_authorization(self):
        policy = self.get_policy("main")
        login_data = policy.authenticated_userid(self.request)
        if login_data is not None:
            login_data = literal_eval(login_data)
            if login_data["group"] == "mainApp":
                self.user = get_user_data(login_data["login"], self.request)
                if self.user is None:
                    raise HTTPFound(
                        location=self.request.route_url(
                            "login", _query={"next": self.request.url}
                        )
                    )
                self.check_post_put_delete()
            else:
                raise HTTPFound(
                    location=self.request.route_url(
                        "login", _query={"next": self.request.url}
                    )
                )
        else:
            raise HTTPFound(
                location=self.request.route_url(
                    "login", _query={"next": self.request.url}
                )
            )

    def __call__(self):
        error = self.request.session.pop_flash(queue="error")
        if len(error) > 0:
            self.append_to_errors(error[0].replace("|error", ""))

        self.userID = self.request.matchdict["userid"]
        if not user_exists(self.request, self.userID):
            raise HTTPNotFound()
        self.classResult["userDetails"] = get_user_details(self.request, self.userID)
        self.guestAccess = False

        i_user_authorization = p.PluginImplementations(p.IUserAuthorization)
        continue_authorization = True
        for plugin in i_user_authorization:
            continue_authorization = plugin.before_check_authorization(self.request)
            break  # Only only plugin will be called for before_check_authorization
        if continue_authorization:
            self.check_authorization()
        else:
            authorized = False
            user_authorized = ""
            for plugin in i_user_authorization:
                authorized, user_authorized = plugin.custom_authorization(self.request)
                break  # Only only plugin will be called for custom_authorization
            if authorized:
                self.user = get_user_data(user_authorized, self.request)
                if self.user is None:
                    raise HTTPFound(
                        location=self.request.route_url(
                            "login", _query={"next": self.request.url}
                        )
                    )
                self.check_post_put_delete()
            else:
                raise HTTPFound(
                    location=self.request.route_url(
                        "login", _query={"next": self.request.url}
                    )
                )

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

        i_private_view_implementations = p.PluginImplementations(p.IPrivateView)
        for plugin in i_private_view_implementations:
            plugin.before_processing(
                self.request,
                {
                    "returnRawViewResult": self.returnRawViewResult,
                    "privateOnly": self.privateOnly,
                    "guestAccess": self.guestAccess,
                    "viewingSelfAccount": self.viewingSelfAccount,
                    "showWelcome": self.showWelcome,
                    "checkCrossPost": self.checkCrossPost,
                    "queryProjects": self.queryProjects,
                    "user": self.user,
                },
            )

        self.viewResult = self.process_view()

        if not self.returnRawViewResult:
            if self.request.matched_route is not None:
                if self.request.matched_route.name == "dashboard":
                    i_view_implementations = p.PluginImplementations(p.IDashBoardView)
                    for plugin in i_view_implementations:
                        self.viewResult = plugin.after_dashboard_processing(
                            self.request,
                            {
                                "returnRawViewResult": self.returnRawViewResult,
                                "privateOnly": self.privateOnly,
                                "guestAccess": self.guestAccess,
                                "viewingSelfAccount": self.viewingSelfAccount,
                                "showWelcome": self.showWelcome,
                                "checkCrossPost": self.checkCrossPost,
                                "queryProjects": self.queryProjects,
                                "user": self.user,
                            },
                            self.viewResult,
                        )
                if self.request.matched_route.name == "project_details":
                    i_view_implementations = p.PluginImplementations(
                        p.IProjectDetailsView
                    )
                    for plugin in i_view_implementations:
                        self.viewResult = plugin.after_project_details_processing(
                            self.request,
                            {
                                "returnRawViewResult": self.returnRawViewResult,
                                "privateOnly": self.privateOnly,
                                "guestAccess": self.guestAccess,
                                "viewingSelfAccount": self.viewingSelfAccount,
                                "showWelcome": self.showWelcome,
                                "checkCrossPost": self.checkCrossPost,
                                "queryProjects": self.queryProjects,
                                "user": self.user,
                            },
                            self.viewResult,
                        )
                if self.request.matched_route.name == "form_details":
                    i_view_implementations = p.PluginImplementations(p.IFormDetailsView)
                    for plugin in i_view_implementations:
                        self.viewResult = plugin.after_form_details_processing(
                            self.request,
                            {
                                "returnRawViewResult": self.returnRawViewResult,
                                "privateOnly": self.privateOnly,
                                "guestAccess": self.guestAccess,
                                "viewingSelfAccount": self.viewingSelfAccount,
                                "showWelcome": self.showWelcome,
                                "checkCrossPost": self.checkCrossPost,
                                "queryProjects": self.queryProjects,
                                "user": self.user,
                            },
                            self.viewResult,
                        )

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

    def get_project_access_level(self):
        """
        Return the access level of a logged user to a project. This could be:
             1: Owner
             2: Administrator (Can edit the project and its forms + add other collaborators)
             3: Editor (Can edit the project and its forms)
             4: Member (Can access the project and its forms)
             5: No access (Either the project does not exits or the user has no access to it)
        """
        user_id = self.request.matchdict.get("userid", None)
        project_code = self.request.matchdict.get("projcode", None)
        if user_id is not None and project_code is not None:
            project_id = get_project_id_from_name(self.request, user_id, project_code)
            project_details = {}
            if project_id is not None:
                project_found = False
                for project in self.user_projects:
                    if project["project_id"] == project_id:
                        project_found = True
                        project_details = project
                if not project_found:
                    return 5
            else:
                return 5
        else:
            return 5

        return project_details["access_type"]


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
        self.set_active_menu("profile")
        PrivateView.__call__(self)
        if not self.returnRawViewResult:
            self.classResult.update(self.viewResult)
            return self.classResult
        else:
            return self.viewResult


class ProjectsView(PrivateView):
    def __call__(self):
        self.set_active_menu("projects")
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

    def append_to_errors(self, error):
        self.request.response.headers["FS_error"] = "true"
        self.errors.append(error)

    def __call__(self):
        error = self.request.session.pop_flash(queue="error")
        if len(error) > 0:
            self.append_to_errors(error[0])

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
            if (
                self.request.registry.settings.get("perform_post_checks", "true")
                == "true"
            ):
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
        self.api_key = ""
        self._ = self.request.translate
        self.error = False

    def __call__(self):
        if self.request.method == "GET":
            self.api_key = self.request.params.get("apikey", None)
        else:
            self.api_key = self.request.POST.get("apikey", None)
        if self.api_key is not None:
            self.user = get_user_by_api_key(self.request, self.api_key)
            if self.user is None:
                response = Response(
                    content_type="application/json",
                    status=401,
                    body=json.dumps(
                        {
                            "error": self._(
                                "This API key does not exist or is inactive"
                            ),
                            "error_type": "authentication",
                        }
                    ).encode(),
                )
                return response
        else:
            response = Response(
                content_type="application/json",
                status=401,
                body=json.dumps(
                    {
                        "error": self._("You need to specify an API key"),
                        "error_type": "api_key_missing",
                    }
                ).encode(),
            )
            return response

        res = self.process_view()
        if not self.error:
            return res
        else:
            response = Response(
                content_type="application/json",
                status=400,
                body=json.dumps(res).encode(),
            )
            return response

    def process_view(self):
        return {"key": self.api_key}

    def check_keys(self, key_list):
        not_found_keys = []
        for a_key in key_list:
            if a_key not in self.request.POST.keys():
                not_found_keys.append(a_key)
        if not_found_keys:
            json_result = {
                "error": self._(
                    "The following keys were not present in the submitted JSON"
                ),
                "keys": [],
                "error_type": "missing_key",
            }
            for a_key in not_found_keys:
                json_result["keys"].append(a_key)

            response = exception_response(
                400,
                content_type="application/json",
                body=json.dumps(json_result).encode(),
            )
            raise response

    def return_error(self, error_type, error_message):
        response = exception_response(
            400,
            content_type="application/json",
            body=json.dumps(
                {"error": error_message, "error_type": error_type}
            ).encode(),
        )
        raise response


class AssistantAPIView(object):
    def __init__(self, request):
        self.request = request
        self.assistant = None
        self.api_key = ""
        self.project_id = None
        self._ = self.request.translate
        self.error = False
        self.json = {}

    def __call__(self):
        if self.request.method == "GET":
            self.api_key = self.request.params.get("apikey", None)
        else:
            self.api_key = self.request.POST.get("apikey", None)
            if self.api_key is not None:
                self.json = self.request.POST
            else:
                try:
                    json_body = json.loads(self.request.body)
                    self.api_key = json_body.get("apikey", None)
                    if self.api_key is not None:
                        self.json = json_body
                except Exception as e:
                    log.error("Unable to parse API POST body. Error {}".format(str(e)))
                    self.api_key = None
        if self.api_key is not None:
            user_id = self.request.matchdict["userid"]
            project_code = self.request.matchdict["projcode"]
            self.project_id = get_project_id_from_name(
                self.request, user_id, project_code
            )
            if self.project_id is not None:
                self.assistant = get_assistant_by_api_key(
                    self.request, self.project_id, self.api_key
                )
                if not self.assistant:
                    response = Response(
                        content_type="application/json",
                        status=401,
                        body=json.dumps(
                            {
                                "error": self._(
                                    "This API key does not exist or is inactive"
                                ),
                                "error_type": "authentication",
                            }
                        ).encode(),
                    )
                    return response
            else:
                response = Response(
                    content_type="application/json",
                    status=400,
                    body=json.dumps(
                        {
                            "error": self._("The project cannot be found"),
                            "error_type": "project_not_found",
                        }
                    ).encode(),
                )
                return response
        else:
            response = Response(
                content_type="application/json",
                status=401,
                body=json.dumps(
                    {
                        "error": self._("You need to specify an API key"),
                        "error_type": "api_key_missing",
                    }
                ).encode(),
            )
            return response

        res = self.process_view()
        if not self.error:
            return res
        else:
            response = Response(
                content_type="application/json",
                status=400,
                body=json.dumps(res).encode(),
            )
            return response

    def process_view(self):
        return {"key": self.api_key}

    def check_keys(self, key_list):
        not_found_keys = []
        for a_key in key_list:
            if a_key not in self.request.POST.keys():
                not_found_keys.append(a_key)
        if not_found_keys:
            json_result = {
                "error": self._(
                    "The following keys were not present in the submitted JSON"
                ),
                "keys": [],
                "error_type": "missing_key",
            }
            for a_key in not_found_keys:
                json_result["keys"].append(a_key)

            response = exception_response(
                400,
                content_type="application/json",
                body=json.dumps(json_result).encode(),
            )
            raise response

    def return_error(self, error_type, error_message):
        response = exception_response(
            400,
            content_type="application/json",
            body=json.dumps(
                {"error": error_message, "error_type": error_type}
            ).encode(),
        )
        raise response
