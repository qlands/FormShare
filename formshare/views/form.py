from .classes import PrivateView
from formshare.processes.db import get_project_id_from_name, get_form_details, get_form_data, update_form, delete_form, \
    add_file_to_form
from formshare.processes.odk import upload_odk_form, get_odk_path, update_form_title
from formshare.processes.storage import store_file
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from formshare.processes.utilities import add_params_to_url
import validators
from cgi import FieldStorage
import pprint


class FormDetails(PrivateView):
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

            if form_data['form_target'] == '':
                form_data['form_target'] = 0

            uploaded, message = upload_odk_form(self.request, project_id, self.user.login, odk_path, form_data)

            if uploaded:
                next_page = self.request.route_url('form_details', userid=project_details['owner'],
                                                   projcode=project_code, formid=message)
                self.request.session.flash(self._('The form was added successfully'))
                return HTTPFound(next_page)
            else:
                next_page = self.request.params.get('next') or self.request.route_url('project_details',
                                                                                      userid=project_details['owner'],
                                                                                      projcode=project_code)
                params = {'error': self._('Unable to upload the form: ') + message}
                return HTTPFound(add_params_to_url(next_page, params))

        else:
            raise HTTPNotFound


class EditForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject['project_id'] == project_id:
            self.set_active_menu('assistants')
        else:
            self.set_active_menu('projects')
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
            current_form_data = get_form_data(self.request, project_id, form_id)
            form_data = self.get_post_dict()
            if 'form_accsub' in form_data.keys():
                form_data['form_accsub'] = 1
            else:
                form_data['form_accsub'] = 0

            if form_data['form_target'] == '':
                form_data['form_target'] = 0

            form_name_changed = False
            if current_form_data['form_name'] == form_data['form_name']:
                form_name_changed = True

            next_page = self.request.params.get('next') or self.request.route_url('form_details',
                                                                                  userid=user_id,
                                                                                  projcode=project_code,
                                                                                  formid=form_id)
            edited, message = update_form(self.request, project_id, form_id, form_data)
            if edited:
                if form_name_changed:
                    update_form_title(self.request, project_id, form_id, form_data['form_name'])
                self.request.session.flash(self._('The form was edited successfully'))
                self.returnRawViewResult = True
                return HTTPFound(next_page)
            else:
                self.errors.append(message)
        else:
            form_data = get_form_data(self.request, project_id, form_id)
        return {'formData': form_data, 'projectDetails': project_details, 'userid': user_id, 'formid': form_id}


class DeleteForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject['project_id'] == project_id:
            self.set_active_menu('assistants')
        else:
            self.set_active_menu('projects')
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

        form_data = get_form_data(self.request, project_id, form_id)
        if project_details["access_type"] == 1 or form_data["form_pubby"] == self.user.id:
            if self.request.method == 'POST':
                next_page = self.request.params.get('next') or self.request.route_url('project_details',
                                                                                      userid=user_id,
                                                                                      projcode=project_code)
                deleted, message = delete_form(self.request, project_id, form_id)
                if deleted:
                    self.request.session.flash(self._('The form was deleted successfully'))
                    self.returnRawViewResult = True
                    return HTTPFound(next_page)
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class AddFileToForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

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

        if project_details["access_type"] == 4:
            raise HTTPNotFound  # Don't edit a public or a project that I am just a member

        if self.request.method == 'POST':
            files = self.request.POST.getall('filetoupload')
            form_data = self.get_post_dict()
            processing_upload = False
            if isinstance(files[0], FieldStorage):
                processing_upload = True
            else:
                if not validators.url(form_data['form_file']):
                    next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                       formid=form_id, _query={'error': "The URL is invalid"})
                    return HTTPFound(location=next_page)

            self.returnRawViewResult = True

            next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code, formid=form_id)
            if not processing_upload:
                added, message = add_file_to_form(self.request, project_id, form_id, form_data['file_name'],
                                                  form_data['form_file'])
                if added:
                    self.request.session.flash(self._('The file was linked successfully'))
                    return HTTPFound(location=next_page)
                else:
                    next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                       formid=form_id, _query={'error': message})
                    return HTTPFound(location=next_page)
            else:
                error = False
                message = ""
                for file in files:
                    file_name = file.filename
                    added, message = add_file_to_form(self.request, project_id, form_id, file_name)
                    if added:
                        store_file(self.request, project_id, file_name, file.file)
                    else:
                        error = True
                        break
                if not error:
                    if len(files) == 1:
                        self.request.session.flash(self._('The file was uploaded successfully'))
                    else:
                        self.request.session.flash(self._('The files were uploaded successfully'))
                    return HTTPFound(location=next_page)
                else:
                    next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                       formid=form_id, _query={'error': message})
                    return HTTPFound(location=next_page)

        else:
            raise HTTPNotFound
