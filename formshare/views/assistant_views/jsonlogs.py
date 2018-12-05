from formshare.views.classes import AssistantView
from formshare.processes.db import get_project_id_from_name
from formshare.processes.odk.processes import get_assistant_permissions_on_a_form, get_errors_by_assistant, \
    get_submission_error_details, get_submission_details, checkout_submission, cancel_checkout, cancel_revision, \
    fix_revision, fail_revision, disregard_revision, cancel_disregard_revision
from formshare.processes.odk.api import generate_diff, get_submission_file, store_new_version, get_html_from_diff, \
    restore_from_revision, push_revision
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from webhelpers2.html import literal
import os
import uuid
import json

import logging
log = logging.getLogger(__name__)


class JSONList(AssistantView):
    def process_view(self):
        form_id = self.request.matchdict['formid']
        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        if permissions["enum_cansubmit"] == 1 or permissions["enum_canclean"] == 1:
            if permissions["enum_canclean"] == 1:
                errors = get_errors_by_assistant(self.request, self.projectID, form_id, None)
            else:
                errors = get_errors_by_assistant(self.request, self.projectID, form_id, self.assistantID)
            return {'errors': errors, 'canclean': permissions["enum_canclean"], 'formid': form_id}
        else:
            raise HTTPNotFound()


class JSONCompare(AssistantView):
    def process_view(self):        
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        permissions = get_assistant_permissions_on_a_form(self.request, self.userID, self.projectID, self.assistantID,
                                                          form_id)
        if permissions["enum_canclean"] == 1:
            data = get_submission_error_details(self.request, self.projectID, form_id, submission_id)
            comp_data = {}
            if data is not None:
                if data["status"] != 0:
                    error_summary = {}
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
                                    error_summary['contact'] = self._("An error ocurred while comparing the files. "
                                                                      "Sorry for this. Please send the below error "
                                                                      "message to support_for_ilri@qlands.com")
                                    error_summary = {'error': diff}
                                    diff = None
                                else:
                                    diff = literal(diff)
                            else:
                                comp_data = {}
                                error_summary = {'error': self._('The submission ID does not exist')}
                        else:
                            error_summary = {'error': self._('No point to compare to the same submission ID')}

                    return {'formid': form_id, 'submissionid': submission_id,
                            'data': data, 'error_summary': error_summary, 'comp_data': comp_data,
                            'diff': diff}
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()


class JSONCheckout(AssistantView):
    def process_view(self):
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        project_id = get_project_id_from_name(self.request, project_code)
        if project_id is not None:
            permissions = get_assistant_permissions_on_a_form(self.request,project_id,self.enum.enum,form_id)
            if permissions["enum_canclean"] == 1:
                data = get_submission_error_details(self.request,project_id,form_id,submission_id)
                if data is not None:
                    if data["status"] == 1:
                        if self.request.method == 'POST':
                            checkout_submission(self.request,project_id,form_id,submission_id,self.enum.enum)
                            return HTTPFound(location=self.request.route_url('errorlist', pname=project_code, formid=form_id))
                        else:
                            return HTTPFound(location=self.request.route_url('errorlist',pname=project_code,formid=form_id))
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()


class JSONCancelCheckout(AssistantView):
    def process_view(self):
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        project_id = get_project_id_from_name(self.request, project_code)
        if project_id is not None:
            permissions = get_assistant_permissions_on_a_form(self.request,project_id,self.enum.enum,form_id)
            if permissions["enum_canclean"] == 1:
                data = get_submission_error_details(self.request,project_id,form_id,submission_id)
                if data is not None:
                    if data["status"] == 2:
                        if self.request.method == 'POST':
                            cancel_checkout(self.request,project_id,form_id,submission_id,self.enum.enum)
                            return HTTPFound(location=self.request.route_url('errorlist', pname=project_code, formid=form_id))
                        else:
                            return HTTPFound(location=self.request.route_url('errorlist',pname=project_code,formid=form_id))
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
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        project_id = get_project_id_from_name(self.request, project_code)
        if project_id is not None:
            permissions = get_assistant_permissions_on_a_form(self.request,project_id,self.enum.enum,form_id)
            if permissions["enum_canclean"] == 1:
                data = get_submission_error_details(self.request,project_id,form_id,submission_id)
                if data is not None:
                    if data["status"] == 2:
                        return get_submission_file(project_id,form_id,submission_id,self.request)
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()


