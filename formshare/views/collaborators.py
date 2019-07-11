from formshare.views.classes import PrivateView
from formshare.processes.db import get_project_collaborators, get_project_id_from_name, \
    remove_collaborator_from_project, add_collaborator_to_project, set_collaborator_role
from pyramid.httpexceptions import HTTPFound, HTTPNotFound


class CollaboratorsListView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if not self.activeProject:
            self.returnRawViewResult = True
            return HTTPFound(self.request.route_url('dashboard', userid=self.user.id))
        if self.activeProject['project_id'] == project_id:
            self.set_active_menu('collaborators')
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

        if project_details["access_type"] > 2:
            raise HTTPNotFound

        if self.request.method == 'POST':
            collaborator_details = self.get_post_dict()
            if "add_collaborator" in collaborator_details.keys():
                if "collaborator" in collaborator_details.keys():
                    added, message = add_collaborator_to_project(self.request, project_id,
                                                                 collaborator_details['collaborator'])
                    if added:
                        self.request.session.flash(self._('The collaborator was added to this project'))
                        self.returnRawViewResult = True
                        return HTTPFound(self.request.route_url('collaborators', userid=user_id, projcode=project_code))
                    else:
                        self.errors.append(message)
            if "change_role" in collaborator_details.keys():
                changed, message = set_collaborator_role(self.request, project_id,
                                                         collaborator_details['collaborator_id'],
                                                         collaborator_details['role_collaborator'])
                if changed:
                    self.request.session.flash(self._('The role was changed'))
                    self.returnRawViewResult = True
                    return HTTPFound(self.request.route_url('collaborators', userid=user_id, projcode=project_code))
                else:
                    self.errors.append(message)

        collaborators, more = get_project_collaborators(self.request, project_id)
        return {'collaborators': collaborators, 'projectDetails': project_details, 'userid': user_id}


class RemoveCollaborator(PrivateView):
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

        if project_details["access_type"] > 2:
            raise HTTPNotFound
        if self.request.method == 'POST':
            self.returnRawViewResult = True
            collaborator_id = self.request.matchdict['collid']
            removed, message = remove_collaborator_from_project(self.request, project_id, collaborator_id)
            next_page = self.request.route_url('collaborators', userid=user_id, projcode=project_code)
            if removed:
                self.request.session.flash(self._('The collaborator was removed successfully'))
                return HTTPFound(next_page)
            else:
                self.request.session.flash(self._('Unable to remove the collaborator: ') + message)
                return HTTPFound(next_page)

        else:
            raise HTTPNotFound
