from formshare.views.classes import PrivateView
from formshare.processes.db import get_project_assistants, get_project_id_from_name, add_assistant, \
    get_assistant_data, modify_assistant, delete_assistant, change_assistant_password
from pyramid.httpexceptions import HTTPFound, HTTPNotFound


class AssistantsListView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
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

        error = self.request.params.get('error')
        if error is not None:
            self.errors.append(error)

        assistants, more = get_project_assistants(self.request, project_id)
        return {'assistants': assistants, 'projectDetails': project_details, 'userid': user_id}


class AddAssistantsView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
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
            assistant_data = self.get_post_dict()
            if 'coll_prjshare' in assistant_data.keys():
                assistant_data['coll_prjshare'] = 1
            else:
                assistant_data['coll_prjshare'] = 0

            if assistant_data['coll_id'] != "":
                if assistant_data['coll_password'] == assistant_data['coll_password2']:
                    assistant_data.pop('coll_password2')
                    if assistant_data['coll_password'] != "":
                        next_page = self.request.params.get('next') or self.request.route_url('assistants',
                                                                                              userid=user_id,
                                                                                              projcode=project_code)
                        added, message = add_assistant(self.request, project_id, assistant_data)
                        if added:
                            self.request.session.flash(self._('The assistant was added to this project'))
                            self.returnRawViewResult = True
                            return HTTPFound(next_page)
                        else:
                            self.errors.append(message)
                    else:
                        self.errors.append(self._("The password cannot be empty"))
                else:
                    self.errors.append(self._("The password and its confirmation are not the same"))
            else:
                self.errors.append(self._("You need to specify an user name"))
        else:
            assistant_data = {}
        return {'assistantData': assistant_data, 'projectDetails': project_details, 'userid': user_id}


class EditAssistantsView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        assistant_id = self.request.matchdict['assistid']
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
            assistant_data = self.get_post_dict()
            if 'coll_prjshare' in assistant_data.keys():
                assistant_data['coll_prjshare'] = 1
            else:
                assistant_data['coll_prjshare'] = 0

            if 'coll_active' in assistant_data.keys():
                assistant_data['coll_active'] = 1
            else:
                assistant_data['coll_active'] = 0
            assistant_data.pop('coll_id')
            next_page = self.request.params.get('next') or self.request.route_url('assistants',
                                                                                  userid=user_id,
                                                                                  projcode=project_code)
            edited, message = modify_assistant(self.request, project_id, assistant_id, assistant_data)
            if edited:
                self.request.session.flash(self._('The assistant was edited successfully'))
                self.returnRawViewResult = True
                return HTTPFound(next_page)
            else:
                self.errors.append(message)
        else:
            assistant_data = get_assistant_data(self.request, project_id, assistant_id)
        return {'assistantData': assistant_data, 'projectDetails': project_details, 'userid': user_id}


class DeleteAssistant(PrivateView):
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
            assistant_id = self.request.matchdict['assistid']
            removed, message = delete_assistant(self.request, project_id, assistant_id)
            next_page = self.request.params.get('next') or self.request.route_url('assistants',
                                                                                  userid=user_id,
                                                                                  projcode=project_code)
            if removed:
                self.request.session.flash(self._('The assistant was deleted successfully'))
                return HTTPFound(next_page)
            else:
                self.request.session.flash(self._('Unable to delete the assistant: ') + message)
                return HTTPFound(next_page)

        else:
            raise HTTPNotFound


class ChangeAssistantPassword(PrivateView):
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
            assistant_data = self.get_post_dict()
            assistant_id = self.request.matchdict['assistid']
            if assistant_data['coll_password'] != '':
                if assistant_data['coll_password'] == assistant_data['coll_password2']:
                    changed, message = change_assistant_password(self.request, project_id, assistant_id,
                                                                 assistant_data['coll_password'])
                    if changed:
                        self.request.session.flash(self._('The password was changed successfully'))
                        return HTTPFound(self.request.route_url('assistants', userid=user_id, projcode=project_code))
                    else:
                        return HTTPFound(self.request.route_url('assistants', userid=user_id, projcode=project_code,
                                                                _query={'error': self._(
                                                                    'Unable to the password: ') + message}))
                else:
                    return HTTPFound(self.request.route_url('assistants', userid=user_id, projcode=project_code,
                                                            _query={'error': self._(
                                                                "The password and its confirmation are not the same")}))
            else:
                return HTTPFound(self.request.route_url('assistants', userid=user_id, projcode=project_code,
                                                        _query={'error': self._("The password cannot be empty")}))

        else:
            raise HTTPNotFound
