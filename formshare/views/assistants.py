import re

from pyramid.httpexceptions import HTTPFound, HTTPNotFound

import formshare.plugins as p
from formshare.processes.db import (
    get_project_assistants,
    get_project_id_from_name,
    add_assistant,
    get_assistant_data,
    modify_assistant,
    delete_assistant,
    change_assistant_password,
    get_timezones,
    get_project_details,
    get_project_access_type,
)
from formshare.views.classes import PrivateView


class AssistantsListView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject.get("project_id", None) == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        assistants, more = get_project_assistants(self.request, project_id)
        return {
            "assistants": assistants,
            "projectDetails": project_details,
            "userid": user_id,
        }


class AddAssistantsView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject.get("project_id", None) == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        if self.request.method == "POST":
            assistant_data = self.get_post_dict()
            if "coll_prjshare" in assistant_data.keys():
                assistant_data["coll_prjshare"] = 1
            else:
                assistant_data["coll_prjshare"] = 0

            if assistant_data["coll_id"] != "":
                if re.match(r"^[A-Za-z0-9._]+$", assistant_data["coll_id"]):
                    if (
                        assistant_data["coll_password"]
                        == assistant_data["coll_password2"]
                    ):
                        assistant_data.pop("coll_password2")
                        if assistant_data["coll_password"] != "":
                            continue_creation = True
                            for plugin in p.PluginImplementations(p.IAssistant):
                                if continue_creation:
                                    (
                                        data,
                                        continue_creation,
                                        error_message,
                                    ) = plugin.before_creating_assistant(
                                        self.request,
                                        user_id,
                                        project_id,
                                        assistant_data,
                                    )
                                    if not continue_creation:
                                        self.append_to_errors(error_message)
                                    else:
                                        assistant_data = data
                            if continue_creation:
                                next_page = self.request.params.get(
                                    "next"
                                ) or self.request.route_url(
                                    "assistants", userid=user_id, projcode=project_code
                                )
                                added, message = add_assistant(
                                    self.request, user_id, project_id, assistant_data
                                )
                                if added:
                                    for plugin in p.PluginImplementations(p.IAssistant):
                                        plugin.after_creating_assistant(
                                            self.request,
                                            user_id,
                                            project_id,
                                            assistant_data,
                                        )

                                    self.request.session.flash(
                                        self._(
                                            "The assistant was added to this project"
                                        )
                                    )
                                    self.returnRawViewResult = True
                                    return HTTPFound(next_page)
                                else:
                                    self.append_to_errors(message)
                        else:
                            self.append_to_errors(
                                self._("The password cannot be empty")
                            )
                    else:
                        self.append_to_errors(
                            self._("The password and its confirmation are not the same")
                        )
                else:
                    self.append_to_errors(
                        self._(
                            "The user id has invalid characters. Only underscore "
                            "and dot are allowed"
                        )
                    )
            else:
                self.append_to_errors(self._("You need to specify a user id"))
        else:
            assistant_data = {}
        return {
            "assistantData": assistant_data,
            "projectDetails": project_details,
            "userid": user_id,
            "timezones": get_timezones(self.request),
        }


