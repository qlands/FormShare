from formshare.views.classes import ODKView
from formshare.processes.odk.api import get_manifest, get_media_file, get_form_list, get_xml_form, store_submission
from formshare.processes.db import get_project_id_from_name, is_assistant_active, get_assistant_password, \
    assistant_has_form
from pyramid.response import Response


class ODKFormList(ODKView):
    def process_view(self):
        project_code = self.request.matchdict['projcode']
        user_id = self.request.matchdict['userid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if is_assistant_active(self.request, user_id, project_id, self.user):
                if self.authorize(get_assistant_password(self.request, user_id, project_id, self.user)):
                    return self.create_xmll_response(get_form_list(self.request, user_id, project_code, self.user))
                else:
                    return self.ask_for_credentials()
            else:
                return self.ask_for_credentials()
        else:
            response = Response(status=404)
            return response


class ODKPushData(ODKView):
    def process_view(self):
        project_code = self.request.matchdict['projcode']
        user_id = self.request.matchdict['userid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if self.request.method == "POST":
                if is_assistant_active(self.request, user_id, project_id, self.user):
                    if self.authorize(get_assistant_password(self.request, user_id, project_id, self.user)):
                        stored, error = store_submission(self.request, user_id, project_id, self.user)
                        if stored:
                            response = Response(status=201)
                            return response
                        else:
                            response = Response(status=error)
                            return response
                    else:
                        return self.ask_for_credentials()
                else:
                    response = Response(status=401)
                    return response
            else:
                response = Response(status=404)
                return response
        else:
            response = Response(status=404)
            return response


class ODKSubmission(ODKView):
    def process_view(self):
        project_code = self.request.matchdict['projcode']
        user_id = self.request.matchdict['userid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if self.request.method == 'HEAD':
                if is_assistant_active(self.request, user_id, project_id, self.user):
                    headers = [('Location', self.request.route_url('odkpush', userid=user_id, projcode=project_code))]
                    response = Response(headerlist=headers, status=204)
                    return response
                else:
                    return self.ask_for_credentials()
            else:
                response = Response(status=404)
                return response
        else:
            response = Response(status=404)
            return response


class ODKXMLForm(ODKView):
    def process_view(self):
        form_id = self.request.matchdict['formid']
        project_code = self.request.matchdict['projcode']
        user_id = self.request.matchdict['userid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if is_assistant_active(self.request, user_id, project_id, self.user):
                if assistant_has_form(self.request, user_id, project_id, form_id, self.user):
                    if self.authorize(get_assistant_password(self.request, user_id, project_id, self.user)):
                        return get_xml_form(self.request, project_id, form_id)
                    else:
                        return self.ask_for_credentials()
                else:
                    return self.ask_for_credentials()
            else:
                return self.ask_for_credentials()
        else:
            response = Response(status=404)
            return response


class ODKManifest(ODKView):
    def process_view(self):
        form_id = self.request.matchdict['formid']
        project_code = self.request.matchdict['projcode']
        user_id = self.request.matchdict['userid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if is_assistant_active(self.request, user_id, project_id, self.user):
                if assistant_has_form(self.request, user_id, project_id, form_id, self.user):
                    if self.authorize(get_assistant_password(self.request, user_id, project_id, self.user)):
                        return self.create_xmll_response(
                            get_manifest(self.request, user_id, project_code, project_id, form_id))
                    else:
                        return self.ask_for_credentials()
                else:
                    return self.ask_for_credentials()
            else:
                return self.ask_for_credentials()
        else:
            response = Response(status=404)
            return response


class ODKMediaFile(ODKView):
    def process_view(self):
        file_id = self.request.matchdict['fileid']
        form_id = self.request.matchdict['formid']
        project_code = self.request.matchdict['projcode']
        user_id = self.request.matchdict['userid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if is_assistant_active(self.request, user_id, project_id, self.user):
                if assistant_has_form(self.request, user_id, project_id, form_id, self.user):
                    if self.authorize(get_assistant_password(self.request, user_id, project_id, self.user)):
                        return get_media_file(self.request, project_id, form_id, file_id)
                    else:
                        return self.ask_for_credentials()
                else:
                    return self.ask_for_credentials()
            else:
                return self.ask_for_credentials()
        else:
            response = Response(status=404)
            return response
