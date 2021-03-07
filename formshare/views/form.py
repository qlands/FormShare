import json
import logging
import os
import shutil
from hashlib import md5
import formshare.plugins as p
from lxml import etree
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.response import FileResponse
import datetime
import uuid
import glob
import mimetypes
import formshare.plugins as plugins
from formshare.processes.db import (
    get_project_id_from_name,
    get_form_details,
    get_form_data,
    update_form,
    delete_form,
    add_file_to_form,
    get_form_files,
    remove_file_from_form,
    get_all_assistants,
    add_assistant_to_form,
    get_form_assistants,
    update_assistant_privileges,
    remove_assistant_from_form,
    get_project_groups,
    add_group_to_form,
    get_form_groups,
    update_group_privileges,
    remove_group_from_form,
    get_form_xls_file,
    set_form_status,
    get_assigned_assistants,
    get_form_directory,
    get_form_processing_products,
    get_task_status,
    get_output_by_task,
    collect_maps_for_schema,
    get_create_xml_for_schema,
    get_insert_xml_for_schema,
    get_form_directories_for_schema,
    get_forms_for_schema,
    get_media_files,
    get_maintable_information,
)
from formshare.processes.elasticsearch.record_index import delete_record_index
from formshare.processes.elasticsearch.repository_index import (
    delete_dataset_index,
    get_number_of_datasets_with_gps,
)
from formshare.processes.email.send_email import send_error_to_technical_team
from formshare.processes.odk.api import (
    get_odk_path,
    upload_odk_form,
    retrieve_form_file,
    update_odk_form,
    get_missing_support_files,
    import_external_data,
    create_repository,
    merge_versions,
    check_jxform_file,
    store_file_in_directory,
)
from formshare.processes.odk.processes import get_form_primary_key
from formshare.processes.storage import store_file, delete_stream, delete_bucket
from formshare.processes.submission.api import (
    get_submission_media_files,
    json_to_csv,
    get_gps_points_from_form,
    get_tables_from_form,
    get_dataset_info_from_file,
    get_fields_from_table,
    list_submission_media_files,
    get_submission_media_file,
)
from formshare.products import get_form_products
from formshare.products import stop_task
from formshare.products.export.csv import (
    generate_public_csv_file,
    generate_private_csv_file,
)
from formshare.products.export.kml import generate_kml_file
from formshare.products.export.media import generate_media_zip_file
from formshare.products.export.xlsx import (
    generate_public_xlsx_file,
    generate_private_xlsx_file,
)
from formshare.views.classes import PrivateView

log = logging.getLogger("formshare")


