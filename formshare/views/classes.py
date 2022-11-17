# -*- coding: utf-8 -*-
"""
    formshare.resources.resources
    ~~~~~~~~~~~~~~~~~~

    Provides the basic view classes for FormShare and
    the Digest Authorization for ODK

    :copyright: (c) 2017 by QLands Technology Consultants.
    :license: AGPL, see LICENSE for more details.
"""

import datetime
import hashlib
import json
import logging
import uuid
from ast import literal_eval

from babel import Locale
from formencode.variabledecode import variable_decode
from formshare import plugins as p
from formshare.config.auth import get_user_data, get_assistant_data, get_partner_data
from formshare.processes.db import (
    get_project_id_from_name,
    user_exists,
    get_user_details,
    get_active_project,
    get_project_from_assistant,
    get_user_timezone,
    get_timezone_offset,
    get_timezone_name,
    get_assistant_timezone,
    get_project_details,
    get_partner_timezone,
    get_timezones,
    timezone_exists,
    get_assistant_with_token,
    project_has_crowdsourcing,
    update_last_login,
    get_project_access_type,
    get_user_with_token,
)
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound, exception_response
from pyramid.response import Response
from pyramid.session import check_csrf_token

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
        project_code = self.request.matchdict["projcode"]
        user_id = self.request.matchdict["userid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
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
            if not project_has_crowdsourcing(self.request, project_id):
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
            else:
                self.user = ""
                return self.process_view()

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


keys_to_remove = [
    "user_password",
    "user_apisecret",
    "user_query_password",
    "user_apikey",
    "user_apitoken",
    "user_apitoken_expires_on",
    "user_query_user",
    "user_query_password",
    "user_password_reset_key",
    "user_password_reset_token",
    "user_password_reset_expires_on",
    "timezones",
    "user_super",
    "user_active",
    "form_xlsfile",
    "form_xmlfile",
    "form_jsonfile",
    "form_createxmlfile",
    "form_insertxmlfile",
    "form_index",
    "form_reptask",
    "json_file",
    "allPages",
    "form_mergetask",
    "rtl",
    "form_directory",
]


def remove_keys(obj, insecure_keys):
    if isinstance(obj, dict):
        obj = {
            key: remove_keys(value, insecure_keys)
            for key, value in obj.items()
            if key not in insecure_keys
        }
    elif isinstance(obj, list):
        obj = [
            remove_keys(item, insecure_keys)
            for item in obj
            if item not in insecure_keys
        ]
    return obj


class PrivateView(object):
    def __init__(self, request):
        self.request = request
        self.user = None
        self._ = self.request.translate
        self.errors = []
        self.error_occurred = False
        self.userID = ""
        self.classResult = {"activeUser": None, "userProjects": [], "activeProject": {}}
        self.viewResult = {}
        self.returnRawViewResult = False
        self.privateOnly = True
        self.showWelcome = False
        self.checkCrossPost = True
        self.queryProjects = True
        self.activeProject = {}
        self.api = False
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
        """
        This function returns an error to the screen when redirects DO NOT happen.
        The error will appear to the user as a div or in a modal
        """
        self.error_occurred = True
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

    def clean_api_result(self, result):
        user_keys = keys_to_remove
        for plugin in p.PluginImplementations(p.IAPISecurity):
            plugin_keys = plugin.secure_json_result(self.request)
            user_keys = plugin_keys + plugin_keys
        return remove_keys(result, user_keys)

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
        start_time = datetime.datetime.now()
        error = self.request.session.pop_flash(queue="error")
        if len(error) > 0:
            self.append_to_errors(error[0].replace("|error", ""))

        self.userID = self.request.matchdict["userid"]
        if not user_exists(self.request, self.userID):
            raise HTTPNotFound()
        self.classResult["userDetails"] = get_user_details(self.request, self.userID)

        if self.request.headers.get("Authorization", "").find("Bearer") >= 0:
            parts = self.request.headers.get("Authorization", "").split(" ")
            if len(parts) > 1:
                authorization_token = parts[1]
                token_user = get_user_with_token(self.request, authorization_token)
                if token_user is not None:
                    self.user = get_user_data(token_user, self.request)
                    if self.user is None:
                        self.returnRawViewResult = True
                        response = Response(
                            content_type="application/json",
                            status=401,
                            body=json.dumps(
                                {
                                    "status": "401",
                                    "error": self._("Such API key does not exist."),
                                }
                            ).encode(),
                        )
                        return response
                    else:
                        self.api = True
                else:
                    self.returnRawViewResult = True
                    response = Response(
                        content_type="application/json",
                        status=401,
                        body=json.dumps(
                            {
                                "status": "401",
                                "error": self._("Such API key does not exist."),
                            }
                        ).encode(),
                    )
                    return response
        if not self.api:
            i_user_authorization = p.PluginImplementations(p.IUserAuthorization)
            continue_authorization = True
            for plugin in i_user_authorization:
                continue_authorization = plugin.before_check_authorization(self.request)
                break  # Only plugin will be called for before_check_authorization
            if continue_authorization:
                self.check_authorization()
            else:  # pragma: no cover
                authorized = False
                user_authorized = ""
                for plugin in i_user_authorization:
                    authorized, user_authorized = plugin.custom_authorization(
                        self.request
                    )
                    break  # Only one plugin will be called for custom_authorization
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

        if self.user is not None:
            self.activeProject = get_active_project(self.request, self.user.login)
            self.classResult["activeProject"] = self.activeProject
        else:
            self.classResult["activeProject"] = {}

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
        update_last_login(self.request, self.user.login)
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
                            "active_project": self.activeProject,
                            "user": self.user,
                        },
                        self.viewResult,
                    )
        end_time = datetime.datetime.now()
        time_delta = end_time - start_time
        total_seconds = time_delta.total_seconds()
        if (
            self.request.registry.settings.get("report_processing_time", "false")
            == "true"
        ):
            if self.request.matched_route is not None:
                log.error(
                    "Processing {} by {} took {} seconds".format(
                        self.request.matched_route.name, self.user.login, total_seconds
                    )
                )
        if not self.returnRawViewResult:
            self.classResult.update(self.viewResult)
            if not self.api:
                return self.classResult
            else:
                data_result = {
                    "error": self.error_occurred,
                    "errors": self.errors,
                    "message": "",
                    "result": self.clean_api_result(self.classResult),
                }
                status_code = 200
                if self.error_occurred:
                    status_code = 400
                    data_result["result"] = {}
                response = Response(
                    content_type="application/json",
                    status=status_code,
                    body=json.dumps(
                        data_result,
                        indent=4,
                        default=str,
                        ensure_ascii=False,
                    ).encode(),
                )
                return response
        else:
            if not self.api:
                return self.viewResult
            else:
                if self.error_occurred:
                    data_result = {
                        "error": self.error_occurred,
                        "errors": self.errors,
                        "message": "",
                        "result": {},
                    }
                    status_code = 400
                else:
                    data_result = {
                        "error": self.error_occurred,
                        "errors": [],
                        "message": self.request.session.pop_flash(),
                        "result": {},
                    }
                    status_code = 200
                response = Response(
                    content_type="application/json",
                    status=status_code,
                    body=json.dumps(
                        self.clean_api_result(data_result),
                        indent=4,
                        default=str,
                        ensure_ascii=False,
                    ).encode(),
                )
                return response

    def process_view(self):
        return {"activeUser": self.user}

    def set_active_menu(self, menu_name):
        self.classResult["activeMenu"] = menu_name

    def get_post_dict(self):
        if not self.api:
            dct = variable_decode(self.request.POST)
            for key, value in dct.items():
                if isinstance(value, str):
                    dct[key] = value.strip()
            return dct
        else:
            return self.request.json_body

    def reload_user_details(self):
        self.classResult["userDetails"] = get_user_details(self.request, self.userID)
        self.classResult["userDetails"]["user_apisecret"] = ""

    def add_error(self, message, with_queue=True):
        """
        This function returns an error to the screen when redirects happen.
        The error will appear to the user as a sweet alert
        """
        self.error_occurred = True
        if not self.api:
            self.request.response.headers["FS_error"] = "true"
            if with_queue:
                self.request.session.flash("{}|error".format(message), queue="error")
            else:
                self.request.session.flash("{}|error".format(message))
        else:
            self.errors.append(message)

    def get_project_access_level(self):
        """
        Return the access level of a logged user to a project. This could be:
             1: Owner
             2: Administrator (Can edit the project and its forms + add other collaborators)
             3: Editor (Can edit the project and its forms)
             4: Member (Can access the project and its forms)
             5: No access (Either the project does not exist or the user has no access to it)
        """
        user_id = self.request.matchdict.get("userid", None)
        project_code = self.request.matchdict.get("projcode", None)
        if user_id is not None and project_code is not None:
            project_id = get_project_id_from_name(self.request, user_id, project_code)
            if project_id is not None:
                if project_id is not None:
                    return get_project_access_type(
                        self.request, project_id, user_id, self.user.login
                    )
                else:
                    raise HTTPNotFound
            else:
                return 5
        else:
            return 5


