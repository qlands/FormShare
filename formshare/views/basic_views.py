import datetime
import logging
import re
import traceback
import uuid
from ast import literal_eval
import secrets
import validators
from elasticfeeds.activity import Actor, Object, Activity
from formencode.variabledecode import variable_decode
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response
from pyramid.security import remember
from pyramid.session import check_csrf_token

import formshare.plugins as p
from formshare.config.auth import (
    get_user_data,
    get_assistant_data,
    reset_key_exists,
    get_partner_data,
    set_password_reset_token,
    reset_password,
)
from formshare.config.elasticfeeds import get_manager
from formshare.config.encdecdata import encode_data, decode_data
from formshare.processes.avatar import Avatar
from formshare.processes.db import (
    register_user,
    get_project_id_from_name,
    get_project_from_assistant,
    update_last_login,
)
from formshare.processes.elasticsearch.user_index import get_user_index_manager
from formshare.processes.email.send_email import send_error_to_technical_team
from formshare.processes.email.send_email import send_password_email
from formshare.views.classes import PublicView, ExceptionView

log = logging.getLogger("formshare")


class HealthView(PublicView):
    def process_view(self):
        self.returnRawViewResult = True
        engine = self.request.dbsession.get_bind()
        try:
            res = self.request.dbsession.execute(
                "show status like 'Threads_connected%'"
            ).fetchone()
            threads_connected = res[1]
        except Exception as e:
            threads_connected = str(e)
        return {
            "health": {
                "pool": engine.pool.status(),
                "threads_connected": threads_connected,
            }
        }


class HomeView(PublicView):
    def process_view(self):
        return {"activeUser": None}


class NotFoundView(ExceptionView):
    def process_view(self):
        self.request.response.status = 404
        return {}


class Gravatar(PublicView):
    def process_view(self):
        self.returnRawViewResult = True
        try:
            size = int(self.request.params.get("size", 45))
        except ValueError:
            size = 45
        name = self.request.params.get("name", "#")
        avatar = Avatar.generate(size, name, "PNG")
        headers = [("Content-Type", "image/png")]
        return Response(avatar, 200, headers)


class ErrorView(ExceptionView):
    def process_view(self):
        user = None
        policy = get_policy(self.request, "main")
        login_data = policy.authenticated_userid(self.request)
        if login_data is not None:
            login_data = literal_eval(login_data)
            if login_data["group"] == "mainApp":
                user = login_data["login"]

        if user is None:
            policy = get_policy(self.request, "assistant")
            login_data = policy.authenticated_userid(self.request)
            if login_data is not None:
                login_data = literal_eval(login_data)
                if login_data["group"] == "collaborators":
                    user = login_data["login"]

        if user is None:
            policy = get_policy(self.request, "partner")
            login_data = policy.authenticated_userid(self.request)
            if login_data is not None:
                login_data = literal_eval(login_data)
                if login_data["group"] == "partners":
                    user = login_data["login"]

        if user is None:
            user = "Unknown"
        log.error(
            "Server Error in URL {}.\nAccount: {}\nError: \n{}".format(
                self.request.url, user, traceback.format_exc()
            )
        )
        send_error_to_technical_team(
            self.request,
            "Server Error in URL {}.\nAccount: {}\nError: \n{}".format(
                self.request.url, user, traceback.format_exc()
            ),
        )
        self.request.response.status = 500
        return {}


