from formshare.views.classes import AssistantView
from formshare.processes.odk.processes import get_assistant_permissions_on_a_form, get_errors_by_assistant, \
    get_submission_error_details, get_submission_details, checkout_submission, cancel_checkout, cancel_revision, \
    fix_revision, fail_revision, disregard_revision, cancel_disregard_revision, get_error_description_from_file, \
    get_number_of_errors_by_assistant
from formshare.processes.odk.api import generate_diff, get_submission_file, store_new_version, get_html_from_diff, \
    restore_from_revision, push_revision
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from webhelpers2.html import literal
import os
import uuid
import json
from formshare.processes.db import get_form_data, get_project_from_assistant
import logging
import paginate
log = logging.getLogger("formshare")


class JSONList(AssistantView):
    def process_view(self):
        form_id = self.request.matchdict['formid']
        project_code = self.request.matchdict['projcode']
        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        form_data = get_form_data(self.request, self.projectID, form_id)
        if permissions["enum_cansubmit"] == 1 or permissions["enum_canclean"] == 1:
            current_page = int(self.request.params.get("page", "1"))
            status = self.request.params.get("status", "all")
            status_code = None
            if status == "fixed":
                status_code = 0
            if status == "error":
                status_code = 1
            if status == "checkout":
                status_code = 2
            if status == "disregarded":
                status_code = 4

            if permissions["enum_canclean"] == 1:
                number_of_errors = get_number_of_errors_by_assistant(self.request, self.projectID, form_id, None,
                                                                     status_code)

            else:
                number_of_errors = get_number_of_errors_by_assistant(self.request, self.projectID, form_id,
                                                                     self.assistantID, status_code)
            page_size = 6
            item_collection = range(number_of_errors)
            page = paginate.Page(item_collection, current_page, page_size)

            all_pages = []
            page_params = {}
            if status != "all":
                page_params['status'] = status

            if page.last_page is not None:
                if page.last_page > 1:
                    for a in range(1, page.last_page+1):
                        next_page = False
                        if a == current_page + 1:
                            next_page = True
                        page_params['page'] = a
                        all_pages.append({"page": a, 'next': next_page,
                                          'url': self.request.route_url('errorlist', userid=self.userID,
                                                                        projcode=project_code, formid=form_id,
                                                                        _query=page_params)})
            if page.first_item is not None:
                start = page.first_item - 1
            else:
                start = 0
            if permissions["enum_canclean"] == 1:
                errors = get_errors_by_assistant(self.request, self.userID, self.projectID, form_id, None, start,
                                                 page_size, status_code)
            else:
                errors = get_errors_by_assistant(self.request, self.userID, self.projectID, form_id,
                                                 self.assistantID, start, page_size, status_code)
            return {'errors': errors, 'canclean': permissions["enum_canclean"], 'formid': form_id,
                    'formData': form_data, 'allPages': all_pages, 'status': status}
        else:
            raise HTTPNotFound()


class JSONCompare(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        if permissions["enum_canclean"] == 1:
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_id)
            form_data = get_form_data(self.request, self.projectID, form_id)
            comp_data = {}
            if data is not None:
                if data["status"] != 0:                    
                    diff = None
                    if self.request.method == 'POST':
                        post_data = self.get_post_dict()
                        if post_data["submissionid"] != submission_id:
                            comp_code = post_data["submissionid"]
                            comp_data = get_submission_details(self.request, self.projectID, form_id, comp_code)
                            if comp_data is not None:
                                error, diff = generate_diff(self.request, self.projectID, form_id, submission_id,
                                                            comp_code)
                                if error != 0:
                                    self.errors.append(self._("An error occurred while comparing the files. "
                                                              "Sorry for this. Please post the below error "
                                                              "as an issue in ") + "https://github.com/qlands/FormShare")
                                    self.errors.append(diff)
                                    diff = None
                                else:
                                    diff = literal(diff)
                            else:
                                comp_data = {}
                                self.errors.append(self._('The submission ID does not exist'))
                        else:
                            self.errors.append(self._('No point to compare to the same submission ID'))

                    return {'formid': form_id, 'submissionid': submission_id,
                            'data': data, 'compData': comp_data, 'diff': diff, 'formData': form_data}
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()


