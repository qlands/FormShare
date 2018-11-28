from .classes import PrivateView
from formshare.processes.db import get_project_id_from_name, get_form_details, get_form_data, update_form, delete_form,\
    add_file_to_form, get_form_files, remove_file_from_form, get_all_assistants, add_assistant_to_form, \
    get_form_assistants, update_assistant_privileges, remove_assistant_from_form, get_project_groups, \
    add_group_to_form, get_form_groups, update_group_privileges, remove_group_from_form
from formshare.processes.odk import upload_odk_form, get_odk_path, update_form_title, retrieve_form_file
from formshare.processes.storage import store_file, delete_stream
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from formshare.processes.utilities import add_params_to_url
import validators
from cgi import FieldStorage
from hashlib import md5
import logging
log = logging.getLogger(__name__)


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

        error = self.request.params.get('error')
        if error is not None:
            self.errors.append(error)

        form_data = get_form_details(self.request, project_id, form_id)
        form_files = get_form_files(self.request, project_id, form_id)
        assistants = get_all_assistants(self.request, project_id, self.user.login)
        form_assistants = get_form_assistants(self.request, project_id, form_id)
        groups = get_project_groups(self.request, project_id)
        form_groups = get_form_groups(self.request, project_id, form_id)
        return {'projectDetails': project_details, 'formid': form_id, 'formDetails': form_data, 'userid': user_id,
                'formFiles': form_files, 'assistants': assistants, 'formassistants': form_assistants, 'groups': groups,
                'formgroups': form_groups}


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

            form_name_changed = True
            if current_form_data['form_name'] == form_data['form_name']:
                form_name_changed = False

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
                if "overwrite" in form_data.keys():
                    overwrite = True
                else:
                    overwrite = False
                for file in files:
                    file_name = file.filename
                    md5sum = md5(file.file.read()).hexdigest()
                    added, message = add_file_to_form(self.request, project_id, form_id, file_name, None, overwrite,
                                                      md5sum)
                    if added:
                        file.file.seek(0)
                        bucket_id = project_id + form_id
                        bucket_id = md5(bucket_id.encode('utf-8')).hexdigest()
                        store_file(self.request, bucket_id, file_name, file.file)
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


class RemoveFileFromForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        file_name = self.request.matchdict['filename']
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
            self.returnRawViewResult = True

            next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code, formid=form_id)
            removed, message = remove_file_from_form(self.request, project_id, form_id, file_name)
            if removed:
                bucket_id = project_id + form_id
                bucket_id = md5(bucket_id.encode('utf-8')).hexdigest()
                delete_stream(self.request, bucket_id, file_name)
                self.request.session.flash(self._('The files was removed successfully'))
            else:
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id, _query={'error': message})
                return HTTPFound(location=next_page)
            return HTTPFound(location=next_page)
        else:
            raise HTTPNotFound


class FormStoredFile(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        file_name = self.request.matchdict['filename']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
            if project_found:
                self.returnRawViewResult = True
                return retrieve_form_file(self.request, project_id, form_id, file_name)
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class AddAssistant(PrivateView):
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound

        if self.request.method == 'POST':
            assistant_data = self.get_post_dict()
            if assistant_data['coll_id'] != "":
                parts = assistant_data['coll_id'].split("|")
                privilege = assistant_data["privilege"]
                if len(parts) == 2:
                    added, message = add_assistant_to_form(self.request, project_id, form_id, parts[0], parts[1],
                                                           privilege)
                    if added:
                        self.request.session.flash(self._("The assistant was added successfully"))
                        next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                           formid=form_id)
                        return HTTPFound(location=next_page)
                    else:
                        next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                           formid=form_id,
                                                           _query={'error': message})
                        return HTTPFound(location=next_page)

                else:
                    next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                       formid=form_id,
                                                       _query={'error': "Error in submitted assistant"})
                    return HTTPFound(location=next_page)
            else:
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id, _query={'error': "The assistant cannot be empty"})
                return HTTPFound(location=next_page)

        else:
            raise HTTPNotFound


class EditAssistant(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        assistant_project_id = self.request.matchdict['projectid']
        assistant_id = self.request.matchdict['assistantid']
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
            assistant_data = self.get_post_dict()
            privilege = assistant_data["privilege"]
            updated, message = update_assistant_privileges(self.request, project_id, form_id, assistant_project_id,
                                                           assistant_id, privilege)
            if updated:
                self.request.session.flash(self._("The role was changed successfully"))
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
                return HTTPFound(location=next_page)
            else:
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id,
                                                   _query={'error': message})
                return HTTPFound(location=next_page)
        else:
            raise HTTPNotFound


class RemoveAssistant(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        assistant_project_id = self.request.matchdict['projectid']
        assistant_id = self.request.matchdict['assistantid']
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
            removed, message = remove_assistant_from_form(self.request, project_id, form_id, assistant_project_id,
                                                          assistant_id)
            if removed:
                self.request.session.flash(self._("The assistant was removed successfully"))
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
                return HTTPFound(location=next_page)
            else:
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id,
                                                   _query={'error': message})
                return HTTPFound(location=next_page)
        else:
            raise HTTPNotFound


class AddGroupToForm(PrivateView):
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound

        if self.request.method == 'POST':
            assistant_data = self.get_post_dict()
            if assistant_data['group_id'] != "":
                privilege = assistant_data["group_privilege"]
                added, message = add_group_to_form(self.request, project_id, form_id, assistant_data['group_id'],
                                                   privilege)
                if added:
                    self.request.session.flash(self._("The group was added successfully"))
                    next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                       formid=form_id)
                    return HTTPFound(location=next_page)
                else:
                    next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                       formid=form_id,
                                                       _query={'error': message})
                    return HTTPFound(location=next_page)
            else:
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id, _query={'error': "The group cannot be empty"})
                return HTTPFound(location=next_page)

        else:
            raise HTTPNotFound


class EditFormGroup(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        group_id = self.request.matchdict['groupid']
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
            assistant_data = self.get_post_dict()
            privilege = assistant_data["privilege"]
            updated, message = update_group_privileges(self.request, project_id, form_id, group_id, privilege)
            if updated:
                self.request.session.flash(self._("The role was changed successfully"))
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
                return HTTPFound(location=next_page)
            else:
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id,
                                                   _query={'error': message})
                return HTTPFound(location=next_page)
        else:
            raise HTTPNotFound


class RemoveGroupForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        group_id = self.request.matchdict['groupid']
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
            removed, message = remove_group_from_form(self.request, project_id, form_id, group_id)
            if removed:
                self.request.session.flash(self._("The group was removed successfully"))
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
                return HTTPFound(location=next_page)
            else:
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id,
                                                   _query={'error': message})
                return HTTPFound(location=next_page)
        else:
            raise HTTPNotFound
