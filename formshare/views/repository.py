from .classes import PrivateView
from formshare.processes.odk.processes import get_form_data, update_form_stage, \
    get_stage_info_from_form, update_form_stage_number, update_form_separation_file,\
    table_belongs_to_form, get_table_items, save_separation_order, add_group,\
    is_separation_ok, set_group_desc, get_group_name_from_id, delete_group, get_group_number_of_items, \
    get_tables_to_separate, generate_separation_file

from formshare.processes.db import get_project_id_from_name
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from formshare.processes.odk.api import create_repository, get_odk_path
from lxml import etree
import json
import re


class GenerateRepository(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound

        form_data = get_form_data(project_id, form_id, self.request)
        odk_path = get_odk_path(self.request)
        if form_data:
            if form_data["schema"] is None:
                get = True
                error_summary = {}
                list_array = []
                result_code = -1
                stage, primary_key, deflanguage, languages, yesvalue, novalue, other_languages, yes_no_strings, \
                    default_language, separation_file = get_stage_info_from_form(self.request, project_id, form_id)

                has_tables_to_separate, sep_tables = get_tables_to_separate(self.request, project_id, form_id)
                qvars = {'formid': form_id}
                if self.request.method == 'POST':
                    get = False
                    postdata = self.get_post_dict()
                    if postdata["stage"] == "1":
                        stage = 1
                        primary_key = postdata["primarykey"]
                        if primary_key != "":
                            result_code, message = create_repository(self.request, project_id, form_id,
                                                                     odk_path,
                                                                     form_data["directory"], primary_key)

                            # -------------------------------------------------------Stage 1 reply
                            if result_code != 0:
                                update_form_stage(self.request, project_id, form_id, stage, primary_key, None, None,
                                                  None, None)
                            if result_code == 3 or result_code == 4 or (6 <= result_code <= 8):
                                # Ask for language

                                root = etree.fromstring(message)
                                language_array = root.findall(".//language")  # language
                                if language_array:
                                    languages = []
                                    for aLang in language_array:
                                        languages.append({"code": "", "name": aLang.text})

                                update_form_stage_number(self.request, project_id, form_id, 2)
                                stage = 2
                            if result_code == 2:
                                # This will ask about a separation file
                                root = etree.fromstring(message)
                                e_sep_file = root.find(".//sepfile")
                                update_form_separation_file(self.request, project_id, form_id, e_sep_file.text)
                                update_form_stage_number(self.request, project_id, form_id, 3)
                                has_tables_to_separate, sep_tables = get_tables_to_separate(self.request, project_id,
                                                                                            form_id)
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
                                                {'variable': aRef.get("variable"),
                                                 'option': aRef.get("option")})
                                        list_element["references"] = ref_array
                                        list_array.append(list_element)
                                update_form_stage_number(self.request, project_id, form_id, 4)
                                stage = 4
                            if result_code == 10 or result_code == 11:
                                # This would happen if for some reason the id that was chosen has a problem
                                stage = 1
                                primary_key = ""
                                deflanguage = ""
                                languages = ""
                                yesvalue = ""
                                novalue = ""
                                other_languages = ""
                                yes_no_strings = ""
                                default_language = ""
                                update_form_stage_number(self.request, project_id, form_id, 1)

                            if result_code == 13:
                                # Tell the user it missed a CSV or ZIP file
                                update_form_stage_number(self.request, project_id, form_id, 5)
                                stage = 5

                            if result_code == 14 or result_code == 15:
                                # Tell the user it missed a CSV or ZIP file
                                update_form_stage_number(self.request, project_id, form_id, 6)
                                stage = 6
                                error_summary = {'error': message}

                            if result_code == 1:
                                # This is bad!!! So send the form to QLands
                                error_summary = {'error': message}
                        else:
                            error_summary = {'error': self._('You need to specify a variable as primary key')}

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
                                languages.append({'code': postdata[key], 'name': parts[1]})
                        if deflanguage != "":
                            cont_proc = True
                            if deflanguage.upper() != "ENGLISH":
                                if yesvalue == "" or novalue == "":
                                    error_summary = {'error': self._(
                                        'Since the default language is not English you '
                                        'need to indicate Yes / No values')}
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
                                    default_language = '(' + def_lang_code + ")" + deflanguage
                                    lang_array = []
                                    for lang in languages:
                                        lang_array.append("(" + lang["code"] + ")" + lang["name"])
                                    other_languages = ",".join(lang_array)
                                    yes_no_strings = yesvalue + "|" + novalue
                                    if yes_no_strings == "|":
                                        yes_no_strings = None
                                    result_code, message = create_repository(self.request, project_id, form_id,
                                                                             odk_path, form_data["directory"],
                                                                             primary_key, separation_file,
                                                                             default_language, other_languages,
                                                                             yes_no_strings)
                                    # -------------------------------------------------Stage 2 reply
                                    if result_code != 0:
                                        update_form_stage(self.request, project_id, form_id, stage, primary_key,
                                                          default_language, other_languages, yes_no_strings, None)
                                    if result_code == 3 or result_code == 4 or (6 <= result_code <= 8):
                                        # At this stage the information should be ok. However if the user
                                        # exits the process, changes form and adds a new language then
                                        # reenter this information is required

                                        root = etree.fromstring(message)
                                        language_array = root.findall(".//language")
                                        if language_array:
                                            languages = []
                                            for aLang in language_array:
                                                languages.append({"code": "", "name": aLang.text})
                                        update_form_stage_number(self.request, project_id, form_id, 2)
                                        stage = 2

                                    if result_code == 2:
                                        # This will ask about a separation file
                                        root = etree.fromstring(message)
                                        e_sep_file = root.find(".//sepfile")
                                        update_form_separation_file(self.request, project_id, form_id, e_sep_file.text)
                                        update_form_stage_number(self.request, project_id, form_id, 3)
                                        has_tables_to_separate, sep_tables = get_tables_to_separate(self.request,
                                                                                                    project_id, form_id)
                                        stage = 3
                                    if result_code == 9:
                                        # This will ask to fix the options
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
                                                        {'variable': aRef.get("variable"),
                                                         'option': aRef.get("option")})
                                                list_element["references"] = ref_array
                                                list_array.append(list_element)
                                        update_form_stage_number(self.request, project_id, form_id, 4)
                                        stage = 4
                                    if result_code == 5:
                                        error_summary = {'error': message + self._(
                                            ". You need to fix the XLSX, upload it again and continue this process.")}
                                    if result_code == 10 or result_code == 11:
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
                                        update_form_stage_number(self.request, project_id, form_id, 1)
                                        # We need to reset the language

                                    if result_code == 13:
                                        # Tell the user it missed a CSV or ZIP file
                                        update_form_stage_number(self.request, project_id, form_id, 5)
                                        stage = 5

                                    if result_code == 14 or result_code == 15:
                                        # Tell the user it missed a CSV or ZIP file
                                        update_form_stage_number(self.request, project_id, form_id, 6)
                                        stage = 6
                                        error_summary = {'error': message}

                                    if result_code == 1:
                                        # This is bad!!! So send the form to QLands
                                        error_summary = {'error': message}
                                else:
                                    result_code = 3
                                    error_summary = {'error': self._('Each language needs a ISO 639-1 code')}

                        else:
                            error_summary = {'error': self._('You need to specify a default language')}

                    # -----------------------------------------------------------------Stage 3

                    if postdata["stage"] == "3":
                        has_tables_to_separate, sep_tables = get_tables_to_separate(self.request, project_id, form_id)

                        primary_key = postdata["primarykey"]
                        default_language = postdata["defaultLanguage"]
                        other_languages = postdata["otherLanguages"]
                        yes_no_strings = postdata["yesNoStrings"]

                        if not has_tables_to_separate:

                            # Constructs separation file and apply it
                            separation_file = generate_separation_file(self.request, project_id, form_id)

                            if default_language == "":
                                default_language = None
                                other_languages = None
                                yes_no_strings = None

                            result_code, message = create_repository(self.request, project_id, form_id, odk_path,
                                                                     form_data["directory"], primary_key,
                                                                     separation_file, default_language, other_languages,
                                                                     yes_no_strings)

                            # -----------------------------------------------------------------------------Stage3 reply
                            if result_code != 0:
                                update_form_stage(self.request, project_id, form_id, stage, primary_key,
                                                  default_language, other_languages, yes_no_strings, separation_file)
                            if result_code == 10 or result_code == 11:
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
                                update_form_stage_number(self.request, project_id, form_id, 1)

                            if result_code == 3 or result_code == 4 or (6 <= result_code <= 8):
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
                                update_form_stage_number(self.request, project_id, form_id, 2)
                                stage = 2

                            if result_code == 5:
                                error_summary = {'error': message + self._(
                                    ". You need to fix the XLSX, upload it again and continue this process.")}

                            if result_code == 2:
                                # At this stage the information should be ok however,
                                # this would happen if the user exited the process to make
                                # the changes in the options but changed the form so much
                                # that a new separation file is needed so reset the separation form
                                # and go back to 3
                                root = etree.fromstring(message)
                                e_sep_file = root.find(".//sepfile")
                                update_form_separation_file(self.request, project_id, form_id, e_sep_file.text)
                                update_form_stage_number(self.request, project_id, form_id, 3)
                                has_tables_to_separate, sep_tables = get_tables_to_separate(self.request, project_id,
                                                                                            form_id)
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
                                                {'variable': aRef.get("variable"),
                                                 'option': aRef.get("option")})
                                        list_element["references"] = ref_array
                                        list_array.append(list_element)
                                update_form_stage_number(self.request, project_id, form_id, 4)
                                stage = 4

                            if result_code == 13:
                                # Tell the user it missed a CSV or ZIP file
                                update_form_stage_number(self.request, project_id, form_id, 5)
                                stage = 5

                            if result_code == 14 or result_code == 15:
                                # Tell the user it missed a CSV or ZIP file
                                update_form_stage_number(self.request, project_id, form_id, 6)
                                stage = 6
                                error_summary = {'error': message}

                            if result_code == 1:
                                # This is bad!!! So send the form to QLands
                                error_summary = {'error': message}

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

                        result_code, message = create_repository(self.request, project_id, form_id, odk_path,
                                                                 form_data["directory"], primary_key, separation_file,
                                                                 default_language, other_languages, yes_no_strings)

                        # --------------------------------------------------------------------------Stage 4 reply

                        if result_code != 0:
                            update_form_stage(self.request, project_id, form_id, stage, primary_key, default_language,
                                              other_languages, yes_no_strings, None)
                        if result_code == 10 or result_code == 11:
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
                            update_form_stage_number(self.request, project_id, form_id, 1)

                        if result_code == 3 or result_code == 4 or (6 <= result_code <= 8):
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
                            update_form_stage_number(self.request, project_id, form_id, 2)
                            stage = 2

                        if result_code == 5:
                            error_summary = {'error': message + self._(
                                ". You need to fix the XLSX, upload it again and continue this process.")}

                        if result_code == 2:
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but changed the form so much
                            # that a new separation file is needed so reset the separation form
                            # and go back to 3
                            root = etree.fromstring(message)
                            e_sep_file = root.find(".//sepfile")
                            update_form_separation_file(self.request, project_id, form_id, e_sep_file.text)
                            update_form_stage_number(self.request, project_id, form_id, 3)
                            has_tables_to_separate, sep_tables = get_tables_to_separate(self.request, project_id,
                                                                                        form_id)
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
                                            {'variable': aRef.get("variable"), 'option': aRef.get("option")})
                                    list_element["references"] = ref_array
                                    list_array.append(list_element)
                            update_form_stage_number(self.request, project_id, form_id, 4)
                            stage = 4

                        if result_code == 13:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(self.request, project_id, form_id, 5)
                            stage = 5

                        if result_code == 14 or result_code == 15:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(self.request, project_id, form_id, 6)
                            stage = 6
                            error_summary = {'error': message}

                        if result_code == 1:
                            # This is bad!!! So send the form to QLands
                            error_summary = {'error': message}

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

                        result_code, message = create_repository(self.request, project_id, form_id, odk_path,
                                                                 form_data["directory"], primary_key, separation_file,
                                                                 default_language, other_languages, yes_no_strings)

                        # ---------------------------------Stage5 Reply- -----------------------------------------------

                        if result_code != 0:
                            update_form_stage(self.request, project_id, form_id, stage, primary_key, default_language,
                                              other_languages, yes_no_strings, None)
                        if result_code == 10 or result_code == 11:
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
                            update_form_stage_number(self.request, project_id, form_id, 1)

                        if result_code == 3 or result_code == 4 or (6 <= result_code <= 8):
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
                            update_form_stage_number(self.request, project_id, form_id, 2)
                            stage = 2

                        if result_code == 5:
                            error_summary = {'error': message + self._(
                                ". You need to fix the XLSX, upload it again and continue this process.")}

                        if result_code == 2:
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but changed the form so much
                            # that a new separation file is needed so reset the separation form
                            # and go back to 3
                            root = etree.fromstring(message)
                            e_sep_file = root.find(".//sepfile")
                            update_form_separation_file(self.request, project_id, form_id, e_sep_file.text)
                            update_form_stage_number(self.request, project_id, form_id, 3)
                            has_tables_to_separate, sep_tables = get_tables_to_separate(self.request, project_id,
                                                                                        form_id)
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
                                            {'variable': aRef.get("variable"), 'option': aRef.get("option")})
                                    list_element["references"] = ref_array
                                    list_array.append(list_element)
                            update_form_stage_number(self.request, project_id, form_id, 4)
                            stage = 4

                        if result_code == 13:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(self.request, project_id, form_id, 5)
                            stage = 5

                        if result_code == 14 or result_code == 15:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(self.request, project_id, form_id, 6)
                            stage = 6
                            error_summary = {'error': message}

                        if result_code == 1:
                            # This is bad!!! So send the form to QLands
                            error_summary = {'error': message}

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

                        result_code, message = create_repository(self.request, project_id, form_id, odk_path,
                                                                 form_data["directory"], primary_key, separation_file,
                                                                 default_language, other_languages, yes_no_strings)

                        # ----------------------------------------Stage 6 Reply----------------------------

                        if result_code != 0:
                            update_form_stage(self.request, project_id, form_id, stage, primary_key, default_language,
                                              other_languages, yes_no_strings, None)
                        if result_code == 10 or result_code == 11:
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
                            update_form_stage_number(self.request, project_id, form_id, 1)

                        if result_code == 3 or result_code == 4 or (6 <= result_code <= 8):
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
                            update_form_stage_number(self.request, project_id, form_id, 2)
                            stage = 2

                        if result_code == 5:
                            error_summary = {'error': message + self._(
                                ". You need to fix the XLSX, upload it again and continue this process.")}

                        if result_code == 2:
                            # At this stage the information should be ok however,
                            # this would happen if the user exited the process to make
                            # the changes in the options but changed the form so much
                            # that a new separation file is needed so reset the separation form
                            # and go back to 3
                            root = etree.fromstring(message)
                            e_sep_file = root.find(".//sepfile")
                            update_form_separation_file(self.request, project_id, form_id, e_sep_file.text)
                            update_form_stage_number(self.request, project_id, form_id, 3)
                            has_tables_to_separate, sep_tables = get_tables_to_separate(self.request, project_id,
                                                                                        form_id)
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
                                            {'variable': aRef.get("variable"), 'option': aRef.get("option")})
                                    list_element["references"] = ref_array
                                    list_array.append(list_element)
                            update_form_stage_number(self.request, project_id, form_id, 4)
                            stage = 4

                        if result_code == 13:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(self.request, project_id, form_id, 5)
                            stage = 5

                        if result_code == 14 or result_code == 15:
                            # Tell the user it missed a CSV or ZIP file
                            update_form_stage_number(self.request, project_id, form_id, 6)
                            stage = 6
                            error_summary = {'error': message}

                        if result_code == 1:
                            # This is bad!!! So send the form to QLands
                            error_summary = {'error': message}

                if self.request.method == 'GET':
                    if len(languages) == 0 and stage == 2:
                        stage = 1

                if result_code == 0:
                    self.returnRawViewResult = True
                    self.request.session.flash(self._('The repository was created successfully'))
                    return HTTPFound(
                        self.request.route_url('form_details', userid=user_id, projcode=project_code, formid=form_id))
                else:
                    return {'formData': form_data, 'stage': stage, 'error_summary': self.errors,
                            'resCode': result_code, 'primaryKey': primary_key, 'languages': languages,
                            'yesvalue': yesvalue, 'novalue': novalue,
                            'deflanguage': deflanguage, 'otherLanguages': other_languages,
                            'yesNoStrings': yes_no_strings, 'defaultLanguage': default_language,
                            'listArray': list_array, 'sepTables': sep_tables, 'qvars': qvars,
                            'userid': user_id, 'projcode': project_code, 'formid': form_id,
                            'hasTablesToSeparate': has_tables_to_separate, 'get': get,
                            'projectDetails': project_details}
            else:
                return HTTPFound(
                    location=self.request.route_url('exist', userid=user_id, projcode=project_code, formid=form_id))
        else:
            raise HTTPNotFound()


class SeparateTable(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def get_group_count(self, project_id, form_id, table_name, section_id):
        return get_group_number_of_items(self.request, project_id, form_id, table_name, section_id)

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        form_id = self.request.matchdict['formid']
        table_name = self.request.matchdict['tablename']
        form_data = get_form_data(project_id, form_id, self.request)
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound

        if table_belongs_to_form(self.request, project_id, form_id, table_name):
            if self.request.method == 'POST':
                if 'saveorder' in self.request.POST:
                    new_order_str = self.request.POST.get('neworder', '[]')
                    if new_order_str == "":
                        new_order_str = "[]"
                    new_order = json.loads(new_order_str)
                    question_without_group_main = False
                    for item in new_order:
                        if item["type"] == "question":
                            question_without_group_main = True

                    new_order_str_2 = self.request.POST.get('neworder2', '[]')
                    if new_order_str_2 == "":
                        new_order_str_2 = "[]"
                    new_order2 = json.loads(new_order_str_2)
                    question_without_group = False
                    for item in new_order2:
                        if item["type"] == "question":
                            question_without_group = True

                    if not question_without_group and not question_without_group_main:
                        modified, error = save_separation_order(self.request, project_id, form_id, table_name,
                                                                new_order, new_order2)
                        if not modified:
                            self.errors.append(error)
                        else:
                            self.returnRawViewResult = True
                            return HTTPFound(self.request.url)
                    else:
                        self.errors.append(self._("Items cannot be outside a group"))
                else:
                    self.returnRawViewResult = True
                    return HTTPFound(self.request.url)

            data = get_table_items(self.request, project_id, form_id, table_name, True)
            # The following is to help jinja2 to render the groups and questions
            # This because the scope constraint makes it difficult to control
            section_id = -99
            group_index = -1
            for a in range(0, len(data)):
                if data[a]["section_id"] != section_id:
                    group_index = a
                    data[a]["createGRP"] = True
                    data[a]["grpCannotDelete"] = False
                    section_id = data[a]["section_id"]
                    if a == 0:
                        data[a]["closeQst"] = False
                        data[a]["closeGrp"] = False
                    else:
                        if data[a - 1]["hasQuestions"]:
                            data[a]["closeQst"] = True
                            data[a]["closeGrp"] = True
                        else:
                            data[a]["closeGrp"] = False
                            data[a]["closeQst"] = False
                else:
                    data[a]["createGRP"] = False
                    data[a]["closeQst"] = False
                    data[a]["closeGrp"] = False

                if data[a]["item_name"] is not None:
                    data[a]["hasQuestions"] = True
                    data[group_index]["grpCannotDelete"] = True
                else:
                    data[a]["hasQuestions"] = False
            if len(data) > 0:
                final_close_question = data[len(data) - 1]["hasQuestions"]
            else:
                final_close_question = False

            data2 = get_table_items(self.request, project_id, form_id, table_name, False)
            # The following is to help jinja2 to render the groups and questions
            # This because the scope constraint makes it difficult to control
            section_id = -99
            group_index = -1
            for a in range(0, len(data2)):
                if data2[a]["section_id"] != section_id:
                    group_index = a
                    data2[a]["createGRP"] = True
                    data2[a]["grpCannotDelete"] = False
                    section_id = data2[a]["section_id"]
                    if a == 0:
                        data2[a]["closeQst"] = False
                        data2[a]["closeGrp"] = False
                    else:
                        if data2[a - 1]["hasQuestions"]:
                            data2[a]["closeQst"] = True
                            data2[a]["closeGrp"] = True
                        else:
                            data2[a]["closeGrp"] = False
                            data2[a]["closeQst"] = False
                else:
                    data2[a]["createGRP"] = False
                    data2[a]["closeQst"] = False
                    data2[a]["closeGrp"] = False

                if data2[a]["item_name"] is not None:
                    data2[a]["hasQuestions"] = True
                    data2[group_index]["grpCannotDelete"] = True
                else:
                    data2[a]["hasQuestions"] = False
            if len(data2) > 0:
                final_close_question2 = data2[len(data2) - 1]["hasQuestions"]
            else:
                final_close_question2 = False

            separation_ok = is_separation_ok(self.request, project_id, form_id, table_name)
            qvars = {'formid': form_id}
            return {'data': data, 'data2': data2, 'finalCloseQst': final_close_question,
                    'projectID': project_id,
                    'tableName': table_name,
                    'getGroupCount': self.get_group_count,
                    'finalCloseQst2': final_close_question2, 'qvars': qvars,
                    'userid': user_id, 'projcode': project_code, 'formid': form_id, 'separationOK': separation_ok,
                    'formData': form_data, 'projectDetails': project_details}
        else:
            raise HTTPNotFound()


def check_table_name(table_name):
    res = True
    if table_name.lower() == 'table':
        res = False
    if table_name.lower() == 'group':
        res = False
    if table_name.lower() == 'select':
        res = False
    if table_name.lower() == 'from':
        res = False
    if table_name.lower() == 'where':
        res = False
    if table_name.lower() == 'on':
        res = False
    if table_name.lower() == 'and':
        res = False
    if table_name.lower() == 'or':
        res = False
    if table_name.lower() == 'by':
        res = False
    if table_name.lower() == 'not':
        res = False
    if table_name.lower() == 'order':
        res = False
    if table_name.lower() == 'procedure':
        res = False
    if table_name.lower() == 'update':
        res = False
    if table_name.lower() == 'delete':
        res = False
    if table_name.lower() == 'set':
        res = False
    if table_name.lower() == 'commit':
        res = False
    if table_name.lower() == 'trigger':
        res = False
    if table_name.lower() == 'rollback':
        res = False
    if table_name.lower() == 'insert':
        res = False
    if table_name.lower() == 'integer':
        res = False
    if table_name.lower() == 'varchar':
        res = False
    return res


class NewGroup(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        table_name = self.request.matchdict['tablename']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        project_details = {}
        form_data = get_form_data(project_id, form_id, self.request)
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound

        if table_belongs_to_form(self.request, project_id, form_id, table_name):
            if self.request.method == 'POST':
                post_data = self.get_post_dict()
                group_name = post_data["name"].lower()
                group_name = group_name.replace(' ', '')
                group_desc = post_data["desc"]
                if group_name != "" and group_desc != "":
                    if re.match(r'^[A-Za-z0-9_]+$', group_name):
                        if group_name[0].isdigit():
                            self.errors.append(self._("The name cannot start with a number"))
                        else:
                            if check_table_name(group_name):
                                added, message = add_group(self.request, project_id, form_id, table_name, group_name,
                                                           group_desc)
                                qvars = {'formid': form_id}
                                if added:
                                    self.returnRawViewResult = True
                                    return HTTPFound(location=self.request.route_url('separatetable', userid=user_id,
                                                                                     projcode=project_code, formid=form_id,
                                                                                     tablename=table_name, _query=qvars))
                                else:
                                    self.errors.append(message)
                            else:
                                self.errors.append(self._("Such name is not valid"))
                    else:
                        self.errors.append(self._("The group name has invalid characters. Only underscore is allowed"))
                else:
                    self.errors.append(self._("The group name and description cannot be empty"))
            qvars = {'formid': form_id}
            return {'table_name': table_name, 'userid': user_id, 'projcode': project_code, 'formid': form_id,
                    'qvars': qvars, 'formData': form_data, 'projectDetails': project_details}
        else:
            raise HTTPNotFound()


class EditGroup(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        table_name = self.request.matchdict['tablename']
        group_id = self.request.matchdict['groupid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        project_details = {}
        form_data = get_form_data(project_id, form_id, self.request)
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound

        if table_belongs_to_form(self.request, project_id, form_id, table_name):
            group_name = get_group_name_from_id(self.request, project_id, form_id, table_name, group_id)
            if group_name is not None:
                if self.request.method == 'POST':
                    post_data = self.get_post_dict()
                    group_desc = post_data["desc"]
                    if group_desc != "":
                        updated, message = set_group_desc(self.request, project_id, form_id, table_name, group_id,
                                                          group_desc)
                        qvars = {'formid': form_id}
                        if updated:
                            self.returnRawViewResult = True
                            return HTTPFound(
                                location=self.request.route_url('separatetable', userid=user_id, projcode=project_code,
                                                                formid=form_id, tablename=table_name, _query=qvars))
                        else:
                            self.errors.append(message)
                    else:
                        self.errors.append(self._("The group description cannot be empty"))
                qvars = {'formid': form_id}
                return {'tableName': table_name, 'userid': user_id, 'projcode': project_code, 'formid': form_id,
                        'qvars': qvars, 'groupName': group_name, 'formData': form_data, 'projectDetails': project_details}
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()


class DeleteGroup(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        table_name = self.request.matchdict['tablename']
        group_id = self.request.matchdict['groupid']
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound

        if table_belongs_to_form(self.request, project_id, form_id, table_name):
            group_name = get_group_name_from_id(self.request, project_id, form_id, table_name, group_id)
            if group_name is not None:
                if get_group_number_of_items(self.request, project_id, form_id, table_name, group_id) == 0:
                    if self.request.method == 'POST':
                        deleted, message = delete_group(self.request, project_id, form_id, table_name, group_id)
                        qvars = {'formid': form_id}
                        if deleted:
                            self.returnRawViewResult = True
                            return HTTPFound(
                                location=self.request.route_url('separatetable', userid=user_id, projcode=project_code,
                                                                formid=form_id, tablename=table_name, _query=qvars))
                    else:
                        raise HTTPNotFound()
                else:
                    raise HTTPNotFound()
            else:
                raise HTTPNotFound()
        else:
            raise HTTPNotFound()


class RepositoryExist(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        return {'userid': user_id, 'projcode': project_code, 'formid': form_id}
