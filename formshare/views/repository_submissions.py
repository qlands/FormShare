from .classes import PrivateView
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from formshare.processes.db import get_form_data, get_project_id_from_name, get_project_owner, get_form_details
from formshare.config.auth import get_user_data
import json
from formshare.processes.submission.api import get_request_data_jqgrid, get_fields_from_table, delete_submission, \
    delete_all_submission


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

        form_data = get_form_details(self.request, user_id, project_id, form_id)
        if form_data is not None:
            if form_data['form_schema'] is None:
                raise HTTPNotFound
            if form_data['submissions'] <= 0:
                raise HTTPNotFound

            fields, checked = get_fields_from_table(self.request, project_id, form_id, 'maintable', [])
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

        if project_details["access_type"] >= 3:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if form_data['form_schema'] is None:
                raise HTTPNotFound
            if self.request.method == 'GET':
                raise HTTPNotFound
            request_data = self.get_post_dict()
            call_back = self.request.params.get('callback')

            search_field = request_data.get('searchField', None)
            search_string = request_data.get('searchString', '')
            search_operator = request_data.get('searchOper', None)

            fields, checked = get_fields_from_table(self.request, project_id, form_id, 'maintable', [])
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
                                           table_order, order_direction, search_field, search_string, search_operator)

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

        if project_details["access_type"] >= 3:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if form_data['form_schema'] is None:
                raise HTTPNotFound
            if self.request.method == 'GET':
                raise HTTPNotFound
            request_data = self.get_post_dict()
            if request_data.get('oper', None) == 'del':
                if request_data.get('id', '') != '':
                    delete_submission(self.request, user_id, project_id, form_id, request_data.get('id'), project_code)
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

        if project_details["access_type"] != 1:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if form_data['form_schema'] is None:
                raise HTTPNotFound
            if self.request.method == 'GET':
                raise HTTPNotFound
            request_data = self.get_post_dict()
            owner = get_project_owner(self.request, project_id)
            user_data = get_user_data(owner, self.request)
            if request_data.get('owner_email', '') != "":
                if user_data.email == request_data.get('owner_email', ''):
                    deleted, message = delete_all_submission(self.request, user_id, project_id, form_id, project_code)
                    if deleted:
                        return HTTPFound(
                            location=self.request.route_url("form_details", userid=project_details['owner'],
                                                            projcode=project_code, formid=form_id))
                    else:
                        self.add_error(self._('Unable to delete all submissions'))
                        return HTTPFound(
                            location=self.request.route_url("manageSubmissions", userid=project_details['owner'],
                                                            projcode=project_code, formid=form_id))
                else:
                    self.add_error(self._('The email is not correct'))
                    return HTTPFound(
                        location=self.request.route_url("manageSubmissions", userid=project_details['owner'],
                                                        projcode=project_code, formid=form_id))
            else:
                self.add_error(self._('You need to enter your email'))
                return HTTPFound(location=self.request.route_url("manageSubmissions", userid=project_details['owner'],
                                                                 projcode=project_code, formid=form_id))

        else:
            raise HTTPNotFound