class JSONCheckout(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):
        self.returnRawViewResult = True
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        if permissions["enum_canclean"] == 1:
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_id)
            if data is not None:
                if data["status"] == 1:
                    if self.request.method == 'POST':
                        project_of_assistant = get_project_from_assistant(self.request, self.userID, self.projectID,
                                                                          self.assistantID)
                        checkout_submission(self.request, self.projectID, form_id, submission_id, project_of_assistant,
                                            self.assistantID)
                        return HTTPFound(
                            location=self.request.route_url('errorlist', userid=self.userID, projcode=self.projectCode,
                                                            formid=form_id))
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
        

class JSONCancelCheckout(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):
        self.returnRawViewResult = True
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']

        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        if permissions["enum_canclean"] == 1:
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_id)
            if data is not None:
                if data["status"] == 2:
                    if self.request.method == 'POST':
                        project_of_assistant = get_project_from_assistant(self.request, self.userID, self.projectID,
                                                                          self.assistantID)
                        cancel_checkout(self.request, self.projectID, form_id, submission_id, project_of_assistant,
                                        self.assistantID)
                        return HTTPFound(
                            location=self.request.route_url('errorlist', userid=self.userID, projcode=self.projectCode,
                                                            formid=form_id))
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
        

class JSONGetSubmission(AssistantView):
    def process_view(self):
        self.returnRawViewResult = True
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        if permissions["enum_canclean"] == 1:
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_id)
            if data is not None:
                if data["status"] == 2:
                    return get_submission_file(self.request, self.projectID, form_id, submission_id)
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
        

class JSONCheckin(AssistantView):
    def process_view(self):        
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        
        if permissions["enum_canclean"] == 1:
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_id)
            form_data = get_form_data(self.request, self.projectID, form_id)
            if data is not None:
                if data["status"] == 2:
                    if self.request.method == 'POST':
                        if not isinstance(self.request.POST['json'], bytes):
                            filename = self.request.POST['json'].filename
                            input_file = self.request.POST['json'].file
                            base_name, file_extension = os.path.splitext(filename)
                            if base_name == submission_id:
                                try:
                                    byte_str = input_file.read()
                                    text_obj = byte_str.decode()
                                    json.loads(text_obj)
                                    input_file.seek(0)
                                    sequence = str(uuid.uuid4())
                                    sequence = sequence[-12:]
                                    notes = self.request.POST['notes']
                                    res, message = store_new_version(self.request, self.userID, self.projectID, form_id,
                                                                     submission_id, self.assistantID, sequence,
                                                                     input_file, notes)
                                    if res == 0:
                                        self.returnRawViewResult = True
                                        return HTTPFound(
                                            location=self.request.route_url('errorlist', userid=self.userID,
                                                                            projcode=self.projectCode, formid=form_id))
                                    else:
                                        self.errors.append(message)
                                except Exception as ex:
                                    log.debug(str(ex))
                                    self.errors.append(self._("Error reading JSON file"))
                            else:
                                self.errors.append(self._("The new file must have the same name as the submission"))

                    return {'formid': form_id, 'submissionid': submission_id, 'data': data, 'formData': form_data}
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
        

class JSONViewRevision(AssistantView):
    def process_view(self):
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        revision_id = self.request.matchdict['revisionid']
        
        if "pushed" in self.request.params.keys():
            pushed = self.request.params["pushed"]
        else:
            pushed = 'false'

        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        
        if permissions["enum_canclean"] == 1:
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_id)
            form_data = get_form_data(self.request, self.projectID, form_id)
            if data is not None:
                error_code, diff = get_html_from_diff(self.request, self.projectID, form_id, submission_id, revision_id)
                if error_code != 0:
                    diff = None
                else:
                    diff = literal(diff)
                return {'formid': form_id, 'submissionid': submission_id, 'data': data, 'diff': diff,
                        'revisionid': revision_id, 'pushed': pushed, 'formData': form_data}
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
        

class JSONCancelRevision(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):
        self.returnRawViewResult = True
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        revision_id = self.request.matchdict['revisionid']

        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        
        if permissions["enum_canclean"] == 1:
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_id)
            if data is not None:
                if data["status"] == 3:
                    if self.request.method == 'POST':
                        res_code, message = restore_from_revision(self.request, self.projectID, form_id, submission_id,
                                                                  revision_id)
                        if res_code == 0:
                            project_of_assistant = get_project_from_assistant(self.request, self.userID, self.projectID,
                                                                              self.assistantID)
                            cancel_revision(self.request, self.projectID, form_id, submission_id, project_of_assistant,
                                            self.assistantID, revision_id)
                        return HTTPFound(
                            location=self.request.route_url('errorlist', userid=self.userID, projcode=self.projectCode,
                                                            formid=form_id))
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
        

