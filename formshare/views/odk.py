from webob.exc import HTTPNotFound

from formshare.processes.db import (
    get_project_id_from_name,
    is_assistant_active,
    get_assistant_password,
    assistant_has_form,
    project_has_crowdsourcing,
)
from formshare.processes.odk.api import (
    get_manifest,
    get_media_file,
    get_form_list,
    get_xml_form,
    store_submission,
    store_json_submission,
)
from formshare.processes.db.assistant import get_odk_assistant_uuid
from formshare.views.classes import ODKView
from formshare.middleware.response import Response


class ODKFormList(ODKView):
    def process_view(self):
        project_code = self.request.matchdict["projcode"]
        user_id = self.request.matchdict["userid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if not project_has_crowdsourcing(self.request, project_id):
                assistant_uuid = get_odk_assistant_uuid(
                    self.request, user_id, project_id, self.user
                )
                if not self.api:
                    if is_assistant_active(self.request, assistant_uuid):
                        if self.authorize(
                            get_assistant_password(self.request, assistant_uuid)
                        ):
                            return self.create_xmll_response(
                                get_form_list(
                                    self.request, user_id, project_code, assistant_uuid
                                )
                            )
                        else:
                            return self.ask_for_credentials()
                    else:
                        return self.ask_for_credentials()
                else:
                    return self.create_xmll_response(
                        get_form_list(
                            self.request, user_id, project_code, assistant_uuid, True
                        )
                    )
            else:
                return self.create_xmll_response(
                    get_form_list(self.request, user_id, project_code, "NA")
                )
        else:
            response = Response(status=404)
            return response


class ODKPushData(ODKView):
    def process_view(self):
        project_code = self.request.matchdict["projcode"]
        user_id = self.request.matchdict["userid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if self.request.method == "POST":
                if not project_has_crowdsourcing(self.request, project_id):
                    assistant_uuid = get_odk_assistant_uuid(
                        self.request, user_id, project_id, self.user
                    )
                    if is_assistant_active(self.request, assistant_uuid):
                        if self.authorize(
                            get_assistant_password(self.request, assistant_uuid)
                        ):
                            stored, error = store_submission(
                                self.request, user_id, project_id, assistant_uuid
                            )
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
                    stored, error = store_submission(
                        self.request, user_id, project_id, "public"
                    )
                    if stored:
                        response = Response(status=201)
                        return response
                    else:
                        response = Response(status=error)
                        return response
            else:
                response = Response(status=404)
                return response
        else:
            response = Response(status=404)
            return response


class ODKPushJSONData(ODKView):
    def process_view(self):
        project_code = self.request.matchdict["projcode"]
        user_id = self.request.matchdict["userid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if self.request.method == "POST":
                if not project_has_crowdsourcing(self.request, project_id):
                    assistant_uuid = get_odk_assistant_uuid(
                        self.request, user_id, project_id, self.user
                    )
                    if is_assistant_active(self.request, assistant_uuid):
                        if self.authorize(
                            get_assistant_password(self.request, assistant_uuid)
                        ):
                            stored, error = store_json_submission(
                                self.request, user_id, project_id, assistant_uuid
                            )
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
                    stored, error = store_json_submission(
                        self.request, user_id, project_id, "public"
                    )
                    if stored:
                        response = Response(status=201)
                        return response
                    else:
                        response = Response(status=error)
                        return response
            else:
                response = Response(status=404)
                return response
        else:
            response = Response(status=404)
            return response


class ODKSubmission(ODKView):
    def process_view(self):
        project_code = self.request.matchdict["projcode"]
        user_id = self.request.matchdict["userid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if self.request.method == "HEAD":
                if not project_has_crowdsourcing(self.request, project_id):
                    assistant_uuid = get_odk_assistant_uuid(
                        self.request, user_id, project_id, self.user
                    )
                    if is_assistant_active(self.request, assistant_uuid):
                        headers = [
                            (
                                "Location",
                                self.request.route_url(
                                    "odkpush", userid=user_id, projcode=project_code
                                ),
                            ),
                            ("x-openrosa-accept-content-length", "10000000"),
                        ]
                        response = Response(headerlist=headers, status=204)
                        return response
                    else:
                        return self.ask_for_credentials()
                else:
                    headers = [
                        (
                            "Location",
                            self.request.route_url(
                                "odkpush", userid=user_id, projcode=project_code
                            ),
                        ),
                        ("x-openrosa-accept-content-length", "10000000"),
                    ]
                    response = Response(headerlist=headers, status=204)
                    return response
            else:
                if self.request.method == "POST":
                    if not project_has_crowdsourcing(self.request, project_id):
                        assistant_uuid = get_odk_assistant_uuid(
                            self.request, user_id, project_id, self.user
                        )
                        if is_assistant_active(self.request, assistant_uuid):
                            if self.authorize(
                                get_assistant_password(self.request, assistant_uuid)
                            ):
                                stored, error = store_submission(
                                    self.request, user_id, project_id, assistant_uuid
                                )
                                if stored:
                                    response = Response(status=201)
                                    return response
                                else:
                                    response = Response(status=error)
                                    return response
                            else:
                                return self.ask_for_credentials()
                        else:
                            return self.ask_for_credentials()
                    else:
                        stored, error = store_submission(
                            self.request, user_id, project_id, "public"
                        )
                        if stored:
                            response = Response(status=201)
                            return response
                        else:
                            response = Response(status=error)
                            return response
                else:
                    response = Response(status=404)
                    return response
        else:
            response = Response(status=404)
            return response


class ODKXMLForm(ODKView):
    def process_view(self):
        form_id = self.request.matchdict["formid"]
        project_code = self.request.matchdict["projcode"]
        user_id = self.request.matchdict["userid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if not project_has_crowdsourcing(self.request, project_id):
                assistant_uuid = get_odk_assistant_uuid(
                    self.request, user_id, project_id, self.user
                )
                if not self.api:
                    if is_assistant_active(self.request, assistant_uuid):
                        if assistant_has_form(
                            self.request, user_id, project_id, form_id, assistant_uuid
                        ):
                            if self.authorize(
                                get_assistant_password(self.request, assistant_uuid)
                            ):
                                res = get_xml_form(self.request, project_id, form_id)
                                if res is not None:
                                    return res
                                else:
                                    return self.ask_for_credentials()
                            else:
                                return self.ask_for_credentials()
                        else:
                            return self.ask_for_credentials()
                    else:
                        return self.ask_for_credentials()
                else:
                    res = get_xml_form(self.request, project_id, form_id)
                    if res is not None:
                        return res
                    else:
                        return self.ask_for_credentials()
            else:
                res = get_xml_form(self.request, project_id, form_id)
                if res is not None:
                    return res
                else:
                    raise HTTPNotFound
        else:
            response = Response(status=404)
            return response


class ODKManifest(ODKView):
    def process_view(self):
        print("***************** I am in process_view")
        form_id = self.request.matchdict["formid"]
        project_code = self.request.matchdict["projcode"]
        user_id = self.request.matchdict["userid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if not project_has_crowdsourcing(self.request, project_id):
                assistant_uuid = get_odk_assistant_uuid(
                    self.request, user_id, project_id, self.user
                )
                if not self.api:
                    if is_assistant_active(self.request, assistant_uuid):
                        if assistant_has_form(
                            self.request, user_id, project_id, form_id, assistant_uuid
                        ):
                            if self.authorize(
                                get_assistant_password(self.request, assistant_uuid)
                            ):
                                return self.create_xmll_response(
                                    get_manifest(
                                        self.request,
                                        user_id,
                                        project_code,
                                        project_id,
                                        form_id,
                                    )
                                )
                            else:
                                print("***************** Assistant is not authorized")
                                return self.ask_for_credentials()
                        else:
                            print(
                                "***************** Assistant is not active does not have form"
                            )
                            return self.ask_for_credentials()
                    else:
                        print("***************** Assistant is not active")
                        return self.ask_for_credentials()
                else:
                    return self.create_xmll_response(
                        get_manifest(
                            self.request, user_id, project_code, project_id, form_id
                        )
                    )
            else:
                return self.create_xmll_response(
                    get_manifest(
                        self.request, user_id, project_code, project_id, form_id
                    )
                )
        else:
            response = Response(status=404)
            return response


class ODKMediaFile(ODKView):
    def process_view(self):
        file_id = self.request.matchdict["fileid"]
        form_id = self.request.matchdict["formid"]
        project_code = self.request.matchdict["projcode"]
        user_id = self.request.matchdict["userid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            if not project_has_crowdsourcing(self.request, project_id):
                assistant_uuid = get_odk_assistant_uuid(
                    self.request, user_id, project_id, self.user
                )
                if not self.api:
                    if is_assistant_active(self.request, assistant_uuid):
                        if assistant_has_form(
                            self.request, user_id, project_id, form_id, assistant_uuid
                        ):
                            if self.authorize(
                                get_assistant_password(self.request, assistant_uuid)
                            ):
                                return get_media_file(
                                    self.request, project_id, form_id, file_id
                                )
                            else:
                                return self.ask_for_credentials()
                        else:
                            return self.ask_for_credentials()
                    else:
                        return self.ask_for_credentials()
                else:
                    return get_media_file(self.request, project_id, form_id, file_id)
            else:
                return get_media_file(self.request, project_id, form_id, file_id)
        else:
            response = Response(status=404)
            return response
