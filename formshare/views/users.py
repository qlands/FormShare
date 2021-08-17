import datetime
import logging
import re
import uuid

import validators
from elasticfeeds.activity import Actor, Object, Activity
from pyramid.httpexceptions import HTTPNotFound, HTTPFound

import formshare.plugins as p
from formshare.config.elasticfeeds import get_manager
from formshare.config.encdecdata import encode_data
from formshare.processes.db import (
    get_user_details,
    update_profile,
    email_exists,
    user_exists,
    register_user,
)
from formshare.processes.db.user import update_password
from formshare.processes.elasticsearch.user_index import get_user_index_manager
from formshare.views.classes import PrivateView

log = logging.getLogger("formshare")


class UsersListView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.set_active_menu("users")

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        if self.user.id != user_id:
            raise HTTPNotFound
        if self.user.super != 1:
            raise HTTPNotFound
        if self.request.registry.settings.get("always_add_user", "false") == "false":
            if (
                self.request.registry.settings.get(
                    "auth.register_users_via_web", "true"
                )
                == "true"
            ):
                raise HTTPNotFound
        return {"userid": user_id}


class EditUserView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.set_active_menu("users")

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        user_to_modify = self.request.matchdict["manageuser"]
        if self.user.id != user_id:
            raise HTTPNotFound
        if self.user.super != 1:
            raise HTTPNotFound
        if self.request.registry.settings.get("always_add_user", "false") == "false":
            if (
                self.request.registry.settings.get(
                    "auth.register_users_via_web", "true"
                )
                == "true"
            ):
                raise HTTPNotFound
        user_data = get_user_details(self.request, user_to_modify, False)
        if not user_data:
            raise HTTPNotFound
        if self.request.method == "POST":
            action = None
            user_details = self.get_post_dict()
            if "modify" in user_details.keys():
                action = "modify"
                if "user_id" in user_details.keys():
                    user_details.pop("user_id")

                email_valid = validators.email(user_details["user_email"])
                if not email_valid:
                    self.append_to_errors(self._("This email address is not valid"))
                else:
                    if email_exists(
                        self.request, user_to_modify, user_details["user_email"]
                    ):
                        self.append_to_errors(
                            self._(
                                "This email address already belongs to another account"
                            )
                        )
                    else:
                        if "user_super" in user_details.keys():
                            user_details["user_super"] = 1
                        else:
                            user_details["user_super"] = 0

                        if "user_active" in user_details.keys():
                            user_details["user_active"] = 1
                        else:
                            user_details["user_active"] = 0

                        if user_data["user_apikey"] != user_details["user_apikey"]:
                            log.warning(
                                "Administrator {} changed the API key of user {} from {} to {}".format(
                                    user_id,
                                    user_to_modify,
                                    user_data["user_apikey"],
                                    user_details["user_apikey"],
                                )
                            )
                        continue_edit = True
                        for plugin in p.PluginImplementations(p.IUser):
                            (data, continue_edit, error_message,) = plugin.before_edit(
                                self.request, user_to_modify, user_details
                            )
                            if not continue_edit:
                                self.append_to_errors(error_message)
                            else:
                                user_details = data
                            break  # Only one plugging will be called to extend before_create
                        if continue_edit:
                            res, message = update_profile(
                                self.request, user_to_modify, user_details
                            )
                            if res:
                                for plugin in p.PluginImplementations(p.IUser):
                                    plugin.after_edit(
                                        self.request,
                                        user_to_modify,
                                        user_details,
                                    )

                                user_index = get_user_index_manager(self.request)
                                user_index_data = user_details
                                user_index_data.pop("user_apikey", None)
                                user_index_data.pop("user_active", None)
                                user_index_data.pop("csrf_token", None)
                                user_index_data.pop("user_super", None)
                                user_index_data.pop("modify", None)

                                user_index.update_user(user_to_modify, user_index_data)
                                self.request.session.flash(
                                    self._("The user has been updated")
                                )
                                self.returnRawViewResult = True
                                return HTTPFound(
                                    location=self.request.route_url(
                                        "manage_users", userid=user_id
                                    )
                                )
                            else:
                                self.append_to_errors(message)

            if "changepass" in user_details.keys():
                action = "changepass"
                if user_details["user_password"] != "":
                    if user_details["user_password"] == user_details["user_password2"]:
                        encoded_password = encode_data(
                            self.request, user_details["user_password"]
                        )
                        updated, message = update_password(
                            self.request, user_to_modify, encoded_password
                        )
                        if updated:
                            log.warning(
                                "Tha administrator user {} changed the password for user {}".format(
                                    user_id, user_to_modify
                                )
                            )
                            self.returnRawViewResult = True
                            self.request.session.flash(
                                self._(
                                    "The password for {} was modified".format(
                                        user_data["user_name"]
                                    )
                                )
                            )
                            return HTTPFound(
                                location=self.request.route_url(
                                    "manage_users", userid=user_id
                                )
                            )
                        else:
                            self.append_to_errors(message)
                    else:
                        self.append_to_errors(
                            self._("The password and its confirmation are not the same")
                        )
                else:
                    self.append_to_errors(self._("The password cannot be empty"))
        else:
            action = None
        return {"userid": user_id, "userData": user_data, "action": action}


