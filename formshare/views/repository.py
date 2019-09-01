from .classes import PrivateView
from formshare.processes.odk.processes import get_form_data
import json
from formshare.processes.db import get_project_id_from_name
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from formshare.processes.odk.api import create_repository, get_odk_path
from lxml import etree
from formshare.processes.elasticsearch.repository_index import delete_dataset_index


class GenerateRepository(PrivateView):
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

        form_data = get_form_data(project_id, form_id, self.request)
        result_code = -1
        list_array = []
        duplicated_choices = []
        languages = []
        languages_string = ""
        file_with_error = ""
        method = "get"
        stage = 1
        primary_key = ""
        if form_data:
            if form_data["schema"] is None:
                if self.request.method == "POST":
                    method = "post"
                    postdata = self.get_post_dict()
                    run_process = True
                    if "start_stage1" in postdata.keys():
                        stage = 1
                        if postdata.get("form_pkey", "") != "":
                            primary_key = postdata.get("form_pkey")
                        else:
                            self.errors.append(
                                self._("The primary key cannot be empty")
                            )
                            run_process = False
                    default_language_string = "("
                    other_languages_string = ""
                    yes_no_string = ""
                    if "start_stage2" in postdata.keys():
                        stage = 2
                        languages_string = postdata.get("languages_string", "")
                        primary_key = postdata.get("form_pkey")
                        languages = json.loads(languages_string)
                        default_language = ""
                        if postdata.get("form_deflang", "") != "":
                            default_language = postdata.get("form_deflang")
                        else:
                            self.errors.append(
                                self._("You need to indicate the primary language")
                            )
                            run_process = False

                        other_languages = []
                        empty_code_found = False
                        for language in languages:
                            if postdata.get("LNG-" + language["name"], "") != "":
                                if language["name"] == default_language:
                                    default_language_string = (
                                        default_language_string
                                        + postdata.get("LNG-" + language["name"])
                                        + ")"
                                        + language["name"]
                                    )
                                    language["code"] = postdata.get("LNG-" + language["name"])
                                else:
                                    other_languages.append(
                                        "("
                                        + postdata.get("LNG-" + language["name"])
                                        + ")"
                                        + language["name"]
                                    )
                                    language["code"] = postdata.get("LNG-" + language["name"])
                            else:
                                empty_code_found = True
                                break
                        if empty_code_found:
                            self.errors.append(
                                self._(
                                    "You need to indicate a ISO 639-1 for each language"
                                )
                            )
                            run_process = False
                        else:
                            other_languages_string = ",".join(other_languages)

                        print("****************************88")
                        print(default_language_string)
                        print(other_languages_string)
                        print("****************************88")

                        if (
                            postdata.get("yesvalue", "") != ""
                            and postdata.get("novalue", "") != ""
                        ):
                            yes_no_string = (
                                postdata.get("yesvalue")
                                + "|"
                                + postdata.get("novalue", "")
                            )
                        else:
                            self.errors.append(
                                self._("You need to indicate the yes and no values for the primary language")
                            )
                            run_process = False
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
                                default_language_string,
                                other_languages_string,
                                yes_no_string,
                            )
                        if result_code == 0:
                            delete_dataset_index(
                                self.request.registry.settings,
                                user_id,
                                project_code,
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
                            if result_code == 1:
                                # Internal error: Report issue
                                stage = -1
                            if result_code == 2:
                                # 64 or more relationships. Report issue because this was checked before
                                stage = -1
                            if 3 <= result_code <= 8:
                                if result_code == 3:
                                    root = etree.fromstring(message)
                                    language_array = root.findall(
                                        ".//language"
                                    )  # language
                                    if language_array:
                                        for aLang in language_array:
                                            languages.append({"code": "", "name": aLang.get("name")})
                                    languages_string = json.dumps(languages)
                                    stage = 2
                                else:
                                    stage = -1

                            if result_code == 9:
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
                            if result_code == 10:
                                # Primary key not found
                                stage = 1
                                self.errors.append(
                                    self._(
                                        "The primary key was not found in the ODK form"
                                    )
                                )
                            if result_code == 11 or result_code == 12:
                                # Parsing XML error
                                root = etree.fromstring(message)
                                file_list = root.findall(".//file")
                                if file_list:
                                    for a_file in file_list:
                                        file_with_error = a_file.get("name")
                                stage = -1
                            if 13 <= result_code <= 15:
                                # Parsing CSV error
                                root = etree.fromstring(message)
                                file_list = root.findall(".//file")
                                if file_list:
                                    for a_file in file_list:
                                        file_with_error = a_file.get("name")
                                stage = -1
                            if result_code == 16:
                                # Search error. Report issue
                                stage = -1
                            if result_code == 17:
                                # Primary key is invalid
                                self.errors.append(self._("The primary is invalid."))
                                stage = 1
                            if result_code == 18:
                                # Duplicate tables. Report issue because this was checked before
                                stage = -1
                            if result_code == 19:
                                # Duplicate fields. Report issue because this was checked before
                                stage = -1
                            if result_code == 20:
                                # Invalid fields. Report issue because this was checked before
                                stage = -1
                            if result_code == 21:
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

                return {
                    "form_data": form_data,
                    "userid": user_id,
                    "projcode": project_code,
                    "formid": form_id,
                    "projectDetails": project_details,
                    "result_code": result_code,
                    "list_array": list_array,
                    "duplicated_choices": duplicated_choices,
                    "file_with_error": file_with_error,
                    "method": method,
                    "stage": stage,
                    "languages": languages,
                    "languages_string": languages_string,
                    "primary_key": primary_key,
                }

            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()
