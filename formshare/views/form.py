import datetime
import glob
import json
import logging
import mimetypes
import os
import re
import shutil
import uuid
from hashlib import md5

import formshare.plugins as p
import formshare.plugins as plugins
import pandas as pd
from formshare.processes.db import (
    get_project_id_from_name,
    get_form_details,
    get_form_data,
    update_form,
    delete_form,
    add_file_to_form,
    get_form_files,
    remove_file_from_form,
    form_file_exists,
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
    update_dictionary_tables,
    get_case_lookup_fields,
    add_case_lookup_field,
    remove_case_lookup_field,
    update_case_lookup_field_alias,
    get_field_details,
    delete_case_lookup_table,
    invalid_aliases,
    alias_exists,
    field_exists,
    get_form_partners,
    add_partner_to_form,
    update_partner_form_options,
    remove_partner_from_form,
    get_form_survey_file,
    get_form_xml_create_file,
    get_form_xml_insert_file,
    get_project_access_type,
    get_project_details,
    get_extended_project_details,
    get_number_of_case_creators,
    get_number_of_case_creators_with_repository,
    get_case_form,
    get_forms_number,
    is_csv_a_lookup,
    get_name_and_label_from_file,
    update_lookup_from_csv,
)
from formshare.processes.elasticsearch.record_index import delete_form_records
from formshare.processes.elasticsearch.repository_index import (
    delete_dataset_from_index,
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
from formshare.processes.odk.processes import get_form_primary_key, get_form_case_params
from formshare.processes.storage import (
    store_file,
    delete_stream,
    delete_bucket,
    get_temporary_file,
)
from formshare.processes.submission.api import (
    get_submission_media_files,
    json_to_csv,
    get_gps_points_from_form,
    get_tables_from_form,
    get_dataset_info_from_file,
    get_fields_from_table,
    list_submission_media_files,
    get_submission_media_file,
    get_tables_from_original_form,
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
from formshare.products.export.zip_csv import (
    generate_private_zip_csv_file,
    generate_public_zip_csv_file,
)
from formshare.products.export.zip_json import (
    generate_private_zip_json_file,
    generate_public_zip_json_file,
)
from formshare.views.classes import PrivateView
from lxml import etree
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.response import FileResponse

log = logging.getLogger("formshare")


class FormDetails(PrivateView):
    def report_critical_error(
        self, user, project, form, error_code, message
    ):  # pragma: no cover
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

            form_data = get_form_data(self.request, project_id, new_form_id)

            # If it is a case form and its follow up, activate or deactivate then
            # we modify the create XML file to:
            # - Link the form_caseselector of the form with the form_pkey of the creator form.
            # This will allow a proper merge between Forms
            if form_data["form_case"] == 1 and form_data["form_casetype"] > 1:
                form_creator = get_case_form(self.request, project_id)
                form_creator_data = get_form_data(
                    self.request, project_id, form_creator
                )
                creator_pkey_data = get_field_details(
                    self.request,
                    project_id,
                    form_creator,
                    "maintable",
                    form_creator_data["form_pkey"],
                )
                tree = etree.parse(new_create_file)
                root = tree.getroot()
                table = root.find(".//table[@name='maintable']")
                if table is not None:
                    field = table.find(
                        ".//field[@name='" + form_data["form_caseselector"] + "']"
                    )
                    if field is not None:
                        field.set("type", creator_pkey_data["field_type"])
                        field.set("size", str(creator_pkey_data["field_size"]))
                        field.set(
                            "rtable",
                            form_creator_data["form_schema"] + ".maintable",
                        )
                        field.set("rfield", form_creator_data["form_pkey"])
                        field.set("rname", "fk_" + str(uuid.uuid4()).replace("-", "_"))
                        field.set("rlookup", "false")
                        # Save the changes in the XML Create file
                        if not os.path.exists(new_create_file + ".case.bk"):
                            shutil.copy(new_create_file, new_create_file + ".case.bk")
                        tree.write(
                            new_create_file,
                            pretty_print=True,
                            xml_declaration=True,
                            encoding="utf-8",
                        )
                    else:  # pragma: no cover
                        #  This might not be possible to happen. Left here just in case
                        log.error(
                            "The selector field {} was not found in {}".format(
                                form_data["form_caseselector"], new_create_file
                            )
                        )
                        return (
                            1,
                            "The case selector field {} was not found in the ODK form".format(
                                form_data["form_caseselector"]
                            ),
                        )
                else:  # pragma: no cover
                    #  This might not be possible to happen. Left here just in case
                    log.error("Main table was not found in {}".format(new_create_file))
                    return (
                        1,
                        "Main table was not found in {}".format(new_create_file),
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
                return 0, ""
            else:
                try:
                    root = etree.fromstring(output)
                    xml_errors = root.findall(".//error")
                    if xml_errors:
                        fatal_error = False
                        for a_error in xml_errors:
                            error_code = a_error.get("code")
                            if error_code == "TNS":
                                fatal_error = True
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
                            if error_code == "TWP":  # pragma: no cover
                                #  We leave it here just in case.. TWP might not be possible.
                                fatal_error = True
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
                                fatal_error = True
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
                            if error_code == "RNS":
                                fatal_error = True
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
                        if not fatal_error:
                            form_data = {"form_abletomerge": 1}
                            update_form(
                                self.request, project_id, new_form_id, form_data
                            )
                            return 0, ""
                        else:
                            error_string = json.dumps({"errors": errors})
                            return 1, error_string
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
            # This might not happen. Left here just in case
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
            if created == 7:
                # Malformed language in the ODK Form. Report issue because this was checked before
                self.report_critical_error(
                    user_id, project_id, new_form_id, created, message
                )
                errors.append(
                    self._(
                        "An unexpected error occurred while processing the merge. "
                        "An email has been sent to the technical team and they will contact you ASAP."
                    )
                )
            if created == 8:
                # Options without labels. Report issue because this was checked before
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
                if created == 3:
                    errors.append(
                        self._(
                            "This new version of the form has multiple languages when the previous one did not."
                            '\n\nUse the "Fix language" button to set the languages in '
                            "this version of the ODK Form."
                        )
                    )
                if created == 4:
                    root = etree.fromstring(message)
                    language_array = root.findall(".//language")
                    error_message = self._(
                        "This version of the ODK Form differs in the languages used. "
                        "The following languages are undefined:\n\n"
                    )
                    for a_language in language_array:
                        error_message = (
                            error_message + "\t" + a_language.get("name", "") + "\n"
                        )
                    error_message = (
                        error_message
                        + '\nUse the "Fix language" button to set the languages in this '
                        "version of the ODK Form."
                    )
                    errors.append(error_message)
                if created != 3 and created != 4:
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
                txt_message = (
                    'The following files have invalid characters like : in the column heads". '
                    "Only _ is allowed. \n"
                )
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
                    if created == 14:
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
                        "An unexpected error occurred while processing the search expression. "
                        "An email has been sent to the technical team and they will contact you ASAP."
                    )
                )
            if created == 17:
                # Primary key is invalid
                errors.append(
                    self._(
                        "The variable to control duplicate submissions has an invalid type. "
                        "E.g., the variable cannot be note, picture, video, sound, select_multiple, "
                        "or geo-spacial. The most appropriate types are text, datetime, barcode, "
                        "calculate, select_one, or integer."
                    )
                )
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
            if created == 25:
                txt_message = self._(
                    "This ODK form mixes coded and not coded languages. "
                    "For example label::English (en) and label::Español. "
                    "You need to code all the labels that are marked for translation."
                )
                errors.append(txt_message)
            if created == 24:
                # Table names with more than 64 characters
                txt_message = (
                    self._(
                        "FormShare needs you to shorten the name of some of your tables."
                    )
                    + "\n"
                )
                txt_message = (
                    txt_message
                    + self._(
                        "The following tables have a name longer than 64 characters:"
                    )
                    + "\n"
                )
                root = etree.fromstring(message)
                tables_with_name_error = root.findall(".//table")
                if tables_with_name_error:
                    for a_table in tables_with_name_error:
                        table_name = a_table.get("name")
                        table_msel = a_table.get("msel")
                        if table_msel == "false":
                            txt_message = txt_message + "\t" + table_name + "\n"
                        else:
                            parts = table_name.split("_msel_")
                            txt_message = (
                                txt_message
                                + "\t"
                                + parts[0]
                                + " with select "
                                + parts[1]
                                + "\n"
                            )
                    txt_message = (
                        txt_message
                        + "\n"
                        + self._(
                            "Please shorten the name of the tables and/or the selects and try again."
                        )
                    )
                errors.append(txt_message)
            if created == 22:
                errors.append(message)
            if created == 23:
                errors.append(message)

        error_string = json.dumps({"errors": errors})
        # form_data = {"form_abletomerge": 0, "form_mergerrors": error_string}
        # update_form(self.request, project_id, new_form_id, form_data)
        return created, error_string

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            access_type = get_project_access_type(
                self.request, project_id, user_id, self.user.login
            )
            if access_type > 4:
                raise HTTPNotFound
            project_details = get_extended_project_details(
                self.request, user_id, project_id
            )
            project_details["access_type"] = access_type
        else:
            raise HTTPNotFound

        form_data = get_form_details(self.request, user_id, project_id, form_id)
        if form_data is not None:
            if form_data["form_schema"] is not None:
                if form_data["form_hasdictionary"] == 0:  # pragma: no cover
                    updated = update_dictionary_tables(
                        self.request, project_id, form_id
                    )
                    if updated:
                        form_dict_data = {"form_hasdictionary": 1}
                        update_form(self.request, project_id, form_id, form_dict_data)

            form_files = get_form_files(self.request, project_id, form_id)

            assistants = get_all_assistants(self.request, user_id, project_id)

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
            merge_language_problem = False
            if (
                len(missing_files) == 0
                and form_data["form_abletomerge"] == -1
                and form_data["parent_form"] is not None
            ):
                if form_data["form_mergelngerror"] != 2:
                    def_language_to_use = form_data["parent_form_data"]["form_deflang"]
                    other_languages_to_use = form_data["parent_form_data"][
                        "form_othlangs"
                    ]
                else:
                    def_language_to_use = form_data["form_deflang"]
                    other_languages_to_use = form_data["form_othlangs"]
                able_to_merge, errors = self.check_merge(
                    user_id,
                    project_id,
                    form_id,
                    form_data["form_directory"],
                    form_data["parent_form_data"]["form_id"],
                    form_data["parent_form_data"]["form_createxmlfile"],
                    form_data["parent_form_data"]["form_insertxmlfile"],
                    form_data["parent_form_data"]["form_pkey"],
                    def_language_to_use,
                    other_languages_to_use,
                )
                if able_to_merge == 0:
                    form_data["form_abletomerge"] = 1
                else:
                    if (
                        able_to_merge == 22
                        or able_to_merge == 23
                        or (3 <= able_to_merge <= 6)
                    ):
                        merge_language_problem = True
                        update_form(
                            self.request,
                            project_id,
                            form_id,
                            {"form_mergelngerror": 1},
                        )
                        form_data["form_mergelngerror"] = 1
                        form_data["form_abletomerge"] = 0
                        form_data["form_mergerrors"] = errors
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
                self.request.registry.settings, project_id, forms
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
                "form_partners": get_form_partners(self.request, project_id, form_id),
                "processing": get_form_processing_products(
                    self.request, project_id, form_id, form_data["form_reptask"]
                ),
                "merging_errors": merging_errors,
                "merge_language_problem": merge_language_problem,
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
            project_details["total_forms"] = get_forms_number(self.request, project_id)
        else:
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
            form_casetype = None
            form_caselabel = None
            form_caseselector = None
            form_casedatetime = None
            if for_merging:
                form_id = self.request.matchdict["formid"]
                primary_key = get_form_primary_key(self.request, project_id, form_id)
                if project_details["project_case"] == 1:
                    (
                        form_casetype,
                        form_caselabel,
                        form_caseselector,
                        form_casedatetime,
                    ) = get_form_case_params(self.request, project_id, form_id)
            else:
                primary_key = form_data.get("form_pkey", None)
                if project_details["project_case"] == 1:
                    if project_details["total_forms"] == 0:
                        form_casetype = 1
                        form_caselabel = form_data.get("form_caselabel", "")
                        if form_caselabel == "":
                            next_page = self.request.params.get(
                                "next"
                            ) or self.request.route_url(
                                "project_details",
                                userid=project_details["owner"],
                                projcode=project_code,
                            )
                            self.add_error(
                                self._(
                                    "You need to indicate a variable for labeling the cases"
                                )
                            )
                            return HTTPFound(next_page, headers={"FS_error": "true"})
                        if form_caselabel.upper() == primary_key.upper():
                            next_page = self.request.params.get(
                                "next"
                            ) or self.request.route_url(
                                "project_details",
                                userid=project_details["owner"],
                                projcode=project_code,
                            )
                            self.add_error(
                                self._(
                                    "The labeling variable and the variable to identify each case cannot be the same"
                                )
                            )
                            return HTTPFound(next_page, headers={"FS_error": "true"})
                    else:
                        form_casetype = int(form_data.get("form_casetype", "0"))
                        if form_casetype == 0:
                            next_page = self.request.params.get(
                                "next"
                            ) or self.request.route_url(
                                "project_details",
                                userid=project_details["owner"],
                                projcode=project_code,
                            )
                            self.add_error(
                                self._("You need to indicate a type of case form")
                            )
                            return HTTPFound(next_page, headers={"FS_error": "true"})
                        else:
                            form_caseselector = form_data.get("form_caseselector", "")
                            if form_caseselector == "":
                                next_page = self.request.params.get(
                                    "next"
                                ) or self.request.route_url(
                                    "project_details",
                                    userid=project_details["owner"],
                                    projcode=project_code,
                                )
                                self.add_error(
                                    self._(
                                        "You need to indicate a variable for searching and "
                                        "selecting cases"
                                    )
                                )
                                return HTTPFound(
                                    next_page, headers={"FS_error": "true"}
                                )
                            if form_caseselector.upper() == primary_key.upper():
                                next_page = self.request.params.get(
                                    "next"
                                ) or self.request.route_url(
                                    "project_details",
                                    userid=project_details["owner"],
                                    projcode=project_code,
                                )
                                self.add_error(
                                    self._(
                                        "The variable for searching and selecting cases cannot "
                                        "be the same as the primary key"
                                    )
                                )
                                return HTTPFound(
                                    next_page, headers={"FS_error": "true"}
                                )
                            form_casedatetime = form_data.get("form_casedatetime", "")
                            if form_casedatetime == "":
                                next_page = self.request.params.get(
                                    "next"
                                ) or self.request.route_url(
                                    "project_details",
                                    userid=project_details["owner"],
                                    projcode=project_code,
                                )
                                self.add_error(
                                    self._(
                                        "You need to indicate a variable that records date or date and time"
                                    )
                                )
                                return HTTPFound(
                                    next_page, headers={"FS_error": "true"}
                                )
                            if (
                                form_casedatetime.upper() == primary_key.upper()
                                or form_casedatetime.upper() == form_caseselector
                            ):
                                next_page = self.request.params.get(
                                    "next"
                                ) or self.request.route_url(
                                    "project_details",
                                    userid=project_details["owner"],
                                    projcode=project_code,
                                )
                                self.add_error(
                                    self._(
                                        "The variable for recording a date or a date and time cannot "
                                        "be the same as the primary key or the case selector variable"
                                    )
                                )
                                return HTTPFound(
                                    next_page, headers={"FS_error": "true"}
                                )

            uploaded, message = upload_odk_form(
                self.request,
                project_id,
                user_id,
                odk_path,
                form_data,
                primary_key,
                for_merging,
                project_details["project_case"],
                form_casetype,
                form_caselabel,
                form_caseselector,
                form_casedatetime,
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
            project_details["total_forms"] = get_forms_number(self.request, project_id)
        else:
            raise HTTPNotFound

        if self.request.method == "POST":
            self.returnRawViewResult = True
            odk_path = get_odk_path(self.request)
            form_data = self.get_post_dict()
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
            form_casetype = None
            form_caselabel = None
            form_caseselector = None
            form_casedatetime = None
            if project_details["project_case"] == 1:
                if project_details["total_forms"] <= 1:
                    form_casetype = int(form_data.get("form_casetype", 1))
                else:
                    form_casetype = int(form_data.get("form_casetype", 0))
                if form_casetype == 1:
                    form_caselabel = form_data.get("form_caselabel", "")
                    if form_caselabel == "":
                        next_page = self.request.route_url(
                            "form_details",
                            userid=project_details["owner"],
                            projcode=project_code,
                            formid=form_id,
                        )
                        self.add_error(
                            self._(
                                "You need to indicate a variable for labeling the cases"
                            )
                        )
                        return HTTPFound(next_page, headers={"FS_error": "true"})
                    if form_caselabel.upper() == primary_key.upper():
                        next_page = self.request.route_url(
                            "form_details",
                            userid=project_details["owner"],
                            projcode=project_code,
                            formid=form_id,
                        )
                        self.add_error(
                            self._(
                                "The labeling variable and the variable to identify each case cannot be the same"
                            )
                        )
                        return HTTPFound(next_page, headers={"FS_error": "true"})
                else:
                    if form_casetype == 0:
                        next_page = self.request.route_url(
                            "form_details",
                            userid=project_details["owner"],
                            projcode=project_code,
                            formid=form_id,
                        )
                        self.add_error(
                            self._("You need to indicate a type of case form")
                        )
                        return HTTPFound(next_page, headers={"FS_error": "true"})
                    if form_casetype > 1:
                        form_caseselector = form_data.get("form_caseselector", "")
                        if form_caseselector == "":
                            next_page = self.request.route_url(
                                "form_details",
                                userid=project_details["owner"],
                                projcode=project_code,
                                formid=form_id,
                            )
                            self.add_error(
                                self._(
                                    "You need to indicate a variable for searching and "
                                    "selecting cases"
                                )
                            )
                            return HTTPFound(next_page, headers={"FS_error": "true"})
                        if form_caseselector.upper() == primary_key.upper():
                            next_page = self.request.route_url(
                                "form_details",
                                userid=project_details["owner"],
                                projcode=project_code,
                                formid=form_id,
                            )
                            self.add_error(
                                self._(
                                    "The variable for searching and selecting cases cannot "
                                    "be the same as the primary key"
                                )
                            )
                            return HTTPFound(next_page, headers={"FS_error": "true"})
                        form_casedatetime = form_data.get("form_casedatetime", "")
                        if form_casedatetime == "":
                            next_page = self.request.params.get(
                                "next"
                            ) or self.request.route_url(
                                "project_details",
                                userid=project_details["owner"],
                                projcode=project_code,
                            )
                            self.add_error(
                                self._(
                                    "You need to indicate a variable that records date or date and time"
                                )
                            )
                            return HTTPFound(next_page, headers={"FS_error": "true"})
                        if (
                            form_casedatetime.upper() == primary_key.upper()
                            or form_casedatetime.upper() == form_caseselector
                        ):
                            next_page = self.request.params.get(
                                "next"
                            ) or self.request.route_url(
                                "project_details",
                                userid=project_details["owner"],
                                projcode=project_code,
                            )
                            self.add_error(
                                self._(
                                    "The variable for recording a date or a date and time cannot "
                                    "be the same as the primary key or the case selector variable"
                                )
                            )
                            return HTTPFound(next_page, headers={"FS_error": "true"})

            updated, message = update_odk_form(
                self.request,
                user_id,
                project_id,
                form_id,
                odk_path,
                form_data,
                primary_key,
                project_details["project_case"],
                form_casetype,
                form_caselabel,
                form_caseselector,
                form_casedatetime,
            )

            if updated:
                delete_dataset_from_index(
                    self.request.registry.settings, project_id, form_id
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
        if self.activeProject.get("project_id", None) == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
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
        if self.activeProject.get("project_id", None) == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")

        if project_id is None:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound
        if (
            get_project_access_type(self.request, project_id, user_id, self.user.login)
            <= 2
            or form_data["form_pubby"] == self.user.id
        ):
            if self.request.method == "POST":
                next_page = self.request.params.get("next") or self.request.route_url(
                    "project_details", userid=user_id, projcode=project_code
                )

                continue_delete = True
                message = ""
                for a_plugin in plugins.PluginImplementations(plugins.IForm):
                    if continue_delete:
                        continue_delete, message = a_plugin.before_deleting_form(
                            self.request, "ODK", user_id, project_id, form_id
                        )
                if continue_delete:
                    deleted, forms_deleted, message = delete_form(
                        self.request, project_id, form_id
                    )
                    if deleted:
                        for a_plugin in plugins.PluginImplementations(plugins.IForm):
                            a_plugin.after_deleting_form(
                                self.request,
                                "ODK",
                                user_id,
                                project_id,
                                form_id,
                                form_data,
                            )
                        if (
                            form_data["form_case"] == 1
                            and form_data["form_casetype"] == 1
                        ):
                            delete_case_lookup_table(self.request, project_id)
                        for a_deleted_form in forms_deleted:
                            delete_dataset_from_index(
                                self.request.registry.settings,
                                project_id,
                                a_deleted_form["form_id"],
                            )
                            delete_form_records(
                                self.request.registry.settings,
                                project_id,
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
        if self.activeProject.get("project_id", None) == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
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
        if self.activeProject.get("project_id", None) == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

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
                    csv_is_lookup = False
                    csv_data = None
                    if file_name.upper().find(".CSV") > 0:
                        tmp_file = get_temporary_file(self.request, "csv")
                        file.file.seek(0)
                        with open(tmp_file, "wb") as output_file:
                            shutil.copyfileobj(file.file, output_file)
                        try:
                            pd.read_csv(
                                tmp_file, header=None
                            )  # Read first without headers to check structure
                            csv_data = pd.read_csv(tmp_file)
                            if current_form_data["form_schema"] is not None:
                                if is_csv_a_lookup(
                                    self.request, project_id, form_id, file_name
                                ):
                                    name, label = get_name_and_label_from_file(
                                        self.request, project_id, form_id, file_name
                                    )
                                    if (
                                        name not in csv_data.columns
                                        or label not in csv_data.columns
                                    ):
                                        message = "The CSV file does not have the columns '{}' or '{}'".format(
                                            name, label
                                        )
                                        error = True
                                        break
                                    csv_is_lookup = True
                        except Exception as e:
                            log.error(
                                "Unable to read {}. Error {}".format(file_name, str(e))
                            )
                            message = (
                                "Unable to read {}. The CSV may have errors".format(
                                    file_name
                                )
                            )
                            error = True
                            break
                    added, message = add_file_to_form(
                        self.request, project_id, form_id, file_name, overwrite, md5sum
                    )
                    if added:
                        file.file.seek(0)
                        bucket_id = project_id + form_id
                        bucket_id = md5(bucket_id.encode("utf-8")).hexdigest()
                        store_file(self.request, bucket_id, file_name, file.file)
                        if (
                            current_form_data["form_caseselectorfilename"] == file_name
                            and current_form_data["form_case"] == 1
                            and current_form_data["form_casetype"] > 1
                        ):
                            form_update_data = {"form_caseselectorlastgen": None}
                            update_form(
                                self.request, project_id, form_id, form_update_data
                            )
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
                            if file_name in required_files and csv_is_lookup:
                                result, message = update_lookup_from_csv(
                                    self.request,
                                    user_id,
                                    project_id,
                                    form_id,
                                    current_form_data["form_schema"],
                                    file_name,
                                    csv_data,
                                )
                                error = not result
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if not form_file_exists(self.request, project_id, form_id, file_name):
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                > 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if form_file_exists(self.request, project_id, form_id, file_name):
            self.returnRawViewResult = True
            return retrieve_form_file(self.request, project_id, form_id, file_name)
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
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

                if "coll_can_submit" in assistant_data.keys():
                    assistant_data["coll_can_submit"] = 1
                else:
                    assistant_data["coll_can_submit"] = 0

                if "coll_can_clean" in assistant_data.keys():
                    assistant_data["coll_can_clean"] = 1
                else:
                    assistant_data["coll_can_clean"] = 0

                if len(parts) == 2:
                    continue_creation = True
                    for plugin in p.PluginImplementations(p.IFormAccess):
                        (
                            data,
                            continue_creation,
                            error_message,
                        ) = plugin.before_giving_access_to_assistant(
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
                                plugin.after_giving_access_to_assistant(
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            assistant_data = self.get_post_dict()

            if "coll_can_submit" in assistant_data.keys():
                assistant_data["coll_can_submit"] = 1
            else:
                assistant_data["coll_can_submit"] = 0

            if "coll_can_clean" in assistant_data.keys():
                assistant_data["coll_can_clean"] = 1
            else:
                assistant_data["coll_can_clean"] = 0

            continue_editing = True
            for plugin in p.PluginImplementations(p.IFormAccess):
                (
                    data,
                    continue_editing,
                    error_message,
                ) = plugin.before_editing_assistant_access(
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
                        plugin.after_editing_assistant_access(
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            continue_remove = True
            for plugin in p.PluginImplementations(p.IFormAccess):
                (
                    continue_remove,
                    error_message,
                ) = plugin.before_revoking_assistant_access(
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
                        plugin.after_revoking_assistant_access(
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            assistant_data = self.get_post_dict()
            if "group_id" in assistant_data.keys():
                if assistant_data["group_id"] != "":
                    if "group_can_submit" in assistant_data.keys():
                        can_submit = 1
                    else:
                        can_submit = 0

                    if "group_can_clean" in assistant_data.keys():
                        can_clean = 1
                    else:
                        can_clean = 0

                    added, message = add_group_to_form(
                        self.request,
                        project_id,
                        form_id,
                        assistant_data["group_id"],
                        can_submit,
                        can_clean,
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            assistant_data = self.get_post_dict()
            if "group_can_submit" in assistant_data.keys():
                can_submit = 1
            else:
                can_submit = 0

            if "group_can_clean" in assistant_data.keys():
                can_clean = 1
            else:
                can_clean = 0

            updated, message = update_group_privileges(
                self.request, project_id, form_id, group_id, can_submit, can_clean
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                > 4
            ):
                raise HTTPNotFound
        else:
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
        options = int(self.request.params.get("options", "1"))

        if "multiselects" in self.request.params.keys():
            include_multiselect = True
        else:
            include_multiselect = False
        if "lookups" in self.request.params.keys():
            include_lookups = True
        else:
            include_lookups = False

        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        odk_dir = get_odk_path(self.request)
        generate_public_xlsx_file(
            self.request,
            self.user.id,
            project_id,
            form_id,
            odk_dir,
            form_data["form_schema"],
            options,
            include_multiselect,
            include_lookups,
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


class DownloadPublicZIPCSVData(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        options = int(self.request.params.get("options", "1"))
        if "multiselects" in self.request.params.keys():
            include_multiselect = True
        else:
            include_multiselect = False
        if "lookups" in self.request.params.keys():
            include_lookups = True
        else:
            include_lookups = False
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        odk_dir = get_odk_path(self.request)
        generate_public_zip_csv_file(
            self.request,
            self.user.id,
            project_id,
            form_id,
            odk_dir,
            form_data["form_schema"],
            options,
            include_multiselect,
            include_lookups,
        )

        next_page = self.request.route_url(
            "form_details",
            userid=user_id,
            projcode=project_code,
            formid=form_id,
            _query={"tab": "task", "product": "zip_csv_public_export"},
            _anchor="products_and_tasks",
        )
        self.returnRawViewResult = True
        return HTTPFound(location=next_page)


class DownloadPublicZIPJSONData(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        options = int(self.request.params.get("options", "1"))
        if "multiselects" in self.request.params.keys():
            include_multiselects = True
        else:
            include_multiselects = False
        if "lookups" in self.request.params.keys():
            include_lookups = True
        else:
            include_lookups = False
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        odk_dir = get_odk_path(self.request)
        generate_public_zip_json_file(
            self.request,
            self.user.id,
            project_id,
            form_id,
            odk_dir,
            form_data["form_schema"],
            options,
            include_multiselects,
            include_lookups,
        )

        next_page = self.request.route_url(
            "form_details",
            userid=user_id,
            projcode=project_code,
            formid=form_id,
            _query={"tab": "task", "product": "zip_json_public_export"},
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
        options = int(self.request.params.get("options", "1"))

        if "multiselects" in self.request.params.keys():
            include_multiselect = True
        else:
            include_multiselect = False
        if "lookups" in self.request.params.keys():
            include_lookups = True
        else:
            include_lookups = False

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        odk_dir = get_odk_path(self.request)
        generate_private_xlsx_file(
            self.request,
            self.user.id,
            project_id,
            form_id,
            odk_dir,
            form_data["form_schema"],
            options,
            include_multiselect,
            include_lookups,
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


class DownloadPrivateZIPCSVData(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        options = int(self.request.params.get("options", "1"))
        if "multiselects" in self.request.params.keys():
            include_multiselect = True
        else:
            include_multiselect = False
        if "lookups" in self.request.params.keys():
            include_lookups = True
        else:
            include_lookups = False

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        odk_dir = get_odk_path(self.request)
        generate_private_zip_csv_file(
            self.request,
            self.user.id,
            project_id,
            form_id,
            odk_dir,
            form_data["form_schema"],
            options,
            include_multiselect,
            include_lookups,
        )

        next_page = self.request.route_url(
            "form_details",
            userid=user_id,
            projcode=project_code,
            formid=form_id,
            _query={"tab": "task", "product": "zip_csv_private_export"},
            _anchor="products_and_tasks",
        )
        self.returnRawViewResult = True
        return HTTPFound(location=next_page)


class DownloadPrivateZIPJSONData(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        options = int(self.request.params.get("options", "1"))
        if "multiselects" in self.request.params.keys():
            include_multiselects = True
        else:
            include_multiselects = False
        if "lookups" in self.request.params.keys():
            include_lookups = True
        else:
            include_lookups = False

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        odk_dir = get_odk_path(self.request)
        generate_private_zip_json_file(
            self.request,
            self.user.id,
            project_id,
            form_id,
            odk_dir,
            form_data["form_schema"],
            options,
            include_multiselects,
            include_lookups,
        )

        next_page = self.request.route_url(
            "form_details",
            userid=user_id,
            projcode=project_code,
            formid=form_id,
            _query={"tab": "task", "product": "zip_json_private_export"},
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                > 4
            ):
                raise HTTPNotFound
        else:
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

        if project_id is None:
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
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound

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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                > 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        created, data = get_gps_points_from_form(self.request, project_id, form_id)
        return data


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
        options = int(self.request.params.get("options", "1"))

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
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
            options,
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
        options = int(self.request.params.get("options", "1"))

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
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
            options,
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
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

                imported, message, next_page = import_external_data(
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
                    self.returnRawViewResult = True
                    return HTTPFound(location=next_page)
                else:
                    self.append_to_errors(message)

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
        if self.activeProject.get("project_id", None) == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                > 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

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
            "projectDetails": project_details,
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                > 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
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


class CaseLookUpCSV(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject.get("project_id", None) == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        if project_details["project_case"] == 0:
            raise HTTPNotFound

        if get_number_of_case_creators(self.request, project_id) == 0:
            raise HTTPNotFound

        if (
            get_number_of_case_creators(self.request, project_id) > 0
            and get_number_of_case_creators_with_repository(self.request, project_id)
            == 0
        ):
            raise HTTPNotFound

        form_id = get_case_form(self.request, project_id)
        fields, checked = get_fields_from_table(
            self.request, project_id, form_id, "maintable", [], False
        )

        form_data = get_form_data(self.request, project_id, form_id)
        case_fields, created = get_case_lookup_fields(
            self.request,
            project_id,
            form_data["form_pkey"],
            form_data["form_caselabel"],
        )
        for a_field in fields:
            a_field["checked"] = False
            a_field["editable"] = 1
            a_field["as"] = ""
            for a_case_field in case_fields:
                if a_field["name"] == a_case_field["field_name"]:
                    a_field["checked"] = True
                    a_field["editable"] = a_case_field["field_editable"]
                    a_field["field_as"] = a_case_field["field_as"]
                    break
        csv_keys = ["list_name", "name", "label"]
        for a_field in fields:
            if a_field["editable"] == 1 and a_field["checked"] == True:
                csv_keys.append(a_field["field_as"])
        csv_array = []
        for row in range(6):
            data = {}
            for a_key in csv_keys:
                added = False
                if a_key == "list_name":
                    data["list_name"] = "list_of_cases"
                    added = True
                if a_key == "name":
                    data["name"] = "Case id for row {}".format(row + 2)
                    added = True
                if a_key == "label":
                    data["label"] = "Case label for row {}".format(row + 2)
                    added = True
                if not added:
                    data[a_key] = "{} for row {}".format(a_key, row + 2)
            csv_array.append(data)
        df = pd.DataFrame.from_dict(csv_array)

        repository_path = self.request.registry.settings["repository.path"]
        if not os.path.exists(repository_path):
            os.makedirs(repository_path)
        unique_id = str(uuid.uuid4())
        csv_file = os.path.join(repository_path, *["tmp", unique_id + ".csv"])
        df.to_csv(csv_file, index=False, header=True)

        response = FileResponse(csv_file, request=self.request, content_type="text/csv")
        response.content_disposition = (
            'attachment; filename="cases_of_' + project_code + '.csv"'
        )
        self.returnRawViewResult = True
        return response


class CaseLookUpTable(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject.get("project_id", None) == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")

        if project_id is not None:
            access_type = get_project_access_type(
                self.request, project_id, user_id, self.user.login
            )
            if access_type >= 4:
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
            project_details["access_type"] = access_type
        else:
            raise HTTPNotFound

        if project_details["project_case"] == 0:
            raise HTTPNotFound

        if get_number_of_case_creators(self.request, project_id) == 0:
            raise HTTPNotFound

        if (
            get_number_of_case_creators(self.request, project_id) > 0
            and get_number_of_case_creators_with_repository(self.request, project_id)
            == 0
        ):
            raise HTTPNotFound

        if self.request.method == "POST":
            field_data = self.get_post_dict()
            if "add_field" in field_data.keys():
                add_case_lookup_field(
                    self.request, project_id, field_data["field_name"]
                )
                self.returnRawViewResult = True
                return HTTPFound(self.request.url)
            if "remove_field" in field_data.keys():
                remove_case_lookup_field(
                    self.request, project_id, field_data["field_name"]
                )
                self.returnRawViewResult = True
                return HTTPFound(self.request.url)
            if "change_alias" in field_data.keys():
                field_alias = field_data.get("field_alias", "")
                if field_alias == "":
                    field_alias = field_data["field_name"]
                field_alias = field_alias.lower()
                if re.match(r"^[A-Za-z0-9_]+$", field_alias):
                    if field_alias.upper() not in invalid_aliases:
                        if not field_alias.isnumeric():
                            if field_exists(
                                self.request, project_id, field_data["field_name"]
                            ):
                                if not alias_exists(
                                    self.request,
                                    project_id,
                                    field_data["field_name"],
                                    field_alias,
                                ):
                                    update_case_lookup_field_alias(
                                        self.request,
                                        project_id,
                                        field_data["field_name"],
                                        field_alias,
                                    )
                                    self.returnRawViewResult = True
                                    return HTTPFound(self.request.url)
                                else:
                                    self.append_to_errors(
                                        self._("Such alias already exist")
                                    )
                            else:
                                self.append_to_errors(
                                    self._("Such field does not exist")
                                )
                        else:
                            self.append_to_errors(
                                self._("The alias cannot be a number")
                            )
                    else:
                        self.append_to_errors(self._("The alias is invalid"))
                else:
                    self.append_to_errors(
                        self._(
                            "The alias has invalid characters. Only underscore (_) is allowed"
                        )
                    )

        form_id = get_case_form(self.request, project_id)
        fields, checked = get_fields_from_table(
            self.request, project_id, form_id, "maintable", [], False
        )

        form_data = get_form_data(self.request, project_id, form_id)
        case_fields, created = get_case_lookup_fields(
            self.request,
            project_id,
            form_data["form_pkey"],
            form_data["form_caselabel"],
        )
        for a_field in fields:
            a_field["checked"] = False
            a_field["editable"] = 1
            a_field["as"] = ""
            for a_case_field in case_fields:
                if a_field["name"] == a_case_field["field_name"]:
                    a_field["checked"] = True
                    a_field["editable"] = a_case_field["field_editable"]
                    a_field["field_as"] = a_case_field["field_as"]
                    break

        return {
            "projectDetails": project_details,
            "userid": user_id,
            "fields": fields,
            "created": created,
        }


class AddPartnerToForm(PrivateView):
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            partner_data = self.get_post_dict()
            if "partner_id" in partner_data.keys():
                if partner_data["partner_id"] != "":

                    if "time_bound" in partner_data.keys():
                        partner_data["time_bound"] = True
                    else:
                        partner_data["time_bound"] = False

                    access_from = None
                    access_to = None
                    if partner_data["time_bound"]:
                        try:
                            access_from = datetime.datetime.strptime(
                                partner_data["access_from"], "%Y-%m-%d"
                            )
                            access_to = datetime.datetime.strptime(
                                partner_data["access_to"], "%Y-%m-%d"
                            )
                        except ValueError:
                            self.add_error(self._("Invalid dates"))
                            next_page = self.request.route_url(
                                "form_details",
                                userid=user_id,
                                projcode=project_code,
                                formid=form_id,
                            )
                            return HTTPFound(
                                location=next_page, headers={"FS_error": "true"}
                            )
                    if access_from is not None:
                        if access_to < access_from:
                            self.add_error(self._("Invalid dates"))
                            next_page = self.request.route_url(
                                "form_details",
                                userid=user_id,
                                projcode=project_code,
                                formid=form_id,
                            )
                            return HTTPFound(
                                location=next_page, headers={"FS_error": "true"}
                            )

                    partner_data["access_from"] = access_from
                    partner_data["access_to"] = access_to
                    partner_data["project_id"] = project_id
                    partner_data["form_id"] = form_id
                    partner_data["access_date"] = datetime.datetime.now()
                    partner_data["granted_by"] = project_details["owner"]
                    added, message = add_partner_to_form(self.request, partner_data)
                    if added:
                        self.request.session.flash(
                            self._("The partner was added successfully to this form")
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
                    self.add_error("The partner cannot be empty")
                    next_page = self.request.route_url(
                        "form_details",
                        userid=user_id,
                        projcode=project_code,
                        formid=form_id,
                    )
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})
            else:
                self.add_error("The partner cannot be empty")
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                )
                return HTTPFound(location=next_page, headers={"FS_error": "true"})

        else:
            raise HTTPNotFound


class EditPartnerFormOptions(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        partner_id = self.request.matchdict["partnerid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            partner_data = self.get_post_dict()
            if "time_bound" in partner_data.keys():
                partner_data["time_bound"] = True
            else:
                partner_data["time_bound"] = False

            access_from = None
            access_to = None
            if partner_data["time_bound"]:
                try:
                    access_from = datetime.datetime.strptime(
                        partner_data["access_from"], "%Y-%m-%d"
                    )
                    access_to = datetime.datetime.strptime(
                        partner_data["access_to"], "%Y-%m-%d"
                    )
                except ValueError:
                    self.add_error(self._("Invalid dates"))
                    next_page = self.request.route_url(
                        "form_details",
                        userid=user_id,
                        projcode=project_code,
                        formid=form_id,
                    )
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})
            if access_from is not None:
                if access_to < access_from:
                    self.add_error(self._("Invalid dates"))
                    next_page = self.request.route_url(
                        "form_details",
                        userid=user_id,
                        projcode=project_code,
                        formid=form_id,
                    )
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})

            updated, message = update_partner_form_options(
                self.request, project_id, form_id, partner_id, partner_data
            )
            if updated:
                self.request.session.flash(
                    self._("The partner was successfully updated")
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
            raise HTTPNotFound


class RemovePartnerFromForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        partner_id = self.request.matchdict["partnerid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            removed, message = remove_partner_from_form(
                self.request, project_id, form_id, partner_id
            )
            if removed:
                self.request.session.flash(
                    self._("The partner was successfully removed from this form")
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
            raise HTTPNotFound


class FixMergeLanguage(PrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if form_data["parent_form"] is not None and form_data["form_abletomerge"] == -1:
            parent_form_data = get_form_data(
                self.request, project_id, form_data["parent_form"]
            )

            odk_dir = get_odk_path(self.request)
            media_files = get_media_files(self.request, project_id, form_id)
            tmp_uid = str(uuid.uuid4())
            target_dir = os.path.join(odk_dir, *["tmp", tmp_uid])
            os.makedirs(target_dir)
            for media_file in media_files:
                store_file_in_directory(
                    self.request, project_id, form_id, media_file.file_name, target_dir
                )
            path = os.path.join(odk_dir, *["tmp", tmp_uid, "*.*"])
            files = glob.glob(path)
            odk_media_files = []
            if files:
                for aFile in files:
                    odk_media_files.append(aFile)
            survey_file = get_form_survey_file(self.request, project_id, form_id)
            create_file = get_form_xml_create_file(self.request, project_id, form_id)
            insert_file = get_form_xml_insert_file(self.request, project_id, form_id)
            result, languages = check_jxform_file(
                self.request,
                survey_file,
                create_file,
                insert_file,
                parent_form_data["form_pkey"],
                odk_media_files,
                True,
            )

            default = False
            idx = 0
            for language in languages:
                if language["name"] == "default":
                    default = True
                    languages.insert(0, languages.pop(idx))
                idx = idx + 1

            parent_has_no_language = False
            if parent_form_data["form_deflang"] is not None:
                if parent_form_data["form_deflang"].find("default") >= 0:
                    default = True
            else:
                parent_has_no_language = True
            if self.request.method == "POST":
                if languages:
                    run_process = True
                    postdata = self.get_post_dict()
                    default_language_string = "("
                    default_language = ""
                    if postdata.get("form_deflang", "") != "":
                        default_language = postdata.get("form_deflang")
                    else:
                        run_process = False
                        self.append_to_errors(
                            self._("You need to indicate the primary language")
                        )
                    other_languages = []
                    empty_code_found = False
                    language_codes = []
                    duplicated_code = False
                    for language in languages:
                        if language["name"] == "default":
                            default = True
                        if postdata.get("LNG-" + language["name"], "") != "":
                            found = False
                            for a_code in language_codes:
                                if a_code == postdata.get(
                                    "LNG-" + language["name"], ""
                                ):
                                    found = True
                            if not found:
                                language_codes.append(
                                    postdata.get("LNG-" + language["name"], "")
                                )
                            else:
                                duplicated_code = True
                                break

                            if language["name"] == default_language:
                                default_language_string = (
                                    default_language_string
                                    + postdata.get("LNG-" + language["name"])
                                    + ")"
                                    + language["name"]
                                )
                                language["code"] = postdata.get(
                                    "LNG-" + language["name"]
                                )
                            else:
                                other_languages.append(
                                    "("
                                    + postdata.get("LNG-" + language["name"])
                                    + ")"
                                    + language["name"]
                                )
                                language["code"] = postdata.get(
                                    "LNG-" + language["name"]
                                )
                        else:
                            empty_code_found = True
                            break
                    if duplicated_code:
                        self.append_to_errors(
                            self._(
                                "Each language needs to have an unique ISO 639-1 code"
                            )
                        )
                        run_process = False
                    if empty_code_found:
                        self.append_to_errors(
                            self._(
                                "You need to indicate a ISO 639-1 code for each language"
                            )
                        )
                        run_process = False

                    if run_process:
                        update_form(
                            self.request,
                            project_id,
                            form_id,
                            {
                                "form_deflang": default_language_string,
                                "form_othlangs": ",".join(other_languages),
                                "form_mergelngerror": 2,
                            },
                        )
                        next_page = self.request.route_url(
                            "form_details",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                        self.returnRawViewResult = True
                        return HTTPFound(location=next_page)
                    else:
                        return {
                            "languages": languages,
                            "default": default,
                            "userid": user_id,
                            "formData": form_data,
                            "projectDetails": project_details,
                            "projcode": project_code,
                            "formid": form_id,
                            "old_language": parent_form_data["form_deflang"],
                        }
                else:
                    update_form(
                        self.request,
                        project_id,
                        form_id,
                        {
                            "form_deflang": None,
                            "form_othlangs": None,
                            "form_mergelngerror": 2,
                        },
                    )
                    next_page = self.request.route_url(
                        "form_details",
                        userid=user_id,
                        projcode=project_code,
                        formid=form_id,
                    )
                    self.returnRawViewResult = True
                    return HTTPFound(location=next_page)

            return {
                "languages": languages,
                "default": default,
                "userid": user_id,
                "formData": form_data,
                "projectDetails": project_details,
                "projcode": project_code,
                "formid": form_id,
                "old_language": parent_form_data["form_deflang"],
                "parent_has_no_language": parent_has_no_language,
            }
        else:
            raise HTTPNotFound


class ExportData(PrivateView):
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

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound
        if self.request.method == "POST":
            export_data = self.get_post_dict()
            if "export_type" in export_data:
                if export_data["export_type"] == "XLSX":
                    return HTTPFound(
                        location=self.request.route_url(
                            "form_export_xlsx",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                    )
                if export_data["export_type"] == "CSV":
                    return HTTPFound(
                        location=self.request.route_url(
                            "form_export_csv",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                    )
                if export_data["export_type"] == "ZIP_CSV":
                    return HTTPFound(
                        location=self.request.route_url(
                            "form_export_zip_csv",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                    )
                if export_data["export_type"] == "ZIP_JSON":
                    return HTTPFound(
                        location=self.request.route_url(
                            "form_export_zip_json",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                    )
                if export_data["export_type"] == "KML":
                    return HTTPFound(
                        location=self.request.route_url(
                            "form_export_kml",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                    )
                if export_data["export_type"] == "MEDIA":
                    return HTTPFound(
                        location=self.request.route_url(
                            "form_download_media",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                    )
                for a_plugin in plugins.PluginImplementations(plugins.IExport):
                    if a_plugin.has_export_for(
                        self.request, export_data["export_type"]
                    ):
                        return a_plugin.do_export(
                            self.request, export_data["export_type"]
                        )
                raise HTTPNotFound
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class ExportDataToXLSX(PrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            export_data = self.get_post_dict()
            options_type = int(export_data["labels"])
            self.returnRawViewResult = True
            query_dict = {"options": options_type}
            if "multiselects" in export_data.keys():
                query_dict["multiselects"] = 1
            if "lookups" in export_data.keys():
                query_dict["lookups"] = 1
            if export_data["publishable"] == "yes":
                location = self.request.route_url(
                    "form_download_public_xlsx_data",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query=query_dict,
                )
                return HTTPFound(location=location)
            if export_data["publishable"] == "no":
                location = self.request.route_url(
                    "form_download_private_xlsx_data",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query=query_dict,
                )
                return HTTPFound(location=location)

        return {
            "projectDetails": project_details,
            "formid": form_id,
            "formDetails": form_data,
            "userid": user_id,
        }


class ExportDataToZIPCSV(PrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            export_data = self.get_post_dict()
            options_type = int(export_data["labels"])
            self.returnRawViewResult = True
            query_dict = {"options": options_type}
            if "multiselects" in export_data.keys():
                query_dict["multiselects"] = 1
            if "lookups" in export_data.keys():
                query_dict["lookups"] = 1
            if export_data["publishable"] == "yes":
                location = self.request.route_url(
                    "form_download_public_zip_csv_data",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query=query_dict,
                )
                return HTTPFound(location=location)
            if export_data["publishable"] == "no":
                location = self.request.route_url(
                    "form_download_private_zip_csv_data",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query=query_dict,
                )
                return HTTPFound(location=location)

        return {
            "projectDetails": project_details,
            "formid": form_id,
            "formDetails": form_data,
            "userid": user_id,
        }


class ExportDataToZIPJSON(PrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            export_data = self.get_post_dict()
            options_type = int(export_data["labels"])
            self.returnRawViewResult = True
            options_dict = {"options": options_type}
            if "multiselects" in export_data.keys():
                options_dict["multiselects"] = 1
            if "lookups" in export_data.keys():
                options_dict["lookups"] = 1

            if export_data["publishable"] == "yes":
                location = self.request.route_url(
                    "form_download_public_zip_json_data",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query=options_dict,
                )
                return HTTPFound(location=location)
            if export_data["publishable"] == "no":
                location = self.request.route_url(
                    "form_download_private_zip_json_data",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query=options_dict,
                )
                return HTTPFound(location=location)

        return {
            "projectDetails": project_details,
            "formid": form_id,
            "formDetails": form_data,
            "userid": user_id,
        }


class ExportDataToCSV(PrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        if self.request.method == "POST":
            export_data = self.get_post_dict()
            options_type = int(export_data["labels"])
            self.returnRawViewResult = True
            if export_data["publishable"] == "yes":
                location = self.request.route_url(
                    "form_download_repo_public_csv",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query={"options": options_type},
                )
                return HTTPFound(location=location)
            if export_data["publishable"] == "no":
                location = self.request.route_url(
                    "form_download_repo_private_csv",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query={"options": options_type},
                )
                return HTTPFound(location=location)

        return {
            "projectDetails": project_details,
            "formid": form_id,
            "formDetails": form_data,
            "userid": user_id,
        }


class DownloadKML(PrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        fields, checked = get_fields_from_table(
            self.request, project_id, form_id, "maintable", [], False
        )

        if self.request.method == "POST":
            export_data = self.get_post_dict()
            selected_fields = export_data["fields"]
            for a_field in fields:
                if a_field["key"] == "true":
                    selected_fields.insert(0, a_field["name"])
            selected_fields.append("_geopoint")
            selected_fields.append("rowuuid")
            selected_fields.append("_latitude")
            selected_fields.append("_longitude")

            options = int(export_data["labels"])
            generate_kml_file(
                self.request,
                self.user.id,
                project_id,
                form_id,
                form_data["form_schema"],
                form_data["form_createxmlfile"],
                selected_fields,
                options,
            )
            next_page = self.request.params.get("next") or self.request.route_url(
                "form_details",
                userid=user_id,
                projcode=project_code,
                formid=form_id,
                _query={"tab": "task", "product": "kml_export"},
                _anchor="products_and_tasks",
            )
            self.returnRawViewResult = True
            return HTTPFound(location=next_page)
        return {
            "projectDetails": project_details,
            "formid": form_id,
            "formDetails": form_data,
            "userid": user_id,
            "fields": fields,
        }


def add_field_to_table(tables, table, field, field_type="added"):
    table_found = False
    for a_table in tables:
        if a_table["name"] == table["name"]:
            table_found = True
            a_table["fields"].append(
                {"name": field["name"], "desc": field["desc"], "type": field_type}
            )
            break
    if not table_found:
        tables.append(
            {
                "name": table["name"],
                "desc": table["name"],
                "fields": [
                    {"name": field["name"], "desc": field["desc"], "type": field_type}
                ],
            }
        )


class CompareForms(PrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        from_form_id = self.request.matchdict["fromformid"]
        to_form_id = self.request.matchdict["toformid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                > 4
            ):
                raise HTTPNotFound
            project_details = get_project_details(self.request, project_id)
        else:
            raise HTTPNotFound

        from_form_data = get_form_data(self.request, project_id, from_form_id)
        to_form_data = get_form_data(self.request, project_id, to_form_id)
        if from_form_data is None or to_form_data is None:
            raise HTTPNotFound

        old_tables = get_tables_from_original_form(
            self.request, project_id, from_form_id
        )
        new_tables = get_tables_from_original_form(self.request, project_id, to_form_id)

        tables_added = []
        for a_new_table in new_tables:
            table_found = False
            for a_old_table in old_tables:
                if a_new_table["name"] == a_old_table["name"]:
                    table_found = True
            if not table_found:
                tables_added.append(a_new_table)

        tables_removed = []
        for a_old_table in old_tables:
            table_found = False
            for a_new_table in new_tables:
                if a_new_table["name"] == a_old_table["name"]:
                    table_found = True
            if not table_found:
                tables_removed.append(a_old_table)

        tables_modified = []

        for a_new_table in new_tables:
            for a_old_table in old_tables:
                if a_new_table["name"] == a_old_table["name"]:
                    for a_new_field in a_new_table["fields"]:
                        field_found = False
                        for an_old_field in a_old_table["fields"]:
                            if a_new_field["name"] == an_old_field["name"]:
                                field_found = True
                        if not field_found:
                            add_field_to_table(
                                tables_modified, a_new_table, a_new_field
                            )

        for a_old_table in old_tables:
            for a_new_table in new_tables:
                if a_new_table["name"] == a_old_table["name"]:
                    for an_old_field in a_old_table["fields"]:
                        field_found = False
                        for a_new_field in a_new_table["fields"]:
                            if a_new_field["name"] == an_old_field["name"]:
                                field_found = True
                        if not field_found:
                            add_field_to_table(
                                tables_modified, a_old_table, an_old_field, "removed"
                            )

        return {
            "projectDetails": project_details,
            "fromformid": from_form_id,
            "toformid": from_form_id,
            "fromFormDetails": from_form_data,
            "toFormDetails": to_form_data,
            "userid": user_id,
            "TablesAdded": tables_added,
            "TablesRemoved": tables_removed,
            "TablesModified": tables_modified,
        }