class JSONPushRevision(AssistantView):
    def __init__(self, request):
        AssistantView.__init__(self, request)
        self.checkCrossPost = False

    def process_view(self):
        self.returnRawViewResult = True
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        revision_id = self.request.matchdict['revisionid']

        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        
        if permissions["enum_canclean"] == 1:
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_id)
            if data is not None:
                if data["status"] == 3:
                    if self.request.method == 'POST':
                        res_code, message = push_revision(self.request, self.userID, self.projectID, form_id,
                                                          submission_id)
                        project_of_assistant = get_project_from_assistant(self.request, self.userID, self.projectID,
                                                                          self.assistantID)
                        if res_code == 0:
                            fix_revision(self.request, self.projectID, form_id, submission_id, project_of_assistant,
                                         self.assistantID, revision_id)
                        else:
                            fail_revision(self.request, self.projectID, form_id, submission_id, project_of_assistant,
                                          self.assistantID, revision_id)
                        return HTTPFound(
                            location=self.request.route_url('errorlist', userid=self.userID, projcode=self.projectCode,
                                                            formid=form_id))
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
        

class JSONDisregard(AssistantView):
    def process_view(self):        
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']

        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        
        if permissions["enum_canclean"] == 1:
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_id)
            form_data = get_form_data(self.request, self.projectID, form_id)
            if data is not None:
                if data["status"] == 1:
                    if self.request.method == 'POST':
                        post_data = self.get_post_dict()
                        notes = post_data["notes"]
                        if notes != "":
                            project_of_assistant = get_project_from_assistant(self.request, self.userID, self.projectID,
                                                                              self.assistantID)
                            disregard_revision(self.request, self.projectID, form_id, submission_id,
                                               project_of_assistant, self.assistantID, notes)
                            self.returnRawViewResult = True
                            return HTTPFound(
                                location=self.request.route_url('errorlist', userid=self.userID,
                                                                projcode=self.projectCode, formid=form_id))
                        else:
                            self.errors.append(self._("You need to provide an explanation when disregarding an error"))
                    return {'formid': form_id, 'submissionid': submission_id, 'data': data, 'formData': form_data,
                            'errorDesc': get_error_description_from_file(data['log_file'])}
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
        

class JSONCancelDisregard(AssistantView):
    def process_view(self):        
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']

        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
            
        if permissions["enum_canclean"] == 1:
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_id)
            form_data = get_form_data(self.request, self.projectID, form_id)
            if data is not None:
                if data["status"] == 4:

                    if self.request.method == 'POST':
                        post_data = self.get_post_dict()
                        notes = post_data["notes"]
                        if notes != "":
                            project_of_assistant = get_project_from_assistant(self.request, self.userID, self.projectID,
                                                                              self.assistantID)
                            cancel_disregard_revision(self.request, self.projectID, form_id, submission_id,
                                                      project_of_assistant, self.assistantID, notes)
                            self.returnRawViewResult = True
                            return HTTPFound(
                                location=self.request.route_url('errorlist', userid=self.userID,
                                                                projcode=self.projectCode, formid=form_id))
                        else:
                            self.errors.append(self._("You need to provide an explanation when canceling a disregard"))

                    return {'formid': form_id, 'submissionid': submission_id, 'data': data, 'formData': form_data,
                            'errorDesc': get_error_description_from_file(data['log_file'])}
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
       

class JSONCompareSubmissions(AssistantView):
    def process_view(self):        
        form_id = self.request.matchdict['formid']
        submission_a = self.request.matchdict['submissiona']
        submission_b = self.request.matchdict['submissionb']

        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)

        if permissions["enum_canclean"] == 1:
            form_data = get_form_data(self.request, self.projectID, form_id)
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_a)
            comp_data = get_submission_error_details(self.request, self.projectID, form_id, submission_b)

            error, diff = generate_diff(self.request, self.projectID, form_id, submission_a, submission_b)
            if error != 0:
                self.errors.append(self._("An error occurred while comparing the files. "
                                          "Sorry for this. Please post the below error "
                                          "as an issue in ") + "https://github.com/qlands/FormShare")
                self.errors.append(diff)
                diff = None
            else:
                diff = literal(diff)

            return {'formid': form_id, 'submissiona': submission_a, 'data': data, 'compData': comp_data, 'diff': diff,
                    'submissionb': submission_b, 'formData': form_data}
        else:
            raise HTTPNotFound()
