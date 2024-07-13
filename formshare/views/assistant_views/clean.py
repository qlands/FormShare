import json
import logging
from pyramid.response import Response
from formshare.processes.db import get_form_data, is_form_blocked
from formshare.processes.odk.processes import get_assistant_permissions_on_a_form
from formshare.processes.submission.api import (
    get_tables_from_form,
    get_fields_from_table,
    get_request_data_jqgrid,
    update_data,
    get_primary_key_data,
    get_lookup_options,
    update_multiselect_data,
)
from formshare.processes.db.dictionary import (
    get_primary_keys,
    get_lookup_relation_fields,
)
from formshare.views.classes import AssistantView
from pyramid.httpexceptions import HTTPNotFound, HTTPFound, HTTPForbidden

log = logging.getLogger("formshare")


class CleanInterface(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):
        form_id = self.request.matchdict["formid"]

        if "table" in self.request.params.keys():
            table = self.request.params["table"]
        else:
            table = None
        if "fields" in self.request.params.keys():
            t_fields = self.request.params["fields"]
        else:
            t_fields = None
        form_data = get_form_data(self.request, self.projectID, form_id)
        permissions = get_assistant_permissions_on_a_form(
            self.request, self.userID, self.projectID, self.assistantID, form_id
        )

        if permissions["enum_canclean"] == 1:
            tables = get_tables_from_form(self.request, self.projectID, form_id)
            fields = []
            checked = 0
            current_fields = []
            str_fields = ""
            if t_fields is not None:
                current_fields = t_fields.split("|")

            if table is not None:
                found = False
                for aTable in tables:
                    if aTable["name"] == table:
                        found = True
                if found:
                    fields, checked = get_fields_from_table(
                        self.request,
                        self.projectID,
                        form_id,
                        table,
                        current_fields,
                    )
                    checked_array = []
                    if checked:
                        for field in fields:
                            if field["checked"]:
                                checked_array.append(field["name"])
                    else:
                        for field in fields:
                            checked_array.append(field["name"])
                    checked_array.append("rowuuid")
                    str_fields = "|".join(checked_array)
                else:
                    table = None

            if self.request.method == "POST":
                if "loadtable" in self.request.POST:
                    post_data = self.get_post_dict()
                    new_table = post_data["table"]
                    found = False
                    for aTable in tables:
                        if aTable["name"] == table:
                            found = True
                    self.returnRawViewResult = True
                    if found:
                        return HTTPFound(
                            location=self.request.route_url(
                                "clean",
                                userid=self.userID,
                                projcode=self.projectCode,
                                formid=form_id,
                                _query={"table": new_table},
                            )
                        )
                    else:
                        return HTTPFound(
                            location=self.request.route_url(
                                "clean",
                                userid=self.userID,
                                projcode=self.projectCode,
                                formid=form_id,
                            )
                        )

                if "loadfields" in self.request.POST:
                    post_data = self.get_post_dict()
                    if "fields" in post_data.keys():
                        new_fields = post_data["fields"]
                        if new_fields:
                            if isinstance(new_fields, list):
                                s_fields = "|".join(new_fields)
                            else:
                                s_fields = new_fields
                            self.returnRawViewResult = True
                            return HTTPFound(
                                location=self.request.route_url(
                                    "clean",
                                    userid=self.userID,
                                    projcode=self.projectCode,
                                    formid=form_id,
                                    _query={"table": table, "fields": s_fields},
                                )
                            )
                        else:
                            self.returnRawViewResult = True
                            return HTTPFound(
                                location=self.request.route_url(
                                    "clean",
                                    userid=self.userID,
                                    projcode=self.projectCode,
                                    formid=form_id,
                                    _query={"table": table},
                                )
                            )
                    else:
                        self.returnRawViewResult = True
                        return HTTPFound(
                            location=self.request.route_url(
                                "clean",
                                userid=self.userID,
                                projcode=self.projectCode,
                                formid=form_id,
                                _query={"table": table},
                            )
                        )

            return {
                "canclean": permissions["enum_canclean"],
                "formid": form_id,
                "table": table,
                "tables": tables,
                "fields": fields,
                "currtable": table,
                "checked": checked,
                "token": self.request.session.get_csrf_token(),
                "strFields": str_fields,
                "formData": form_data,
            }
        else:
            raise HTTPForbidden()


