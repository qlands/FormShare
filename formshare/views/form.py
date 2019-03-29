from .classes import PrivateView
from formshare.processes.db import get_project_id_from_name, get_form_details, get_form_data, update_form, delete_form,\
    add_file_to_form, get_form_files, remove_file_from_form, get_all_assistants, add_assistant_to_form, \
    get_form_assistants, update_assistant_privileges, remove_assistant_from_form, get_project_groups, \
    add_group_to_form, get_form_groups, update_group_privileges, remove_group_from_form, get_form_xls_file, \
    set_form_status, get_assigned_assistants, get_form_directory, reset_form_repository, get_form_processing_products, \
    get_task_status
from formshare.processes.storage import store_file, delete_stream, delete_bucket
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
import os
from hashlib import md5
import logging
import simplekml
from formshare.processes.elasticsearch.repository_index import delete_dataset_index, get_number_of_datasets_with_gps
from pyramid.response import FileResponse
from formshare.processes.submission.api import get_submission_media_files, json_to_csv, get_gps_points_from_form, \
    generate_xlsx_file
from formshare.processes.odk.api import get_odk_path, upload_odk_form, update_form_title, retrieve_form_file, \
    update_odk_form, get_missing_support_files, import_external_data
from formshare.products import stop_task
from formshare.products import get_form_products
import uuid
import shutil


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

        form_data = get_form_details(self.request, user_id, project_id, form_id)
        if form_data is not None:
            form_files = get_form_files(self.request, project_id, form_id)
            if self.user is not None:
                assistants = get_all_assistants(self.request, project_id, self.user.login)
            else:
                assistants = []
            form_assistants = get_form_assistants(self.request, project_id, form_id)
            groups = get_project_groups(self.request, project_id)
            form_groups = get_form_groups(self.request, project_id, form_id)
            if form_data['form_reqfiles'] is not None:
                required_files = form_data['form_reqfiles'].split(',')
                missing_files = get_missing_support_files(self.request, project_id, form_id, required_files, form_files)
            else:
                missing_files = []
            if form_data['form_reptask'] is not None:
                res_code, error = get_task_status(self.request, form_data['form_reptask'])
                task_data = {'rescode': res_code, 'error': error}
            else:
                task_data = {'rescode': None, 'error': None}

            return {'projectDetails': project_details, 'formid': form_id, 'formDetails': form_data, 'userid': user_id,
                    'formFiles': form_files, 'assistants': assistants, 'formassistants': form_assistants,
                    'groups': groups, 'formgroups': form_groups,
                    'withgps': get_number_of_datasets_with_gps(self.request.registry.settings, user_id, project_code,
                                                               form_id), 'missingFiles': ", ".join(missing_files),
                    'taskdata': task_data, 'products': get_form_products(self.request, project_id, form_id),
                    'processing': get_form_processing_products(self.request, project_id, form_id,
                                                               form_data['form_reptask'])}
        else:
            raise HTTPNotFound


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
                self.add_error(self._('Unable to upload the form: ') + message)
                return HTTPFound(next_page)

        else:
            raise HTTPNotFound


