from .classes import PrivateView
from formshare.views.classes import ProjectsView
from formshare.processes import add_project
from pyramid.httpexceptions import HTTPFound


class FormShareProjectView(PrivateView):
    def process_view(self):
        # self.request.h.setActiveMenu("projects")
        return {}


class ProjectDetailsView(PrivateView):
    def process_view(self):
        project_id = self.request.matchdict['projid']
        project_name = "Test of a project 1"
        # self.request.h.setActiveMenu("projects")
        return {'projectID': project_id, 'projectName': project_name}


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
                self.request.session.flash(self._('The project has been created'))
                self.returnRawViewResult = True
                return HTTPFound(location=next_page)
            else:
                self.errors.append(message)
        else:
            project_details = {}
        return {'projectDetails': project_details}