class JSONCheckin(AssistantView):
    def process_view(self):
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        project_id = get_project_id_from_name(self.request, project_code)
        if project_id is not None:
            permissions = get_assistant_permissions_on_a_form(self.request,project_id,self.enum.enum,form_id)
            if permissions["enum_canclean"] == 1:
                data = get_submission_error_details(self.request,project_id,form_id,submission_id)
                if data is not None:
                    if data["status"] == 2:
                        error_summary = {}
                        if self.request.method == 'POST':
                            if not isinstance(self.request.POST['json'], bytes):
                                filename = self.request.POST['json'].filename
                                input_file = self.request.POST['json'].file
                                baseName, file_extension = os.path.splitext(filename)
                                if baseName == submission_id:
                                    try:
                                        byte_str = input_file.read()
                                        text_obj = byte_str.decode()
                                        json.loads(text_obj)
                                        input_file.seek(0)
                                        sequence = str(uuid.uuid4())
                                        sequence = sequence[-12:]
                                        notes = self.request.POST['notes']
                                        res,message = store_new_version(self.request,project_id,form_id,submission_id,self.enum.enum,sequence,input_file,notes)
                                        if res == 0:
                                            return HTTPFound(
                                                location=self.request.route_url('errorlist', pname=project_code,
                                                                                formid=form_id))
                                        else:
                                            error_summary["error"] = message
                                    except Exception as ex:
                                        log.debug(str(ex))
                                        error_summary["error"] = "Error reading JSON file"
                                else:
                                    error_summary["error"] = "The new file must have the same name as the submission"

                        return {'pname':project_code,'formid':form_id,'submissionid':submission_id,
                                'data':data,'error_summary':error_summary}
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()


class JSONViewRevision(AssistantView):
    def process_view(self):
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        revisionID = self.request.matchdict['revisionid']
        project_id = get_project_id_from_name(self.request, project_code)
        if "pushed" in self.request.params.keys():
            pushed = self.request.params["pushed"]
        else:
            pushed = 'false'
        if project_id is not None:
            permissions = get_assistant_permissions_on_a_form(self.request,project_id,self.enum.enum,form_id)
            if permissions["enum_canclean"] == 1:
                data = get_submission_error_details(self.request,project_id,form_id,submission_id)
                if data is not None:
                    error_summary = {}
                    diff = None
                    errorCode,diff = get_html_from_diff(self.request,project_id,form_id,submission_id,revisionID)
                    if errorCode != 0:
                        diff = None
                    else:
                        diff = literal(diff)
                    return {'pname':project_code,'formid':form_id,'submissionid':submission_id,
                            'data':data,'error_summary':error_summary,
                            'diff':diff,'revisionid':revisionID,'pushed':pushed}
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()


class JSONCancelRevision(AssistantView):
    def process_view(self):
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        revisionID = self.request.matchdict['revisionid']
        project_id = get_project_id_from_name(self.request, project_code)
        if project_id is not None:
            permissions = get_assistant_permissions_on_a_form(self.request,project_id,self.enum.enum,form_id)
            if permissions["enum_canclean"] == 1:
                data = get_submission_error_details(self.request,project_id,form_id,submission_id)
                if data is not None:
                    if data["status"] == 3:
                        if self.request.method == 'POST':
                            resCode,message = restore_from_revision(self.request,project_id,form_id,submission_id,revisionID)
                            if resCode == 0:
                                cancel_revision(self.request,project_id,form_id,submission_id,self.enum.enum,revisionID)
                            return HTTPFound(location=self.request.route_url('errorlist', pname=project_code, formid=form_id))
                        else:
                            return HTTPFound(location=self.request.route_url('errorlist',pname=project_code,formid=form_id))
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()


