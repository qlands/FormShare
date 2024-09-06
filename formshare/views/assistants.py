import os
import re
import uuid
import logging
from formshare.processes.logging.loggerclass import SecretLogger
import pandas as pd
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.response import FileResponse
import shutil
import formshare.plugins as p
import validators
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
    assistant_exist,
)
from formshare.views.classes import PrivateView
from sqlalchemy.exc import IntegrityError

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


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
            access_type = get_project_access_type(
                self.request, project_id, user_id, self.user.login
            )
            if access_type > 4:
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
            project_details["access_type"] = access_type
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

            if assistant_data["coll_id"].strip() != "":
                if assistant_data["coll_name"].strip() != "":
                    if re.match(r"^[A-Za-z0-9_]+$", assistant_data["coll_id"]):
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
                                        "assistants",
                                        userid=user_id,
                                        projcode=project_code,
                                    )
                                    added, message = add_assistant(
                                        self.request,
                                        user_id,
                                        project_id,
                                        assistant_data,
                                    )
                                    if added:
                                        for plugin in p.PluginImplementations(
                                            p.IAssistant
                                        ):
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
                                self._(
                                    "The password and its confirmation are not the same"
                                )
                            )
                    else:
                        self.append_to_errors(
                            self._(
                                "The assistant id has invalid characters. Only underscore "
                                "is allowed"
                            )
                        )
                else:
                    self.append_to_errors(
                        self._("You need to specify an assistant name")
                    )
            else:
                self.append_to_errors(self._("You need to specify an assistant id"))
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
            if "change_password" not in assistant_data.keys():
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
                            self.request,
                            user_id,
                            project_id,
                            assistant_id,
                            assistant_data,
                        )
                        if not continue_editing:
                            self.append_to_errors(error_message)
                        else:
                            assistant_data = data

                if continue_editing:
                    next_page = self.request.params.get(
                        "next"
                    ) or self.request.route_url(
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
                if assistant_data["coll_password"] != "":
                    if (
                        assistant_data["coll_password"]
                        == assistant_data["coll_password2"]
                    ):
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
                                self.returnRawViewResult = True
                                next_page = self.request.params.get(
                                    "next"
                                ) or self.request.route_url(
                                    "assistants", userid=user_id, projcode=project_code
                                )
                                return HTTPFound(next_page)
                            else:
                                self.append_to_errors(
                                    self._("Unable to change the password: ") + message
                                )
                    else:
                        self.append_to_errors(
                            self._("The password and its confirmation are not the same")
                        )
                else:
                    self.append_to_errors(self._("The password cannot be empty"))
                assistant_data = get_assistant_data(
                    self.request, project_id, assistant_id
                )
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


class DownloadCSVTemplate(PrivateView):
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

        csv_array = [
            {
                "coll_id": "required, unique and no special characters besides underscore (_)",
                "coll_name": "required",
                "coll_password": "required",
                "coll_email": "optional",
                "coll_telephone": "optional",
            }
        ]
        for row in range(2):
            data = {
                "coll_id": "collaborator_id_{}".format(row + 1),
                "coll_name": "Assistant number {}".format(row + 1),
                "coll_password": "Password for assistant number {}".format(row + 1),
                "coll_email": "",
                "coll_telephone": "",
            }
            csv_array.append(data)
        df = pd.DataFrame.from_dict(csv_array)

        repository_path = self.request.registry.settings["repository.path"]
        if not os.path.exists(repository_path):
            os.makedirs(repository_path)
        unique_id = str(uuid.uuid4())
        csv_file = os.path.join(repository_path, *["tmp", unique_id + ".csv"])
        df.to_csv(csv_file, index=False, header=True)

        response = FileResponse(
            csv_file, request=self.request, content_type="text/csv", cache_max_age=0
        )
        response.content_disposition = (
            'attachment; filename="assistant_for_' + project_code + '.csv"'
        )
        self.returnRawViewResult = True
        return response


class UploadAssistantsCSV(PrivateView):
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
            input_file = self.request.POST["csv_file"].file
            self.returnRawViewResult = True
            next_page = self.request.route_url(
                "assistants", userid=user_id, projcode=project_code
            )
            error = False
            message = ""
            assistants = []
            try:
                repository = self.request.registry.settings["repository.path"]
                paths = ["tmp"]
                temp_path = os.path.join(repository, *paths)
                if not os.path.exists(temp_path):
                    os.makedirs(temp_path)

                uid = str(uuid.uuid4())
                paths = ["tmp", uid + ".csv"]
                temp_file = os.path.join(repository, *paths)

                input_file.seek(0)
                with open(temp_file, "wb") as permanent_file:
                    shutil.copyfileobj(input_file, permanent_file)
                df = pd.read_csv(temp_file, dtype=str, keep_default_na=False)
                assistants = df.to_dict("records")
            except Exception as e:
                error = True
                log.error(
                    "Error while uploading files into project {}. Error: {}".format(
                        project_id, str(e)
                    )
                )
                message = self._(
                    "Error {} encountered. A log entry has been produced".format(
                        type(e).__name__
                    )
                )
            if not error:
                keys_are_correct = True
                for an_assistant in assistants:
                    if "coll_id" not in an_assistant.keys():
                        keys_are_correct = False
                    if "coll_name" not in an_assistant.keys():
                        keys_are_correct = False
                    if "coll_password" not in an_assistant.keys():
                        keys_are_correct = False
                if not keys_are_correct:
                    error = True
                    message = (
                        self._("The CSV must have the following columns:")
                        + " coll_id, coll_name, and coll_password"
                    )
                if not error:
                    for an_assistant in assistants:
                        if not re.match(r"^[A-Za-z0-9_]+$", an_assistant["coll_id"]):
                            error = True
                            message = self._(
                                'The assistant with id = "{}" is invalid. Only _ is allowed'.format(
                                    an_assistant["coll_id"]
                                )
                            )
                            break
                        if an_assistant["coll_name"].strip() == "":
                            error = True
                            message = self._(
                                "The assistant with id = {} has empty coll_name".format(
                                    an_assistant["coll_id"]
                                )
                            )
                            break
                        if an_assistant["coll_password"].strip() == "":
                            error = True
                            message = self._(
                                "The assistant with id = {} has empty coll_password".format(
                                    an_assistant["coll_id"]
                                )
                            )
                            break
                        if an_assistant.get("coll_email", "").strip() != "":
                            if not validators.email(
                                an_assistant.get("coll_email")
                            ) or not re.match(
                                r"^[A-Za-z0-9._@-]+$", an_assistant.get("coll_email")
                            ):
                                error = True
                                message = self._(
                                    "The assistant with id = {} has an invalid email".format(
                                        an_assistant["coll_id"]
                                    )
                                )
                                break
                        if an_assistant.get("coll_telephone", "").strip() != "":
                            if not re.match(
                                r"^[0-9+]+$", an_assistant.get("coll_telephone")
                            ):
                                error = True
                                message = self._(
                                    "The assistant with id = {} has an invalid telephone".format(
                                        an_assistant["coll_id"]
                                    )
                                )
                                break
                        if assistant_exist(
                            self.request, user_id, project_id, an_assistant
                        ):
                            error = True
                            message = self._(
                                "The assistant with id = {} is already part of your account. "
                                'You do not need to duplicate assistants, just mark them as "Share among projects" '
                                "to use them across projects.".format(
                                    an_assistant["coll_id"]
                                )
                            )
                            break
            if not error:
                all_in = []
                messages = []
                save_point = self.request.tm.savepoint()
                for an_assistant in assistants:
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
                                an_assistant,
                            )
                            if not continue_creation:
                                all_in.append(False)
                                messages.append(error_message)
                            else:
                                an_assistant = data
                                all_in.append(True)
                                messages.append("")
                    if continue_creation:
                        added, message = add_assistant(
                            self.request,
                            user_id,
                            project_id,
                            an_assistant,
                            False,
                            False,
                        )
                        if added:
                            for plugin in p.PluginImplementations(p.IAssistant):
                                plugin.after_creating_assistant(
                                    self.request,
                                    user_id,
                                    project_id,
                                    an_assistant,
                                )
                            all_in.append(True)
                            messages.append("")
                try:
                    self.request.dbsession.flush()
                except IntegrityError:
                    save_point.rollback()
                    error = True
                    message = self._("Your file has assistants with duplicated ids.")
                except Exception as e:
                    save_point.rollback()
                    error = True
                    log.error(
                        "Error {} while adding assistants from CSV in project {}".format(
                            str(e), project_id
                        )
                    )
                    message = self._("Unknown error. A log entry has been created")

                if not error:
                    self.request.session.flash(
                        self._("The file was uploaded successfully")
                    )
                    return HTTPFound(location=next_page)
                else:
                    self.add_error(message)
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})
            else:
                self.add_error(message)
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound
