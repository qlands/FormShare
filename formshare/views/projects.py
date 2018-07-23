from .classes import privateView

class projects_view(privateView):
    def processView(self):
        self.request.h.setActiveMenu("projects")
        return {}

class projectDetails_view(privateView):
    def processView(self):
        projectID = self.request.matchdict['projid']
        projectName = "Test of a project 1"
        self.request.h.setActiveMenu("projects")
        return {'projectID':projectID,'projectName':projectName}