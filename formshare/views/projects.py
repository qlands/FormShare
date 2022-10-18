import base64
import io
import json
import logging
import os
import re
import uuid
import zlib
from datetime import datetime

import qrcode
from elasticfeeds.activity import Actor, Object, Activity
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.response import FileResponse
from pyramid.response import Response

import formshare.plugins as p
from formshare.config.elasticfeeds import get_manager
from formshare.processes.color_hash import ColorHash
from formshare.processes.db import (
    add_project,
    modify_project,
    delete_project,
    is_collaborator,
    get_project_id_from_name,
    get_project_collaborators,
    get_project_assistants,
    get_project_groups,
    add_file_to_project,
    get_project_files,
    remove_file_from_project,
    get_project_forms,
    get_by_details,
    set_project_as_active,
    add_partner_to_project,
    get_project_partners,
    update_partner_options,
    remove_partner_from_project,
    get_timezones,
    get_project_access_type,
    get_project_details,
    get_extended_project_details,
    get_user_projects,
    get_forms_number,
)
from formshare.processes.elasticsearch.repository_index import (
    get_dataset_stats_for_project,
    delete_dataset_index_by_project,
    get_number_of_datasets_with_gps_in_project,
)
from formshare.processes.storage import (
    store_file,
    get_stream,
    response_stream,
    delete_stream,
    delete_bucket,
)
from formshare.processes.submission.api import get_gps_points_from_project
from formshare.views.classes import ProjectsView

log = logging.getLogger("formshare")