class LoginView(PublicView):
    def process_view(self):
        # If we logged in then go to dashboard or next page
        next_page = self.request.params.get("next")
        if self.request.method == "GET":
            policy = get_policy(self.request, "main")
            login_data = policy.authenticated_userid(self.request)
            if login_data is not None:
                login_data = literal_eval(login_data)
                if login_data["group"] == "mainApp":
                    current_user = get_user_data(login_data["login"], self.request)
                    if current_user is not None:
                        self.returnRawViewResult = True
                        next_page = self.request.params.get(
                            "next"
                        ) or self.request.route_url(
                            "dashboard", userid=current_user.login
                        )

                        return HTTPFound(
                            location=next_page,
                        )
        else:
            if (
                self.request.registry.settings.get("perform_post_checks", "true")
                == "true"
            ):
                safe = check_csrf_token(self.request, raises=False)
                if not safe:
                    raise HTTPNotFound()
            data = self.get_post_dict()

            user = data["user"]
            if user != "":
                log.error(
                    "Suspicious bot login from IP: {}. Agent: {}. Email/Account: {}".format(
                        self.request.remote_addr, self.request.user_agent, data["email"]
                    )
                )
            data.pop("user")
            login = data["email"]
            passwd = data["passwd"]
            user = get_user_data(login, self.request)
            login_data = {"login": login, "group": "mainApp"}
            if user is not None:
                password_ok, message = user.check_password(passwd, self.request)
                if password_ok:
                    continue_login = True
                    # Load connected plugins and check if they modify the login authorization
                    for plugin in p.PluginImplementations(p.IUserAuthentication):
                        continue_with_login, error_message = plugin.after_login(
                            self.request, user
                        )
                        if not continue_with_login:
                            self.append_to_errors(error_message)
                            continue_login = False
                        break  # Only one plugging will be called to extend after_login
                    if continue_login:
                        update_last_login(self.request, user.login)
                        headers = remember(
                            self.request, str(login_data), policies=["main"]
                        )
                        next_page = self.request.params.get(
                            "next"
                        ) or self.request.route_url("dashboard", userid=user.login)
                        self.returnRawViewResult = True

                        return HTTPFound(location=next_page, headers=headers)
                else:
                    log.error(
                        "Logging into account {} provided an invalid password. Message: {}".format(
                            login, message
                        )
                    )
                    self.append_to_errors(message)
            else:
                log.error("User account {} does not exist".format(login))
                self.append_to_errors(
                    self._("The user account does not exist or the password is invalid")
                )
        return {"next": next_page}


class RefreshSessionView(PublicView):
    def process_view(self):
        return {}


class ResetPasswordView(PublicView):
    def process_view(self):
        if (
            self.request.registry.settings.get("mail.server.available", "false")
            == "false"
        ):
            if (
                self.request.registry.settings.get("ignore_email_check", "false")
                == "false"
            ):
                raise HTTPNotFound()
        reset_key = self.request.matchdict["reset_key"]
        if not reset_key_exists(self.request, reset_key):
            raise HTTPNotFound()

        if self.request.method == "POST":
            if (
                self.request.registry.settings.get("perform_post_checks", "true")
                == "true"
            ):
                safe = check_csrf_token(self.request, raises=False)
                if not safe:
                    raise HTTPNotFound()
            data = variable_decode(self.request.POST)
            login = data.get("email", "")
            token = data.get("token", "")
            new_password = data.get("password", "").strip()
            new_password2 = data.get("password2", "").strip()
            user = data.get("user", "hola")
            if user != "":
                log.error(
                    "Suspicious bot password recovery from IP: {}. Agent: {}. Email: {}".format(
                        self.request.remote_addr, self.request.user_agent, data["email"]
                    )
                )
            user = get_user_data(login, self.request)
            if user is not None:
                if user.userData["user_password_reset_key"] == reset_key:
                    if user.userData["user_password_reset_token"] == token:
                        if (
                            user.userData["user_password_reset_expires_on"]
                            > datetime.datetime.now()
                        ):
                            if new_password != "":
                                if new_password == new_password2:
                                    new_password = encode_data(
                                        self.request, new_password
                                    )
                                    reset_password(
                                        self.request,
                                        user.id,
                                        reset_key,
                                        token,
                                        new_password,
                                    )
                                    self.returnRawViewResult = True
                                    return HTTPFound(
                                        location=self.request.route_url("login")
                                    )
                                else:
                                    self.append_to_errors(
                                        self._(
                                            "The password and the confirmation are not the same"
                                        )
                                    )
                            else:
                                self.append_to_errors(
                                    self._("The password cannot be empty")
                                )
                        else:
                            self.append_to_errors(self._("Invalid token"))
                    else:
                        self.append_to_errors(self._("Invalid token"))
                else:
                    self.append_to_errors(self._("Invalid key"))
            else:
                self.append_to_errors(self._("User does not exist"))
        return {}