class DashboardView(PrivateView):
    def __call__(self):
        self.set_active_menu("dashboard")
        self.showWelcome = True
        return PrivateView.__call__(self)


class ProfileView(PrivateView):
    def __call__(self):
        self.set_active_menu("profile")
        return PrivateView.__call__(self)


class ProjectsView(PrivateView):
    def __call__(self):
        self.set_active_menu("projects")
        return PrivateView.__call__(self)


class AssistantView(object):
    def __init__(self, request):
        self.request = request
        self.projectID = ""
        self.project_has_crowdsourcing = False
        self.userID = ""
        self.projectCode = ""
        self.error_occurred = False
        self.api = False
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
        self.error_occurred = True
        self.request.response.headers["FS_error"] = "true"
        self.errors.append(error)

    def get_json_response(self, data, error_code=200):
        json_data = {"result": data, "status": error_code}
        response = Response(
            content_type="application/json",
            status=error_code,
            body=json.dumps(json_data, indent=4, default=str).encode(),
        )
        return response

    def clean_api_result(self, result):
        user_keys = keys_to_remove
        for plugin in p.PluginImplementations(p.IAPISecurity):
            plugin_keys = plugin.secure_json_result(self.request)
            user_keys = plugin_keys + plugin_keys
        return remove_keys(result, user_keys)

    def __call__(self):
        error = self.request.session.pop_flash(queue="error")
        if len(error) > 0:
            self.append_to_errors(error[0])

        self.userID = self.request.matchdict["userid"]
        self.projectCode = self.request.matchdict["projcode"]
        self.projectID = get_project_id_from_name(
            self.request, self.userID, self.projectCode
        )
        self.project_has_crowdsourcing = project_has_crowdsourcing(
            self.request, self.projectID
        )
        if self.projectID is None:
            raise HTTPNotFound()

        if self.request.headers.get("Authorization", "").find("Bearer") >= 0:
            parts = self.request.headers.get("Authorization", "").split(" ")
            if len(parts) > 1:
                authorization_token = parts[1]
                token_assistant = get_assistant_with_token(
                    self.request, authorization_token
                )
                if token_assistant is not None:
                    self.project_assistant = get_project_from_assistant(
                        self.request, self.userID, self.projectID, token_assistant
                    )
                    self.assistant = get_assistant_data(
                        self.project_assistant, token_assistant, self.request
                    )
                    if self.assistant is None:
                        response = Response(
                            content_type="application/json",
                            status=401,
                            body=json.dumps(
                                {
                                    "status": "401",
                                    "error": self._("Such API key does not exist."),
                                }
                            ).encode(),
                        )
                        return response
                    else:
                        self.api = True
                else:
                    self.returnRawViewResult = True
                    response = Response(
                        content_type="application/json",
                        status=401,
                        body=json.dumps(
                            {
                                "status": "401",
                                "error": self._("Such API key does not exist."),
                            }
                        ).encode(),
                    )
                    return response
        if not self.api:
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
            self.resultDict["activeAssistant"] = self.assistant
        self.assistantID = self.assistant.login
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
            if not self.api:
                return self.resultDict
            else:
                data_result = {
                    "error": self.error_occurred,
                    "errors": self.errors,
                    "message": "",
                    "result": self.clean_api_result(self.resultDict),
                }
                status_code = 200
                if self.error_occurred:
                    status_code = 400
                    data_result["result"] = {}
                response = Response(
                    content_type="application/json",
                    status=status_code,
                    body=json.dumps(
                        data_result,
                        indent=4,
                        default=str,
                        ensure_ascii=False,
                    ).encode(),
                )
                return response
        else:
            if not self.api:
                return process_dict
            else:
                if self.error_occurred:
                    data_result = {
                        "error": self.error_occurred,
                        "errors": self.errors,
                        "message": "",
                        "result": {},
                    }
                    status_code = 400
                else:
                    data_result = {
                        "error": self.error_occurred,
                        "errors": [],
                        "message": self.request.session.pop_flash(),
                        "result": {},
                    }
                    status_code = 200
                response = Response(
                    content_type="application/json",
                    status=status_code,
                    body=json.dumps(
                        self.clean_api_result(data_result),
                        indent=4,
                        default=str,
                        ensure_ascii=False,
                    ).encode(),
                )
                return response

    def process_view(self):
        return {"activeAssistant": self.assistant}

    def get_post_dict(self):
        dct = variable_decode(self.request.POST)
        return dct

    def add_error(self, message):
        self.error_occurred = True
        if not self.api:
            self.request.session.flash(message, queue="error")
        else:
            self.errors.append(message)


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
