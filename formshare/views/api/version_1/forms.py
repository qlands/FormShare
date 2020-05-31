import logging
import os
from hashlib import md5

from pyramid.httpexceptions import HTTPNotFound

from formshare.processes.db import (
    get_project_id_from_name,
    get_project_access_type,
    get_form_data,
    add_file_to_form,
)
from formshare.processes.storage import store_file
from formshare.views.classes import APIView

__all__ = [
    "API1UploadFileToForm",
]

log = logging.getLogger("formshare")


class API1UploadFileToForm(APIView):
    def __init__(self, request):
        APIView.__init__(self, request)

    def process_view(self):
        if self.request.method == "POST":
            required_keys = ["user_id", "project_code", "form_id"]
            self.check_keys(required_keys)

            user_id = self.request.POST.get("user_id", None)
            project_code = self.request.POST.get("project_code", None)
            form_id = self.request.POST.get("form_id", None)
            project_id = get_project_id_from_name(self.request, user_id, project_code)
            access_type = get_project_access_type(
                self.request, self.user["user_id"], project_id
            )
            if access_type is None:
                self.return_error(
                    "authorization",
                    self._("You are not authorized to modify this project"),
                )
            else:
                if access_type >= 4:
                    self.return_error(
                        "authorization",
                        self._("You are not authorized to modify this project"),
                    )

            form_data = get_form_data(self.request, project_id, form_id)
            if form_data is None:
                self.return_error(
                    "form_does_not_exist", self._("The form does not exists")
                )

            if "file_to_upload" not in self.request.POST.keys():
                self.return_error(
                    "file_not_attached", self._("You did not attached any file")
                )

            if "overwrite" in self.request.POST.keys():
                overwrite = True
            else:
                overwrite = False

            try:
                file_name = self.request.POST["file_to_upload"].filename
                if os.path.isabs(file_name):
                    file_name = os.path.basename(file_name)
                slash_index = file_name.find("\\")
                if slash_index >= 0:
                    file_name = file_name[slash_index + 1 :]
                md5sum = md5(
                    self.request.POST["file_to_upload"].file.read()
                ).hexdigest()
                added, message = add_file_to_form(
                    self.request, project_id, form_id, file_name, overwrite, md5sum
                )
                if added:
                    self.request.POST["file_to_upload"].file.seek(0)
                    bucket_id = project_id + form_id
                    bucket_id = md5(bucket_id.encode("utf-8")).hexdigest()
                    store_file(
                        self.request,
                        bucket_id,
                        file_name,
                        self.request.POST["file_to_upload"].file,
                    )
                else:
                    self.error = True
                    return {"error": message, "error_type": "storage_error"}
            except Exception as e:
                log.error(
                    "Error while uploading files into form {} of project {}. Error: {}".format(
                        form_id, project_id, str(e)
                    )
                )
                self.error = True
                return {"error": str(e), "error_type": "storage_error"}

            return {"status": "OK", "message": self._("The file was uploaded")}
        else:
            raise HTTPNotFound
