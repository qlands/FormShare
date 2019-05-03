from .classes import PrivateView
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from formshare.processes.db import get_form_data, get_project_id_from_name
from formshare.processes.odk.api import get_tables_from_form, update_table_desc
from pyramid.response import Response
import json


class EditDictionaryTables(PrivateView):
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

            tables = get_tables_from_form(self.request, project_id, form_id)
            if self.request.method == 'POST':
                table_data = self.get_post_dict()
                self.returnRawViewResult = True
                response = Response(status=200)
                if table_data['table_desc'] != "":
                    if update_table_desc(self.request, project_id, form_id, table_data['table_name'],
                                         table_data['table_desc']):
                        response.text = json.dumps({'status': 'changed'})
                    else:
                        response.text = json.dumps({'status': 'not changed'})
                else:
                    response.text = json.dumps({'status': 'not changed'})

                response.content_type = 'application/json'
                return response

            return {'projectDetails': project_details, 'formid': form_id, 'formDetails': form_data, 'userid': user_id,
                    'tables': tables}
        else:
            raise HTTPNotFound