class DataRequest(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        form_id = self.request.matchdict["formid"]
        table_name = self.request.matchdict["tablename"]

        permissions = get_assistant_permissions_on_a_form(
            self.request, self.userID, self.projectID, self.assistantID, form_id
        )

        if permissions["enum_canclean"] == 1:
            if self.request.method == "POST":
                request_data = self.get_post_dict()
                call_back = self.request.params.get("callback")
                search_field = request_data.get("searchField", None)
                search_string = request_data.get("searchString", "")
                search_operator = request_data.get("searchOper", None)

                fields, checked = get_fields_from_table(
                    self.request, self.projectID, form_id, table_name, []
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
                    self.projectID,
                    form_id,
                    table_name,
                    field_names,
                    int(request_data["page"]),
                    int(request_data["rows"]),
                    table_order,
                    order_direction,
                    search_field,
                    search_string,
                    search_operator,
                )

                return call_back + "(" + json.dumps(data) + ")"
            else:
                raise HTTPNotFound()
        else:
            raise HTTPForbidden()


class PerformAction(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):
        form_id = self.request.matchdict["formid"]

        table_name = self.request.matchdict["tablename"]

        permissions = get_assistant_permissions_on_a_form(
            self.request, self.userID, self.projectID, self.assistantID, form_id
        )

        if is_form_blocked(self.request, self.projectID, form_id):
            raise HTTPNotFound()

        if permissions["enum_canclean"] == 1:
            self.returnRawViewResult = True
            if self.request.method == "POST":
                post_data = self.get_post_dict()
                operator = post_data["oper"]
                row_uuid = post_data["id"]
                if operator == "edit":
                    post_data.pop("oper")
                    post_data.pop("id")
                    post_data.pop("csrf_token", None)
                    for key, value in post_data.items():
                        update_data(
                            self.request,
                            self.assistant.login,
                            self.projectID,
                            form_id,
                            table_name,
                            row_uuid,
                            key,
                            value,
                        )
                    return {}
                else:
                    raise HTTPNotFound()
            self.request.response.headers["FS_error"] = "true"
            return {}
        else:
            raise HTTPForbidden()


class CleanMultiSelect(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):
        form_id = self.request.matchdict["formid"]
        table_name = self.request.matchdict["table"]
        multi_select_table_name = self.request.matchdict["mseltable"]
        row_uuid = self.request.matchdict["rowuuid"]
        row_uuid = row_uuid.strip()

        permissions = get_assistant_permissions_on_a_form(
            self.request, self.userID, self.projectID, self.assistantID, form_id
        )

        if permissions["enum_canclean"] == 1:
            if self.request.method == "GET":
                primary_keys = get_primary_keys(
                    self.request, self.projectID, form_id, table_name
                )
                primary_key_data = get_primary_key_data(
                    self.request,
                    self.projectID,
                    form_id,
                    table_name,
                    primary_keys,
                    row_uuid,
                )
                field_name, related_table, related_field = get_lookup_relation_fields(
                    self.request, self.projectID, form_id, multi_select_table_name
                )
                available_options, selected_options = get_lookup_options(
                    self.request,
                    self.projectID,
                    form_id,
                    related_table,
                    related_field,
                    multi_select_table_name,
                    field_name,
                    primary_key_data,
                )
                return {
                    "table": table_name,
                    "rowuuid": row_uuid,
                    "avaoptions": available_options,
                    "seloptions": selected_options,
                }
            else:
                self.returnRawViewResult = True
                self.checkCrossPost = False
                form_data = self.get_post_dict()

                selected_items = []
                to_items = form_data.get("to[]", [])
                if isinstance(to_items, str):
                    selected_items.append(to_items)
                else:
                    selected_items = to_items

                primary_keys = get_primary_keys(
                    self.request, self.projectID, form_id, table_name
                )
                primary_key_data = get_primary_key_data(
                    self.request,
                    self.projectID,
                    form_id,
                    table_name,
                    primary_keys,
                    row_uuid,
                )
                field_name, related_table, related_field = get_lookup_relation_fields(
                    self.request, self.projectID, form_id, multi_select_table_name
                )

                parts = multi_select_table_name.split("_msel_")
                print("****{}***".format(row_uuid))
                updated = update_multiselect_data(
                    self.request,
                    self.assistant.login,
                    self.projectID,
                    form_id,
                    row_uuid,
                    table_name,
                    parts[1],
                    multi_select_table_name,
                    field_name,
                    primary_key_data,
                    selected_items,
                )
                if updated:
                    status = 200
                    message = self._("The multiselect has been updated")
                else:
                    status = 400
                    message = self._("The multiselect has been updated")
                response = Response(
                    content_type="application/json",
                    status=200,
                    body=json.dumps(
                        {
                            "status": status,
                            "message": message,
                        }
                    ).encode(),
                )
                return response
        else:
            raise HTTPForbidden()
