from formshare.views.classes import AssistantView
from formshare.processes.db import (
    get_assistant_forms_for_cleaning,
    get_project_forms,
    get_number_of_submissions_by_assistant,
    get_project_details,
    get_project_from_assistant,
    change_assistant_password,
    get_assistant_password,
    modify_assistant,
)
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from formshare.config.auth import check_assistant_login
import json
import qrcode
import zlib
import base64
from pyramid.response import FileResponse
import os
import uuid


class AssistantForms(AssistantView):
    def process_view(self):
        assistant_forms = get_assistant_forms_for_cleaning(
            self.request, self.projectID, self.project_assistant, self.assistant.login
        )
        project_forms = get_project_forms(self.request, self.userID, self.projectID)
        forms = []
        for prj_form in project_forms:
            for ass_form in assistant_forms:
                if prj_form["form_id"] == ass_form["form_id"]:
                    prj_form["privileges"] = ass_form["privileges"]
                    forms.append(prj_form)
        for form in forms:
            submissions, last, in_database, in_logs, in_error = get_number_of_submissions_by_assistant(
                self.request,
                form["project_id"],
                form["form_id"],
                self.project_assistant,
                self.assistant.login,
            )
            form["assistant_data"] = {
                "submissions": submissions,
                "last": last,
                "indb": in_database,
                "inlogs": in_logs,
                "inerror": in_error,
            }

        return {
            "activeUser": None,
            "forms": forms,
            "projectDetails": get_project_details(self.request, self.projectID),
        }


class ChangeMyAssistantPassword(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):
        if self.request.method == "POST":
            next_page = self.request.params.get("next") or self.request.route_url(
                "assistant_forms", userid=self.userID, projcode=self.projectCode
            )
            self.returnRawViewResult = True
            assistant_data = self.get_post_dict()
            if assistant_data["coll_password"] != "":
                if assistant_data["coll_password"] == assistant_data["coll_password2"]:
                    project_of_assistant = get_project_from_assistant(
                        self.request, self.userID, self.projectID, self.assistantID
                    )
                    if check_assistant_login(
                        project_of_assistant,
                        self.assistantID,
                        assistant_data["old_password"],
                        self.request,
                    ):

                        changed, message = change_assistant_password(
                            self.request,
                            project_of_assistant,
                            self.assistantID,
                            assistant_data["coll_password"],
                        )
                        if changed:
                            next_page = self.request.route_url(
                                "assistant_logout",
                                userid=self.userID,
                                projcode=self.projectCode,
                            )
                            return HTTPFound(next_page)
                        else:
                            self.add_error(
                                self._("Unable to change the password: ") + message
                            )
                            return HTTPFound(next_page, headers={"FS_error": "true"})
                    else:
                        self.add_error(self._("The old password is not correct"))
                        return HTTPFound(next_page, headers={"FS_error": "true"})
                else:
                    self.add_error(
                        self._("The password and its confirmation are not the same")
                    )
                    return HTTPFound(next_page, headers={"FS_error": "true"})
            else:
                self.add_error(self._("The password cannot be empty"))
                return HTTPFound(next_page, headers={"FS_error": "true"})

        else:
            raise HTTPNotFound


class ChangeMyAPIKey(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):
        if self.request.method == "POST":
            next_page = self.request.params.get("next") or self.request.route_url(
                "assistant_forms", userid=self.userID, projcode=self.projectCode
            )
            self.returnRawViewResult = True
            assistant_data = self.get_post_dict()

            project_of_assistant = get_project_from_assistant(
                self.request, self.userID, self.projectID, self.assistantID
            )

            modified, message = modify_assistant(
                self.request, project_of_assistant, self.assistantID, assistant_data
            )
            if modified:
                return HTTPFound(next_page)
            else:
                self.add_error(self._("Unable to change the password: ") + message)
                return HTTPFound(next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class GetQRCode(AssistantView):
    def process_view(self):
        form_id = self.request.matchdict["formid"]
        url = self.request.route_url(
            "project_details", userid=self.userID, projcode=self.projectCode
        )
        assistant_password = get_assistant_password(
            self.request, self.userID, self.projectID, self.assistantID
        )
        odk_settings = {
            "admin": {"change_server": True, "change_form_metadata": False},
            "general": {
                "change_server": True,
                "navigation": "buttons",
                "server_url": url,
                "username": self.assistantID,
                "password": assistant_password.decode(),
            },
        }
        qr_json = json.dumps(odk_settings).encode()
        zip_json = zlib.compress(qr_json)
        serialization = base64.encodebytes(zip_json)
        serialization = serialization.decode()
        serialization = serialization.replace("\n", "")
        img = qrcode.make(serialization)

        repository_path = self.request.registry.settings["repository.path"]
        if not os.path.exists(repository_path):
            os.makedirs(repository_path)
        unique_id = str(uuid.uuid4())
        temp_path = os.path.join(repository_path, *["odk", "tmp", unique_id])
        os.makedirs(temp_path)

        qr_file = os.path.join(temp_path, *[form_id + ".png"])
        img.save(qr_file)
        response = FileResponse(qr_file, request=self.request, content_type="image/png")
        response.content_disposition = 'attachment; filename="' + form_id + '.png"'
        self.returnRawViewResult = True
        return response