class ProjectStoredFileView(ProjectsView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        file_name = self.request.matchdict["filename"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            stream = get_stream(self.request, project_id, file_name)
            if stream is not None:
                self.returnRawViewResult = True
                response = Response()
                return response_stream(stream, file_name, response)
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class ProjectListView(ProjectsView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        if user_id != self.user.login:
            raise HTTPNotFound()

        next_url = self.request.params.get("next", self.request.url)
        user_projects = get_user_projects(self.request, self.userID, self.userID)

        return {"userProjects": user_projects, "next": next_url}


class ProjectDetailsView(ProjectsView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            access_type = get_project_access_type(
                self.request, project_id, user_id, self.user.login
            )
            if access_type > 4:
                raise HTTPNotFound
            project_data = get_extended_project_details(
                self.request, user_id, project_id
            )
            project_data["access_type"] = access_type
        else:
            raise HTTPNotFound

        project_data["user_collaborates"] = is_collaborator(
            self.request, self.user.login, project_id
        )

        assistants, more_assistants = get_project_assistants(
            self.request, project_id, 8
        )

        collaborators, more_collaborators = get_project_collaborators(
            self.request, project_id, self.user.login, 4
        )

        forms = get_project_forms(self.request, user_id, project_id)
        active_forms = 0
        inactive_forms = 0
        for form in forms:
            if form["form_accsub"] == 1:
                active_forms = active_forms + 1
            else:
                inactive_forms = inactive_forms + 1
        submissions, last, by, in_form = get_dataset_stats_for_project(
            self.request.registry.settings, project_id
        )
        bydetails = get_by_details(self.request, user_id, project_id, by)
        return {
            "projectData": project_data,
            "projectDetails": project_data,
            "userid": user_id,
            "collaborators": collaborators,
            "moreCollaborators": more_collaborators,
            "assistants": assistants,
            "moreAssistants": more_assistants,
            "groups": get_project_groups(self.request, project_id),
            "files": get_project_files(self.request, project_id),
            "forms": forms,
            "activeforms": active_forms,
            "inactiveforms": inactive_forms,
            "submissions": submissions,
            "last": last,
            "by": by,
            "bydetails": bydetails,
            "infom": in_form,
            "project_partners": get_project_partners(self.request, project_id),
            "withgps": get_number_of_datasets_with_gps_in_project(
                self.request.registry.settings, project_id
            ),
        }


class AddProjectView(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        if user_id != self.user.login:
            raise HTTPNotFound()

        if self.request.method == "POST":
            project_details = self.get_post_dict()
            project_details["project_public"] = 0

            if "project_case" in project_details.keys():
                project_details["project_case"] = 1
            else:
                project_details["project_case"] = 0

            if "project_formlist_auth" in project_details.keys():
                project_details["project_formlist_auth"] = 1
            else:
                project_details["project_formlist_auth"] = 0

            if project_details["project_abstract"] == "":
                project_details["project_abstract"] = None

            if project_details["project_code"] != "":
                project_details["project_code"] = project_details[
                    "project_code"
                ].lower()
                if re.match(r"^[A-Za-z0-9_]+$", project_details["project_code"]):
                    next_page = self.request.params.get(
                        "next"
                    ) or self.request.route_url("dashboard", userid=self.user.login)

                    continue_creation = True
                    for plugin in p.PluginImplementations(p.IProject):
                        if continue_creation:
                            (
                                data,
                                continue_creation,
                                error_message,
                            ) = plugin.before_creating_project(
                                self.request, self.user.login, project_details
                            )
                            if not continue_creation:
                                self.append_to_errors(error_message)
                            else:
                                project_details = data

                    if continue_creation:
                        if project_details["project_hexcolor"] == "":
                            project_details["project_hexcolor"] = ColorHash(
                                project_details["project_code"]
                            ).hex

                        added, message = add_project(
                            self.request, self.user.login, project_details
                        )
                        if added:
                            for plugin in p.PluginImplementations(p.IProject):
                                plugin.after_creating_project(
                                    self.request, self.user.login, project_details
                                )

                            # Generate the QR image
                            url = self.request.route_url(
                                "project_details",
                                userid=self.user.login,
                                projcode=project_details["project_code"],
                            )
                            odk_settings = {
                                "admin": {
                                    "change_server": True,
                                    "change_form_metadata": False,
                                },
                                "general": {
                                    "change_server": True,
                                    "navigation": "buttons",
                                    "server_url": url,
                                },
                            }
                            qr_json = json.dumps(odk_settings).encode()
                            zip_json = zlib.compress(qr_json)
                            serialization = base64.encodebytes(zip_json)
                            serialization = serialization.decode()
                            serialization = serialization.replace("\n", "")
                            img = qrcode.make(serialization)
                            img_bytes = io.BytesIO()
                            img.save(img_bytes, "PNG")
                            img_bytes.seek(0)
                            store_file(
                                self.request,
                                message,
                                project_details["project_code"] + ".png",
                                img_bytes,
                            )
                            modify_project(
                                self.request,
                                message,
                                {
                                    "project_code": project_details["project_code"],
                                    "project_image": project_details["project_code"]
                                    + ".png",
                                },
                            )

                            # Store the notifications
                            feed_manager = get_manager(self.request)
                            # Notify tha the user added a project
                            actor = Actor(self.user.login, "person")
                            feed_object = Object(message, "project")
                            activity = Activity("add", actor, feed_object)
                            feed_manager.add_activity_feed(activity)

                            self.request.session.flash(
                                self._("The project has been created")
                            )
                            self.returnRawViewResult = True
                            return HTTPFound(location=next_page)
                        else:
                            self.append_to_errors(message)
                else:
                    self.append_to_errors(
                        self._(
                            "The project code has invalid characters. Only underscore (_) is allowed"
                        )
                    )
            else:
                self.append_to_errors(self._("The project code cannot be empty"))
        else:
            project_details = {
                "project_public": 0,
                "project_case": 0,
                "project_formlist_auth": 1,
            }
        return {
            "projectDetails": project_details,
            "timezones": get_timezones(self.request),
        }


class EditProjectView(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.privateOnly = True

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
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        total_forms = get_forms_number(self.request, project_id)
        project_details["total_forms"] = total_forms

        if self.request.method == "POST":
            project_details = self.get_post_dict()
            project_details["project_public"] = 0

            if "project_case" in project_details.keys():
                project_details["project_case"] = 1
            else:
                if total_forms == 0:
                    project_details["project_case"] = 0

            if "project_formlist_auth" in project_details.keys():
                project_details["project_formlist_auth"] = 1
            else:
                project_details["project_formlist_auth"] = 0

            project_details["project_code"] = project_code

            if project_details["project_hexcolor"] == "":
                project_details["project_hexcolor"] = ColorHash(
                    project_details["project_code"]
                ).hex

            if project_details["project_abstract"] == "":
                project_details["project_abstract"] = None

            if project_details["project_name"] != "":
                next_page = self.request.params.get("next") or self.request.url
                modified, message = modify_project(
                    self.request, project_id, project_details
                )
                if modified:
                    # Store the notifications
                    feed_manager = get_manager(self.request)
                    # Notify tha the user edited the project
                    actor = Actor(self.user.login, "person")
                    feed_object = Object(project_id, "project")
                    activity = Activity("edit", actor, feed_object)
                    feed_manager.add_activity_feed(activity)

                    self.request.session.flash(self._("The project has been modified"))
                    self.returnRawViewResult = True
                    return HTTPFound(location=next_page)
                else:
                    self.append_to_errors(message)
            else:
                self.append_to_errors(self._("The name cannot be empty"))

        return {
            "projectDetails": project_details,
            "timezones": get_timezones(self.request),
        }


class ActivateProjectView(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                > 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if self.request.method == "POST":
            next_page = self.request.params.get("next") or self.request.route_url(
                "projects", userid=self.user.login
            )
            self.returnRawViewResult = True
            activated, message = set_project_as_active(
                self.request, self.user.login, project_id
            )
            if activated:
                self.request.session.flash(self._("The active project has changed"))
                return HTTPFound(location=next_page)
            else:
                self.add_error(self._("Error activating project: ") + message)
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class DeleteProjectView(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                != 1
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if self.request.method == "POST":
            next_page = self.request.params.get("next") or self.request.route_url(
                "projects", userid=self.user.login
            )

            self.returnRawViewResult = True
            deleted, message = delete_project(self.request, self.user.login, project_id)
            if deleted:
                # Delete the bucket
                delete_bucket(self.request, project_id)
                # Store the notifications
                feed_manager = get_manager(self.request)
                # Notify tha the user deleted the project
                actor = Actor(self.user.login, "person")
                feed_object = Object(project_id, "project")
                activity = Activity("delete", actor, feed_object)
                feed_manager.add_activity_feed(activity)
                # Deletes the project from the dataset index
                delete_dataset_index_by_project(
                    self.request.registry.settings, project_id
                )
                self.request.session.flash(
                    self._("The project was deleted successfully")
                )
                return HTTPFound(location=next_page)
            else:
                self.add_error(self._("Unable to delete the project: ") + message)
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class AddFileToProject(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

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
            files = self.request.POST.getall("filetoupload")
            form_data = self.get_post_dict()
            self.returnRawViewResult = True

            next_page = self.request.route_url(
                "project_details", userid=user_id, projcode=project_code
            )

            error = False
            message = ""
            if "overwrite" in form_data.keys():
                overwrite = True
            else:
                overwrite = False
            for file in files:
                try:
                    if os.path.isabs(file.filename):
                        file_name = os.path.basename(file.filename)
                    else:
                        file_name = file.filename
                    slash_index = file_name.find("\\")
                    if slash_index >= 0:
                        file_name = file_name[slash_index + 1 :]
                    added, message = add_file_to_project(
                        self.request, project_id, file_name, overwrite
                    )
                    if added:
                        file.file.seek(0)
                        store_file(self.request, project_id, file_name, file.file)
                    else:
                        error = True
                        break
                except Exception as e:
                    log.error(
                        "Error while uploading files into project {}. Error: {}".format(
                            project_id, str(e)
                        )
                    )
                    error = True
                    if len(files) == 1:
                        if files[0] == b"":
                            message = self._("No files were attached")
                        else:
                            message = self._(
                                "Error {} encountered. A log entry has been produced".format(
                                    type(e).__name__
                                )
                            )

                    else:
                        message = self._(
                            "Error {} encountered. A log entry has been produced".format(
                                type(e).__name__
                            )
                        )

            if not error:
                if len(files) == 1:
                    self.request.session.flash(
                        self._("The file was uploaded successfully")
                    )
                else:
                    self.request.session.flash(
                        self._("The files were uploaded successfully")
                    )
                return HTTPFound(location=next_page)
            else:
                self.add_error(message)
                next_page = self.request.route_url(
                    "project_details", userid=user_id, projcode=project_code
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class RemoveFileFromProject(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        file_name = self.request.matchdict["filename"]

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

            next_page = self.request.route_url(
                "project_details", userid=user_id, projcode=project_code
            )
            removed, message = remove_file_from_project(
                self.request, project_id, file_name
            )
            if removed:
                delete_stream(self.request, project_id, file_name)
                self.request.session.flash(
                    self._("The files were removed successfully")
                )
                return HTTPFound(location=next_page)
            else:
                self.add_error(message)
                next_page = self.request.route_url(
                    "project_details", userid=user_id, projcode=project_code
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class DownloadProjectGPSPoints(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        query_from = self.request.params.get("from")
        if query_from is None:
            query_from = 0
        query_size = self.request.params.get("size")
        if query_size is None:
            query_size = 10000
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                > 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        created, data = get_gps_points_from_project(
            self.request, project_id, query_from, query_size
        )
        return data


class GetProjectQRCode(ProjectsView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]

        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                > 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        url = self.request.route_url(
            "project_details", userid=self.userID, projcode=project_code
        )

        odk_settings = {
            "admin": {"change_server": True, "change_form_metadata": False},
            "general": {
                "change_server": True,
                "navigation": "buttons",
                "server_url": url,
            },
            "project": {
                "name": project_details["project_name"],
                "icon": project_details["project_icon"],
                "color": project_details["project_hexcolor"],
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

        qr_file = os.path.join(temp_path, *[project_id + ".png"])
        img.save(qr_file)
        response = FileResponse(qr_file, request=self.request, content_type="image/png")
        response.content_disposition = 'attachment; filename="' + project_code + '.png"'
        self.returnRawViewResult = True
        return response


class AddPartnerToProject(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

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
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        if self.request.method == "POST":
            form_data = self.get_post_dict()
            self.returnRawViewResult = True
            if form_data.get("partner_id", "") != "":
                if "time_bound" in form_data.keys():
                    form_data["time_bound"] = True
                else:
                    form_data["time_bound"] = False

                access_from = None
                access_to = None
                if form_data["time_bound"]:
                    try:
                        access_from = datetime.strptime(
                            form_data["access_from"], "%Y-%m-%d"
                        )
                        access_to = datetime.strptime(
                            form_data["access_to"], "%Y-%m-%d"
                        )
                    except ValueError:
                        self.add_error(self._("Invalid dates"))
                        next_page = self.request.route_url(
                            "project_details", userid=user_id, projcode=project_code
                        )
                        return HTTPFound(
                            location=next_page, headers={"FS_error": "true"}
                        )
                if access_from is not None:
                    if access_to < access_from:
                        self.add_error(self._("Invalid dates"))
                        next_page = self.request.route_url(
                            "project_details", userid=user_id, projcode=project_code
                        )
                        return HTTPFound(
                            location=next_page, headers={"FS_error": "true"}
                        )
                form_data["access_from"] = access_from
                form_data["access_to"] = access_to
                form_data["project_id"] = project_id
                form_data["access_date"] = datetime.now()
                form_data["granted_by"] = project_details["owner"]

                added, message = add_partner_to_project(self.request, form_data)
                if added:
                    next_page = self.request.route_url(
                        "project_details", userid=user_id, projcode=project_code
                    )
                    self.request.session.flash(
                        self._("The partner was successfully linked to this project")
                    )
                    return HTTPFound(location=next_page)
                else:
                    self.add_error(message)
                    next_page = self.request.route_url(
                        "project_details", userid=user_id, projcode=project_code
                    )
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})
            else:
                self.add_error(self._("You need to indicate a partner"))
                next_page = self.request.route_url(
                    "project_details", userid=user_id, projcode=project_code
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})

        else:
            raise HTTPNotFound


class EditPartnerOptions(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        partner_id = self.request.matchdict["partnerid"]
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
            form_data = self.get_post_dict()
            self.returnRawViewResult = True
            if "time_bound" in form_data.keys():
                form_data["time_bound"] = True
            else:
                form_data["time_bound"] = False

            access_from = None
            access_to = None
            if form_data["time_bound"]:
                try:
                    access_from = datetime.strptime(
                        form_data["access_from"], "%Y-%m-%d"
                    )
                    access_to = datetime.strptime(form_data["access_to"], "%Y-%m-%d")
                except ValueError:
                    self.add_error(self._("Invalid dates"))
                    next_page = self.request.route_url(
                        "project_details", userid=user_id, projcode=project_code
                    )
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})
            if access_from is not None:
                if access_to < access_from:
                    self.add_error(self._("Invalid dates"))
                    next_page = self.request.route_url(
                        "project_details", userid=user_id, projcode=project_code
                    )
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})
            form_data["access_from"] = access_from
            form_data["access_to"] = access_to

            updated, message = update_partner_options(
                self.request, project_id, partner_id, form_data
            )
            if updated:
                next_page = self.request.route_url(
                    "project_details", userid=user_id, projcode=project_code
                )
                self.request.session.flash(
                    self._("The partner was successfully updated")
                )
                return HTTPFound(location=next_page)
            else:
                self.add_error(message)
                next_page = self.request.route_url(
                    "project_details", userid=user_id, projcode=project_code
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})

        else:
            raise HTTPNotFound


class RemovePartnerFromProject(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        partner_id = self.request.matchdict["partnerid"]
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
            removed, message = remove_partner_from_project(
                self.request, project_id, partner_id
            )
            if removed:
                next_page = self.request.route_url(
                    "project_details", userid=user_id, projcode=project_code
                )
                self.request.session.flash(
                    self._("The partner was successfully removed from this project")
                )
                return HTTPFound(location=next_page)
            else:
                self.add_error(message)
                next_page = self.request.route_url(
                    "project_details", userid=user_id, projcode=project_code
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound
