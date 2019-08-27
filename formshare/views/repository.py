from .classes import PrivateView
from formshare.processes.odk.processes import (
    get_form_data,
    update_form_stage,
    get_stage_info_from_form,
    update_form_stage_number,
    update_form_separation_file,
    get_tables_to_separate,
    generate_separation_file,
)

from formshare.processes.db import get_project_id_from_name
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from formshare.processes.odk.api import create_repository, get_odk_path
from lxml import etree
from formshare.processes.elasticsearch.repository_index import delete_dataset_index
from webhelpers2.html import literal


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
        odk_path = get_odk_path(self.request)
        if form_data:
            if form_data["schema"] is None:
                get = True
                list_array = []
                result_code = -1
                dict_variables = get_stage_info_from_form(
                    self.request, project_id, form_id
                )
                stage = dict_variables["stage"]
                primary_key = dict_variables["primary_key"]
                deflanguage = dict_variables["deflanguage"]
                languages = dict_variables["languages"]
                yesvalue = dict_variables["yesvalue"]
                novalue = dict_variables["novalue"]
                other_languages = dict_variables["other_languages"]
                yes_no_strings = dict_variables["yes_no_strings"]
                default_language = dict_variables["default_language"]

                has_tables_to_separate, sep_tables = get_tables_to_separate(
                    self.request, project_id, form_id
                )
                qvars = {"formid": form_id}
                if self.request.method == "POST":
                    get = False
                    postdata = self.get_post_dict()
                    if postdata["stage"] == "1":
                        stage = 1
                        primary_key = postdata["primarykey"]
                        if primary_key != "":
                            result_code, message = create_repository(
                                self.request,
                                self.user.id,
                                project_id,
                                form_id,
                                odk_path,
                                form_data["directory"],
                                primary_key,
                            )

                            # -------------------------------------------------------Stage 1 reply
                            if result_code != 0:
                                update_form_stage(
                                    self.request,
                                    project_id,
                                    form_id,
                                    stage,
                                    primary_key,
                                    None,
                                    None,
                                    None,
                                    None,
                                )
                            if (
                                result_code == 3
                                or result_code == 4
                                or (6 <= result_code <= 8)
                            ):
                                # Ask for language

                                root = etree.fromstring(message)
                                language_array = root.findall(".//language")  # language
                                if language_array:
                                    languages = []
                                    for aLang in language_array:
                                        languages.append(
                                            {"code": "", "name": aLang.text}
                                        )

                                update_form_stage_number(
                                    self.request, project_id, form_id, 2
                                )
                                stage = 2
                            if result_code == 2:
                                # This will ask about a separation file
                                root = etree.fromstring(message)
                                e_sep_file = root.find(".//sepfile")
                                update_form_separation_file(
                                    self.request, project_id, form_id, e_sep_file.text
                                )
                                update_form_stage_number(
                                    self.request, project_id, form_id, 3
                                )
                                has_tables_to_separate, sep_tables = get_tables_to_separate(
                                    self.request, project_id, form_id
                                )
                                stage = 3
                            if result_code == 9:
                                # This will tell the user to correct the repeated options
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
                                update_form_stage_number(
                                    self.request, project_id, form_id, 4
                                )
                                stage = 4
                            if result_code == 10 or result_code == 11:
                                # This would happen if for some reason the id that was chosen has a problem
                                self.errors.append(
                                    self._(
                                        "The primary key field does not exists or "
                                        "is inside a repeat"
                                    )
                                )
                                stage = 1
                                primary_key = ""
                                deflanguage = ""
                                languages = ""
                                yesvalue = ""
                                novalue = ""
                                other_languages = ""
                                yes_no_strings = ""
                                default_language = ""
                                update_form_stage_number(
                                    self.request, project_id, form_id, 1
                                )

                            if result_code == 17:
                                root = etree.fromstring(message)
                                xml_duplicates = root.findall(".//variable")
                                error_message = (
                                    self._(
                                        "The ODK has the following variables duplicated within "
                                        "the same repeat or outside a repeat:"
                                    )
                                    + "<br/>"
                                )
                                if xml_duplicates:
                                    for aDuplicate in xml_duplicates:
                                        error_message = (
                                            error_message + aDuplicate.text + "<br/>"
                                        )
                                error_message = error_message[:-5]
                                self.errors.append(literal(error_message))

                                # This would happen if the ODK has repeated columns. So go back to 1
                                stage = 1
                                primary_key = ""
                                deflanguage = ""
                                languages = ""
                                yesvalue = ""
                                novalue = ""
                                other_languages = ""
                                yes_no_strings = ""
                                default_language = ""
                                update_form_stage_number(
                                    self.request, project_id, form_id, 1
                                )

                            if result_code == 13:
                                # Tell the user it missed a CSV or ZIP file
                                update_form_stage_number(
                                    self.request, project_id, form_id, 5
                                )
                                stage = 5

                            if result_code == 14 or result_code == 15:
                                # Tell the user it missed a CSV or ZIP file
                                update_form_stage_number(
                                    self.request, project_id, form_id, 6
                                )
                                stage = 6
                                self.errors.append(message)

                            if result_code == 1:
                                # This is bad!!! So send the form to QLands
                                self.errors.append(message)
                        else:
                            self.errors.append(
                                self._("You need to specify a variable as primary key")
                            )

                    # ----------------------------------------------Stage 2

                    if postdata["stage"] == "2":
                        stage = 2
                        primary_key = postdata["primarykey"]
                        deflanguage = postdata["deflanguage"]
                        yesvalue = postdata["yesvalue"]
                        novalue = postdata["novalue"]
                        languages = []
                        for key in postdata.keys():
                            if key[:3] == "LNG":
                                parts = key.split("-")
                                languages.append(
                                    {"code": postdata[key], "name": parts[1]}
                                )
                        if deflanguage != "":
                            cont_proc = True
                            if deflanguage.upper() != "ENGLISH":
                                if yesvalue == "" or novalue == "":
                                    self.errors.append(
                                        self._(
                                            "Since the default language is not English you need "
                                            "to indicate Yes / No values"
                                        )
                                    )
                                    cont_proc = False
                                    result_code = 3
                            if cont_proc:
                                chklang = True
                                def_lang_code = ""
                                for lang in languages:
                                    if lang["code"] == "":
                                        chklang = False
                                    else:
                                        if lang["name"].upper() == deflanguage.upper():
                                            def_lang_code = lang["code"]
                                if chklang:
                                    default_language = (
                                        "(" + def_lang_code + ")" + deflanguage
                                    )
                                    lang_array = []
                                    for lang in languages:
                                        lang_array.append(
                                            "(" + lang["code"] + ")" + lang["name"]
                                        )
                                    other_languages = ",".join(lang_array)
                                    yes_no_strings = yesvalue + "|" + novalue
                                    if yes_no_strings == "|":
                                        yes_no_strings = None
                                    result_code, message = create_repository(
                                        self.request,
                                        self.user.id,
                                        project_id,
                                        form_id,
                                        odk_path,
                                        form_data["directory"],
                                        primary_key,
                                        default_language,
                                        other_languages,
                                        yes_no_strings,
                                    )
                                    # -------------------------------------------------Stage 2 reply
                                    if result_code != 0:
                                        update_form_stage(
                                            self.request,
                                            project_id,
                                            form_id,
                                            stage,
                                            primary_key,
                                            default_language,
                                            other_languages,
                                            yes_no_strings,
                                            None,
                                        )
                                    if (
                                        result_code == 3
                                        or result_code == 4
                                        or (6 <= result_code <= 8)
                                    ):
                                        # At this stage the information should be ok. However if the user
                                        # exits the process, changes form and adds a new language then
                                        # reenter this information is required

                                        root = etree.fromstring(message)
                                        language_array = root.findall(".//language")
                                        if language_array:
                                            languages = []
                                            for aLang in language_array:
                                                languages.append(
                                                    {"code": "", "name": aLang.text}
                                                )
                                        update_form_stage_number(
                                            self.request, project_id, form_id, 2
                                        )
                                        stage = 2

                                    if result_code == 2:
                                        # This will ask about a separation file
                                        root = etree.fromstring(message)
                                        e_sep_file = root.find(".//sepfile")
                                        update_form_separation_file(
                                            self.request,
                                            project_id,
                                            form_id,
                                            e_sep_file.text,
                                        )
                                        update_form_stage_number(
                                            self.request, project_id, form_id, 3
                                        )
                                        has_tables_to_separate, sep_tables = get_tables_to_separate(
                                            self.request, project_id, form_id
                                        )
                                        stage = 3
                                    if result_code == 9:
                                        # This will ask to fix the options
                                        root = etree.fromstring(message)
                                        xml_lists = root.findall(".//list")
                                        if xml_lists:
                                            for aList in xml_lists:
                                                list_element = {
                                                    "name": aList.get("name")
                                                }
                                                xml_values = aList.findall(".//value")
                                                value_array = []
                                                for aValue in xml_values:
                                                    value_array.append(aValue.text)
                                                list_element["values"] = value_array
                                                xml_references = aList.findall(
                                                    ".//reference"
                                                )
                                                ref_array = []
                                                for aRef in xml_references:
                                                    ref_array.append(
                                                        {
                                                            "variable": aRef.get(
                                                                "variable"
                                                            ),
                                                            "option": aRef.get(
                                                                "option"
                                                            ),
                                                        }
                                                    )
                                                list_element["references"] = ref_array
                                                list_array.append(list_element)
                                        update_form_stage_number(
                                            self.request, project_id, form_id, 4
                                        )
                                        stage = 4
                                    if result_code == 5:
                                        self.errors.append(
                                            message
                                            + self._(
                                                ". You need to fix the XLSX, upload it again and continue this process."
                                            )
                                        )
                                    if result_code == 10 or result_code == 11:
                                        self.errors.append(
                                            self._(
                                                "The primary key field does not exists or is inside a repeat"
                                            )
                                        )
                                        # At this stage the information should be ok. However if the user
                                        # exits the process, changes the form so much that the primary key is invalid
                                        # reenter this information is required
                                        stage = 1
                                        primary_key = ""
                                        deflanguage = ""
                                        languages = ""
                                        yesvalue = ""
                                        novalue = ""
                                        other_languages = ""
                                        yes_no_strings = ""
                                        default_language = ""
                                        update_form_stage_number(
                                            self.request, project_id, form_id, 1
                                        )
                                        # We need to reset the language

                                    if result_code == 17:
                                        self.errors.append(message)
                                        # This would happen if the ODK has repeated columns. So go back to 1
                                        stage = 1
                                        primary_key = ""
                                        deflanguage = ""
                                        languages = ""
                                        yesvalue = ""
                                        novalue = ""
                                        other_languages = ""
                                        yes_no_strings = ""
                                        default_language = ""
                                        update_form_stage_number(
                                            self.request, project_id, form_id, 1
                                        )

                                    if result_code == 13:
                                        # Tell the user it missed a CSV or ZIP file
                                        update_form_stage_number(
                                            self.request, project_id, form_id, 5
                                        )
                                        stage = 5

                                    if result_code == 14 or result_code == 15:
                                        # Tell the user it missed a CSV or ZIP file
                                        update_form_stage_number(
                                            self.request, project_id, form_id, 6
                                        )
                                        stage = 6
                                        self.errors.append(message)

                                    if result_code == 1:
                                        # This is bad!!! So send the form to QLands
                                        self.errors.append(message)
                                else:
                                    result_code = 3
                                    self.errors.append(
                                        self._("Each language needs a ISO 639-1 code")
                                    )

                        else:
                            self.errors.append(
                                self._("You need to specify a default language")
                            )

                    # -----------------------------------------------------------------Stage 3

                    if postdata["stage"] == "3":
                        has_tables_to_separate, sep_tables = get_tables_to_separate(
                            self.request, project_id, form_id
                        )

                        primary_key = postdata["primarykey"]
                        default_language = postdata["defaultLanguage"]
                        other_languages = postdata["otherLanguages"]
                        yes_no_strings = postdata["yesNoStrings"]

                        if not has_tables_to_separate:

                            # Constructs separation file and apply it
                            separation_file = generate_separation_file(
                                self.request, project_id, form_id
                            )

                            if default_language == "":
                                default_language = None
                                other_languages = None
                                yes_no_strings = None

                            result_code, message = create_repository(
                                self.request,
                                self.user.id,
                                project_id,
                                form_id,
                                odk_path,
                                form_data["directory"],
                                primary_key,
                                default_language,
                                other_languages,
                                yes_no_strings,
                            )

                            # -----------------------------------------------------------------------------Stage3 reply
                            if result_code != 0:
                                update_form_stage(
                                    self.request,
                                    project_id,
                                    form_id,
                                    stage,
                                    primary_key,
                                    default_language,
                                    other_languages,
                                    yes_no_strings,
                                    separation_file,
                                )
                            if result_code == 10 or result_code == 11:
                                # At this stage the information should be ok however,
                                # this would happen if the user exited the process to make
                                # the changes in the options but changed the form so much
                                # and the primary key is invalid. So reset everything and
                                # go back to stage 1
                                self.errors.append(
                                    self._(
                                        "The primary key field does not exists or is inside a repeat"
                                    )
                                )
                                stage = 1
                                primary_key = ""
                                deflanguage = ""
                                languages = ""
                                yesvalue = ""
                                novalue = ""
                                other_languages = ""
                                yes_no_strings = ""
                                default_language = ""
                                update_form_stage_number(
                                    self.request, project_id, form_id, 1
                                )

                            if result_code == 17:
                                self.errors.append(message)
                                # This would happen if the ODK has repeated columns. So go back to 1
                                stage = 1
                                primary_key = ""
                                deflanguage = ""
                                languages = ""
                                yesvalue = ""
                                novalue = ""
                                other_languages = ""
                                yes_no_strings = ""
                                default_language = ""
                                update_form_stage_number(
                                    self.request, project_id, form_id, 1
                                )

                            if (
                                result_code == 3
                                or result_code == 4
                                or (6 <= result_code <= 8)
                            ):
                                # At this stage the information should be ok however,
                                # this would happen if the user exited the process to make
                                # the changes in the options but also added new languages
                                # So go back to 2

                                root = etree.fromstring(message)
                                language_array = root.findall(".//language")
                                if language_array:
                                    languages = []
                                    for aLang in language_array:
                                        languages.append(
                                            {"code": "", "name": aLang.text}
                                        )
                                update_form_stage_number(
                                    self.request, project_id, form_id, 2
                                )
                                stage = 2

                            if result_code == 5:
                                self.errors.append(
                                    message
                                    + self._(
                                        ". You need to fix the XLSX, upload it again "
                                        "and continue this process."
                                    )
                                )

                            if result_code == 2:
                                # At this stage the information should be ok however,
                                # this would happen if the user exited the process to make
                                # the changes in the options but changed the form so much
                                # that a new separation file is needed so reset the separation form
                                # and go back to 3
                                root = etree.fromstring(message)
                                e_sep_file = root.find(".//sepfile")
                                update_form_separation_file(
                                    self.request, project_id, form_id, e_sep_file.text
                                )
                                update_form_stage_number(
                                    self.request, project_id, form_id, 3
                                )
                                has_tables_to_separate, sep_tables = get_tables_to_separate(
                                    self.request, project_id, form_id
                                )
                                stage = 3
                            if result_code == 9:
                                # This will happen if the user did not fixed all options
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
                                update_form_stage_number(
                                    self.request, project_id, form_id, 4
                                )
                                stage = 4

                            if result_code == 13:
                                # Tell the user it missed a CSV or ZIP file
                                update_form_stage_number(
                                    self.request, project_id, form_id, 5
                                )
                                stage = 5

                            if result_code == 14 or result_code == 15:
                                # Tell the user it missed a CSV or ZIP file
                                update_form_stage_number(
                                    self.request, project_id, form_id, 6
                                )
                                stage = 6
                                self.errors.append(message)

                            if result_code == 1:
                                # This is bad!!! So send the form to QLands
                                self.errors.append(message)

                    # ---------------------------------------------------------------------Stage 4

                    if postdata["stage"] == "4":
                        stage = 4
                        primary_key = postdata["primarykey"]
                        default_language = postdata["defaultLanguage"]
                        other_languages = postdata["otherLanguages"]
                        yes_no_strings = postdata["yesNoStrings"]

                        if default_language == "":
                            default_language = None
                            other_languages = None
                            yes_no_strings = None

                        result_code, message = create_repository(
                            self.request,
                            self.user.id,
                            project_id,
                            form_id,
                            odk_path,
                            form_data["directory"],
                            primary_key,
                            default_language,
                            other_languages,
                            yes_no_strings,
                        )

                        # --------------------------------------------------------------------------Stage 4 reply

                        if result_code != 0:
                            update_form_stage(
                                self.request,
                                project_id,
                                form_id,
                                stage,
                                primary_key,
                                default_language,
                                other_languages,
                                yes_no_strings,
                                None,
                            )
                        if result_code == 10 or result_code == 11:
                            self.errors.append(
                                self._(
                                    "The primary key field does not exists or is inside a repeat"
                                )
                            )
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but changed the form so much
                            # and the primary key is invalid. So reset everything and
                            # go back to stage 1
                            stage = 1
                            primary_key = ""
                            deflanguage = ""
                            languages = ""
                            yesvalue = ""
                            novalue = ""
                            other_languages = ""
                            yes_no_strings = ""
                            default_language = ""
                            update_form_stage_number(
                                self.request, project_id, form_id, 1
                            )

                        if result_code == 17:
                            self.errors.append(message)
                            # This would happen if the ODK has repeated columns. So go back to 1
                            stage = 1
                            primary_key = ""
                            deflanguage = ""
                            languages = ""
                            yesvalue = ""
                            novalue = ""
                            other_languages = ""
                            yes_no_strings = ""
                            default_language = ""
                            update_form_stage_number(
                                self.request, project_id, form_id, 1
                            )

                        if (
                            result_code == 3
                            or result_code == 4
                            or (6 <= result_code <= 8)
                        ):
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but also added new languages
                            # So go back to 2

                            root = etree.fromstring(message)
                            language_array = root.findall(".//language")
                            if language_array:
                                languages = []
                                for aLang in language_array:
                                    languages.append({"code": "", "name": aLang.text})
                            update_form_stage_number(
                                self.request, project_id, form_id, 2
                            )
                            stage = 2

                        if result_code == 5:
                            self.errors.append(
                                message
                                + self._(
                                    ". You need to fix the XLSX, upload it again and "
                                    "continue this process."
                                )
                            )

                        if result_code == 2:
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but changed the form so much
                            # that a new separation file is needed so reset the separation form
                            # and go back to 3
                            root = etree.fromstring(message)
                            e_sep_file = root.find(".//sepfile")
                            update_form_separation_file(
                                self.request, project_id, form_id, e_sep_file.text
                            )
                            update_form_stage_number(
                                self.request, project_id, form_id, 3
                            )
                            has_tables_to_separate, sep_tables = get_tables_to_separate(
                                self.request, project_id, form_id
                            )
                            stage = 3
                        if result_code == 9:
                            # This will happen if the user did not fixed all options
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
                            update_form_stage_number(
                                self.request, project_id, form_id, 4
                            )
                            stage = 4

                        if result_code == 13:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(
                                self.request, project_id, form_id, 5
                            )
                            stage = 5

                        if result_code == 14 or result_code == 15:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(
                                self.request, project_id, form_id, 6
                            )
                            stage = 6
                            self.errors.append(message)

                        if result_code == 1:
                            # This is bad!!! So send the form to QLands
                            self.errors.append(message)

                    # ----------------------------------------Stage 5------------------------------------------------

                    if postdata["stage"] == "5":
                        stage = 5
                        primary_key = postdata["primarykey"]
                        default_language = postdata["defaultLanguage"]
                        other_languages = postdata["otherLanguages"]
                        yes_no_strings = postdata["yesNoStrings"]

                        if default_language == "":
                            default_language = None
                            other_languages = None
                            yes_no_strings = None

                        result_code, message = create_repository(
                            self.request,
                            self.user.id,
                            project_id,
                            form_id,
                            odk_path,
                            form_data["directory"],
                            primary_key,
                            default_language,
                            other_languages,
                            yes_no_strings,
                        )

                        # ---------------------------------Stage5 Reply- -----------------------------------------------

                        if result_code != 0:
                            update_form_stage(
                                self.request,
                                project_id,
                                form_id,
                                stage,
                                primary_key,
                                default_language,
                                other_languages,
                                yes_no_strings,
                                None,
                            )
                        if result_code == 10 or result_code == 11:
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but changed the form so much
                            # and the primary key is invalid. So reset everything and
                            # go back to stage 1
                            self.errors.append(
                                self._(
                                    "The primary key field does not exists or is inside a repeat"
                                )
                            )
                            stage = 1
                            primary_key = ""
                            deflanguage = ""
                            languages = ""
                            yesvalue = ""
                            novalue = ""
                            other_languages = ""
                            yes_no_strings = ""
                            default_language = ""
                            update_form_stage_number(
                                self.request, project_id, form_id, 1
                            )

                        if result_code == 17:
                            self.errors.append(message)
                            # This would happen if the ODK has repeated columns. So go back to 1
                            stage = 1
                            primary_key = ""
                            deflanguage = ""
                            languages = ""
                            yesvalue = ""
                            novalue = ""
                            other_languages = ""
                            yes_no_strings = ""
                            default_language = ""
                            update_form_stage_number(
                                self.request, project_id, form_id, 1
                            )

                        if (
                            result_code == 3
                            or result_code == 4
                            or (6 <= result_code <= 8)
                        ):
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but also added new languages
                            # So go back to 2

                            root = etree.fromstring(message)
                            language_array = root.findall(".//language")
                            if language_array:
                                languages = []
                                for aLang in language_array:
                                    languages.append({"code": "", "name": aLang.text})
                            update_form_stage_number(
                                self.request, project_id, form_id, 2
                            )
                            stage = 2

                        if result_code == 5:
                            self.errors.append(
                                message
                                + self._(
                                    ". You need to fix the XLSX, upload it again "
                                    "and continue this process."
                                )
                            )

                        if result_code == 2:
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but changed the form so much
                            # that a new separation file is needed so reset the separation form
                            # and go back to 3
                            root = etree.fromstring(message)
                            e_sep_file = root.find(".//sepfile")
                            update_form_separation_file(
                                self.request, project_id, form_id, e_sep_file.text
                            )
                            update_form_stage_number(
                                self.request, project_id, form_id, 3
                            )
                            has_tables_to_separate, sep_tables = get_tables_to_separate(
                                self.request, project_id, form_id
                            )
                            stage = 3
                        if result_code == 9:
                            # This will happen if the user did not fixed all options
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
                            update_form_stage_number(
                                self.request, project_id, form_id, 4
                            )
                            stage = 4

                        if result_code == 13:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(
                                self.request, project_id, form_id, 5
                            )
                            stage = 5

                        if result_code == 14 or result_code == 15:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(
                                self.request, project_id, form_id, 6
                            )
                            stage = 6
                            self.errors.append(message)

                        if result_code == 1:
                            # This is bad!!! So send the form to QLands
                            self.errors.append(message)

                    # ----------------------------------------Stage 6

                    if postdata["stage"] == "6":
                        stage = 6
                        primary_key = postdata["primarykey"]
                        default_language = postdata["defaultLanguage"]
                        other_languages = postdata["otherLanguages"]
                        yes_no_strings = postdata["yesNoStrings"]

                        if default_language == "":
                            default_language = None
                            other_languages = None
                            yes_no_strings = None

                        result_code, message = create_repository(
                            self.request,
                            self.user.id,
                            project_id,
                            form_id,
                            odk_path,
                            form_data["directory"],
                            primary_key,
                            default_language,
                            other_languages,
                            yes_no_strings,
                        )

                        # ----------------------------------------Stage 6 Reply----------------------------

                        if result_code != 0:
                            update_form_stage(
                                self.request,
                                project_id,
                                form_id,
                                stage,
                                primary_key,
                                default_language,
                                other_languages,
                                yes_no_strings,
                                None,
                            )
                        if result_code == 10 or result_code == 11:
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but changed the form so much
                            # and the primary key is invalid. So reset everything and
                            # go back to stage 1
                            self.errors.append(
                                self._(
                                    "The primary key field does not exists or is inside a repeat"
                                )
                            )
                            stage = 1
                            primary_key = ""
                            deflanguage = ""
                            languages = ""
                            yesvalue = ""
                            novalue = ""
                            other_languages = ""
                            yes_no_strings = ""
                            default_language = ""
                            update_form_stage_number(
                                self.request, project_id, form_id, 1
                            )

                        if result_code == 17:
                            # This would happen if the ODK has repeated columns. So go back to 1
                            self.errors.append(message)
                            stage = 1
                            primary_key = ""
                            deflanguage = ""
                            languages = ""
                            yesvalue = ""
                            novalue = ""
                            other_languages = ""
                            yes_no_strings = ""
                            default_language = ""
                            update_form_stage_number(
                                self.request, project_id, form_id, 1
                            )

                        if (
                            result_code == 3
                            or result_code == 4
                            or (6 <= result_code <= 8)
                        ):
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but also added new languages
                            # So go back to 2

                            root = etree.fromstring(message)
                            language_array = root.findall(".//language")
                            if language_array:
                                languages = []
                                for aLang in language_array:
                                    languages.append({"code": "", "name": aLang.text})
                            update_form_stage_number(
                                self.request, project_id, form_id, 2
                            )
                            stage = 2

                        if result_code == 5:
                            self.errors.append(
                                message
                                + self._(
                                    ". You need to fix the XLSX, upload it "
                                    "again and continue this process."
                                )
                            )

                        if result_code == 2:
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but changed the form so much
                            # that a new separation file is needed so reset the separation form
                            # and go back to 3
                            root = etree.fromstring(message)
                            e_sep_file = root.find(".//sepfile")
                            update_form_separation_file(
                                self.request, project_id, form_id, e_sep_file.text
                            )
                            update_form_stage_number(
                                self.request, project_id, form_id, 3
                            )
                            has_tables_to_separate, sep_tables = get_tables_to_separate(
                                self.request, project_id, form_id
                            )
                            stage = 3
                        if result_code == 9:
                            # This will happen if the user did not fixed all options
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
                            update_form_stage_number(
                                self.request, project_id, form_id, 4
                            )
                            stage = 4

                        if result_code == 13:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(
                                self.request, project_id, form_id, 5
                            )
                            stage = 5

                        if result_code == 14 or result_code == 15:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(
                                self.request, project_id, form_id, 6
                            )
                            stage = 6
                            self.errors.append(message)

                        if result_code == 1:
                            # This is bad!!! So send the form to QLands
                            self.errors.append(message)

                if self.request.method == "GET":
                    if len(languages) == 0 and stage == 2:
                        stage = 1

                if result_code == 0:
                    self.returnRawViewResult = True
                    delete_dataset_index(
                        self.request.registry.settings, user_id, project_code, form_id
                    )
                    self.request.session.flash(
                        self._("FormShare is creating the repository") + "|info"
                    )
                    return HTTPFound(
                        self.request.route_url(
                            "form_details",
                            userid=user_id,
                            projcode=project_code,
                            formid=form_id,
                        )
                    )
                else:
                    return {
                        "formData": form_data,
                        "stage": stage,
                        "error_summary": self.errors,
                        "resCode": result_code,
                        "primaryKey": primary_key,
                        "languages": languages,
                        "yesvalue": yesvalue,
                        "novalue": novalue,
                        "deflanguage": deflanguage,
                        "otherLanguages": other_languages,
                        "yesNoStrings": yes_no_strings,
                        "defaultLanguage": default_language,
                        "listArray": list_array,
                        "sepTables": sep_tables,
                        "qvars": qvars,
                        "userid": user_id,
                        "projcode": project_code,
                        "formid": form_id,
                        "hasTablesToSeparate": has_tables_to_separate,
                        "get": get,
                        "projectDetails": project_details,
                    }
            else:
                return HTTPFound(
                    location=self.request.route_url(
                        "exist", userid=user_id, projcode=project_code, formid=form_id
                    )
                )
        else:
            raise HTTPNotFound()


def check_table_name(table_name):
    res = True
    if table_name.lower() == "table":
        res = False
    if table_name.lower() == "group":
        res = False
    if table_name.lower() == "select":
        res = False
    if table_name.lower() == "from":
        res = False
    if table_name.lower() == "where":
        res = False
    if table_name.lower() == "on":
        res = False
    if table_name.lower() == "and":
        res = False
    if table_name.lower() == "or":
        res = False
    if table_name.lower() == "by":
        res = False
    if table_name.lower() == "not":
        res = False
    if table_name.lower() == "order":
        res = False
    if table_name.lower() == "procedure":
        res = False
    if table_name.lower() == "update":
        res = False
    if table_name.lower() == "delete":
        res = False
    if table_name.lower() == "set":
        res = False
    if table_name.lower() == "commit":
        res = False
    if table_name.lower() == "trigger":
        res = False
    if table_name.lower() == "rollback":
        res = False
    if table_name.lower() == "insert":
        res = False
    if table_name.lower() == "integer":
        res = False
    if table_name.lower() == "varchar":
        res = False
    return res


class RepositoryExist(PrivateView):
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

        return {"userid": user_id, "projcode": project_code, "formid": form_id}
