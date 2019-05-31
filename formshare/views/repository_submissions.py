from .classes import PrivateView
from pyramid.httpexceptions import HTTPNotFound
from formshare.processes.db import get_form_data, get_project_id_from_name
import json
from formshare.processes.submission.api import get_request_data_jqgrid, get_fields_from_table


class ManageSubmissions(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        project_details = {}
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
                    project_details = project
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if project_details["access_type"] >= 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if form_data['form_schema'] is None:
                raise HTTPNotFound

            fields, checked = get_fields_from_table(self.request, project_id, form_id, 'maintable', [], True)
            return {'projectDetails': project_details, 'formid': form_id, 'formDetails': form_data, 'userid': user_id,
                    'fields': fields}
        else:
            raise HTTPNotFound


class GetFormSubmissions(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        project_details = {}
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
                    project_details = project
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if project_details["access_type"] >= 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if form_data['form_schema'] is None:
                raise HTTPNotFound
            if self.request.method == 'GET':
                raise HTTPNotFound
            request_data = self.get_post_dict()
            print("********************55")
            print(request_data)
            print("********************55")
            call_back = self.request.params.get('callback')

            fields, checked = get_fields_from_table(self.request, project_id, form_id, 'maintable', [], True)
            field_names = []
            for field in fields:
                field_names.append(field['name'])

            if request_data['sidx'] == '':
                table_order = None
            else:
                table_order = request_data['sidx']

            order_direction = request_data['sord']
            data = get_request_data_jqgrid(self.request, project_id, form_id, 'maintable', field_names,
                                           int(request_data['page']), int(request_data['rows']),
                                           table_order, order_direction, '')

            return call_back + "(" + json.dumps(data) + ")"
        else:
            raise HTTPNotFound


class DeleteFormSubmission(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        project_details = {}
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
                    project_details = project
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if project_details["access_type"] >= 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if form_data['form_schema'] is None:
                raise HTTPNotFound
            if self.request.method == 'GET':
                raise HTTPNotFound
            request_data = self.get_post_dict()
            print("********************55")
            print(request_data)
            print("********************55")

            return {}
        else:
            raise HTTPNotFound