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
import datetime
from babel import Locale
from formencode.variabledecode import variable_decode
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound, exception_response
from pyramid.response import Response
from pyramid.session import check_csrf_token

from formshare import plugins as p
from formshare.config.auth import get_user_data, get_assistant_data, get_partner_data
from formshare.processes.db import (
    get_project_id_from_name,
    user_exists,
    get_user_details,
    get_active_project,
    get_user_projects,
    get_project_from_assistant,
    get_user_by_api_key,
    get_user_timezone,
    get_partner_by_api_key,
    get_timezone_offset,
    get_timezone_name,
    get_assistant_timezone,
    get_project_details,
    get_partner_timezone,
    get_timezones,
    timezone_exists,
    get_assistant_by_api_key,
)

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

    def get_auth_dict(self):  # pragma: no cover
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
        if (
            self.request.encget("FS_for_testing", default="false") == "false"
        ):  # pragma: no cover
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

    def ask_for_credentials(self):  # pragma: no cover
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
            if testing_calls == "false":  # pragma: no cover
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


class ExceptionView(object):
    """
    This is the Exception view. Used for 404 and 500.
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

        self.request.response.headers.pop("FS_error", None)
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

    def append_to_errors(self, error):
        self.request.response.headers["FS_error"] = "true"
        self.errors.append(error)


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

        if self.request.matched_route is not None:
            for plugin in p.PluginImplementations(p.IPublicView):
                continue_request = plugin.before_processing_public_view(
                    self.request.matched_route.name, self.request
                )
                if not continue_request:
                    raise HTTPNotFound()

        self.request.response.headers.pop("FS_error", None)
        process_dict = self.process_view()

        if not self.returnRawViewResult:
            if self.request.matched_route is not None:
                for plugin in p.PluginImplementations(p.IPublicView):
                    process_dict = plugin.after_processing_public_view(
                        self.request.matched_route.name, self.request, process_dict
                    )
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
        self.classResult["selected_timezone"] = self.request.cookies.get(
            "_TIMEZONE_", "formshare"
        )
        self.selected_timezone = self.request.cookies.get("_TIMEZONE_", "formshare")
        self.classResult["system_timezone"] = (
            datetime.datetime.utcnow().astimezone().tzname()
        )
        self.system_timezone = datetime.datetime.utcnow().astimezone().tzname()
        if not timezone_exists(self.request, self.system_timezone):
            log.warning(
                "Unable to find timezone with code '{}'. Going to UTC as default".format(
                    self.system_timezone
                )
            )
            self.classResult["system_timezone"] = "UTC"
            self.system_timezone = "UTC"
        if self.classResult["system_timezone"] != "UTC":
            self.classResult["system_timezone_offset"] = get_timezone_offset(
                self.request, self.classResult["system_timezone"]
            )
            self.classResult["system_timezone_name"] = get_timezone_name(
                self.request, self.classResult["system_timezone"]
            )
            self.system_timezone_offset = get_timezone_offset(
                self.request, self.classResult["system_timezone"]
            )
            self.system_timezone_name = get_timezone_name(
                self.request, self.classResult["system_timezone"]
            )
        else:
            self.classResult["system_timezone_offset"] = "+00:00"
            self.classResult["system_timezone_name"] = "UTC"
            self.system_timezone_offset = "+00:00"
            self.system_timezone_name = "UTC"

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
            ):  # pragma: no cover
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
        if self.request.method == "POST":
            next_page = self.request.route_url("login")
        else:
            next_page = self.request.route_url(
                "login", _query={"next": self.request.url}
            )
        if login_data is not None:
            login_data = literal_eval(login_data)
            if login_data["group"] == "mainApp":
                self.user = get_user_data(login_data["login"], self.request)
                if self.user is None:
                    raise HTTPFound(location=next_page)
                self.check_post_put_delete()
            else:
                raise HTTPFound(location=next_page)
        else:
            raise HTTPFound(location=next_page)

    def __call__(self):
        error = self.request.session.pop_flash(queue="error")
        if len(error) > 0:
            self.append_to_errors(error[0].replace("|error", ""))

        self.userID = self.request.matchdict["userid"]
        if not user_exists(self.request, self.userID):
            raise HTTPNotFound()
        self.classResult["userDetails"] = get_user_details(self.request, self.userID)

        i_user_authorization = p.PluginImplementations(p.IUserAuthorization)
        continue_authorization = True
        for plugin in i_user_authorization:
            continue_authorization = plugin.before_check_authorization(self.request)
            break  # Only only plugin will be called for before_check_authorization
        if continue_authorization:
            self.check_authorization()
        else:  # pragma: no cover
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

        self.classResult["activeUser"] = self.user
        if self.user.login != self.userID:
            self.viewingSelfAccount = False

        if self.queryProjects:
            if self.user is not None:
                if self.userID == self.user.login:
                    self.user_projects = get_user_projects(
                        self.request, self.userID, self.userID
                    )
                else:
                    self.user_projects = get_user_projects(
                        self.request, self.userID, self.user.login
                    )
            else:
                raise HTTPNotFound()
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

        if self.request.matched_route is not None:
            for plugin in p.PluginImplementations(p.IPrivateView):
                plugin.before_processing(
                    self.request.matched_route.name,
                    self.request,
                    {
                        "returnRawViewResult": self.returnRawViewResult,
                        "privateOnly": self.privateOnly,
                        "viewingSelfAccount": self.viewingSelfAccount,
                        "showWelcome": self.showWelcome,
                        "checkCrossPost": self.checkCrossPost,
                        "queryProjects": self.queryProjects,
                        "user": self.user,
                    },
                )
        self.request.response.headers.pop("FS_error", None)
        self.classResult["user_timezone"] = get_user_timezone(
            self.request, self.user.login
        )
        self.user_timezone = get_user_timezone(self.request, self.user.login)
        self.viewResult = self.process_view()

        if not self.returnRawViewResult:
            if self.request.matched_route is not None:
                for plugin in p.PluginImplementations(p.IPrivateView):
                    self.viewResult = plugin.after_processing(
                        self.request.matched_route.name,
                        self.request,
                        {
                            "showWelcome": self.showWelcome,
                            "checkCrossPost": self.checkCrossPost,
                            "user_projects": self.user_projects,
                            "active_project": self.activeProject,
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
        for key, value in dct.items():
            if isinstance(value, str):
                dct[key] = value.strip()
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
        self.resultDict["timezones"] = get_timezones(self.request)
        self.returnRawViewResult = False
        self.project_assistant = None
        self.checkCrossPost = True
        self.resultDict["selected_timezone"] = self.request.cookies.get(
            "_TIMEZONE_", "formshare"
        )
        self.selected_timezone = self.request.cookies.get("_TIMEZONE_", "formshare")
        self.resultDict["system_timezone"] = (
            datetime.datetime.utcnow().astimezone().tzname()
        )
        self.system_timezone = datetime.datetime.utcnow().astimezone().tzname()
        if not timezone_exists(self.request, self.system_timezone):
            log.warning(
                "Unable to find timezone with code '{}'. Going to UTC as default".format(
                    self.system_timezone
                )
            )
            self.resultDict["system_timezone"] = "UTC"
            self.system_timezone = "UTC"
        if self.resultDict["system_timezone"] != "UTC":
            self.resultDict["system_timezone_offset"] = get_timezone_offset(
                self.request, self.resultDict["system_timezone"]
            )
            self.resultDict["system_timezone_name"] = get_timezone_name(
                self.request, self.resultDict["system_timezone"]
            )
            self.system_timezone_offset = get_timezone_offset(
                self.request, self.resultDict["system_timezone"]
            )
            self.system_timezone_name = get_timezone_name(
                self.request, self.resultDict["system_timezone"]
            )
        else:
            self.resultDict["system_timezone_offset"] = "+00:00"
            self.resultDict["system_timezone_name"] = "UTC"
            self.system_timezone_offset = "+00:00"
            self.system_timezone_name = "UTC"

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
        if self.request.method != "POST":
            next_page = self.request.route_url(
                "assistant_login",
                userid=self.userID,
                projcode=self.projectCode,
                _query={"next": self.request.url},
            )
        else:
            next_page = self.request.route_url(
                "assistant_login",
                userid=self.userID,
                projcode=self.projectCode,
            )
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
                    return HTTPFound(next_page)
            else:
                return HTTPFound(next_page)
        else:
            return HTTPFound(next_page)

        if self.request.method == "POST":
            if (
                self.request.registry.settings.get("perform_post_checks", "true")
                == "true"
            ):  # pragma: no cover
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
        self.resultDict["assistant_id"] = self.assistantID
        self.resultDict["userid"] = self.userID
        self.resultDict["projcode"] = self.projectCode
        self.resultDict["project_id"] = self.projectID
        self.resultDict["project_assistant"] = self.project_assistant
        self.resultDict["posterrors"] = self.errors
        self.resultDict["activeProject"] = get_project_details(
            self.request, self.projectID
        )
        self.resultDict["assistant_timezone"] = get_assistant_timezone(
            self.request, self.project_assistant, self.assistantID
        )
        self.assistant_timezone = get_assistant_timezone(
            self.request, self.project_assistant, self.assistantID
        )

        if self.request.matched_route is not None:
            for plugin in p.PluginImplementations(p.IAssistantView):
                plugin.before_processing_assistant_view(
                    self.request.matched_route.name, self.request, self.resultDict
                )

        process_dict = self.process_view()

        if not self.returnRawViewResult:
            self.resultDict.update(process_dict)
            if self.request.matched_route is not None:
                for plugin in p.PluginImplementations(p.IAssistantView):
                    self.resultDict = plugin.after_processing_assistant_view(
                        self.request.matched_route.name, self.request, self.resultDict
                    )
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


class PartnerView(object):
    def __init__(self, request):
        self.request = request
        self.partner = None
        self._ = self.request.translate
        self.errors = []
        self.resultDict = {"errors": []}
        locale = Locale(request.locale_name)
        if locale.character_order == "left-to-right":
            self.resultDict["rtl"] = False
        else:
            self.resultDict["rtl"] = True
        self.returnRawViewResult = False
        self.checkCrossPost = True
        self.resultDict["timezones"] = get_timezones(self.request)
        self.resultDict["selected_timezone"] = self.request.cookies.get(
            "_TIMEZONE_", "formshare"
        )
        self.selected_timezone = self.request.cookies.get("_TIMEZONE_", "formshare")
        self.resultDict["system_timezone"] = (
            datetime.datetime.utcnow().astimezone().tzname()
        )
        self.system_timezone = datetime.datetime.utcnow().astimezone().tzname()
        if not timezone_exists(self.request, self.system_timezone):
            log.warning(
                "Unable to find timezone with code '{}'. Going to UTC as default".format(
                    self.system_timezone
                )
            )
            self.resultDict["system_timezone"] = "UTC"
            self.system_timezone = "UTC"
        if self.resultDict["system_timezone"] != "UTC":
            self.resultDict["system_timezone_offset"] = get_timezone_offset(
                self.request, self.resultDict["system_timezone"]
            )
            self.resultDict["system_timezone_name"] = get_timezone_name(
                self.request, self.resultDict["system_timezone"]
            )
            self.system_timezone_offset = get_timezone_offset(
                self.request, self.resultDict["system_timezone"]
            )
            self.system_timezone_name = get_timezone_name(
                self.request, self.resultDict["system_timezone"]
            )
        else:
            self.resultDict["system_timezone_offset"] = "+00:00"
            self.resultDict["system_timezone_name"] = "UTC"
            self.system_timezone_offset = "+00:00"
            self.system_timezone_name = "UTC"

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

        policy = self.get_policy("partner")
        login_data = policy.authenticated_userid(self.request)
        if login_data is not None:
            login_data = literal_eval(login_data)
            if login_data["group"] == "partners":
                self.partner = get_partner_data(self.request, login_data["login"])
                if self.partner is None:
                    return HTTPFound(
                        location=self.request.route_url(
                            "partner_login",
                            _query={"next": self.request.url},
                        )
                    )
            else:
                return HTTPFound(
                    location=self.request.route_url(
                        "partner_login",
                        _query={"next": self.request.url},
                    )
                )
        else:
            return HTTPFound(
                location=self.request.route_url(
                    "partner_login",
                    _query={"next": self.request.url},
                )
            )

        if self.request.method == "POST":
            if (
                self.request.registry.settings.get("perform_post_checks", "true")
                == "true"
            ):  # pragma: no cover
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

        self.partnerID = self.partner.id
        self.partnerEmail = self.partner.email
        self.resultDict["activePartner"] = self.partner
        self.resultDict["partner_id"] = self.partnerID
        self.resultDict["partner_email"] = self.partner.email
        self.resultDict["posterrors"] = self.errors
        self.resultDict["partner_timezone"] = get_partner_timezone(
            self.request, self.partnerEmail
        )
        self.partner_timezone = get_partner_timezone(self.request, self.partnerEmail)

        if self.request.matched_route is not None:
            for plugin in p.PluginImplementations(p.IPartnerView):
                plugin.before_processing_partner_view(
                    self.request.matched_route.name, self.request, self.resultDict
                )

        process_dict = self.process_view()
        if not self.returnRawViewResult:
            self.resultDict.update(process_dict)
            if self.request.matched_route is not None:
                for plugin in p.PluginImplementations(p.IPartnerView):
                    self.resultDict = plugin.after_processing_partner_view(
                        self.request.matched_route.name, self.request, self.resultDict
                    )
            return self.resultDict
        else:
            return process_dict

    def process_view(self):
        return {"activePartner": self.partner}

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
        self.using_assistant = False
        self.assistant_id = ""
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
                assistant_data = get_assistant_by_api_key(self.request, self.api_key)
                if assistant_data:
                    self.using_assistant = True
                    self.assistant_id = assistant_data["coll_id"]
                else:
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


# class AssistantAPIView(object):
#     def __init__(self, request):
#         self.request = request
#         self.assistant = None
#         self.api_key = ""
#         self.project_id = None
#         self._ = self.request.translate
#         self.error = False
#         self.json = {}
#
#     def __call__(self):
#         if self.request.method == "GET":
#             self.api_key = self.request.params.get("apikey", None)
#         else:
#             self.api_key = self.request.POST.get("apikey", None)
#             if self.api_key is not None:
#                 self.json = self.request.POST
#             else:
#                 try:
#                     json_body = json.loads(self.request.body)
#                     self.api_key = json_body.get("apikey", None)
#                     if self.api_key is not None:
#                         self.json = json_body
#                 except Exception as e:
#                     log.error("Unable to parse API POST body. Error {}".format(str(e)))
#                     self.api_key = None
#         if self.api_key is not None:
#             user_id = self.request.matchdict["userid"]
#             project_code = self.request.matchdict["projcode"]
#             self.project_id = get_project_id_from_name(
#                 self.request, user_id, project_code
#             )
#             if self.project_id is not None:
#                 self.assistant = get_assistant_by_api_key(
#                     self.request, self.project_id, self.api_key
#                 )
#                 if not self.assistant:
#                     response = Response(
#                         content_type="application/json",
#                         status=401,
#                         body=json.dumps(
#                             {
#                                 "error": self._(
#                                     "This API key does not exist or is inactive"
#                                 ),
#                                 "error_type": "authentication",
#                             }
#                         ).encode(),
#                     )
#                     return response
#             else:
#                 response = Response(
#                     content_type="application/json",
#                     status=400,
#                     body=json.dumps(
#                         {
#                             "error": self._("The project cannot be found"),
#                             "error_type": "project_not_found",
#                         }
#                     ).encode(),
#                 )
#                 return response
#         else:
#             response = Response(
#                 content_type="application/json",
#                 status=401,
#                 body=json.dumps(
#                     {
#                         "error": self._("You need to specify an API key"),
#                         "error_type": "api_key_missing",
#                     }
#                 ).encode(),
#             )
#             return response
#
#         res = self.process_view()
#         if not self.error:
#             return res
#         else:
#             response = Response(
#                 content_type="application/json",
#                 status=400,
#                 body=json.dumps(res).encode(),
#             )
#             return response
#
#     def process_view(self):
#         return {"key": self.api_key}
#
#     def check_keys(self, key_list):
#         not_found_keys = []
#         for a_key in key_list:
#             if a_key not in self.request.POST.keys():
#                 not_found_keys.append(a_key)
#         if not_found_keys:
#             json_result = {
#                 "error": self._(
#                     "The following keys were not present in the submitted JSON"
#                 ),
#                 "keys": [],
#                 "error_type": "missing_key",
#             }
#             for a_key in not_found_keys:
#                 json_result["keys"].append(a_key)
#
#             response = exception_response(
#                 400,
#                 content_type="application/json",
#                 body=json.dumps(json_result).encode(),
#             )
#             raise response
#
#     def return_error(self, error_type, error_message):
#         response = exception_response(
#             400,
#             content_type="application/json",
#             body=json.dumps(
#                 {"error": error_message, "error_type": error_type}
#             ).encode(),
#         )
#         raise response


class UpdateAPIView(object):
    def __init__(self, request):
        self.request = request
        self.api_key = ""
        self.rowuuid = ""
        self._ = self.request.translate
        self.error = False
        self.error_code = 400
        self.json = {}

    def __call__(self):
        if self.request.method == "GET":
            raise HTTPNotFound()
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

            self.rowuuid = self.request.POST.get("rowuuid", None)
            if self.rowuuid is not None:
                self.json = self.request.POST
            else:
                try:
                    json_body = json.loads(self.request.body)
                    self.rowuuid = json_body.get("rowuuid", None)
                    if self.rowuuid is not None:
                        self.json = json_body
                except Exception as e:
                    log.error("Unable to parse API POST body. Error {}".format(str(e)))
                    self.rowuuid = None

        if self.api_key is not None:
            if self.rowuuid is None:
                response = Response(
                    content_type="application/json",
                    status=400,
                    body=json.dumps(
                        {
                            "error": self._("You need to specify a rowuuid"),
                            "error_type": "rowuuid_missing",
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
                        "error": self._(
                            "You need to specify an assistant API key (apikey)"
                        ),
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
                status=self.error_code,
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
            self.error_code,
            content_type="application/json",
            body=json.dumps(
                {"error": error_message, "error_type": error_type}
            ).encode(),
        )
        raise response


class PartnerAPIView(object):
    def __init__(self, request):
        self.request = request
        self.partner = None
        self.api_key = ""
        self.partnerID = None
        self._ = self.request.translate
        self.error = False

    def __call__(self):
        if self.request.method == "GET":
            self.api_key = self.request.params.get("apikey", None)
        else:
            self.api_key = self.request.POST.get("apikey", None)
        if self.api_key is not None:
            self.partner = get_partner_by_api_key(self.request, self.api_key)
            if self.partner is None:
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
                self.partnerID = self.partner["partner_id"]
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
