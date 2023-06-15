import json
import formshare.plugins as plugins
from formshare.processes.db import (
    get_form_data,
    get_project_id_from_name,
    update_dictionary_tables,
    update_form,
    get_project_access_type,
    get_project_details,
)
from formshare.processes.submission.api import (
    get_tables_from_form,
    update_table_desc,
    get_fields_from_table,
    get_table_desc,
    update_field_metadata,
    update_field_sensitive,
)
from formshare.views.classes import PrivateView
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response
from pyramid.httpexceptions import HTTPFound


class EditDictionaryTables(PrivateView):
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
            if self.request.method == "GET":
                if access_type > 4:
                    raise HTTPNotFound
            else:
                if access_type >= 4:
                    raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if form_data["form_schema"] is None:
                raise HTTPNotFound
            else:
                if form_data["form_hasdictionary"] == 0:
                    updated = update_dictionary_tables(
                        self.request, project_id, form_id
                    )
                    if updated:
                        form_dict_data = {"form_hasdictionary": 1}
                        update_form(self.request, project_id, form_id, form_dict_data)
            if form_data["form_blocked"] != 0:
                raise HTTPNotFound

            tables = get_tables_from_form(self.request, project_id, form_id)
            if self.request.method == "POST":
                table_data = self.get_post_dict()
                self.returnRawViewResult = True
                response = Response(status=200)
                if table_data["table_desc"] != "":
                    if update_table_desc(
                        self.request,
                        project_id,
                        form_id,
                        table_data["table_name"],
                        table_data["table_desc"],
                    ):
                        response.text = json.dumps({"status": "changed"})
                    else:
                        response.text = json.dumps({"status": "not changed"})
                else:
                    response.text = json.dumps({"status": "not changed"})

                response.content_type = "application/json"
                return response

            return {
                "projectDetails": project_details,
                "formid": form_id,
                "formDetails": form_data,
                "userid": user_id,
                "tables": tables,
                "access_type": access_type,
            }
        else:
            raise HTTPNotFound


class EditDictionaryFields(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        table_id = self.request.matchdict["tableid"]
        if project_id is not None:
            access_type = get_project_access_type(
                self.request, project_id, user_id, self.user.login
            )
            if self.request.method == "GET":
                if access_type > 4:
                    raise HTTPNotFound
            else:
                if access_type >= 4:
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
            table_desc = get_table_desc(self.request, project_id, form_id, table_id)
            fields, checked = get_fields_from_table(
                self.request, project_id, form_id, table_id, []
            )
            if not fields:
                raise HTTPNotFound
            if self.request.method == "POST":
                table_data = self.get_post_dict()

                if table_data["post_type"] == "change_as_sensitive":
                    self.returnRawViewResult = True
                    response = Response(status=200)
                    if update_field_sensitive(
                        self.request,
                        project_id,
                        form_id,
                        table_id,
                        table_data["field_name"],
                        True,
                        table_data["field_protection"],
                    ):
                        response.text = json.dumps({"status": "changed"})
                    else:
                        response.text = json.dumps({"status": "not changed"})

                    response.content_type = "application/json"
                    return response

                if table_data["post_type"] == "change_as_not_sensitive":
                    self.returnRawViewResult = True
                    response = Response(status=200)
                    if update_field_sensitive(
                        self.request,
                        project_id,
                        form_id,
                        table_id,
                        table_data["field_name"],
                        False,
                    ):
                        response.text = json.dumps({"status": "changed"})
                    else:
                        response.text = json.dumps({"status": "not changed"})

                    response.content_type = "application/json"
                    return response

            return {
                "projectDetails": project_details,
                "formid": form_id,
                "formDetails": form_data,
                "userid": user_id,
                "fields": fields,
                "table_desc": table_desc,
                "table_name": table_id,
                "access_type": access_type,
            }
        else:
            raise HTTPNotFound


class EditDictionaryFieldMetadata(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def get_metadata_info(
        self, user_id, project_id, form_id, table_name, field_name, metadata_key
    ):
        if metadata_key == "name":
            return self._("Field name"), False
        if metadata_key == "desc":
            return self._("Field description"), True
        if metadata_key == "type":
            return self._("Field type"), False
        if metadata_key == "xmlcode":
            return self._("Code in ODK XML data"), False
        if metadata_key == "size":
            return self._("Size of the field"), False
        if metadata_key == "decsize":
            return self._("Decimal size of the field"), False
        if metadata_key == "sensitive":
            return self._("The field is sensitive"), False
        if metadata_key == "protection":
            return self._("Protection type of the sensitive field"), False
        if metadata_key == "encrypted":
            return self._("The field is encrypted"), False
        if metadata_key == "ontology":
            return self._("Ontological code"), True
        if metadata_key == "key":
            return self._("The field is a primary key"), False
        if metadata_key == "rlookup":
            return self._("The field is linked to a lookup table"), False
        if metadata_key == "rtable":
            return self._("Referenced table"), False
        if metadata_key == "rfield":
            return self._("Referenced field"), False

        for plugin in plugins.PluginImplementations(plugins.IFormDataColumns):
            return plugin.get_form_survey_property_info(
                self.request,
                user_id,
                project_id,
                form_id,
                table_name,
                field_name,
                metadata_key,
            )
        return metadata_key, False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        table_id = self.request.matchdict["tableid"]
        field_id = self.request.matchdict["fieldid"]
        if project_id is not None:
            access_type = get_project_access_type(
                self.request, project_id, user_id, self.user.login
            )
            if self.request.method == "GET":
                if access_type > 4:
                    raise HTTPNotFound
            else:
                if access_type >= 4:
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
            table_desc = get_table_desc(self.request, project_id, form_id, table_id)
            fields, checked = get_fields_from_table(
                self.request, project_id, form_id, table_id, []
            )
            if not fields:
                raise HTTPNotFound

            field = {}
            for a_field in fields:
                if a_field["name"] == field_id:
                    field = a_field
                    break

            if not field:
                raise HTTPNotFound

            field_metadata = []
            for a_key in field.keys():
                if (
                    a_key != "checked"
                    and a_key != "protection_desc"
                    and a_key != "editable"
                    and a_key != "lookupvalues"
                ):
                    key_description, key_editable = self.get_metadata_info(
                        user_id, project_id, form_id, table_id, field["name"], a_key
                    )
                    field_metadata.append(
                        {
                            "metadata_key": a_key,
                            "metadata_value": field[a_key],
                            "metadata_desc": key_description,
                            "metadata_editable": key_editable,
                        }
                    )

            if self.request.method == "POST":
                form_data = self.get_post_dict()
                update_dict = {}
                for a_key in form_data.keys():
                    if a_key in field.keys():
                        key_description, key_editable = self.get_metadata_info(
                            user_id, project_id, form_id, table_id, field_id, a_key
                        )
                        if key_editable:
                            update_dict[a_key] = form_data[a_key]
                if update_dict:
                    update_field_metadata(
                        self.request,
                        project_id,
                        form_id,
                        table_id,
                        field_id,
                        update_dict,
                    )
                self.returnRawViewResult = True
                return HTTPFound(location=self.request.url)

            return {
                "projectDetails": project_details,
                "formid": form_id,
                "formDetails": form_data,
                "userid": user_id,
                "field": field["name"],
                "table_desc": table_desc,
                "table_name": table_id,
                "access_type": access_type,
                "field_metadata": field_metadata,
            }
        else:
            raise HTTPNotFound