class RecoverPasswordView(PublicView):
    def process_view(self):
        if (
            self.request.registry.settings.get("mail.server.available", "false")
            == "false"
        ):
            if (
                self.request.registry.settings.get("ignore_email_check", "false")
                == "false"
            ):
                raise HTTPNotFound()
        if self.request.method == "POST":
            if (
                self.request.registry.settings.get("perform_post_checks", "true")
                == "true"
            ):
                safe = check_csrf_token(self.request, raises=False)
                if not safe:
                    raise HTTPNotFound()
            data = variable_decode(self.request.POST)
            login = data["email"]
            user = data["user"]
            if user != "":
                log.error(
                    "Suspicious bot password recovery from IP: {}. Agent: {}. Email: {}".format(
                        self.request.remote_addr, self.request.user_agent, data["email"]
                    )
                )
            user = get_user_data(login, self.request)
            if user is not None:
                reset_key = str(uuid.uuid4())
                reset_token = secrets.token_hex(16)
                set_password_reset_token(self.request, user.id, reset_key, reset_token)
                send_password_email(
                    self.request, user.email, reset_token, reset_key, user.userData
                )
                self.returnRawViewResult = True
                return HTTPFound(location=self.request.route_url("login"))
            else:
                self.append_to_errors(self._("Invalid email"))
        return {}


