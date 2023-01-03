import logging
import formshare.plugins as p
from formshare.config.auth import get_user_data
from formshare.config.encdecdata import encode_data
from formshare.processes.db import update_profile, get_timezones, get_user_projects
from formshare.processes.db.user import update_password, update_api_key
from formshare.processes.elasticsearch.user_index import (
    get_user_index_manager,
    UserNotExistError,
)
from formshare.views.classes import ProfileView
from pyramid.httpexceptions import HTTPNotFound, HTTPFound

log = logging.getLogger("formshare")


class UserProfileView(ProfileView):
    def __init__(self, request):
        ProfileView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        if user_id != self.user.login:
            raise HTTPNotFound()
        return {"userProjects": get_user_projects(self.request, user_id, user_id)}


class EditProfileView(ProfileView):
    def __init__(self, request):
        ProfileView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        if user_id != self.user.login:
            raise HTTPNotFound()
        if self.request.method == "POST":
            data = self.get_post_dict()
            if "editprofile" in data.keys():
                if data["user_name"] != "":
                    if (
                        self.request.registry.settings["auth.allow_edit_profile_name"]
                        == "false"
                    ):
                        data["user_name"] = self.user.name
                    res, message = update_profile(self.request, user_id, data)
                    if res:
                        user_index = get_user_index_manager(self.request)
                        try:
                            user_index.update_user(
                                user_id, {"user_name": data["user_name"]}
                            )
                        except UserNotExistError:
                            try:
                                log.error(
                                    "User {} was not found in index. Trying to add it".format(
                                        user_id
                                    )
                                )
                                user_index.add_user(
                                    user_id,
                                    {
                                        "user_id": user_id,
                                        "user_name": data["user_name"],
                                    },
                                )
                            except Exception as e:
                                log.error(
                                    "Error in ElasticSearch user index: {}".format(
                                        str(e)
                                    )
                                )

                        self.reload_user_details()
                        self.request.session.flash(
                            self._("The profile has been updated")
                        )
                        self.returnRawViewResult = True
                        return HTTPFound(location=self.request.url)
                    else:
                        self.append_to_errors(message)
                else:
                    self.append_to_errors(self._("The name cannot be empty"))
            if "changepass" in data.keys():
                if (
                    self.request.registry.settings["auth.allow_user_change_password"]
                    == "true"
                ):
                    if data["old_pass"] != "":
                        if data["new_pass"] != "":
                            if data["new_pass"] == data["conf_pass"]:
                                user = get_user_data(user_id, self.request)
                                pass_ok, message = user.check_password(
                                    data["old_pass"], self.request
                                )
                                if pass_ok:
                                    plugin_password = False
                                    encoded_password = ""
                                    for plugin in p.PluginImplementations(
                                        p.IUserPassword
                                    ):  # pragma: no cover
                                        encoded_password = plugin.encrypt_user_password(
                                            self.request, data["new_pass"]
                                        )
                                        plugin_password = True
                                        break  # Only one plugin will encrypt the password
                                    if not plugin_password:
                                        encoded_password = encode_data(
                                            self.request, data["new_pass"]
                                        )
                                    updated, message = update_password(
                                        self.request, user_id, encoded_password
                                    )
                                    if updated:
                                        self.returnRawViewResult = True
                                        return HTTPFound(
                                            location=self.request.route_url("logout")
                                        )
                                    else:
                                        self.append_to_errors(message)
                                else:
                                    self.append_to_errors(
                                        self._("The old password is incorrect")
                                    )
                            else:
                                self.append_to_errors(
                                    self._(
                                        "The new password and its confirmation are not the same"
                                    )
                                )
                        else:
                            self.append_to_errors(
                                self._("You need to specify a new password")
                            )
                    else:
                        self.append_to_errors(
                            self._("You need to specify the old password")
                        )
                else:
                    raise HTTPNotFound()
            if "changeapikey" in data.keys():
                api_key = data.get("user_apikey", "").strip()
                api_secret = data.get("user_apisecret", "").strip()
                if api_secret != "" and api_key != "":
                    api_secret = encode_data(self.request, api_secret)
                    updated, message = update_api_key(
                        self.request, user_id, api_key, api_secret
                    )
                    if updated:
                        self.request.session.flash(
                            self._("The key and secret has been updated")
                        )
                        self.returnRawViewResult = True
                        return HTTPFound(location=self.request.url)
                    else:
                        self.append_to_errors(message)
                else:
                    self.append_to_errors(
                        self._("You need to specify the an API key and secret")
                    )
        return {"timezones": get_timezones(self.request)}