class UploadNewVersion(PrivateView):
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

            updated, message = update_odk_form(self.request, project_id, form_id, odk_path, form_data)

            if updated:
                delete_dataset_index(self.request.registry.settings, user_id, project_code, form_id)
                next_page = self.request.route_url('form_details', userid=project_details['owner'],
                                                   projcode=project_code, formid=form_id)
                self.request.session.flash(self._('The ODK form was successfully updated'))
                return HTTPFound(next_page)
            else:
                next_page = self.request.route_url('form_details', userid=project_details['owner'],
                                                   projcode=project_code, formid=form_id)
                self.add_error(self._('Unable to upload the form: ') + message)
                return HTTPFound(next_page)

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
            if form_data is None:
                raise HTTPNotFound
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
        if form_data is None:
            raise HTTPNotFound
        if project_details["access_type"] == 1 or form_data["form_pubby"] == self.user.id:
            if self.request.method == 'POST':
                next_page = self.request.params.get('next') or self.request.route_url('project_details',
                                                                                      userid=user_id,
                                                                                      projcode=project_code)
                form_directory = get_form_directory(self.request, project_id, form_id)
                paths = ['forms', form_directory]
                odk_dir = get_odk_path(self.request)
                form_directory = os.path.join(odk_dir, *paths)
                deleted, message = delete_form(self.request, project_id, form_id)
                if deleted:
                    delete_dataset_index(self.request.registry.settings, user_id, project_code, form_id)
                    try:
                        shutil.rmtree(form_directory)
                    except Exception as e:
                        log.error("Error {} while removing form {} in project {}. Cannot delete directory {}".
                                  format(str(e), form_id, project_id, form_directory))
                    bucket_id = project_id + form_id
                    bucket_id = md5(bucket_id.encode('utf-8')).hexdigest()
                    delete_bucket(self.request, bucket_id)

                    self.request.session.flash(self._('The form was deleted successfully'))
                    self.returnRawViewResult = True
                    return HTTPFound(next_page)
                else:
                    self.returnRawViewResult = True
                    self.add_error(message)
                    return HTTPFound(next_page)
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class ActivateForm(PrivateView):
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == 'POST':
            next_page = self.request.params.get('next') or self.request.route_url('project_details',
                                                                                  userid=user_id,
                                                                                  projcode=project_code)
            changed, message = set_form_status(self.request, project_id, form_id, 1)
            if changed:
                self.request.session.flash(self._('The form was activated successfully'))
                self.returnRawViewResult = True
                return HTTPFound(next_page)
            else:
                self.returnRawViewResult = True
                self.add_error(message)
                return HTTPFound(next_page)
        else:
            raise HTTPNotFound


class DeActivateForm(PrivateView):
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == 'POST':
            next_page = self.request.params.get('next') or self.request.route_url('project_details',
                                                                                  userid=user_id,
                                                                                  projcode=project_code)
            changed, message = set_form_status(self.request, project_id, form_id, 0)
            if changed:
                self.request.session.flash(self._('The form was deactivated successfully'))
                self.returnRawViewResult = True
                return HTTPFound(next_page)
            else:
                self.returnRawViewResult = True
                self.add_error(message)
                return HTTPFound(next_page)
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == 'POST':
            files = self.request.POST.getall('filetoupload')
            form_data = self.get_post_dict()
            self.returnRawViewResult = True

            next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code, formid=form_id)

            error = False
            message = ""
            if "overwrite" in form_data.keys():
                overwrite = True
            else:
                overwrite = False
            for file in files:
                file_name = file.filename
                md5sum = md5(file.file.read()).hexdigest()
                added, message = add_file_to_form(self.request, project_id, form_id, file_name, overwrite, md5sum)
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
                self.add_error(message)
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

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
                self.add_error(message)
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
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
                        self.add_error(message)
                        next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                           formid=form_id)
                        return HTTPFound(location=next_page)

                else:
                    self.add_error("Error in submitted assistant")
                    next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                       formid=form_id)
                    return HTTPFound(location=next_page)
            else:
                self.add_error("The assistant cannot be empty")
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
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
                self.add_error(message)
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
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
                self.add_error(message)
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
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
                    self.add_error(message)
                    next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                       formid=form_id)
                    return HTTPFound(location=next_page)
            else:
                self.add_error("The group cannot be empty")
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
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
                self.add_error(message)
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == 'POST':
            removed, message = remove_group_from_form(self.request, project_id, form_id, group_id)
            if removed:
                self.request.session.flash(self._("The group was removed successfully"))
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
                return HTTPFound(location=next_page)
            else:
                self.add_error(message)
                next_page = self.request.route_url('form_details', userid=user_id, projcode=project_code,
                                                   formid=form_id)
                return HTTPFound(location=next_page)
        else:
            raise HTTPNotFound


class DownloadCSVData(PrivateView):
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
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        created, file = json_to_csv(self.request, project_id, form_id)
        if created:
            response = FileResponse(file, request=self.request, content_type='application/csv')
            response.content_disposition = 'attachment; filename="' + form_id + '.csv"'
            return response
        else:
            self.add_error(file)
            next_page = self.request.params.get('next') or self.request.route_url('form_details', userid=user_id,
                                                                                  projcode=project_code, formid=form_id)
            return HTTPFound(location=next_page)


