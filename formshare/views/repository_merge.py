from .classes import PrivateView
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from formshare.processes.db import (
    get_project_id_from_name,
    get_media_files,
    add_file_to_form,
    update_form,
    delete_form,
)
from formshare.processes.odk.processes import get_form_data
from formshare.processes.odk.api import (
    get_odk_path,
    upload_odk_form,
    create_repository,
    merge_versions,
)
from formshare.processes.storage import get_stream, store_file, delete_bucket
from hashlib import md5
import os
import shutil
from formshare.processes.elasticsearch.repository_index import delete_dataset_index
from formshare.processes.elasticsearch.record_index import delete_record_index
import logging
from lxml import etree
from formshare.processes.email.send_email import send_error_to_technical_team

log = logging.getLogger("formshare")


class RepositoryMergeForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def delete_new_form(
        self, odk_path, user_id, project_code, project_id, form_id, form_directory
    ):
        directory_path = os.path.join(odk_path, *["forms", form_directory])

        deleted, message = delete_form(self.request, project_id, form_id)
        if deleted:
            delete_dataset_index(
                self.request.registry.settings, user_id, project_code, form_id
            )
            delete_record_index(
                self.request.registry.settings, user_id, project_code, form_id
            )
            try:
                shutil.rmtree(directory_path)
            except Exception as e:
                log.error(
                    "Error {} while removing form {} in project {}. Cannot delete directory {}".format(
                        str(e), form_id, project_id, form_directory
                    )
                )
            bucket_id = project_id + form_id
            bucket_id = md5(bucket_id.encode("utf-8")).hexdigest()
            delete_bucket(self.request, bucket_id)

            return True
        else:
            return False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]

        project_id = get_project_id_from_name(self.request, user_id, project_code)
        project_details = {}
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
                    project_details = project
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if project_details["access_type"] >= 4:
            raise HTTPNotFound

        form_data = get_form_data(project_id, form_id, self.request)
        errors = []
        error_type = 0
        values_to_ignore = []
        input_file_name = ""
        s_values_to_ignore = None
        if self.request.method == "POST":
            odk_path = get_odk_path(self.request)
            post_data = self.get_post_dict()
            input_file_name = self.request.POST["xlsx"].filename.lower()
            if "valuestoignore" in post_data.keys():
                s_values_to_ignore = post_data["valuestoignore"]
                if input_file_name != post_data["inputfilename"]:
                    self.add_error(self._("The file is not the same"))
                    self.returnRawViewResult = True
                    return HTTPFound(self.request.url)
            post_data["form_target"] = 0
            post_data.pop("xlsx")
            uploaded, message = upload_odk_form(
                self.request, project_id, self.user.login, odk_path, post_data
            )
            if uploaded:
                new_form_id = message
                new_form_data = get_form_data(project_id, new_form_id, self.request)
                old_form_data = get_form_data(project_id, form_id, self.request)

                # TODO: This will not work because the old files might not apply for the new form!

                # Copying the media files from the old form the to new_one
                old_form_files = get_media_files(self.request, project_id, form_id)
                new_form_files = get_media_files(self.request, project_id, new_form_id)
                for a_old_file in old_form_files:
                    found = False
                    for a_new_file in new_form_files:
                        if a_old_file.file_name == a_new_file.file_name:
                            found = True
                    if not found:
                        bucket_id = project_id + form_id
                        bucket_id = md5(bucket_id.encode("utf-8")).hexdigest()
                        file_stream = get_stream(
                            self.request, bucket_id, a_old_file.file_name
                        )
                        if file_stream is not None:
                            md5sum = md5(file_stream.read()).hexdigest()
                            added, message = add_file_to_form(
                                self.request,
                                project_id,
                                new_form_id,
                                a_old_file.file_name,
                                True,
                                md5sum,
                            )
                            if added:
                                file_stream.seek(0)
                                store_file(
                                    self.request,
                                    bucket_id,
                                    a_old_file.file_name,
                                    file_stream,
                                )
                old_form_data.pop("id")
                old_form_data.pop("name")
                old_directory = old_form_data["directory"]
                old_form_data.pop("directory")
                old_form_data["parent_project"] = project_id
                old_form_data["parent_form"] = form_id
                old_form_data["form_incversion"] = 1
                update_form(self.request, project_id, new_form_id, old_form_data)
                old_form_data["directory"] = old_directory
                old_create_file = os.path.join(
                    odk_path,
                    *["forms", old_form_data["directory"], "repository", "create.xml"]
                )
                old_insert_file = os.path.join(
                    odk_path,
                    *["forms", old_form_data["directory"], "repository", "insert.xml"]
                )

                created, message = create_repository(
                    self.request,
                    user_id,
                    project_id,
                    new_form_id,
                    odk_path,
                    new_form_data["directory"],
                    old_form_data["form_pkey"],
                    old_form_data["form_deflang"],
                    old_form_data["form_othlangs"],
                    True,
                )
                if created == 0:
                    new_create_file = os.path.join(
                        odk_path,
                        *[
                            "forms",
                            new_form_data["directory"],
                            "repository",
                            "create.xml",
                        ]
                    )
                    new_insert_file = os.path.join(
                        odk_path,
                        *[
                            "forms",
                            new_form_data["directory"],
                            "repository",
                            "insert.xml",
                        ]
                    )

                    merged, output = merge_versions(
                        self.request,
                        odk_path,
                        new_form_data["directory"],
                        new_create_file,
                        new_insert_file,
                        old_create_file,
                        old_insert_file,
                        s_values_to_ignore,
                    )
                    if merged == 0:
                        next_page = self.request.route_url(
                            "form_details",
                            userid=project_details["owner"],
                            projcode=project_code,
                            formid=new_form_id,
                        )
                        self.request.session.flash(
                            self._("The form was uploaded successfully")
                        )
                        self.returnRawViewResult = True
                        return HTTPFound(next_page)
                    else:
                        try:
                            root = etree.fromstring(output)
                            xml_errors = root.findall(".//error")
                            if xml_errors:
                                for a_error in xml_errors:
                                    error_code = a_error.get("code")
                                    if error_code == "TNS":
                                        error_type = 2
                                        table_name = a_error.get("table")
                                        c_from = a_error.get("from")
                                        c_to = a_error.get("to")
                                        errors.append(
                                            self._(
                                                'The repeat "{}" changed parent from "{}" to "{}". '
                                                "You must rename the repeat before merging".format(
                                                    table_name, c_from, c_to
                                                )
                                            )
                                        )
                                    if error_code == "TWP":
                                        error_type = 2
                                        table_name = a_error.get("table")
                                        c_from = a_error.get("from")
                                        errors.append(
                                            self._(
                                                'The parent repeat "{}" of repeat "{}" does not exist anymore.'
                                                ' You must rename the repeat "{}" before merging'.format(
                                                    c_from, table_name, table_name
                                                )
                                            )
                                        )
                                    if error_code == "FNS":
                                        error_type = 2
                                        table_name = a_error.get("table")
                                        field_name = a_error.get("field")
                                        errors.append(
                                            self._(
                                                'The field "{}" in table "{}" changed type. '
                                                "You must rename the field before merging.".format(
                                                    field_name, table_name
                                                )
                                            )
                                        )
                                    if error_code == "VNS":
                                        error_type = 1
                                        table_name = a_error.get("table")
                                        value_code = a_error.get("value")
                                        c_from = a_error.get("from")
                                        c_to = a_error.get("to")
                                        values_to_ignore.append(
                                            table_name + ":" + value_code
                                        )
                                        errors.append(
                                            self._(
                                                'The option "{}" in lookup table "{}" changed '
                                                'description from "{}" to "{}".'.format(
                                                    value_code, table_name, c_from, c_to
                                                )
                                            )
                                        )
                                    if error_code == "RNS":
                                        error_type = 2
                                        table_name = a_error.get("table")
                                        field_code = a_error.get("field")
                                        errors.append(
                                            self._(
                                                'The field "{}" in table "{}" changed relationship'.format(
                                                    field_code, table_name
                                                )
                                            )
                                        )
                        except Exception as e:
                            send_error_to_technical_team(
                                self.request,
                                "Error while parsing the result of a merge. "
                                "Merging form {} into {} in project {}. \nAccount: {}\nError: \n{}".format(
                                    new_form_id, form_id, project_id, user_id, str(e)
                                ),
                            )
                            self.add_error(
                                self._(
                                    "Unknown error while merging. A message has been sent to the support team and "
                                    "they will contact you ASAP."
                                )
                            )

                            self.delete_new_form(
                                odk_path,
                                user_id,
                                project_code,
                                project_id,
                                new_form_id,
                                new_form_data["directory"],
                            )

                            self.returnRawViewResult = True
                            return HTTPFound(self.request.url)

                        self.delete_new_form(
                            odk_path,
                            user_id,
                            project_code,
                            project_id,
                            new_form_id,
                            new_form_data["directory"],
                        )
                else:
                    self.delete_new_form(
                        odk_path,
                        user_id,
                        project_code,
                        project_id,
                        new_form_id,
                        new_form_data["directory"],
                    )
                    self.add_error(
                        self._("Unable to build the repository files for form: ")
                        + message
                    )
                    self.returnRawViewResult = True
                    return HTTPFound(self.request.url)
            else:
                self.add_error(self._("Unable to upload the form: ") + message)
                self.returnRawViewResult = True
                return HTTPFound(self.request.url)

        return {
            "userid": user_id,
            "formData": form_data,
            "projectDetails": project_details,
            "projcode": project_code,
            "formid": form_id,
            "merge_errors": errors,
            "errortype": error_type,
            "valuestoignore": ";".join(values_to_ignore),
            "inputfilename": input_file_name,
        }