class FormDetails(PrivateView):
    def report_critical_error(self, user, project, form, error_code, message):
        send_error_to_technical_team(
            self.request,
            "Error while creating the repository for form {} in "
            "project {}. \nAccount: {}\nError: {}\nMessage: {}\n".format(
                form, project, user, error_code, message
            ),
        )
        log.error(
            "Error while creating the repository for form {} in "
            "project {}. \nAccount: {}\nError: {}\nMessage: {}\n".format(
                form, project, user, error_code, message
            )
        )

    def check_repository(self, survey_file, primary_key, external_files):
        odk_dir = get_odk_path(self.request)
        uid = str(uuid.uuid4())
        paths = ["tmp", uid]
        os.makedirs(os.path.join(odk_dir, *paths))

        paths = ["tmp", uid, "create.xml"]
        create_file = os.path.join(odk_dir, *paths)

        paths = ["tmp", uid, "insert.xml"]
        insert_file = os.path.join(odk_dir, *paths)

        return check_jxform_file(
            self.request,
            survey_file,
            create_file,
            insert_file,
            primary_key,
            external_files,
        )

    def check_merge(
        self,
        user_id,
        project_id,
        new_form_id,
        new_form_directory,
        old_form_id,
        old_create_file,
        old_insert_file,
        old_form_pkey,
        old_form_deflang,
        old_form_othlangs,
    ):
        errors = []
        odk_path = get_odk_path(self.request)
        created, message = create_repository(
            self.request,
            user_id,
            project_id,
            new_form_id,
            odk_path,
            new_form_directory,
            old_form_pkey,
            False,
            old_form_deflang,
            old_form_othlangs,
            True,
        )
        if created == 0:
            new_create_file = os.path.join(
                odk_path, *["forms", new_form_directory, "repository", "create.xml"]
            )
            new_insert_file = os.path.join(
                odk_path, *["forms", new_form_directory, "repository", "insert.xml"]
            )

            merged, output = merge_versions(
                self.request,
                odk_path,
                new_form_directory,
                new_create_file,
                new_insert_file,
                old_create_file,
                old_insert_file,
            )
            if merged == 0:
                form_data = {"form_abletomerge": 1}
                update_form(self.request, project_id, new_form_id, form_data)
                return True, ""
            else:
                try:
                    root = etree.fromstring(output)
                    xml_errors = root.findall(".//error")
                    if xml_errors:
                        for a_error in xml_errors:
                            error_code = a_error.get("code")
                            if error_code == "TNS":
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
                                table_name = a_error.get("table")
                                field_name = a_error.get("field")
                                errors.append(
                                    self._(
                                        'The variable "{}" in repeat "{}" changed type. '
                                        "You must rename the variable before merging.".format(
                                            field_name, table_name
                                        )
                                    )
                                )
                            if error_code == "VNS":
                                form_data = {"form_abletomerge": 1}
                                update_form(
                                    self.request, project_id, new_form_id, form_data
                                )
                                return True, ""
                            if error_code == "RNS":
                                table_name = a_error.get("table")
                                field_code = a_error.get("field")
                                errors.append(
                                    self._(
                                        'The variable "{}" in repeat "{}" has a different choice list name. '
                                        "You must rename the variable before merging. ".format(
                                            field_code, table_name
                                        )
                                    )
                                )
                except Exception as e:
                    send_error_to_technical_team(
                        self.request,
                        "Error while parsing the result of a merge. "
                        "Merging form {} into {} in project {}. \nAccount: {}\nError: \n{}".format(
                            new_form_id, old_form_id, project_id, user_id, str(e)
                        ),
                    )
                    errors.append(
                        self._(
                            "Unknown error while merging. A message has been sent to the support team and "
                            "they will contact you ASAP."
                        )
                    )
        else:
            if created == 1:
                # Internal error: Report issue
                self.report_critical_error(
                    user_id, project_id, new_form_id, created, message
                )
                errors.append(
                    self._(
                        "An unexpected error occurred while processing the merge. "
                        "An email has been sent to the technical team and they will contact you ASAP."
                    )
                )
            if created == 2:
                # 64 or more relationships. Report issue because this was checked before
                self.report_critical_error(
                    user_id, project_id, new_form_id, created, message
                )
                errors.append(
                    self._(
                        "An unexpected error occurred while processing the merge. "
                        "An email has been sent to the technical team and they will contact you ASAP."
                    )
                )
            if 3 <= created <= 6:
                self.report_critical_error(
                    user_id, project_id, new_form_id, created, message
                )
                errors.append(
                    self._(
                        "An unexpected error occurred while processing the merge. "
                        "An email has been sent to the technical team and they will contact you ASAP."
                    )
                )
            if created == 14:
                txt_message = 'The following files have invalid characters like extra ". Only _ is allowed : \n'
                root = etree.fromstring(message)
                files_with_problems = root.findall(".//file")
                if files_with_problems:
                    for a_file in files_with_problems:
                        txt_message = (
                            txt_message
                            + "\t"
                            + os.path.basename(a_file.get("name", ""))
                            + "\n"
                        )
                errors.append(txt_message)
            if created == 15:
                txt_message = "The following files have an invalid structure: \n"
                root = etree.fromstring(message)
                files_with_problems = root.findall(".//file")
                if files_with_problems:
                    for a_file in files_with_problems:
                        txt_message = txt_message + "\t" + a_file.get("name", "") + "\n"
                errors.append(txt_message)
            if created == 9:
                # Duplicated options
                root = etree.fromstring(message)
                duplicated_items = root.findall(".//duplicatedItem")
                txt_message = (
                    self._("FormShare thoroughly checks your ODK for inconsistencies.")
                    + "\n"
                )
                txt_message = (
                    txt_message
                    + self._(
                        "The following options are duplicated in the ODK you just submitted:"
                    )
                    + "\n"
                )
                if duplicated_items:
                    for a_item in duplicated_items:
                        variable_name = a_item.get("variableName")
                        duplicated_option = a_item.get("duplicatedValue")
                        txt_message = (
                            txt_message
                            + "\t"
                            + self._("Option {} in variable {}").format(
                                duplicated_option, variable_name
                            )
                            + "\n"
                        )
                errors.append(txt_message)

            if created == 10:
                # Primary key not found
                errors.append(
                    self._(
                        "The primary key was not found in the ODK form or is inside a repeat"
                    )
                )
            if created == 11 or created == 12:
                # Parsing XML error
                if created == 11:
                    txt_message = (
                        self._(
                            "The following files are missing and you need to attach them:"
                        )
                        + "\n"
                    )
                else:
                    txt_message = (
                        self._(
                            "There was an error while processing some of the XML resource files:"
                        )
                        + "\n"
                    )
                root = etree.fromstring(message)
                file_list = root.findall(".//file")
                if file_list:
                    for a_file in file_list:
                        txt_message = txt_message + "\t" + a_file.get("name") + "\n"
                errors.append(txt_message)
            if 13 <= created <= 15:
                # Parsing CSV error
                if created == 13:
                    txt_message = (
                        self._(
                            "The following files are missing and you need to attach them:"
                        )
                        + "\n"
                    )
                else:
                    if created == 13:
                        txt_message = (
                            self._(
                                "The following CSV resource files have invalid characters:"
                            )
                            + "\n"
                        )
                    else:
                        txt_message = (
                            self._(
                                "There was an error while processing some of the CSV resource files:"
                            )
                            + "\n"
                        )
                root = etree.fromstring(message)
                file_list = root.findall(".//file")
                if file_list:
                    for a_file in file_list:
                        txt_message = txt_message + "\t" + a_file.get("name") + "\n"
                errors.append(txt_message)
            if created == 16:
                # Search error. Report issue
                self.report_critical_error(
                    user_id, project_id, new_form_id, created, message
                )
                errors.append(
                    self._(
                        "An unexpected error occurred while processing the merge. "
                        "An email has been sent to the technical team and they will contact you ASAP."
                    )
                )
            if created == 17:
                # Primary key is invalid
                errors.append(self._("The primary key is invalid."))
            if created == 18:
                # Duplicate tables. Report issue because this was checked before
                self.report_critical_error(
                    user_id, project_id, new_form_id, created, message
                )
                errors.append(
                    self._(
                        "An unexpected error occurred while processing the merge. "
                        "An email has been sent to the technical team and they will contact you ASAP."
                    )
                )
            if created == 19:
                # Duplicate fields. Report issue because this was checked before
                self.report_critical_error(
                    user_id, project_id, new_form_id, created, message
                )
                errors.append(
                    self._(
                        "An unexpected error occurred while processing the merge. "
                        "An email has been sent to the technical team and they will contact you ASAP."
                    )
                )
            if created == 20:
                # Invalid fields. Report issue because this was checked before
                self.report_critical_error(
                    user_id, project_id, new_form_id, created, message
                )
                errors.append(
                    self._(
                        "An unexpected error occurred while processing the merge. "
                        "An email has been sent to the technical team and they will contact you ASAP."
                    )
                )
            if created == 21:
                # Duplicated lookups
                txt_message = (
                    self._("The following choices are duplicated in your ODK:") + "\n"
                )
                root = etree.fromstring(message)
                duplicated_tables = root.findall(".//table")
                if duplicated_tables:
                    for a_table in duplicated_tables:
                        txt_message = (
                            txt_message
                            + "- "
                            + a_table.get("name")
                            + " "
                            + self._("with the following duplicates:")
                            + "\n"
                        )
                        duplicated_names = a_table.findall(".//duplicate")
                        if duplicated_names:
                            for a_name in duplicated_names:
                                txt_message = (
                                    txt_message + "\t" + a_name.get("name") + "\n"
                                )
                        txt_message = txt_message + "\t"
                errors.append(txt_message)

        error_string = json.dumps({"errors": errors})
        # form_data = {"form_abletomerge": 0, "form_mergerrors": error_string}
        # update_form(self.request, project_id, new_form_id, form_data)
        return False, error_string

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

        if project_details["access_type"] > 4:
            raise HTTPNotFound

        form_data = get_form_details(self.request, user_id, project_id, form_id)
        if form_data is not None:
            form_files = get_form_files(self.request, project_id, form_id)
            if self.user is not None:
                assistants = get_all_assistants(self.request, user_id)
            else:
                assistants = []
            form_assistants = get_form_assistants(self.request, project_id, form_id)
            groups = get_project_groups(self.request, project_id)
            form_groups = get_form_groups(self.request, project_id, form_id)
            if form_data["form_reqfiles"] is not None:
                required_files = form_data["form_reqfiles"].split(",")
                missing_files = get_missing_support_files(
                    self.request, project_id, form_id, required_files, form_files
                )
            else:
                missing_files = []

            if (
                len(missing_files) == 0
                and form_data["form_reqfiles"] is not None
                and form_data["form_schema"] is None
                and form_data["form_pkey"] is not None
                and form_data["form_repositorypossible"] == -1
            ):
                odk_dir = get_odk_path(self.request)
                media_files = get_media_files(self.request, project_id, form_id)
                tmp_uid = str(uuid.uuid4())
                target_dir = os.path.join(odk_dir, *["tmp", tmp_uid])
                os.makedirs(target_dir)
                for media_file in media_files:
                    store_file_in_directory(
                        self.request,
                        project_id,
                        form_id,
                        media_file.file_name,
                        target_dir,
                    )
                path = os.path.join(odk_dir, *["tmp", tmp_uid, "*.*"])
                files = glob.glob(path)
                media_files = []
                if files:
                    for aFile in files:
                        media_files.append(aFile)
                error, message = self.check_repository(
                    form_data["form_jsonfile"], form_data["form_pkey"], media_files
                )
                if error == 0:
                    if message == "":
                        form_data["form_repositorypossible"] = 1
                        form_update_data = {"form_repositorypossible": 1}
                        update_form(self.request, project_id, form_id, form_update_data)
                else:
                    form_data["form_repoErrors"] = message
                    form_data["form_repositorypossible"] = 0
            else:
                if (
                    form_data["form_reqfiles"] is None
                    or form_data["form_pkey"] is None
                    or form_data["form_schema"] is not None
                ):
                    if form_data["form_repositorypossible"] != 1:
                        form_data["form_repositorypossible"] = 1
                        form_update_data = {"form_repositorypossible": 1}
                        update_form(self.request, project_id, form_id, form_update_data)

            if (
                len(missing_files) == 0
                and form_data["form_abletomerge"] == -1
                and form_data["parent_form"] is not None
            ):
                able_to_merge, errors = self.check_merge(
                    user_id,
                    project_id,
                    form_id,
                    form_data["form_directory"],
                    form_data["parent_form_data"]["form_id"],
                    form_data["parent_form_data"]["form_createxmlfile"],
                    form_data["parent_form_data"]["form_insertxmlfile"],
                    form_data["parent_form_data"]["form_pkey"],
                    form_data["parent_form_data"]["form_deflang"],
                    form_data["parent_form_data"]["form_othlangs"],
                )
                if able_to_merge == 1:
                    form_data["form_abletomerge"] = 1
                else:
                    form_data["form_abletomerge"] = 0
                    form_data["form_mergerrors"] = errors
            merging_errors = {"errors": []}
            if form_data["form_abletomerge"] == 0:
                merging_errors = json.loads(form_data["form_mergerrors"])
            if form_data["form_reptask"] is not None:
                res_code, error = get_task_status(
                    self.request, form_data["form_reptask"]
                )
                task_data = {"rescode": res_code, "error": error}
            else:
                task_data = {"rescode": None, "error": None}

            if form_data["form_mergetask"] is not None:
                res_code, error = get_task_status(
                    self.request, form_data["form_mergetask"]
                )
                merge_task_data = {"rescode": res_code, "error": error}
            else:
                merge_task_data = {"rescode": None, "error": None}

            dictionary_data = get_tables_from_form(self.request, project_id, form_id)
            num_sensitive = 0
            num_tables = 0
            for a_table in dictionary_data:
                num_tables = num_tables + 1
                num_sensitive = num_sensitive + a_table.get("numsensitive", 0)
            if form_data["form_schema"] is None:
                forms = [form_id]
            else:
                forms = get_forms_for_schema(self.request, form_data["form_schema"])
            number_with_gps = get_number_of_datasets_with_gps(
                self.request.registry.settings, user_id, project_code, forms
            )
            products = get_form_products(self.request, project_id, form_id)
            return {
                "projectDetails": project_details,
                "formid": form_id,
                "formDetails": form_data,
                "userid": user_id,
                "formFiles": form_files,
                "assistants": assistants,
                "formassistants": form_assistants,
                "groups": groups,
                "formgroups": form_groups,
                "withgps": number_with_gps,
                "missingFiles": ", ".join(missing_files),
                "taskdata": task_data,
                "mergetaskdata": merge_task_data,
                "numsensitive": num_sensitive,
                "numtables": num_tables,
                "products": products,
                "processing": get_form_processing_products(
                    self.request, project_id, form_id, form_data["form_reptask"]
                ),
                "merging_errors": merging_errors,
            }
        else:
            raise HTTPNotFound


class AddNewForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
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

        if self.request.method == "POST":
            self.returnRawViewResult = True
            odk_path = get_odk_path(self.request)
            for_merging = False
            form_data = self.get_post_dict()
            if "form_target" not in form_data.keys():
                form_data["form_target"] = 0

            if "for_merging" in form_data.keys():
                form_data.pop("for_merging")
                for_merging = True

            form_data.pop("xlsx")

            if form_data["form_target"] == "":
                form_data["form_target"] = 0

            if not for_merging:
                if "form_pkey" not in form_data.keys():
                    next_page = self.request.params.get(
                        "next"
                    ) or self.request.route_url(
                        "project_details",
                        userid=project_details["owner"],
                        projcode=project_code,
                    )
                    self.add_error(self._("You need to indicate a primary key"))
                    return HTTPFound(next_page, headers={"FS_error": "true"})
            if for_merging:
                form_id = self.request.matchdict["formid"]
                primary_key = get_form_primary_key(self.request, project_id, form_id)
            else:
                primary_key = form_data.get("form_pkey", None)
            uploaded, message = upload_odk_form(
                self.request,
                project_id,
                user_id,
                odk_path,
                form_data,
                primary_key,
                for_merging,
            )

            if uploaded:
                next_page = self.request.route_url(
                    "form_details",
                    userid=project_details["owner"],
                    projcode=project_code,
                    formid=message,
                )
                self.request.session.flash(self._("The form was added successfully"))
                return HTTPFound(next_page)
            else:
                if not for_merging:
                    next_page = self.request.params.get(
                        "next"
                    ) or self.request.route_url(
                        "project_details",
                        userid=project_details["owner"],
                        projcode=project_code,
                    )
                else:
                    next_page = self.request.route_url(
                        "form_details",
                        userid=project_details["owner"],
                        projcode=project_code,
                        formid=form_data["parent_form"],
                    )
                self.add_error(self._("Unable to upload the form: ") + message)
                return HTTPFound(next_page, headers={"FS_error": "true"})

        else:
            raise HTTPNotFound


