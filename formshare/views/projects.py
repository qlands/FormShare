from .classes import privateView
from formshare.views.classes import projectsView
from formshare.processes import add_project
from pyramid.httpexceptions import HTTPFound

class projects_view(privateView):
    def processView(self):
        # self.request.h.setActiveMenu("projects")
        return {}

class projectDetails_view(privateView):
    def processView(self):
        projectID = self.request.matchdict['projid']
        projectName = "Test of a project 1"
        # self.request.h.setActiveMenu("projects")
        return {'projectID':projectID,'projectName':projectName}

class project_add_view(projectsView):
    def __init__(self, request):
        projectsView.__init__(self, request)
        self.privateOnly = True
    def processView(self):
        if self.request.method == 'POST':
            projectDetails = self.getPostDict()
            if 'project_public' in projectDetails.keys():
                projectDetails['project_public'] = 1
            else:
                projectDetails['project_public'] = 0
            nextPage = self.request.params.get('next') or self.request.route_url('dashboard',userid=self.user.login)
            added,message = add_project(self.request,self.user.login,projectDetails)
            if added:
                self.request.session.flash(self._('The project has been created'))
                self.returnRawViewResult = True
                return HTTPFound(location=nextPage)
            else:
                self.errors.append(message)
        else:
            projectDetails = {}
        return {'projectDetails':projectDetails}