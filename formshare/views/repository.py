import json
import logging
import os

from formshare.processes.db import (
    get_project_id_from_name,
    get_project_access_type,
    get_project_details,
    get_one_assistant,
)
from formshare.processes.elasticsearch.repository_index import delete_dataset_from_index
from formshare.processes.email.send_email import send_error_to_technical_team
from formshare.processes.odk.api import create_repository, get_odk_path
from formshare.processes.odk.processes import get_form_data
from formshare.views.classes import PrivateView
from lxml import etree
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
import formshare.plugins as plugins

log = logging.getLogger("formshare")


class GenerateRepository(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def report_critical_error(
        self, user, project, form, error_code, message
    ):  # pragma: no cover
        send_error_to_technical_team(
            self.request,
            "Error while creating the repository for form {} in "
            "project {}. \nURL:{} \nAccount: {}\nError: {}\nMessage: {}\n".format(
                form, project, self.request.url, user, error_code, message
            ),
        )
        log.error(
            "Error while creating the repository for form {} in "
            "project {}. \nAccount: {}\nError: {}\nMessage: {}\n".format(
                form, project, user, error_code, message
            )
        )

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

        has_submit_assistant = True
        project, assistant = get_one_assistant(self.request, project_id, form_id)
        if project is None:
            has_submit_assistant = False

        form_data = get_form_data(project_id, form_id, self.request)
        result_code = -1
        list_array = []
        duplicated_choices = []
        tables_with_name_error = []
        languages = []
        default = False
        languages_string = ""
        file_with_error = ""
        method = "get"
        stage = 1
        primary_key = ""
        discard_testing_data = False
        survey_data_columns = []
        choices_data_columns = []
        if form_data:
            if form_data["schema"] is None:
                if self.request.method == "POST":
                    method = "post"
                    postdata = self.get_post_dict()

                    if "survey_data_columns" in postdata.keys():
                        if "survey_data_columns" in postdata.keys():
                            if isinstance(postdata["survey_data_columns"], list):
                                survey_data_columns = postdata["survey_data_columns"]
                            else:
                                survey_data_columns = postdata[
                                    "survey_data_columns"
                                ].split("|")

                    if "choices_data_columns" in postdata.keys():
                        if "choices_data_columns" in postdata.keys():
                            if isinstance(postdata["choices_data_columns"], list):
                                choices_data_columns = postdata["choices_data_columns"]
                            else:
                                choices_data_columns = postdata[
                                    "choices_data_columns"
                                ].split("|")

                    if "formshare_sensitive" not in survey_data_columns:
                        survey_data_columns.append("formshare_sensitive")
                    if "formshare_encrypted" not in survey_data_columns:
                        survey_data_columns.append("formshare_encrypted")
                    if "formshare_unique" not in survey_data_columns:
                        survey_data_columns.append("formshare_unique")
                    if "formshare_ontological_term" not in survey_data_columns:
                        survey_data_columns.append("formshare_ontological_term")

                    if "formshare_ontological_term" not in choices_data_columns:
                        choices_data_columns.append("formshare_ontological_term")

                    for a_plugin in plugins.PluginImplementations(
                        plugins.IFormDataColumns
                    ):
                        a_plugin.add_to_form_survey_columns(
                            self.request,
                            user_id,
                            project_id,
                            form_id,
                            survey_data_columns,
                        )

                    for a_plugin in plugins.PluginImplementations(
                        plugins.IFormDataColumns
                    ):
                        a_plugin.add_to_form_choices_columns(
                            self.request,
                            user_id,
                            project_id,
                            form_id,
                            choices_data_columns,
                        )

                    run_process = True
                    if "discard_testing_data" in postdata.keys():
                        discard_testing_data = True
                    if "start_stage1" in postdata.keys():
                        stage = 1
                        if postdata.get("form_pkey", "") != "":
                            primary_key = postdata.get("form_pkey")
                        else:
                            self.append_to_errors(
                                self._("The primary key cannot be empty")
                            )
                            run_process = False
                    default_language_string = "("
                    other_languages_string = ""
                    if "start_stage2" in postdata.keys():
                        stage = 2
                        languages_string = postdata.get("languages_string", "")
                        primary_key = postdata.get("form_pkey")
                        if "discard_testing_data" in postdata.keys():
                            discard_testing_data = True
                        languages = json.loads(languages_string)
                        default_language = ""
                        if postdata.get("form_deflang", "") != "":
                            default_language = postdata.get("form_deflang")
                        else:
                            self.append_to_errors(
                                self._("You need to indicate the primary language")
                            )
                            run_process = False

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
                        else:
                            other_languages_string = ",".join(other_languages)

                    if run_process:
                        odk_path = get_odk_path(self.request)
                        if stage == 1:
                            result_code, message = create_repository(
                                self.request,
                                self.user.id,
                                project_id,
                                form_id,
                                odk_path,
                                form_data["directory"],
                                primary_key,
                                discard_testing_data,
                                "|".join(survey_data_columns),
                                "|".join(choices_data_columns),
                            )
                        else:
                            result_code, message = create_repository(
                                self.request,
                                self.user.id,
                                project_id,
                                form_id,
                                odk_path,
                                form_data["directory"],
                                primary_key,
                                discard_testing_data,
                                "|".join(survey_data_columns),
                                "|".join(choices_data_columns),
                                default_language_string,
                                other_languages_string,
                            )
                        if result_code == 0:
                            delete_dataset_from_index(
                                self.request.registry.settings,
                                project_id,
                                form_id,
                            )
                            self.request.session.flash(
                                self._("FormShare is creating the repository") + "|info"
                            )
                            self.returnRawViewResult = True
                            return HTTPFound(
                                self.request.route_url(
                                    "form_details",
                                    userid=user_id,
                                    projcode=project_code,
                                    formid=form_id,
                                )
                            )
                        else:
                            # Most of this code is not included in coverage
                            # because it is extremely unlikely that will be executed
                            # as it is checked elsewhere before. Is here just in case
                            if result_code == 1:  # pragma: no cover
                                # Internal error: Report issue
                                self.report_critical_error(
                                    user_id, project_id, form_id, result_code, message
                                )
                                stage = -1
                            if result_code == 7:  # pragma: no cover
                                # Internal error: Report issue
                                self.report_critical_error(
                                    user_id, project_id, form_id, result_code, message
                                )
                                stage = -1
                            if result_code == 8:  # pragma: no cover
                                # Internal error: Report issue
                                self.report_critical_error(
                                    user_id, project_id, form_id, result_code, message
                                )
                                stage = -1
                            if result_code == 2:  # pragma: no cover
                                # 64 or more relationships. Report issue because this was checked before
                                self.report_critical_error(
                                    user_id, project_id, form_id, result_code, message
                                )
                                stage = -1
                            if result_code == 34:  # pragma: no cover
                                # Too many fields. Report issue because this was checked before
                                self.report_critical_error(
                                    user_id, project_id, form_id, result_code, message
                                )
                                stage = -1
                            if result_code == 35:  # pragma: no cover
                                # Or other was used. Report issue because this was checked before
                                self.report_critical_error(
                                    user_id, project_id, form_id, result_code, message
                                )
                                stage = -1
                            if 3 <= result_code <= 6:
                                if result_code == 3 or result_code == 4:
                                    root = etree.fromstring(message)
                                    language_array = root.findall(
                                        ".//language"
                                    )  # language
                                    if language_array:
                                        for aLang in language_array:
                                            if (
                                                aLang.get("name")
                                                or aLang.get("description") == "default"
                                            ):
                                                languages.insert(
                                                    0,
                                                    {
                                                        "code": aLang.get("code", ""),
                                                        "name": aLang.get("name")
                                                        or aLang.get("description"),
                                                    },
                                                )
                                                if (
                                                    aLang.get("description")
                                                    == "default"
                                                    or aLang.get("name") == "default"
                                                ):
                                                    default = True
                                            else:
                                                languages.append(
                                                    {
                                                        "code": aLang.get("code", ""),
                                                        "name": aLang.get("name")
                                                        or aLang.get("description"),
                                                    }
                                                )
                                    languages_string = json.dumps(languages)
                                    stage = 2
                                else:  # pragma: no cover
                                    self.report_critical_error(
                                        user_id,
                                        project_id,
                                        form_id,
                                        result_code,
                                        message,
                                    )
                                    stage = -1

                            if result_code == 14:  # pragma: no cover
                                txt_message = (
                                    'The following files have invalid characters like extra ". '
                                    "Only _ is allowed : \n"
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
                                self.append_to_errors(txt_message)
                            if result_code == 15:  # pragma: no cover
                                txt_message = (
                                    "The following files have an invalid structure: \n"
                                )
                                root = etree.fromstring(message)
                                files_with_problems = root.findall(".//file")
                                if files_with_problems:
                                    for a_file in files_with_problems:
                                        txt_message = (
                                            txt_message
                                            + "\t"
                                            + a_file.get("name", "")
                                            + "\n"
                                        )
                                self.append_to_errors(txt_message)
                            if result_code == 26:  # pragma: no cover
                                txt_message = (
                                    "The following GeoJSON file cannot be opened: \n"
                                )
                                root = etree.fromstring(message)
                                files_with_problems = root.findall(".//file")
                                if files_with_problems:
                                    for a_file in files_with_problems:
                                        txt_message = (
                                            txt_message
                                            + "\t"
                                            + a_file.get("name", "")
                                            + "\n"
                                        )
                                self.append_to_errors(txt_message)

                            if result_code == 27:  # pragma: no cover
                                txt_message = "The following GeoJSON file is not a FeatureCollection: \n"
                                root = etree.fromstring(message)
                                files_with_problems = root.findall(".//file")
                                if files_with_problems:
                                    for a_file in files_with_problems:
                                        txt_message = (
                                            txt_message
                                            + "\t"
                                            + a_file.get("name", "")
                                            + "\n"
                                        )
                                self.append_to_errors(txt_message)

                            if result_code == 28:  # pragma: no cover
                                txt_message = "The following GeoJSON file does not have features: \n"
                                root = etree.fromstring(message)
                                files_with_problems = root.findall(".//file")
                                if files_with_problems:
                                    for a_file in files_with_problems:
                                        txt_message = (
                                            txt_message
                                            + "\t"
                                            + a_file.get("name", "")
                                            + "\n"
                                        )
                                self.append_to_errors(txt_message)

                            if result_code == 29:  # pragma: no cover
                                txt_message = "The following GeoJSON file does not have properties: \n"
                                root = etree.fromstring(message)
                                files_with_problems = root.findall(".//file")
                                if files_with_problems:
                                    for a_file in files_with_problems:
                                        txt_message = (
                                            txt_message
                                            + "\t"
                                            + a_file.get("name", "")
                                            + "\n"
                                        )
                                self.append_to_errors(txt_message)

                            if result_code == 30:  # pragma: no cover
                                txt_message = "The following GeoJSON file does not have the id or title columns: \n"
                                root = etree.fromstring(message)
                                files_with_problems = root.findall(".//file")
                                if files_with_problems:
                                    for a_file in files_with_problems:
                                        txt_message = (
                                            txt_message
                                            + "\t"
                                            + a_file.get("name", "")
                                            + "\n"
                                        )
                                self.append_to_errors(txt_message)

                            if result_code == 31:  # pragma: no cover
                                txt_message = "The following GeoJSON file has features without geometry: \n"
                                root = etree.fromstring(message)
                                files_with_problems = root.findall(".//file")
                                if files_with_problems:
                                    for a_file in files_with_problems:
                                        txt_message = (
                                            txt_message
                                            + "\t"
                                            + a_file.get("name", "")
                                            + "\n"
                                        )
                                self.append_to_errors(txt_message)

                            if result_code == 32:  # pragma: no cover
                                txt_message = "The following GeoJSON file has features that are not point: \n"
                                root = etree.fromstring(message)
                                files_with_problems = root.findall(".//file")
                                if files_with_problems:
                                    for a_file in files_with_problems:
                                        txt_message = (
                                            txt_message
                                            + "\t"
                                            + a_file.get("name", "")
                                            + "\n"
                                        )
                                self.append_to_errors(txt_message)

                            if result_code == 9:  # pragma: no cover
                                # Duplicated options
                                stage = -1
                                root = etree.fromstring(message)
                                xml_lists = root.findall(".//list")
                                if xml_lists:
                                    for aList in xml_lists:
                                        list_element = {"name": aList.get("name")}
                                        xml_values = aList.findall(".//value")
                                        value_array = []
                                        for aValue in xml_values:
                                            value_array.append(aValue.text)
                                        list_element["values"] = value_array
                                        xml_references = aList.findall(".//reference")
                                        ref_array = []
                                        for aRef in xml_references:
                                            ref_array.append(
                                                {
                                                    "variable": aRef.get("variable"),
                                                    "option": aRef.get("option"),
                                                }
                                            )
                                        list_element["references"] = ref_array
                                        list_array.append(list_element)
                                else:
                                    xml_lists = root.findall(".//duplicatedItem")
                                    if xml_lists:
                                        for aList in xml_lists:
                                            variable_name = aList.get("variableName")
                                            duplicated_value = aList.get(
                                                "duplicatedValue"
                                            )
                                            found_index = -1
                                            for index, an_error in enumerate(
                                                list_array
                                            ):
                                                if (
                                                    an_error["name"]
                                                    == variable_name + ".csv"
                                                ):
                                                    found_index = index
                                                    break
                                            if found_index == -1:
                                                list_element = {
                                                    "name": variable_name + ".csv",
                                                    "values": [duplicated_value],
                                                }
                                                list_array.append(list_element)
                                            else:
                                                list_array[found_index][
                                                    "values"
                                                ].append(duplicated_value)

                            if result_code == 36:  # pragma: no cover
                                # Multi-select variable with spaces in options
                                stage = -1
                                root = etree.fromstring(message)
                                xml_lists = root.findall(".//list")
                                if xml_lists:
                                    for aList in xml_lists:
                                        list_element = {"name": aList.get("name")}
                                        xml_values = aList.findall(".//value")
                                        value_array = []
                                        for aValue in xml_values:
                                            value_array.append(aValue.text)
                                        list_element["values"] = value_array
                                        xml_references = aList.findall(".//reference")
                                        ref_array = []
                                        for aRef in xml_references:
                                            ref_array.append(
                                                {
                                                    "variable": aRef.get("variable"),
                                                    "option": aRef.get("option"),
                                                }
                                            )
                                        list_element["references"] = ref_array
                                        list_array.append(list_element)
                                else:
                                    xml_lists = root.findall(".//invalidItem")
                                    if xml_lists:
                                        for aList in xml_lists:
                                            variable_name = aList.get("variableName")
                                            duplicated_value = aList.get("invalidValue")
                                            found_index = -1
                                            for index, an_error in enumerate(
                                                list_array
                                            ):
                                                if (
                                                    an_error["name"]
                                                    == variable_name + ".csv"
                                                ):
                                                    found_index = index
                                                    break
                                            if found_index == -1:
                                                list_element = {
                                                    "name": variable_name + ".csv",
                                                    "values": [duplicated_value],
                                                }
                                                list_array.append(list_element)
                                            else:
                                                list_array[found_index][
                                                    "values"
                                                ].append(duplicated_value)

                            if result_code == 10:  # pragma: no cover
                                # Primary key not found
                                stage = 1
                                self.append_to_errors(
                                    self._(
                                        "The primary key was not found in the ODK form or is inside a repeat"
                                    )
                                )
                            if (
                                result_code == 11 or result_code == 12
                            ):  # pragma: no cover
                                # Parsing XML error
                                root = etree.fromstring(message)
                                file_list = root.findall(".//file")
                                if file_list:
                                    for a_file in file_list:
                                        file_with_error = a_file.get("name")
                                stage = -1
                            if 13 <= result_code <= 15:  # pragma: no cover
                                # Parsing CSV error
                                root = etree.fromstring(message)
                                file_list = root.findall(".//file")
                                if file_list:
                                    for a_file in file_list:
                                        file_with_error = a_file.get("name")
                                stage = -1
                            if result_code == 16:  # pragma: no cover
                                # Search error. Report issue
                                self.report_critical_error(
                                    user_id, project_id, form_id, result_code, message
                                )
                                stage = -1
                            if result_code == 17:  # pragma: no cover
                                # Primary key is invalid
                                self.append_to_errors(
                                    self._("The primary key is invalid.")
                                )
                                stage = 1
                            if result_code == 18:  # pragma: no cover
                                # Duplicate tables. Report issue because this was checked before
                                self.report_critical_error(
                                    user_id, project_id, form_id, result_code, message
                                )
                                stage = -1
                            if result_code == 19:  # pragma: no cover
                                # Duplicate fields. Report issue because this was checked before
                                self.report_critical_error(
                                    user_id, project_id, form_id, result_code, message
                                )
                                stage = -1
                            if result_code == 20:  # pragma: no cover
                                # Invalid fields. Report issue because this was checked before
                                self.report_critical_error(
                                    user_id, project_id, form_id, result_code, message
                                )
                                stage = -1
                            if result_code == 21:  # pragma: no cover
                                # Duplicated lookups
                                root = etree.fromstring(message)
                                duplicated_tables = root.findall(".//table")
                                if duplicated_tables:
                                    for a_table in duplicated_tables:
                                        option = {
                                            "name": a_table.get("name"),
                                            "duplicates": [],
                                        }
                                        duplicated_names = a_table.findall(
                                            ".//duplicate"
                                        )
                                        if duplicated_names:
                                            for a_name in duplicated_names:
                                                option["duplicates"].append(
                                                    a_name.get("name")
                                                )
                                        duplicated_choices.append(option)
                                stage = -1
                            if result_code == 25:  # pragma: no cover
                                self.report_critical_error(
                                    user_id, project_id, form_id, result_code, message
                                )
                                stage = -1
                            if result_code == 24:  # pragma: no cover
                                # Tables with more than 64 characters
                                root = etree.fromstring(message)
                                tables_with_error = root.findall(".//table")
                                if tables_with_error:
                                    for a_table in tables_with_error:
                                        table_name = a_table.get("name")
                                        table_msel = a_table.get("msel")
                                        if table_msel == "false":
                                            tables_with_name_error.append(table_name)
                                        else:
                                            parts = table_name.split("_msel_")
                                            tables_with_name_error.append(
                                                parts[0]
                                                + " "
                                                + self._("with select")
                                                + " "
                                                + parts[1]
                                            )
                                stage = -1

                return {
                    "form_data": form_data,
                    "userid": user_id,
                    "projcode": project_code,
                    "formid": form_id,
                    "projectDetails": project_details,
                    "result_code": result_code,
                    "list_array": list_array,
                    "duplicated_choices": duplicated_choices,
                    "tables_with_name_error": tables_with_name_error,
                    "file_with_error": file_with_error,
                    "method": method,
                    "stage": stage,
                    "languages": languages,
                    "languages_string": languages_string,
                    "primary_key": primary_key,
                    "discard_testing_data": discard_testing_data,
                    "default": default,
                    "has_submit_assistant": has_submit_assistant,
                    "survey_data_columns": "|".join(survey_data_columns),
                    "choices_data_columns": "|".join(choices_data_columns),
                }
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