class UploadNewVersion(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

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

        if self.request.method == "POST":
            self.returnRawViewResult = True
            odk_path = get_odk_path(self.request)

            form_data = self.get_post_dict()
            if "form_target" not in form_data.keys():
                form_data["form_target"] = 0

            form_data.pop("xlsx")

            if "form_pkey" not in form_data.keys():
                next_page = self.request.route_url(
                    "form_details",
                    userid=project_details["owner"],
                    projcode=project_code,
                    formid=form_id,
                )
                self.add_error(self._("You need to specify a primary key"))
                return HTTPFound(next_page, headers={"FS_error": "true"})

            primary_key = form_data.get("form_pkey", None)

            updated, message = update_odk_form(
                self.request,
                user_id,
                project_id,
                form_id,
                odk_path,
                form_data,
                primary_key,
            )

            if updated:
                delete_dataset_index(
                    self.request.registry.settings, user_id, project_code, form_id
                )
                next_page = self.request.route_url(
                    "form_details",
                    userid=project_details["owner"],
                    projcode=project_code,
                    formid=form_id,
                )
                self.request.session.flash(
                    self._("The ODK form was successfully updated")
                )
                return HTTPFound(next_page)
            else:
                next_page = self.request.route_url(
                    "form_details",
                    userid=project_details["owner"],
                    projcode=project_code,
                    formid=form_id,
                )
                self.add_error(self._("Unable to upload the form: ") + message)
                return HTTPFound(next_page, headers={"FS_error": "true"})

        else:
            raise HTTPNotFound


class EditForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject["project_id"] == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")
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

        if self.request.method == "POST":
            form_data = self.get_post_dict()
            if "form_accsub" in form_data.keys():
                form_data["form_accsub"] = 1
            else:
                form_data["form_accsub"] = 0

            if form_data["form_target"] == "":
                form_data["form_target"] = 0

            next_page = self.request.params.get("next") or self.request.route_url(
                "form_details", userid=user_id, projcode=project_code, formid=form_id
            )
            edited, message = update_form(self.request, project_id, form_id, form_data)
            if edited:
                self.request.session.flash(self._("The form was edited successfully"))
                self.returnRawViewResult = True
                return HTTPFound(next_page)
            else:
                self.append_to_errors(message)
        else:
            form_data = get_form_data(self.request, project_id, form_id)
            if form_data is None:
                raise HTTPNotFound
        return {
            "formData": form_data,
            "projectDetails": project_details,
            "userid": user_id,
            "formid": form_id,
        }


class DeleteForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject["project_id"] == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound
        if (
            project_details["access_type"] <= 2
            or form_data["form_pubby"] == self.user.id
        ):
            if self.request.method == "POST":
                next_page = self.request.params.get("next") or self.request.route_url(
                    "project_details", userid=user_id, projcode=project_code
                )

                continue_delete = True
                message = ""
                for a_plugin in plugins.PluginImplementations(plugins.IForm):
                    continue_delete, message = a_plugin.before_deleting_form(
                        self.request, "ODK", user_id, project_id, form_id
                    )
                    break  # Only one plugin is executed
                if continue_delete:
                    deleted, forms_deleted, message = delete_form(
                        self.request, project_id, form_id
                    )
                    if deleted:
                        for a_plugin in plugins.PluginImplementations(plugins.IForm):
                            a_plugin.after_deleting_form(
                                self.request, "ODK", user_id, project_id, form_id
                            )

                        for a_deleted_form in forms_deleted:
                            delete_dataset_index(
                                self.request.registry.settings,
                                user_id,
                                project_code,
                                a_deleted_form["form_id"],
                            )
                            delete_record_index(
                                self.request.registry.settings,
                                user_id,
                                project_code,
                                a_deleted_form["form_id"],
                            )
                            try:
                                form_directory = a_deleted_form["form_directory"]
                                paths = ["forms", form_directory]
                                odk_dir = get_odk_path(self.request)
                                form_directory = os.path.join(odk_dir, *paths)
                                string_date = datetime.datetime.now().strftime(
                                    "%Y_%m_%d:%H_%M_%S"
                                )
                                deleted_string = "_deleted_by_{}_on_{}".format(
                                    self.userID, string_date
                                )
                                if os.path.exists(form_directory):
                                    shutil.move(
                                        form_directory, form_directory + deleted_string
                                    )
                                log.info(
                                    "FormDelete: Form {} in project {} of user {} was deleted by {} on {}".format(
                                        form_id,
                                        project_id,
                                        user_id,
                                        self.userID,
                                        string_date,
                                    )
                                )
                            except Exception as e:
                                log.error(
                                    "Error {} while removing form {} in project {}. Cannot delete directory {}".format(
                                        str(e),
                                        a_deleted_form["form_id"],
                                        project_id,
                                        a_deleted_form["form_directory"],
                                    )
                                )
                            bucket_id = project_id + a_deleted_form["form_id"]
                            bucket_id = md5(bucket_id.encode("utf-8")).hexdigest()
                            delete_bucket(self.request, bucket_id)

                        self.request.session.flash(
                            self._("The form was deleted successfully")
                        )
                        self.returnRawViewResult = True
                        return HTTPFound(next_page)
                    else:
                        self.returnRawViewResult = True
                        self.add_error(message)
                        return HTTPFound(next_page, headers={"FS_error": "true"})
                else:
                    self.returnRawViewResult = True
                    self.add_error(message)
                    return HTTPFound(next_page, headers={"FS_error": "true"})
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class ActivateForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject["project_id"] == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            next_page = self.request.params.get("next") or self.request.route_url(
                "project_details", userid=user_id, projcode=project_code
            )
            changed, message = set_form_status(self.request, project_id, form_id, 1)
            if changed:
                self.request.session.flash(
                    self._("The form was activated successfully")
                )
                self.returnRawViewResult = True
                return HTTPFound(next_page)
            else:
                self.returnRawViewResult = True
                self.add_error(message)
                return HTTPFound(next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class DeActivateForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject["project_id"] == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            next_page = self.request.params.get("next") or self.request.route_url(
                "project_details", userid=user_id, projcode=project_code
            )
            changed, message = set_form_status(self.request, project_id, form_id, 0)
            if changed:
                self.request.session.flash(
                    self._("The form was deactivated successfully")
                )
                self.returnRawViewResult = True
                return HTTPFound(next_page)
            else:
                self.returnRawViewResult = True
                self.add_error(message)
                return HTTPFound(next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class AddFileToForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

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
            raise HTTPNotFound  # Don't edit a public or a project that I am just a member

        current_form_data = get_form_data(self.request, project_id, form_id)
        if current_form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            files = self.request.POST.getall("filetoupload")
            form_data = self.get_post_dict()
            self.returnRawViewResult = True

            next_page = self.request.route_url(
                "form_details", userid=user_id, projcode=project_code, formid=form_id
            )

            error = False
            message = ""
            if "overwrite" in form_data.keys():
                overwrite = True
            else:
                overwrite = False
            for file in files:
                try:
                    file_name = file.filename
                    if os.path.isabs(file_name):
                        file_name = os.path.basename(file_name)
                    slash_index = file_name.find("\\")
                    if slash_index >= 0:
                        file_name = file_name[slash_index + 1 :]
                    md5sum = md5(file.file.read()).hexdigest()
                    added, message = add_file_to_form(
                        self.request, project_id, form_id, file_name, overwrite, md5sum
                    )
                    if added:
                        file.file.seek(0)
                        bucket_id = project_id + form_id
                        bucket_id = md5(bucket_id.encode("utf-8")).hexdigest()
                        store_file(self.request, bucket_id, file_name, file.file)

                        if current_form_data["form_reqfiles"] is not None:
                            required_files = current_form_data["form_reqfiles"].split(
                                ","
                            )
                            if (
                                file_name in required_files
                                and current_form_data["form_schema"] is None
                            ):
                                form_update_data = {
                                    "form_repositorypossible": -1,
                                    "form_reptask": None,
                                }
                                if current_form_data["parent_form"] is not None:
                                    form_update_data["form_abletomerge"] = -1
                                    form_update_data["form_mergetask"] = None
                                update_form(
                                    self.request, project_id, form_id, form_update_data
                                )

                    else:
                        error = True
                        break
                except Exception as e:
                    log.error(
                        "Error while uploading files into form {} of project {}. Error: {}".format(
                            form_id, project_id, str(e)
                        )
                    )
                    error = True
                    if len(files) == 1:
                        if files[0] == b"":
                            message = self._("No files were attached")
                        else:
                            message = self._(
                                "Error {} encountered. A log entry has been produced".format(
                                    type(e).__name__
                                )
                            )

                    else:
                        message = self._(
                            "Error {} encountered. A log entry has been produced".format(
                                type(e).__name__
                            )
                        )
            if not error:
                if len(files) == 1:
                    self.request.session.flash(
                        self._("The file was uploaded successfully")
                    )
                else:
                    self.request.session.flash(
                        self._("The files were uploaded successfully")
                    )
                return HTTPFound(location=next_page)
            else:
                self.add_error(message)
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})

        else:
            raise HTTPNotFound


class RemoveFileFromForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        file_name = self.request.matchdict["filename"]
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
            raise HTTPNotFound  # Don't edit a public or a project that I am just a member

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            self.returnRawViewResult = True
            if form_data["form_reqfiles"] is not None:
                if form_data["form_schema"] is not None:
                    required_files = form_data["form_reqfiles"].split(",")
                    if file_name in required_files:
                        self.add_error(
                            self._(
                                "You cannot remove this file because it is required by the repository"
                            )
                        )
                        next_page = self.request.route_url(
                            "form_details",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                        return HTTPFound(
                            location=next_page, headers={"FS_error": "true"}
                        )

            next_page = self.request.route_url(
                "form_details", userid=user_id, projcode=project_code, formid=form_id
            )
            removed, message = remove_file_from_form(
                self.request, project_id, form_id, file_name
            )
            if removed:
                bucket_id = project_id + form_id
                bucket_id = md5(bucket_id.encode("utf-8")).hexdigest()
                delete_stream(self.request, bucket_id, file_name)
                self.request.session.flash(self._("The files was removed successfully"))
                if form_data["form_reqfiles"] is not None:
                    required_files = form_data["form_reqfiles"].split(",")
                    if file_name in required_files and form_data["form_schema"] is None:
                        form_update_data = {
                            "form_repositorypossible": -1,
                            "form_reptask": None,
                        }
                        if form_data["parent_form"] is not None:
                            form_update_data["form_abletomerge"] = -1
                            form_update_data["form_mergetask"] = None
                        update_form(self.request, project_id, form_id, form_update_data)

                return HTTPFound(location=next_page)
            else:
                self.add_error(message)
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class FormStoredFile(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        file_name = self.request.matchdict["filename"]
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

        if project_details["access_type"] > 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
            if project_found:
                self.returnRawViewResult = True
                return retrieve_form_file(self.request, project_id, form_id, file_name)
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class AddAssistant(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            assistant_data = self.get_post_dict()
            if assistant_data.get("coll_id", "") != "":
                parts = assistant_data["coll_id"].split("|")
                assistant_data["project_id"] = parts[0]
                assistant_data["coll_id"] = parts[1]
                if len(parts) == 2:
                    continue_creation = True
                    for plugin in p.PluginImplementations(p.IFormAccess):
                        (
                            data,
                            continue_creation,
                            error_message,
                        ) = plugin.before_giving_access(
                            self.request,
                            user_id,
                            project_id,
                            form_id,
                            assistant_data["project_id"],
                            assistant_data["coll_id"],
                            assistant_data,
                        )
                        if not continue_creation:
                            self.add_error(error_message)
                        else:
                            assistant_data = data
                        break  # Only one plugging will be called to extend before_giving_access
                    if continue_creation:
                        added, message = add_assistant_to_form(
                            self.request, project_id, form_id, assistant_data
                        )
                        if added:
                            for plugin in p.PluginImplementations(p.IFormAccess):
                                plugin.after_giving_access(
                                    self.request,
                                    user_id,
                                    project_id,
                                    form_id,
                                    assistant_data["project_id"],
                                    assistant_data["coll_id"],
                                    assistant_data,
                                )

                            self.request.session.flash(
                                self._("The assistant was added successfully")
                            )
                            next_page = self.request.route_url(
                                "form_details",
                                userid=user_id,
                                projcode=project_code,
                                formid=form_id,
                            )
                            return HTTPFound(location=next_page)
                        else:
                            self.add_error(message)
                            next_page = self.request.route_url(
                                "form_details",
                                userid=user_id,
                                projcode=project_code,
                                formid=form_id,
                            )
                            return HTTPFound(
                                location=next_page, headers={"FS_error": "true"}
                            )
                    else:
                        next_page = self.request.route_url(
                            "form_details",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                        return HTTPFound(
                            location=next_page, headers={"FS_error": "true"}
                        )

                else:
                    self.add_error("Error in submitted assistant")
                    next_page = self.request.route_url(
                        "form_details",
                        userid=user_id,
                        projcode=project_code,
                        formid=form_id,
                    )
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})
            else:
                self.add_error("The assistant cannot be empty")
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})

        else:
            raise HTTPNotFound


class EditAssistant(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        assistant_project_id = self.request.matchdict["projectid"]
        assistant_id = self.request.matchdict["assistantid"]
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            assistant_data = self.get_post_dict()
            continue_editing = True
            for plugin in p.PluginImplementations(p.IFormAccess):
                data, continue_editing, error_message = plugin.before_editing_access(
                    self.request,
                    user_id,
                    project_id,
                    form_id,
                    assistant_project_id,
                    assistant_id,
                    assistant_data,
                )
                if not continue_editing:
                    self.add_error(error_message)
                else:
                    assistant_data = data
                break  # Only one plugging will be called to extend before_editing_access
            if continue_editing:
                updated, message = update_assistant_privileges(
                    self.request,
                    project_id,
                    form_id,
                    assistant_project_id,
                    assistant_id,
                    assistant_data,
                )
                if updated:
                    for plugin in p.PluginImplementations(p.IFormAccess):
                        plugin.after_editing_access(
                            self.request,
                            user_id,
                            project_id,
                            form_id,
                            assistant_project_id,
                            assistant_id,
                            assistant_data,
                        )

                    self.request.session.flash(
                        self._("The information was changed successfully")
                    )
                    next_page = self.request.route_url(
                        "form_details",
                        userid=user_id,
                        projcode=project_code,
                        formid=form_id,
                    )
                    return HTTPFound(location=next_page)
                else:
                    self.add_error(message)
                    next_page = self.request.route_url(
                        "form_details",
                        userid=user_id,
                        projcode=project_code,
                        formid=form_id,
                    )
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})
            else:
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class RemoveAssistant(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        assistant_project_id = self.request.matchdict["projectid"]
        assistant_id = self.request.matchdict["assistantid"]
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            continue_remove = True
            for plugin in p.PluginImplementations(p.IFormAccess):
                continue_remove, error_message = plugin.before_revoking_access(
                    self.request,
                    user_id,
                    project_id,
                    form_id,
                    assistant_project_id,
                    assistant_id,
                )
                if not continue_remove:
                    self.add_error(error_message)
                break  # Only one plugging will be called to extend before_revoking_access
            if continue_remove:
                removed, message = remove_assistant_from_form(
                    self.request,
                    project_id,
                    form_id,
                    assistant_project_id,
                    assistant_id,
                )
                if removed:
                    for plugin in p.PluginImplementations(p.IFormAccess):
                        plugin.after_revoking_access(
                            self.request,
                            user_id,
                            project_id,
                            form_id,
                            assistant_project_id,
                            assistant_id,
                        )
                    self.request.session.flash(
                        self._("The assistant was removed successfully")
                    )
                    next_page = self.request.route_url(
                        "form_details",
                        userid=user_id,
                        projcode=project_code,
                        formid=form_id,
                    )
                    return HTTPFound(location=next_page)
                else:
                    self.add_error(message)
                    next_page = self.request.route_url(
                        "form_details",
                        userid=user_id,
                        projcode=project_code,
                        formid=form_id,
                    )
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})
            else:
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class AddGroupToForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            assistant_data = self.get_post_dict()
            if "group_id" in assistant_data.keys():
                if assistant_data["group_id"] != "":
                    privilege = assistant_data["group_privilege"]
                    added, message = add_group_to_form(
                        self.request,
                        project_id,
                        form_id,
                        assistant_data["group_id"],
                        privilege,
                    )
                    if added:
                        self.request.session.flash(
                            self._("The group was added successfully")
                        )
                        next_page = self.request.route_url(
                            "form_details",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                        return HTTPFound(location=next_page)
                    else:
                        self.add_error(message)
                        next_page = self.request.route_url(
                            "form_details",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                        return HTTPFound(
                            location=next_page, headers={"FS_error": "true"}
                        )
                else:
                    self.add_error("The group cannot be empty")
                    next_page = self.request.route_url(
                        "form_details",
                        userid=user_id,
                        projcode=project_code,
                        formid=form_id,
                    )
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})
            else:
                self.add_error("The group cannot be empty")
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})

        else:
            raise HTTPNotFound


