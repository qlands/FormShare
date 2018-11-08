from .classes import PrivateView
from formshare.views.classes import ProjectsView
from formshare.processes import add_project
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from formshare.config.elasticfeeds import get_manager
from elasticfeeds.activity import Actor, Object, Activity
from formshare.processes import get_project_id_from_name, get_user_projects


class ProjectListView(ProjectsView):
    def process_view(self):
        # self.request.h.setActiveMenu("projects")
        return {}


class ProjectDetailsView(ProjectsView):
    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        project_data = {}
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
                    project_data = project
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        return {'projectData': project_data}


class AddProjectView(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        if self.request.method == 'POST':
            project_details = self.get_post_dict()
            if 'project_public' in project_details.keys():
                project_details['project_public'] = 1
            else:
                project_details['project_public'] = 0
            next_page = self.request.params.get('next') or self.request.route_url('dashboard', userid=self.user.login)
            added, message = add_project(self.request, self.user.login, project_details)
            if added:
                # Store the notifications
                feed_manager = get_manager(self.request)
                # Notify tha the user added a project
                actor = Actor(self.user.login, 'person')
                feed_object = Object(message, 'project')
                activity = Activity('add', actor, feed_object)
                feed_manager.add_activity_feed(activity)

                self.request.session.flash(self._('The project has been created'))
                self.returnRawViewResult = True
                return HTTPFound(location=next_page)
            else:
                self.errors.append(message)
        else:
            project_details = {}
        return {'projectDetails': project_details}