class DownloadXLSData(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if project_details["access_type"] == 4:
            include_sensitive = False
        else:
            include_sensitive = True

        created, file = generate_xlsx_file(self.request, project_id, form_id, include_sensitive)
        if created:
            response = FileResponse(file, request=self.request,
                                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response.content_disposition = 'attachment; filename="' + form_id + '.xlsx"'
            return response
        else:
            self.add_error(file)
            next_page = self.request.params.get('next') or self.request.route_url('form_details', userid=user_id,
                                                                                  projcode=project_code, formid=form_id)
            return HTTPFound(location=next_page)


class DownloadXLSX(PrivateView):
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
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        xlsx_file = get_form_xls_file(self.request, project_id, form_id)
        response = FileResponse(xlsx_file, request=self.request, content_type='application/csv')
        response.content_disposition = 'attachment; filename="' + os.path.basename(xlsx_file) + '"'
        return response


class DownloadSubmissionFiles(PrivateView):
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
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        created, file = get_submission_media_files(self.request, project_id, form_id)
        if created:
            response = FileResponse(file, request=self.request, content_type='application/zip')
            response.content_disposition = 'attachment; filename="' + form_id + '.zip"'
            return response
        else:
            self.add_error(file)
            next_page = self.request.params.get('next') or self.request.route_url('form_details', userid=user_id,
                                                                                  projcode=project_code, formid=form_id)
            return HTTPFound(location=next_page)


class DownloadGPSPoints(PrivateView):
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
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        created, data = get_gps_points_from_form(self.request, user_id, project_code, form_id)
        return data


class DownloadKML(PrivateView):
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
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        created, data = get_gps_points_from_form(self.request, user_id, project_code, form_id)
        if created:
            kml = simplekml.Kml()
            for point in data["points"]:
                kml.newpoint(name=point['key'], coords=[(float(point['long']), float(point['lati']))])
            odk_dir = get_odk_path(self.request)
            uid = str(uuid.uuid4())
            tmp_file = os.path.join(odk_dir, *['tmp', uid + ".kml"])
            kml.save(tmp_file)
            response = FileResponse(tmp_file, request=self.request, content_type='application/vnd.google-earth.kml+xml')
            response.content_disposition = 'attachment; filename="' + form_id + '.kml"'
            return response
        else:
            raise HTTPNotFound


class ImportData(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
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
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if self.request.method == 'POST':
                odk_path = get_odk_path(self.request)

                form_post_data = self.get_post_dict()
                if 'file' in form_post_data.keys():
                    form_post_data.pop('file')
                parts = form_post_data['assistant'].split("@")
                import_type = int(form_post_data['import_type'])
                if 'ignore_xform' in form_post_data:
                    ignore_xform = True
                else:
                    ignore_xform = False

                imported, message = import_external_data(self.request, user_id, project_id, form_id, odk_path,
                                                         form_data['form_directory'], form_data['form_schema'],
                                                         parts[0], import_type, ignore_xform, form_post_data)
                if imported:
                    next_page = self.request.route_url('form_details', userid=user_id,
                                                       projcode=project_code, formid=form_id)
                    return HTTPFound(location=next_page)

            return {'projectDetails': project_details, 'formid': form_id, 'formDetails': form_data, 'userid': user_id,
                    'assistants': get_assigned_assistants(self.request, project_id, form_id)}
        else:
            raise HTTPNotFound


class StopTask(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        task_id = self.request.matchdict['taskid']
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == 'POST':
            next_page = self.request.params.get('next') or self.request.route_url('form_details',
                                                                                  userid=user_id,
                                                                                  projcode=project_code,
                                                                                  formid=form_id)
            stopped, message = stop_task(self.request, self.userID, project_id, form_id, task_id)
            if stopped:
                self.request.session.flash(self._('The process was stopped successfully'))
                self.returnRawViewResult = True
                return HTTPFound(next_page)
            else:
                self.request.session.flash(self._('FormShare was not able to stop the process') + "|error")
                self.returnRawViewResult = True
                return HTTPFound(next_page)
        else:
            raise HTTPNotFound


class StopRepository(PrivateView):
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == 'POST':
            task_id = form_data['form_reptask']
            next_page = self.request.params.get('next') or self.request.route_url('form_details',
                                                                                  userid=user_id,
                                                                                  projcode=project_code,
                                                                                  formid=form_id)
            stopped, message = stop_task(self.request, self.userID, project_id, form_id, task_id)
            if stopped:
                reset_form_repository(self.request, project_id, form_id)
                self.request.session.flash(self._('The process was stopped successfully'))
                self.returnRawViewResult = True
                return HTTPFound(next_page)
            else:
                self.request.session.flash(self._('FormShare was not able to stop the process') + "|error")
                self.returnRawViewResult = True
                return HTTPFound(next_page)
        else:
            raise HTTPNotFound
