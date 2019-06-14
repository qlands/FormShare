from formshare.views.classes import AssistantView
from formshare.processes.odk.processes import get_assistant_permissions_on_a_form
from formshare.processes.submission.api import get_tables_from_form, get_fields_from_table, \
    get_request_data_jqgrid, update_data, is_field_key
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from formshare.processes.db import get_form_data
import json
import logging
log = logging.getLogger(__name__)


class CleanInterface(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):
        
        form_id = self.request.matchdict['formid']
        
        if "table" in self.request.params.keys():
            table = self.request.params["table"]
        else:
            table = None
        if "fields" in self.request.params.keys():
            t_fields = self.request.params["fields"]
        else:
            t_fields = None
        form_data = get_form_data(self.request, self.projectID, form_id)
        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        
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
                    fields, checked = get_fields_from_table(self.request, self.projectID, form_id, table,
                                                            current_fields)
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

            if self.request.method == 'POST':
                if 'loadtable' in self.request.POST:
                    post_data = self.get_post_dict()
                    new_table = post_data["table"]
                    found = False
                    for aTable in tables:
                        if aTable["name"] == table:
                            found = True
                    self.returnRawViewResult = True
                    if found:
                        return HTTPFound(
                            location=self.request.route_url('clean', userid=self.userID, projcode=self.projectCode,
                                                            formid=form_id, _query={'table': new_table}))
                    else:
                        return HTTPFound(
                            location=self.request.route_url('clean', userid=self.userID, projcode=self.projectCode,
                                                            formid=form_id))

                if 'loadfields' in self.request.POST:
                    post_data = self.get_post_dict()
                    if 'fields' in post_data.keys():
                        new_fields = post_data["fields"]
                        if new_fields:
                            if isinstance(new_fields, list):
                                s_fields = '|'.join(new_fields)
                            else:
                                s_fields = new_fields
                            self.returnRawViewResult = True
                            return HTTPFound(
                                location=self.request.route_url('clean', userid=self.userID, projcode=self.projectCode,
                                                                formid=form_id,
                                                                _query={'table': table, 'fields': s_fields}))
                        else:
                            self.returnRawViewResult = True
                            return HTTPFound(
                                location=self.request.route_url('clean', userid=self.userID, projcode=self.projectCode,
                                                                formid=form_id, _query={'table': table}))
                    else:
                        self.returnRawViewResult = True
                        return HTTPFound(
                            location=self.request.route_url('clean', userid=self.userID, projcode=self.projectCode,
                                                            formid=form_id, _query={'table': table}))

            return {'canclean': permissions["enum_canclean"], 'formid': form_id, 'table': table, 'tables': tables,
                    'fields': fields, 'currtable': table, 'checked': checked,
                    'token': self.request.session.get_csrf_token(), 'strFields': str_fields, 'formData': form_data}
        else:
            raise HTTPNotFound()
        

class DataRequest(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        form_id = self.request.matchdict['formid']        
        table_name = self.request.matchdict['tablename']

        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        
        if permissions["enum_canclean"] == 1:
            if self.request.method == "POST":
                request_data = self.get_post_dict()
                call_back = self.request.params.get('callback')
                search_field = request_data.get('searchField', None)
                search_string = request_data.get('searchString', '')
                search_operator = request_data.get('searchOper', None)

                fields, checked = get_fields_from_table(self.request, self.projectID, form_id, table_name, [])
                field_names = []
                for field in fields:
                    field_names.append(field['name'])

                if request_data['sidx'] == '':
                    table_order = None
                else:
                    table_order = request_data['sidx']

                order_direction = request_data['sord']
                data = get_request_data_jqgrid(self.request, self.projectID, form_id, table_name, field_names,
                                               int(request_data['page']), int(request_data['rows']),
                                               table_order, order_direction, search_field, search_string,
                                               search_operator)

                return call_back + "(" + json.dumps(data) + ")"

                # draw = int(self.request.POST['draw'])
                # fields = []
                # start = 0
                # length = 0
                # order_index = 0
                # order_direction = ''
                # search_value = ""
                # for key in self.request.POST.keys():
                #     if key.find("columns[") >= 0 and key.find("[data]") >= 0:
                #         fields.append(self.request.POST[key])
                #     if key == "start":
                #         start = int(self.request.POST[key])
                #     if key == "length":
                #         length = int(self.request.POST[key])
                #     if key.find("order[") >= 0 and key.find("[column]") >= 0:
                #         order_index = int(self.request.POST[key])
                #     if key.find("order[") >= 0 and key.find("[dir]") >= 0:
                #         order_direction = self.request.POST[key]
                #     if key.find("search[") == 0 and key.find("[value]") >= 0:
                #         search_value = self.request.POST[key]
                # result = get_request_data(self.request, self.projectID, form_id, table_name, draw, fields, start,
                #                           length, order_index, order_direction, search_value)
                # self.returnRawViewResult = True
                # # log.debug(result)
                # return result
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
        

class PerformAction(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):

        form_id = self.request.matchdict['formid']

        table_name = self.request.matchdict['tablename']

        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)

        if permissions["enum_canclean"] == 1:
            self.returnRawViewResult = True
            if self.request.method == 'POST':
                post_data = self.get_post_dict()
                operator = post_data['oper']
                row_uuid = post_data['id']
                if operator == "edit":
                    post_data.pop('oper')
                    post_data.pop('id')
                    post_data.pop('csrf_token')
                    for key, value in post_data.items():
                        update_data(self.request, self.assistant.login, self.projectID, form_id, table_name,
                                    row_uuid, key, value)
                    return {}
                else:
                    raise HTTPNotFound()
            return {}
        else:
            raise HTTPNotFound()
