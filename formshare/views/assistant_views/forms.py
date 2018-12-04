from formshare.views.classes import AssistantView
from formshare.processes.db import get_assistant_forms, get_project_forms, get_number_of_submissions_by_assistant,\
    get_project_details


class AssistantForms(AssistantView):
    def process_view(self):
        assistant_forms = get_assistant_forms(self.request, self.projectID, self.project_assistant, self.assistant.login)
        project_forms = get_project_forms(self.request, self.userID, self.projectID)
        forms = []
        for prj_form in project_forms:
            for ass_form in assistant_forms:
                if prj_form['form_id'] == ass_form['form_id']:
                    forms.append(prj_form)
        for form in forms:
            submissions, last, in_database, \
                in_logs, in_error = get_number_of_submissions_by_assistant(self.request, form['project_id'],
                                                                           form['form_id'],
                                                                           self.project_assistant,
                                                                           self.assistant.login)
            form['assistant_data'] = {"submissions": submissions, 'last': last, 'indb': in_database, 'inlogs': in_logs,
                                      'inerror': in_error}

        return {'activeUser': None, 'forms': forms, 'projectDetails': get_project_details(self.request, self.projectID)}