class AssistantLoginView(PublicView):
    def process_view(self):
        # If we logged in then go to dashboard
        project_code = self.request.matchdict["projcode"]
        user_id = self.request.matchdict["userid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is None:
            raise HTTPNotFound()
        next_page = self.request.params.get("next") or self.request.route_url(
            "assistant_forms", userid=user_id, projcode=project_code
        )
        if self.request.method == "GET":
            policy = get_policy(self.request, "assistant")
            login_data = policy.authenticated_userid(self.request)
            if login_data is not None:
                login_data = literal_eval(login_data)
                if login_data["group"] == "collaborators":
                    project_assistant = get_project_from_assistant(
                        self.request, user_id, project_id, login_data["login"]
                    )
                    current_collaborator = get_assistant_data(
                        project_assistant, login_data["login"], self.request
                    )
                    if current_collaborator is not None:
                        self.returnRawViewResult = True
                        return HTTPFound(
                            location=self.request.route_url(
                                "assistant_forms", userid=user_id, projcode=project_code
                            )
                        )
        else:
            if (
                self.request.registry.settings.get("perform_post_checks", "true")
                == "true"
            ):
                safe = check_csrf_token(self.request, raises=False)
                if not safe:
                    raise HTTPNotFound()
            data = variable_decode(self.request.POST)
            login = data["login"]
            passwd = data["passwd"]
            project_assistant = get_project_from_assistant(
                self.request, user_id, project_id, login
            )
            collaborator = get_assistant_data(project_assistant, login, self.request)
            login_data = {"login": login, "group": "collaborators"}
            if collaborator is not None:
                if collaborator.check_password(passwd, self.request):
                    continue_login = True
                    # Load connected plugins and check if they modify the login authorization
                    for plugin in p.PluginImplementations(p.IAssistantAuthentication):
                        (
                            continue_with_login,
                            error_message,
                        ) = plugin.after_assistant_login(self.request, collaborator)
                        if not continue_with_login:
                            self.append_to_errors(error_message)
                            continue_login = False
                        break  # Only one plugging will be called to extend after_collaborator_login
                    if continue_login:
                        headers = remember(
                            self.request, str(login_data), policies=["assistant"]
                        )
                        self.returnRawViewResult = True
                        return HTTPFound(location=next_page, headers=headers)
                else:
                    log.error(
                        "Logging into assistant account {} for FormShare account {} in project {} "
                        "provided an invalid password".format(
                            login, user_id, project_code
                        )
                    )
                    self.append_to_errors(
                        self._(
                            "The user account does not exist or the password is invalid"
                        )
                    )
            else:
                log.error(
                    "Assistant account {} for FormShare account {} in project {} "
                    "does not exists".format(login, user_id, project_code)
                )
                self.append_to_errors(
                    self._(
                        "The user account does not exists or the password is invalid"
                    )
                )
        return {"next": next_page, "userid": user_id, "projcode": project_code}


class PartnerLoginView(PublicView):
    def process_view(self):
        next_page = self.request.params.get("next") or self.request.route_url(
            "partner_forms"
        )
        if self.request.method == "GET":
            policy = get_policy(self.request, "partner")
            login_data = policy.authenticated_userid(self.request)
            if login_data is not None:
                login_data = literal_eval(login_data)
                if login_data["group"] == "partners":
                    current_partner = get_partner_data(
                        self.request, login_data["login"]
                    )
                    if current_partner is not None:
                        self.returnRawViewResult = True
                        return HTTPFound(location=next_page)
        else:
            if (
                self.request.registry.settings.get("perform_post_checks", "true")
                == "true"
            ):
                safe = check_csrf_token(self.request, raises=False)
                if not safe:
                    raise HTTPNotFound()
            data = variable_decode(self.request.POST)
            login = data["login"]
            passwd = data["passwd"]
            partner = get_partner_data(self.request, login)
            login_data = {"login": login, "group": "partners"}
            if partner is not None:
                if partner.check_password(passwd, self.request):
                    continue_login = True
                    # Load connected plugins and check if they modify the login authorization
                    for plugin in p.PluginImplementations(p.IPartnerAuthentication):
                        (
                            continue_with_login,
                            error_message,
                        ) = plugin.after_partner_login(self.request, partner)
                        if not continue_with_login:
                            self.append_to_errors(error_message)
                            continue_login = False
                        break  # Only one plugging will be called to extend after_partner_login
                    if continue_login:
                        headers = remember(
                            self.request, str(login_data), policies=["partner"]
                        )
                        self.returnRawViewResult = True
                        return HTTPFound(location=next_page, headers=headers)
                else:
                    log.error(
                        "Logging into partner account {} provided an invalid password".format(
                            login
                        )
                    )
                    self.append_to_errors(
                        self._(
                            "The partner account does not exist or the password is invalid"
                        )
                    )
            else:
                log.error("Partner account {} does not exists".format(login))
                self.append_to_errors(
                    self._(
                        "The partner account does not exists or the password is invalid"
                    )
                )
        return {"next": next_page}


def get_policy(request, policy_name):
    policies = request.policies()
    for policy in policies:
        if policy["name"] == policy_name:
            return policy["policy"]
    return None


def log_out_view(request):
    policy = get_policy(request, "main")
    login_data = policy.authenticated_userid(request)
    if login_data is not None:
        login_data = literal_eval(login_data)
        if login_data["group"] == "mainApp":
            current_user = login_data["login"]
            continue_logout = True
            for plugin in p.PluginImplementations(p.ILogOut):
                continue_logout = plugin.before_log_out(
                    request, current_user, continue_logout
                )
            if continue_logout:
                policy = get_policy(request, "main")
                headers = policy.forget(request)
                loc = request.route_url("home")
                for plugin in p.PluginImplementations(p.ILogOut):
                    loc, headers = plugin.after_log_out(
                        request, current_user, loc, headers
                    )
                raise HTTPFound(location=loc, headers=headers)
            else:
                loc = request.route_url("dashboard", userid=current_user)
                raise HTTPFound(location=loc)
        else:
            loc = request.route_url("home")
            raise HTTPFound(location=loc)
    else:
        loc = request.route_url("home")
        raise HTTPFound(location=loc)


def assistant_log_out_view(request):
    policy = get_policy(request, "assistant")
    headers = policy.forget(request)
    project_code = request.matchdict["projcode"]
    user_id = request.matchdict["userid"]
    loc = request.route_url("assistant_login", userid=user_id, projcode=project_code)
    raise HTTPFound(location=loc, headers=headers)


def partner_log_out_view(request):
    policy = get_policy(request, "partner")
    headers = policy.forget(request)
    loc = request.route_url("partner_login")
    raise HTTPFound(location=loc, headers=headers)


class RegisterView(PublicView):
    def process_view(self):
        if self.request.registry.settings["auth.register_users_via_web"] == "false":
            raise HTTPNotFound()
        # If we logged in then go to dashboard
        if self.request.method == "GET":
            data = {}
        else:
            if (
                self.request.registry.settings.get("perform_post_checks", "true")
                == "true"
            ):
                safe = check_csrf_token(self.request, raises=False)
                if not safe:
                    raise HTTPNotFound()
            data = variable_decode(self.request.POST)

            user = data.get("user_address", "")
            if user != "Costa Rica":
                log.error(
                    "Suspicious bot register from IP: {}. Agent: {}. Email: {} ".format(
                        self.request.remote_addr,
                        self.request.user_agent,
                        data["user_email"],
                    )
                )
            data.pop("user_address", None)
            data["user_email"] = data["user_email"].strip()
            if validators.email(data["user_email"]) and re.match(
                r"^[A-Za-z0-9._@-]+$", data["user_email"]
            ):
                if data["user_password"] != "":
                    if re.match(r"^[A-Za-z0-9._]+$", data["user_id"]):
                        if data["user_password"] == data["user_password2"]:
                            if len(data["user_password"]) <= 50:
                                data["user_cdate"] = datetime.datetime.now()
                                if "user_apikey" not in data.keys():
                                    data["user_apikey"] = str(uuid.uuid4())
                                if "user_apisecret" not in data.keys():
                                    data["user_apisecret"] = secrets.token_hex(16)
                                data["user_password"] = encode_data(
                                    self.request, data["user_password"]
                                )
                                data["user_active"] = 1
                                # Load connected plugins and check if they modify the registration of an user
                                continue_registration = True
                                for plugin in p.PluginImplementations(p.IRegistration):
                                    (
                                        data,
                                        continue_with_registration,
                                        error_message,
                                    ) = plugin.before_register(self.request, data)
                                    if not continue_with_registration:
                                        self.append_to_errors(error_message)
                                        continue_registration = False
                                    break  # Only one plugging will be called to extend before_register
                                if continue_registration:
                                    added, error_message = register_user(
                                        self.request, data
                                    )
                                    if not added:
                                        self.append_to_errors(error_message)
                                    else:
                                        # Store the notifications
                                        feed_manager = get_manager(self.request)
                                        # The user follows himself
                                        try:
                                            feed_manager.follow(
                                                data["user_id"], data["user_id"]
                                            )
                                        except Exception as e:
                                            log.warning(
                                                "User {} was in FormShare at some point. Error: {}".format(
                                                    data["user_id"], str(e)
                                                )
                                            )
                                        # The user join FormShare
                                        actor = Actor(data["user_id"], "person")
                                        feed_object = Object("formshare", "platform")
                                        activity = Activity("join", actor, feed_object)
                                        feed_manager.add_activity_feed(activity)

                                        # Add the user to the user index
                                        user_index = get_user_index_manager(
                                            self.request
                                        )
                                        user_index_data = data
                                        user_index_data.pop("user_apikey", None)
                                        user_index_data.pop("user_apisecret", None)
                                        user_index_data.pop("user_password", None)
                                        user_index_data.pop("user_active", None)
                                        user_index_data.pop("user_cdate", None)
                                        user_index_data.pop("csrf_token", None)
                                        user_index.add_user(
                                            data["user_id"], user_index_data
                                        )

                                        # Load connected plugins so they perform actions after the registration
                                        # is performed
                                        next_page = self.request.route_url(
                                            "dashboard", userid=data["user_id"]
                                        )
                                        plugin_next_page = ""
                                        for plugin in p.PluginImplementations(
                                            p.IRegistration
                                        ):
                                            plugin_next_page = plugin.after_register(
                                                self.request, data
                                            )
                                            break  # Only one plugging will be called to extend after_register
                                        if plugin_next_page is not None:
                                            if plugin_next_page != "":
                                                if plugin_next_page != next_page:
                                                    next_page = plugin_next_page
                                        if next_page == self.request.route_url(
                                            "dashboard", userid=data["user_id"]
                                        ):
                                            login_data = {
                                                "login": data["user_id"],
                                                "group": "mainApp",
                                            }
                                            headers = remember(
                                                self.request,
                                                str(login_data),
                                                policies=["main"],
                                            )
                                            self.returnRawViewResult = True
                                            return HTTPFound(
                                                location=self.request.route_url(
                                                    "dashboard", userid=data["user_id"]
                                                ),
                                                headers=headers,
                                            )
                                        else:
                                            self.returnRawViewResult = True
                                            return HTTPFound(next_page)
                            else:
                                self.append_to_errors(
                                    self._(
                                        "The password must be less than 50 characters"
                                    )
                                )
                        else:
                            log.error(
                                "Password {} and confirmation {} are not the same".format(
                                    data["user_password"], data["user_password2"]
                                )
                            )
                            self.append_to_errors(
                                self._(
                                    "The password and its confirmation are not the same"
                                )
                            )
                    else:
                        log.error(
                            "Registering user {} has invalid characters".format(
                                data["user_id"]
                            )
                        )
                        self.append_to_errors(
                            self._(
                                "The user id has invalid characters. Only underscore "
                                "and dot are allowed"
                            )
                        )
                else:
                    log.error(
                        "Registering user {} has empty password".format(data["user_id"])
                    )
                    self.append_to_errors(self._("The password cannot be empty"))
            else:
                log.error("Invalid email {}".format(data["user_email"]))
                self.append_to_errors(self._("Invalid email"))
        return {"next": next, "userdata": data}
