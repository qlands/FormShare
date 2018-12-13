from formshare.views.classes import DashboardView
from pyramid.httpexceptions import HTTPNotFound
from formshare.processes.db import is_collaborator, get_project_assistants, get_project_collaborators, \
    get_user_details, get_project_forms, get_by_details, get_project_groups, get_project_files
from formshare.processes.elasticsearch.repository_index import get_dataset_stats_for_project, \
    get_number_of_datasets_with_gps_in_project


class UserDashBoardView(DashboardView):
    def process_view(self):
        user_id = self.request.matchdict['userid']

        project_data = {}
        if self.activeProject:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == self.activeProject['project_id']:
                    project_found = True
                    project_data = project
                    if self.user is not None:
                        project_data["user_collaborates"] = is_collaborator(self.request, self.user.login,
                                                                            self.activeProject['project_id'])
                    else:
                        project_data["user_collaborates"] = False
            if not project_found:
                raise HTTPNotFound
        
            assistants, more_assistants = get_project_assistants(self.request, self.activeProject['project_id'], 8)
            if self.user is not None:
                collaborators, more_collaborators = get_project_collaborators(self.request,
                                                                              self.activeProject['project_id'],
                                                                              self.user.login, 4)
            else:
                collaborators, more_collaborators = get_project_collaborators(self.request,
                                                                              self.activeProject['project_id'], None, 4)
            user_details = get_user_details(self.request, user_id)
            forms = get_project_forms(self.request, user_id, self.activeProject['project_id'])
            active_forms = 0
            inactive_forms = 0
            for form in forms:
                if form['form_accsub'] == 1:
                    active_forms = active_forms + 1
                else:
                    inactive_forms = inactive_forms + 1

            submissions, last, by, in_form = get_dataset_stats_for_project(self.request, user_id,
                                                                           self.activeProject['project_code'])

            bydetails = get_by_details(self.request, user_id, self.activeProject['project_id'], by)
            return {'projectData': project_data, 'userid': user_id, 'collaborators': collaborators,
                    'moreCollaborators': more_collaborators, 'assistants': assistants, 'moreAssistants': more_assistants,
                    'groups': get_project_groups(self.request, self.activeProject['project_id']),
                    'files': get_project_files(self.request, self.activeProject['project_id']), 'userDetails': user_details,
                    'forms': forms, 'activeforms': active_forms, 'inactiveforms': inactive_forms,
                    'submissions': submissions, 'last': last, 'by': by, 'bydetails': bydetails, 'infom': in_form,
                    'withgps': get_number_of_datasets_with_gps_in_project(self.request, user_id,
                                                                          self.activeProject['project_code'])}
        else:
            return {'projectData': None, 'userid': user_id, 'collaborators': [],
                    'moreCollaborators': 0, 'assistants': [], 'moreAssistants': 0,
                    'groups': [],
                    'files': [], 'userDetails': None,
                    'forms': [], 'activeforms': 0, 'inactiveforms': 0,
                    'submissions': 0, 'last': None, 'by': None, 'bydetails': None, 'infom': 0,
                    'withgps': 0}
