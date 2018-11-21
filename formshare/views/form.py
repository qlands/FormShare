from .classes import PrivateView
from formshare.processes.db import get_project_id_from_name, get_form_details
from formshare.processes.odk import upload_odk_form, get_odk_path
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from formshare.processes.utilities import add_params_to_url


class FormDetailsView(PrivateView):
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

        form_data = get_form_details(self.request, project_id, form_id)

        return {'projectDetails': project_details, 'formid': form_id, 'formDetails': form_data, 'userid': user_id}


class AddNewForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound

        if self.request.method == 'POST':
            self.returnRawViewResult = True
            odk_path = get_odk_path(self.request)

            form_data = self.get_post_dict()
            if 'form_target' not in form_data.keys():
                form_data['form_target'] = 0
            form_data.pop('xlsx')

            uploaded, message = upload_odk_form(self.request, project_id, self.user.login, odk_path, form_data)
            next_page = self.request.params.get('next') or self.request.route_url('form_details',
                                                                                  userid=project_details['owner'],
                                                                                  projcode=project_code,
                                                                                  formid=message)
            if uploaded:
                self.request.session.flash(self._('The form was added successfully'))
                return HTTPFound(next_page)
            else:
                params = {'error': self._('Unable to delete the assistant: ') + message}
                return HTTPFound(add_params_to_url(next_page, params))

        else:
            raise HTTPNotFound
