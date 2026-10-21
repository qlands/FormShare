from formshare.config.auth import get_user_data
from formshare.processes.db import (
    get_form_data,
    get_project_id_from_name,
    get_project_owner,
    get_form_details,
    get_all_assistants,
    get_assistant_by_api_key,
    get_project_access_type,
    get_project_details,
    get_form_xml_create_file,
)
from formshare.processes.db.encryption import encrypted_columns
from formshare.processes.elasticsearch.record_index import (
    get_project_and_form,
    get_table,
)
from formshare.processes.odk.processes import get_assistant_permissions_on_a_form
from formshare.processes.submission.api import (
    get_request_data_jqgrid,
    get_fields_from_table,
    delete_submission,
    delete_all_submission,
    update_record_with_id,
)
from formshare.views.classes import PrivateView, UpdateAPIView
from formshare.middleware.httpexceptions import HTTPNotFound, HTTPFound
from formshare.middleware.response import FileResponse


class ManageSubmissions(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            access_type = get_project_access_type(
                self.request, project_id, user_id, self.user.login
            )
            if access_type >= 3:
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
            project_details["access_type"] = access_type
        else:
            raise HTTPNotFound

        form_data = get_form_details(self.request, user_id, project_id, form_id)
        assistants = get_all_assistants(
            self.request, user_id, project_id, self.user.tenant
        )
        if form_data is not None:
            if form_data["form_schema"] is None:
                raise HTTPNotFound
            if form_data["indb"] <= 0:
                self.returnRawViewResult = True
                return HTTPFound(
                    location=self.request.route_url(
                        "form_details",
                        userid=project_details["owner"],
                        projcode=project_code,
                        formid=form_id,
                    )
                )

            fields, checked = get_fields_from_table(
                self.request, project_id, form_id, "maintable", []
            )
            return {
                "projectDetails": project_details,
                "formid": form_id,
                "formDetails": form_data,
                "userid": user_id,
                "fields": fields,
                "assistants": assistants,
            }
        else:
            raise HTTPNotFound


class DownloadDBXML(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
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

        form_data = get_form_details(self.request, user_id, project_id, form_id)
        if form_data is not None:
            if form_data["form_schema"] is None:
                raise HTTPNotFound
            create_file = get_form_xml_create_file(self.request, project_id, form_id)
            self.returnRawViewResult = True
            response = FileResponse(
                create_file,
                request=self.request,
                content_type="application/xml",
                cache_max_age=0,
            )
            response.content_disposition = 'attachment; filename="' + form_id + '.xml"'
            return response
        else:
            raise HTTPNotFound


class ReviewAudit(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
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

        form_data = get_form_details(self.request, user_id, project_id, form_id)
        if form_data is not None:
            if form_data["form_schema"] is None:
                raise HTTPNotFound

            fields = [
                {"name": "audit_date", "desc": "Date"},
                {"name": "audit_user", "desc": "User"},
                {"name": "audit_action", "desc": "Action"},
                {"name": "audit_table", "desc": "Table"},
                {"name": "audit_column", "desc": "Column"},
                {"name": "audit_oldvalue", "desc": "Previous value"},
                {"name": "audit_newvalue", "desc": "New value"},
                {"name": "audit_key", "desc": "Row ID"},
            ]

            return {
                "projectDetails": project_details,
                "formid": form_id,
                "formDetails": form_data,
                "userid": user_id,
                "fields": fields,
            }
        else:
            raise HTTPNotFound


class GetFormSubmissions(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 3
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if form_data["form_schema"] is None:
                raise HTTPNotFound
            if self.request.method == "GET":
                raise HTTPNotFound
            request_data = self.get_post_dict()

            search_field = request_data.get("searchField", None)
            search_string = request_data.get("searchString", "")
            search_operator = request_data.get("searchOper", None)

            fields, checked = get_fields_from_table(
                self.request, project_id, form_id, "maintable", []
            )
            field_names = []
            for field in fields:
                field_names.append(field["name"])

            if request_data["sidx"] == "":
                table_order = None
            else:
                table_order = request_data["sidx"]

            order_direction = request_data["sord"]
            data = get_request_data_jqgrid(
                self.request,
                project_id,
                form_id,
                "maintable",
                field_names,
                int(request_data["page"]),
                int(request_data["rows"]),
                table_order,
                order_direction,
                search_field,
                search_string,
                search_operator,
                "_xform_id_string",
                form_id,
            )

            return data
        else:
            raise HTTPNotFound


class GetFormAudit(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if form_data["form_schema"] is None:
                raise HTTPNotFound
            if self.request.method == "GET":
                raise HTTPNotFound
            request_data = self.get_post_dict()

            search_field = request_data.get("searchField", None)
            search_string = request_data.get("searchString", "")
            search_operator = request_data.get("searchOper", None)

            if self.request.registry.settings.get("use_timezones", "False") == "True":
                if self.selected_timezone == "formshare":
                    timezone = self.system_timezone
                else:
                    if self.selected_timezone == "user":
                        timezone = self.user_timezone["user_timezone"]
                    else:
                        timezone = project_details["project_timezone"]
                if timezone != self.system_timezone:
                    field_names = [
                        "CONVERT_TZ(`audit_date`,'{}','{}') as audit_date".format(
                            self.system_timezone, timezone
                        ),
                        "audit_user",
                        "audit_action",
                        "audit_table",
                        "audit_column",
                        "audit_oldvalue",
                        "audit_newvalue",
                        "audit_key",
                    ]
                else:
                    field_names = [
                        "audit_date",
                        "audit_user",
                        "audit_action",
                        "audit_table",
                        "audit_column",
                        "audit_oldvalue",
                        "audit_newvalue",
                        "audit_key",
                    ]
            else:
                field_names = [
                    "audit_date",
                    "audit_user",
                    "audit_action",
                    "audit_table",
                    "audit_column",
                    "audit_oldvalue",
                    "audit_newvalue",
                    "audit_key",
                ]

            table_order_is_none = False
            if request_data["sidx"] == "":
                table_order = "audit_date"
                table_order_is_none = True
            else:
                table_order = request_data["sidx"]

            if not table_order_is_none:
                order_direction = request_data["sord"]
            else:
                order_direction = "DESC"
            data = get_request_data_jqgrid(
                self.request,
                project_id,
                form_id,
                "audit_log",
                field_names,
                int(request_data["page"]),
                int(request_data["rows"]),
                table_order,
                order_direction,
                search_field,
                search_string,
                search_operator,
            )

            return data
        else:
            raise HTTPNotFound


class DeleteFormSubmission(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 3
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if form_data["form_schema"] is None:
                raise HTTPNotFound
            if form_data["form_blocked"] != 0:
                raise HTTPNotFound
            if self.request.method == "GET":
                raise HTTPNotFound
            request_data = self.get_post_dict()
            if request_data.get("oper", None) == "del":
                if request_data.get("id", "") != "":
                    delete_submission(
                        self.request,
                        user_id,
                        project_id,
                        form_id,
                        request_data.get("id"),
                        project_code,
                        self.userID,
                    )
            else:
                if "move_submission" in request_data.keys():
                    if request_data.get("rowuuid", "") != "":
                        assistant_data = request_data.get("coll_id", "").split("|")
                        if len(assistant_data) == 3:
                            if assistant_data[0] == "":
                                assistant_data[0] = None
                                assistant_data[1] = None
                            delete_submission(
                                self.request,
                                user_id,
                                project_id,
                                form_id,
                                request_data.get("rowuuid", ""),
                                project_code,
                                self.userID,
                                True,
                                assistant_data[2],
                            )
                    self.returnRawViewResult = True
                    return HTTPFound(
                        location=self.request.route_url(
                            "manageSubmissions",
                            userid=project_details["owner"],
                            projcode=project_code,
                            formid=form_id,
                        )
                    )
            return {}
        else:
            raise HTTPNotFound


class DeleteAllSubmissions(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 3
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if form_data["form_schema"] is None:
                raise HTTPNotFound
            if form_data["form_blocked"] != 0:
                raise HTTPNotFound
            if self.request.method == "GET":
                raise HTTPNotFound
            request_data = self.get_post_dict()
            owner = get_project_owner(self.request, project_id)
            user_data = get_user_data(owner, self.request)
            if user_data is None:
                user_data = get_user_data(self.user.login, self.request)
            if request_data.get("owner_email", "") != "":
                if user_data.email == request_data.get("owner_email", ""):
                    deleted, message = delete_all_submission(
                        self.request,
                        user_id,
                        project_id,
                        form_id,
                        self.userID,
                    )
                    if deleted:
                        return HTTPFound(
                            location=self.request.route_url(
                                "form_details",
                                userid=project_details["owner"],
                                projcode=project_code,
                                formid=form_id,
                            )
                        )
                    else:
                        self.add_error(self._("Unable to delete all submissions"))
                        return HTTPFound(
                            location=self.request.route_url(
                                "manageSubmissions",
                                userid=project_details["owner"],
                                projcode=project_code,
                                formid=form_id,
                            ),
                            headers={"FS_error": "true"},
                        )
                else:
                    self.add_error(self._("The email is not correct"))
                    return HTTPFound(
                        location=self.request.route_url(
                            "manageSubmissions",
                            userid=project_details["owner"],
                            projcode=project_code,
                            formid=form_id,
                        ),
                        headers={"FS_error": "true"},
                    )
            else:
                self.add_error(self._("You need to enter your email"))
                return HTTPFound(
                    location=self.request.route_url(
                        "manageSubmissions",
                        userid=project_details["owner"],
                        projcode=project_code,
                        formid=form_id,
                    ),
                    headers={"FS_error": "true"},
                )

        else:
            raise HTTPNotFound


class API1UpdateRepository(UpdateAPIView):
    def __init__(self, request):
        UpdateAPIView.__init__(self, request)

    def process_view(self):
        project_id, form_id = get_project_and_form(
            self.request.registry.settings,
            self.rowuuid,
        )
        schema, table = get_table(
            self.request.registry.settings,
            self.rowuuid,
        )
        if project_id is None:
            self.error = True
            self.error_code = 404
            return {
                "error": self._(
                    "The unique Row ID (rowuuid) does not point to a project"
                ),
                "error_type": "project_not_found",
            }

        user_id = get_project_owner(self.request, project_id)

        assistan_data = get_assistant_by_api_key(self.request, self.api_key)
        if not assistan_data:
            self.error = True
            self.error_code = 401
            return {
                "error": self._("Cannot find an assistant with such API key"),
                "error_type": "assistant_not_found",
            }

        permissions = get_assistant_permissions_on_a_form(
            self.request, user_id, project_id, assistan_data["coll_uuid"], form_id
        )
        if permissions["enum_canclean"] == 0:
            self.error_code = 401
            self.return_error(
                "unauthorized",
                self._(
                    "This API key don't have permission to clean "
                    "the form associated with the indicated Row ID"
                ),
            )
        if "rowuuid" in self.json.keys():
            # The API leaves encrypted fields alone: only the Encryption
            # plugin's cleaning grid changes them, sealed in a browser. The
            # rest of the update goes ahead, and the answer names what was
            # left out.
            encrypted = encrypted_columns(self.request, project_id, form_id, table)
            ignored = sorted(a_key for a_key in self.json.keys() if a_key in encrypted)
            data = {
                a_key: a_value
                for a_key, a_value in self.json.items()
                if a_key not in encrypted
            }
            if ignored and not set(data) - {"rowuuid", "rowindex", "apikey"}:
                return {
                    "status": "OK",
                    "message": self._(
                        "Nothing was updated: the API does not change encrypted fields"
                    ),
                    "ignored": ignored,
                }
            try:
                modified, error = update_record_with_id(
                    self.request,
                    assistan_data["coll_id"],
                    schema,
                    table,
                    self.json["rowuuid"],
                    data,
                )
                if modified:
                    result = {"status": "OK", "message": self._("Update completed")}
                    if ignored:
                        result["ignored"] = ignored
                    return result
                else:
                    self.error_code = 500
                    self.error = True
                    return {"error": error, "error_type": "update_error"}
            except Exception as e:
                self.error = True
                return {"error": str(e), "error_type": "update_error"}