class EditAssistantsView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        assistant_id = self.request.matchdict["assistid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject.get("project_id", None) == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        if self.request.method == "POST":
            assistant_data = self.get_post_dict()
            if "coll_prjshare" in assistant_data.keys():
                assistant_data["coll_prjshare"] = 1
            else:
                assistant_data["coll_prjshare"] = 0

            if "coll_active" in assistant_data.keys():
                assistant_data["coll_active"] = 1
            else:
                assistant_data["coll_active"] = 0
            assistant_data.pop("coll_id")
            continue_editing = True
            for plugin in p.PluginImplementations(p.IAssistant):
                if continue_editing:
                    (
                        data,
                        continue_editing,
                        error_message,
                    ) = plugin.before_editing_assistant(
                        self.request, user_id, project_id, assistant_id, assistant_data
                    )
                    if not continue_editing:
                        self.append_to_errors(error_message)
                    else:
                        assistant_data = data

            if continue_editing:
                next_page = self.request.params.get("next") or self.request.route_url(
                    "assistants", userid=user_id, projcode=project_code
                )
                edited, message = modify_assistant(
                    self.request, project_id, assistant_id, assistant_data
                )
                if edited:
                    for plugin in p.PluginImplementations(p.IAssistant):
                        plugin.after_editing_assistant(
                            self.request,
                            user_id,
                            project_id,
                            assistant_id,
                            assistant_data,
                        )
                    self.request.session.flash(
                        self._("The assistant was edited successfully")
                    )
                    self.returnRawViewResult = True
                    return HTTPFound(next_page)
                else:
                    self.append_to_errors(message)
        else:
            assistant_data = get_assistant_data(self.request, project_id, assistant_id)
        return {
            "assistantData": assistant_data,
            "projectDetails": project_details,
            "userid": user_id,
            "timezones": get_timezones(self.request),
        }


class DeleteAssistant(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if self.request.method == "POST":
            self.returnRawViewResult = True
            assistant_id = self.request.matchdict["assistid"]
            continue_delete = True
            next_page = self.request.params.get("next") or self.request.route_url(
                "assistants", userid=user_id, projcode=project_code
            )
            for plugin in p.PluginImplementations(p.IAssistant):
                if continue_delete:
                    (
                        continue_delete,
                        error_message,
                    ) = plugin.before_deleting_assistant(
                        self.request, user_id, project_id, assistant_id
                    )
                    if not continue_delete:
                        self.add_error(error_message)

            if continue_delete:
                removed, message = delete_assistant(
                    self.request, project_id, assistant_id
                )
                if removed:
                    for plugin in p.PluginImplementations(p.IAssistant):
                        plugin.after_deleting_assistant(
                            self.request, user_id, project_id, assistant_id
                        )
                    self.request.session.flash(
                        self._("The assistant was deleted successfully")
                    )
                    return HTTPFound(next_page)
                else:
                    self.add_error(
                        "Unable to delete the assistant. Maybe the assistant already collected data? "
                        "You can deactivate it though."
                    )
                    return HTTPFound(next_page, headers={"FS_error": "true"})
            else:
                return HTTPFound(next_page, headers={"FS_error": "true"})

        else:
            raise HTTPNotFound


class ChangeAssistantPassword(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if self.request.method == "POST":
            self.returnRawViewResult = True
            assistant_data = self.get_post_dict()
            assistant_id = self.request.matchdict["assistid"]
            if assistant_data["coll_password"] != "":
                if assistant_data["coll_password"] == assistant_data["coll_password2"]:
                    continue_change = True
                    for plugin in p.PluginImplementations(p.IAssistant):
                        if continue_change:
                            (
                                continue_change,
                                error_message,
                            ) = plugin.before_assistant_password_change(
                                self.request,
                                user_id,
                                project_id,
                                assistant_id,
                                assistant_data["coll_password"],
                            )
                            if not continue_change:
                                self.add_error(error_message)
                    if continue_change:
                        changed, message = change_assistant_password(
                            self.request,
                            project_id,
                            assistant_id,
                            assistant_data["coll_password"],
                        )
                        if changed:
                            for plugin in p.PluginImplementations(p.IAssistant):
                                plugin.after_assistant_password_change(
                                    self.request,
                                    user_id,
                                    project_id,
                                    assistant_id,
                                    assistant_data["coll_password"],
                                )
                            self.request.session.flash(
                                self._("The password was changed successfully")
                            )
                            return HTTPFound(
                                self.request.route_url(
                                    "assistants", userid=user_id, projcode=project_code
                                )
                            )
                        else:
                            self.add_error(
                                self._("Unable to change the password: ") + message
                            )
                            return HTTPFound(
                                self.request.route_url(
                                    "assistants", userid=user_id, projcode=project_code
                                ),
                                headers={"FS_error": "true"},
                            )
                    else:
                        return HTTPFound(
                            self.request.route_url(
                                "assistants", userid=user_id, projcode=project_code
                            ),
                            headers={"FS_error": "true"},
                        )
                else:
                    self.add_error(
                        self._("The password and its confirmation are not the same")
                    )
                    return HTTPFound(
                        self.request.route_url(
                            "assistants", userid=user_id, projcode=project_code
                        ),
                        headers={"FS_error": "true"},
                    )
            else:
                self.add_error(self._("The password cannot be empty"))
                return HTTPFound(
                    self.request.route_url(
                        "assistants", userid=user_id, projcode=project_code
                    ),
                    headers={"FS_error": "true"},
                )

        else:
            raise HTTPNotFound
