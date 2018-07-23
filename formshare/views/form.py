from .classes import privateView

class formDetails_view(privateView):
    def processView(self):
        projectID = self.request.matchdict['projid']
        formID = self.request.matchdict['formid']
        formName = "Test for form 1"
        projectName = "Test of a project 1"
        self.request.h.setActiveMenu("projects")
        return {'projectID': projectID, 'projectName': projectName,'formID':formID,'formName':formName}