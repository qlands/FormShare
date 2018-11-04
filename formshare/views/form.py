from .classes import PrivateView


class FormDetailsView(PrivateView):
    def process_view(self):
        project_id = self.request.matchdict['projid']
        form_id = self.request.matchdict['formid']
        form_name = "Test for form 1"
        project_name = "Test of a project 1"
        self.request.h.setActiveMenu("projects")
        return {'projectID': project_id, 'projectName': project_name, 'formID': form_id, 'formName': form_name}