class AddUserView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.set_active_menu("users")

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        if self.user.id != user_id:
            raise HTTPNotFound
        if self.user.super != 1:
            raise HTTPNotFound
        if self.request.registry.settings.get("always_add_user", "false") == "false":
            if (
                self.request.registry.settings.get(
                    "auth.register_users_via_web", "true"
                )
                == "true"
            ):
                raise HTTPNotFound
        user_details = {}
        if self.request.method == "POST":
            user_details = self.get_post_dict()
            if re.match(r"^[A-Za-z0-9._]+$", user_details["user_id"]):
                if not user_exists(self.request, user_details["user_id"], False):
                    if user_details["user_password"] != "":
                        if (
                            user_details["user_password"]
                            == user_details["user_password2"]
                        ):
                            encoded_password = encode_data(
                                self.request, user_details["user_password"]
                            )

                            email_valid = validators.email(user_details["user_email"])
                            if not email_valid:
                                self.append_to_errors(
                                    self._("This email address is not valid")
                                )
                            else:
                                if email_exists(
                                    self.request,
                                    user_details["user_id"],
                                    user_details["user_email"],
                                ):
                                    self.append_to_errors(
                                        self._(
                                            "This email address already belongs to another account"
                                        )
                                    )
                                else:
                                    if "user_super" in user_details.keys():
                                        user_details["user_super"] = 1
                                    else:
                                        user_details["user_super"] = 0
                                    user_details["user_password"] = encoded_password
                                    user_details.pop("user_password2", None)
                                    user_details["user_cdate"] = datetime.datetime.now()
                                    user_details["user_apikey"] = str(uuid.uuid4())
                                    continue_creation = True
                                    for plugin in p.PluginImplementations(p.IUser):
                                        (
                                            data,
                                            continue_creation,
                                            error_message,
                                        ) = plugin.before_create(
                                            self.request, user_details
                                        )
                                        if not continue_creation:
                                            self.append_to_errors(error_message)
                                        else:
                                            user_details = data
                                        break  # Only one plugging will be called to extend before_create
                                    if continue_creation:
                                        added, error_message = register_user(
                                            self.request, user_details
                                        )
                                        if not added:
                                            self.append_to_errors(error_message)
                                        else:
                                            for plugin in p.PluginImplementations(
                                                p.IUser
                                            ):
                                                plugin.after_create(
                                                    self.request,
                                                    user_details,
                                                )
                                            # Store the notifications
                                            feed_manager = get_manager(self.request)
                                            # The user follows himself
                                            try:
                                                feed_manager.follow(
                                                    user_details["user_id"],
                                                    user_details["user_id"],
                                                )
                                            except Exception as e:
                                                log.warning(
                                                    "User {} was in FormShare at some point. Error: {}".format(
                                                        user_details["user_id"], str(e)
                                                    )
                                                )
                                            # The user join FormShare
                                            actor = Actor(
                                                user_details["user_id"], "person"
                                            )
                                            feed_object = Object(
                                                "formshare", "platform"
                                            )
                                            activity = Activity(
                                                "join", actor, feed_object
                                            )
                                            feed_manager.add_activity_feed(activity)

                                            # Add the user to the user index
                                            user_index = get_user_index_manager(
                                                self.request
                                            )
                                            user_index_data = user_details
                                            user_index_data.pop("user_apikey", None)
                                            user_index_data.pop("user_password", None)
                                            user_index_data.pop("user_active", None)
                                            user_index_data.pop("user_cdate", None)
                                            user_index_data.pop("csrf_token", None)
                                            user_index.add_user(
                                                user_details["user_id"], user_index_data
                                            )
                                            next_page = self.request.route_url(
                                                "manage_users", userid=user_id
                                            )
                                            plugin_next_page = ""
                                            for plugin in p.PluginImplementations(
                                                p.IRegistration
                                            ):
                                                plugin_next_page = (
                                                    plugin.after_register(
                                                        self.request, user_details
                                                    )
                                                )
                                                break  # Only one plugging will be called to extend after_register
                                            if plugin_next_page is not None:
                                                if plugin_next_page != "":
                                                    if plugin_next_page != next_page:
                                                        next_page = plugin_next_page
                                            self.request.session.flash(
                                                self._(
                                                    "The user was added successfully"
                                                )
                                            )
                                            self.returnRawViewResult = True
                                            return HTTPFound(location=next_page)
                        else:
                            self.append_to_errors(
                                self._(
                                    "The password and its confirmation are not the same"
                                )
                            )
                    else:
                        self.append_to_errors(self._("The password cannot be empty"))
                else:
                    self.append_to_errors(self._("This user already exists"))
            else:
                self.append_to_errors(
                    self._(
                        "The user id has invalid characters. Only underscore "
                        "and dot are allowed"
                    )
                )

        return {"userid": user_id, "userData": user_details}