class EditFormGroup(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        group_id = self.request.matchdict["groupid"]
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            assistant_data = self.get_post_dict()
            privilege = assistant_data["group_privilege"]
            updated, message = update_group_privileges(
                self.request, project_id, form_id, group_id, privilege
            )
            if updated:
                self.request.session.flash(self._("The role was changed successfully"))
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page)
            else:
                self.add_error(message)
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class RemoveGroupForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        group_id = self.request.matchdict["groupid"]
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            removed, message = remove_group_from_form(
                self.request, project_id, form_id, group_id
            )
            if removed:
                self.request.session.flash(self._("The group was removed successfully"))
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page)
            else:
                self.add_error(message)
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            raise HTTPNotFound


class DownloadCSVData(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

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

        if project_details["access_type"] > 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        created, file = json_to_csv(self.request, project_id, form_id)
        if created:
            response = FileResponse(
                file, request=self.request, content_type="application/csv"
            )
            response.content_disposition = 'attachment; filename="' + form_id + '.csv"'
            return response
        else:
            self.add_error(file)
            next_page = self.request.params.get("next") or self.request.route_url(
                "form_details", userid=user_id, projcode=project_code, formid=form_id
            )
            return HTTPFound(location=next_page, headers={"FS_error": "true"})


class DownloadPublicXLSData(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if project_details["access_type"] >= 4:
            raise HTTPNotFound

        odk_dir = get_odk_path(self.request)
        form_directory = get_form_directory(self.request, project_id, form_id)
        generate_public_xlsx_file(
            self.request,
            self.user.id,
            project_id,
            form_id,
            odk_dir,
            form_directory,
            form_data["form_schema"],
        )

        next_page = self.request.route_url(
            "form_details",
            userid=user_id,
            projcode=project_code,
            formid=form_id,
            _query={"tab": "task", "product": "xlsx_public_export"},
            _anchor="products_and_tasks",
        )
        self.returnRawViewResult = True
        return HTTPFound(location=next_page)


class DownloadPrivateXLSData(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if project_details["access_type"] >= 4:
            raise HTTPNotFound

        odk_dir = get_odk_path(self.request)
        form_directory = get_form_directory(self.request, project_id, form_id)
        generate_private_xlsx_file(
            self.request,
            self.user.id,
            project_id,
            form_id,
            odk_dir,
            form_directory,
            form_data["form_schema"],
        )

        next_page = self.request.route_url(
            "form_details",
            userid=user_id,
            projcode=project_code,
            formid=form_id,
            _query={"tab": "task", "product": "xlsx_private_export"},
            _anchor="products_and_tasks",
        )
        self.returnRawViewResult = True
        return HTTPFound(location=next_page)


class DownloadXLSX(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

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

        if project_details["access_type"] > 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        xlsx_file = get_form_xls_file(self.request, project_id, form_id)
        response = FileResponse(
            xlsx_file, request=self.request, content_type="application/csv"
        )
        response.content_disposition = (
            'attachment; filename="' + os.path.basename(xlsx_file) + '"'
        )
        return response


class DownloadSubmissionFiles(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

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

        if project_details["access_type"] > 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound
        if form_data["form_schema"] is None:
            created, file = get_submission_media_files(
                self.request, project_id, form_id
            )
            if created:
                response = FileResponse(
                    file, request=self.request, content_type="application/zip"
                )
                response.content_disposition = (
                    'attachment; filename="' + form_id + '.zip"'
                )
                return response
            else:
                self.add_error(file)
                next_page = self.request.params.get("next") or self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
        else:
            get_form_directories = get_form_directories_for_schema(
                self.request, form_data["form_schema"]
            )
            odk_dir = get_odk_path(self.request)
            generate_media_zip_file(
                self.request,
                self.user.id,
                project_id,
                form_id,
                odk_dir,
                get_form_directories,
                form_data["form_schema"],
                form_data["form_pkey"],
            )
            next_page = self.request.params.get("next") or self.request.route_url(
                "form_details",
                userid=user_id,
                projcode=project_code,
                formid=form_id,
                _query={"tab": "task", "product": "media_export"},
                _anchor="products_and_tasks",
            )
            return HTTPFound(location=next_page)


class DownloadGPSPoints(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

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

        if project_details["access_type"] > 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        created, data = get_gps_points_from_form(
            self.request, user_id, project_code, form_id
        )
        return data


class DownloadKML(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        generate_kml_file(
            self.request, self.user.id, project_id, form_id, form_data["form_schema"],
        )
        next_page = self.request.params.get("next") or self.request.route_url(
            "form_details",
            userid=user_id,
            projcode=project_code,
            formid=form_id,
            _query={"tab": "task", "product": "kml_export"},
            _anchor="products_and_tasks",
        )
        return HTTPFound(location=next_page)


class DownloadPublicCSV(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound
        form_schema = form_data["form_schema"]
        maps_directory = collect_maps_for_schema(self.request, form_schema)
        create_xml_file = get_create_xml_for_schema(self.request, form_schema)
        insert_xml_file = get_insert_xml_for_schema(self.request, form_schema)

        generate_public_csv_file(
            self.request,
            self.user.id,
            project_id,
            form_id,
            form_schema,
            maps_directory,
            create_xml_file,
            insert_xml_file,
        )

        next_page = self.request.params.get("next") or self.request.route_url(
            "form_details",
            userid=user_id,
            projcode=project_code,
            formid=form_id,
            _query={"tab": "task", "product": "csv_public_export"},
            _anchor="products_and_tasks",
        )
        return HTTPFound(location=next_page)


class DownloadPrivateCSV(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        form_schema = form_data["form_schema"]
        maps_directory = collect_maps_for_schema(self.request, form_schema)
        create_xml_file = get_create_xml_for_schema(self.request, form_schema)
        insert_xml_file = get_insert_xml_for_schema(self.request, form_schema)

        generate_private_csv_file(
            self.request,
            self.user.id,
            project_id,
            form_id,
            form_data["form_schema"],
            maps_directory,
            create_xml_file,
            insert_xml_file,
        )

        next_page = self.request.params.get("next") or self.request.route_url(
            "form_details",
            userid=user_id,
            projcode=project_code,
            formid=form_id,
            _query={"tab": "task", "product": "csv_private_export"},
            _anchor="products_and_tasks",
        )
        return HTTPFound(location=next_page)


class ImportData(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is not None:
            if self.request.method == "POST":
                odk_path = get_odk_path(self.request)

                form_post_data = self.get_post_dict()
                if "file" in form_post_data.keys():
                    form_post_data.pop("file")
                parts = form_post_data["assistant"].split("@")
                import_type = int(form_post_data["import_type"])
                if "ignore_xform" in form_post_data:
                    ignore_xform = True
                else:
                    ignore_xform = False

                imported, message = import_external_data(
                    self.request,
                    user_id,
                    project_id,
                    form_id,
                    odk_path,
                    form_data["form_directory"],
                    form_data["form_schema"],
                    parts[0],
                    import_type,
                    ignore_xform,
                    form_post_data,
                )
                if imported:
                    next_page = self.request.route_url(
                        "form_details",
                        userid=user_id,
                        projcode=project_code,
                        formid=form_id,
                    )
                    self.returnRawViewResult = True
                    return HTTPFound(location=next_page)

            return {
                "projectDetails": project_details,
                "formid": form_id,
                "formDetails": form_data,
                "userid": user_id,
                "assistants": get_assigned_assistants(
                    self.request, project_id, form_id
                ),
            }
        else:
            raise HTTPNotFound


class StopTask(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        task_id = self.request.matchdict["taskid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject["project_id"] == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")
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

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            product_id, output_id = get_output_by_task(
                self.request, project_id, form_id, task_id
            )
            if product_id is not None:
                next_page = self.request.params.get("next") or self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query={"tab": "task", "product": product_id},
                )
                stopped, message = stop_task(
                    self.request, self.user.id, project_id, form_id, task_id
                )
                if stopped:
                    self.request.session.flash(
                        self._("The process was stopped successfully")
                    )
                    self.returnRawViewResult = True
                    return HTTPFound(next_page)
                else:
                    self.request.session.flash(
                        self._("FormShare was not able to stop the process") + "|error"
                    )
                    self.returnRawViewResult = True
                    return HTTPFound(next_page, headers={"FS_error": "true"})
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class GetSubMissionInfo(PrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        submission_id = self.request.matchdict["submissionid"]
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

        if project_details["access_type"] > 4:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)

        fields, checked = get_fields_from_table(
            self.request, project_id, form_id, "maintable", [], False
        )
        if form_data["form_schema"] is None:
            submission_info = get_dataset_info_from_file(
                self.request, project_id, form_id, submission_id
            )
        else:
            submission_info = get_maintable_information(
                self.request, project_id, form_id, submission_id
            )

        if submission_info is None:
            raise HTTPNotFound

        submission_data = []
        for key, value in submission_info.items():
            field_desc = None
            primary_key = False
            for a_field in fields:
                if form_data["form_schema"] is None:
                    if a_field["xmlcode"] == key:
                        field_desc = a_field["desc"]
                        if a_field["key"] == "true":
                            primary_key = True
                        break
                else:
                    if a_field["name"] == key:
                        field_desc = a_field["desc"]
                        if a_field["key"] == "true":
                            primary_key = True
                        break
            if field_desc is not None:
                submission_data.append(
                    {
                        "key": key,
                        "desc": field_desc,
                        "value": value,
                        "pkey": primary_key,
                    }
                )

        media_files = list_submission_media_files(
            self.request, project_id, form_id, submission_id
        )
        has_other_media = False
        for a_file in media_files:
            if not a_file["image"]:
                has_other_media = True
                break

        has_images = False
        for a_file in media_files:
            if a_file["image"]:
                has_images = True
                break

        return {
            "formData": form_data,
            "submissionData": submission_data,
            "submissionID": submission_id,
            "mediaFiles": media_files,
            "userid": user_id,
            "projcode": project_code,
            "formid": form_id,
            "submissionid": submission_id,
            "hasOtherMedia": has_other_media,
            "hasImages": has_images,
        }


class GetMediaFile(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        submission_id = self.request.matchdict["submissionid"]
        file_name = self.request.matchdict["filename"]
        thumbnail = self.request.params.get("thumbnail", None)
        if thumbnail is None:
            thumbnail = False
        else:
            thumbnail = True
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

        if project_details["access_type"] > 4:
            raise HTTPNotFound

        file = get_submission_media_file(
            self.request, project_id, form_id, submission_id, file_name, thumbnail
        )
        if file is None:
            raise HTTPNotFound
        file_type = mimetypes.guess_type(file)[0]
        if file_type is None:
            file_type = "application/octet-stream"
        response = FileResponse(file, request=self.request, content_type=file_type)
        response.content_disposition = 'attachment; filename="' + os.path.basename(file)
        return response