class JSONPushRevision(AssistantView):
    def process_view(self):
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        revisionID = self.request.matchdict['revisionid']
        project_id = get_project_id_from_name(self.request, project_code)
        if project_id is not None:
            permissions = get_assistant_permissions_on_a_form(self.request,project_id,self.enum.enum,form_id)
            if permissions["enum_canclean"] == 1:
                data = get_submission_error_details(self.request,project_id,form_id,submission_id)
                if data is not None:
                    if data["status"] == 3:
                        if self.request.method == 'POST':
                            resCode,message = push_revision(self.request,project_id,form_id,submission_id)
                            if resCode == 0:
                                fix_revision(self.request,project_id,form_id,submission_id,self.enum.enum,revisionID)
                            else:
                                fail_revision(self.request,project_id,form_id,submission_id,self.enum.enum,revisionID)
                            return HTTPFound(location=self.request.route_url('errorlist', pname=project_code, formid=form_id))
                        else:
                            return HTTPFound(location=self.request.route_url('errorlist',pname=project_code,formid=form_id))
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
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        project_id = get_project_id_from_name(self.request, project_code)
        if project_id is not None:
            permissions = get_assistant_permissions_on_a_form(self.request,project_id,self.enum.enum,form_id)
            if permissions["enum_canclean"] == 1:
                data = get_submission_error_details(self.request,project_id,form_id,submission_id)
                if data is not None:
                    if data["status"] == 1:
                        error_summary = {}
                        if self.request.method == 'POST':
                            post_data = self.get_post_dict()
                            notes = post_data["notes"]
                            if notes != "":
                                disregard_revision(self.request,project_id,form_id,submission_id,self.enum.enum,notes)
                                return HTTPFound(
                                    location=self.request.route_url('errorlist', pname=project_code,
                                                                    formid=form_id))
                            else:
                                error_summary["eror"] = "You need to provide an explanation when disregarding an error"

                        return {'pname':project_code,'formid':form_id,'submissionid':submission_id,
                                'data':data,'error_summary':error_summary}
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()


class JSONCancelDisregard(AssistantView):
    def process_view(self):
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        submission_id = self.request.matchdict['submissionid']
        project_id = get_project_id_from_name(self.request, project_code)
        if project_id is not None:
            permissions = get_assistant_permissions_on_a_form(self.request,project_id,self.enum.enum,form_id)
            if permissions["enum_canclean"] == 1:
                data = get_submission_error_details(self.request,project_id,form_id,submission_id)
                if data is not None:
                    if data["status"] == 4:
                        error_summary = {}
                        if self.request.method == 'POST':
                            post_data = self.get_post_dict()
                            notes = post_data["notes"]
                            if notes != "":
                                cancel_disregard_revision(self.request,project_id,form_id,submission_id,self.enum.enum,notes)
                                return HTTPFound(
                                    location=self.request.route_url('errorlist', pname=project_code,
                                                                    formid=form_id))
                            else:
                                error_summary["eror"] = "You need to provide an explanation when canceling a disregard"

                        return {'pname':project_code,'formid':form_id,'submissionid':submission_id,
                                'data':data,'error_summary':error_summary}
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()


class JSONCompareSubmissions(AssistantView):
    def process_view(self):
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        submissionA = self.request.matchdict['submissiona']
        submissionB = self.request.matchdict['submissionb']
        project_id = get_project_id_from_name(self.request, project_code)
        if project_id is not None:
            permissions = get_assistant_permissions_on_a_form(self.request,project_id,self.enum.enum,form_id)
            if permissions["enum_canclean"] == 1:
                data = get_submission_error_details(self.request, project_id, form_id, submissionA)
                comp_data = get_submission_error_details(self.request, project_id, form_id, submissionB)

                error_summary = {}
                error, diff = generate_diff(self.request, project_id, form_id, submissionA, submissionB)
                if error != 0:
                    error_summary['contact'] = self._(
                        "An error ocurred while comparing the files. Sorry for this. Please send the below error message to support_for_cabi@qlands.com")
                    error_summary = {'error': diff}
                    diff = None
                else:
                    diff = literal(diff)

                return {'pname': project_code, 'formid': form_id, 'submissiona': submissionA,
                        'error_summary': error_summary,'data':data,'comp_data':comp_data,
                        'diff': diff,'submissionb':submissionB}
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
