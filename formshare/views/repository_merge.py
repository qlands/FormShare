import logging
import os
import uuid
import shutil
from formshare.processes.db import (
    get_project_id_from_name,
    update_form,
    get_project_access_type,
    get_project_details,
    get_one_assistant,
    get_case_form,
    get_field_details,
)
from formshare.processes.email.send_email import send_error_to_technical_team
from formshare.processes.odk.api import get_odk_path, merge_versions, create_repository
from formshare.processes.odk.processes import get_form_data
from formshare.products.merge import merge_form
from formshare.views.classes import PrivateView
from lxml import etree
from pyramid.httpexceptions import HTTPNotFound, HTTPFound

log = logging.getLogger("formshare")


class RepositoryMergeForm(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        new_form_id = self.request.matchdict["formid"]
        old_form_id = self.request.matchdict["oldformid"]

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
        project, assistant = get_one_assistant(self.request, project_id, new_form_id)
        if project is None:
            has_submit_assistant = False

        new_form_data = get_form_data(project_id, new_form_id, self.request)
        old_form_data = get_form_data(project_id, old_form_id, self.request)

        if old_form_data["form_surveycolumns"] is not None:
            old_survey_columns = old_form_data["form_surveycolumns"]
        else:
            old_survey_columns = []

        if old_form_data["form_choicescolumns"] is not None:
            old_choices_columns = old_form_data["form_choicescolumns"]
        else:
            old_choices_columns = []

        if new_form_data["form_surveycolumns"] is not None:
            new_survey_columns = new_form_data["form_surveycolumns"]
        else:
            new_survey_columns = []

        if new_form_data["form_choicescolumns"] is not None:
            new_choices_columns = new_form_data["form_choicescolumns"]
        else:
            new_choices_columns = []

        survey_columns = []
        for a_column in new_survey_columns:
            found = False
            if a_column in old_survey_columns:
                found = True
            if not found:
                survey_columns.append(a_column)

        choices_columns = []
        for a_column in new_choices_columns:
            found = False
            if a_column in old_choices_columns:
                found = True
            if not found:
                choices_columns.append(a_column)

        if new_form_data["form_abletomerge"] == 1:
            if old_form_data["schema"] is not None:
                if new_form_data["parent_form"] != old_form_id:
                    raise HTTPNotFound
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        errors = []
        error_type = 0
        values_to_ignore = []
        s_values_to_ignore = None
        discard_testing_data = False
        if self.request.method == "POST":
            odk_path = get_odk_path(self.request)
            post_data = self.get_post_dict()
            if "discard_testing_data" in post_data.keys():
                discard_testing_data = True
            if "valuestoignore" in post_data.keys():
                s_values_to_ignore = post_data["valuestoignore"]

            survey_data_columns = []
            if "survey_data_columns" in post_data.keys():
                if "survey_data_columns" in post_data.keys():
                    if isinstance(post_data["survey_data_columns"], list):
                        survey_data_columns = post_data["survey_data_columns"]
                    else:
                        survey_data_columns = post_data["survey_data_columns"].split(
                            "|"
                        )

            choices_data_columns = []
            if "choices_data_columns" in post_data.keys():
                if "choices_data_columns" in post_data.keys():
                    if isinstance(post_data["choices_data_columns"], list):
                        choices_data_columns = post_data["choices_data_columns"]
                    else:
                        choices_data_columns = post_data["choices_data_columns"].split(
                            "|"
                        )

            survey_data_columns = old_survey_columns + survey_data_columns
            choices_data_columns = old_choices_columns + choices_data_columns

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

            old_create_file = old_form_data["form_createxmlfile"]
            old_insert_file = old_form_data["form_insertxmlfile"]

            if new_form_data["form_mergelngerror"] != 2:
                def_language_to_use = old_form_data["form_deflang"]
                other_languages_to_use = old_form_data["form_othlangs"]
            else:
                def_language_to_use = new_form_data["form_deflang"]
                other_languages_to_use = new_form_data["form_othlangs"]

            created, message = create_repository(
                self.request,
                user_id,
                project_id,
                new_form_id,
                odk_path,
                new_form_data["directory"],
                old_form_data["form_pkey"],
                False,
                "|".join(survey_data_columns),
                "|".join(choices_data_columns),
                def_language_to_use,
                other_languages_to_use,
                True,
            )
            if created == 0:
                # If it is a case form and its follow up, activate or deactivate then
                # we modify the create XML file to:
                # - Link the form_caseselector of the form with the form_pkey of the creator form.
                # This will allow a proper merge between Forms
                new_create_file = os.path.join(
                    odk_path,
                    *["forms", new_form_data["directory"], "repository", "create.xml"]
                )
                new_insert_file = os.path.join(
                    odk_path,
                    *["forms", new_form_data["directory"], "repository", "insert.xml"]
                )
                if (
                    new_form_data["form_case"] == 1
                    and new_form_data["form_casetype"] > 1
                ):
                    form_creator = get_case_form(self.request, project_id)
                    form_creator_data = get_form_data(
                        project_id, form_creator, self.request
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
                            ".//field[@name='"
                            + new_form_data["form_caseselector"]
                            + "']"
                        )
                        if field is not None:
                            field.set("type", creator_pkey_data["field_type"])
                            field.set("size", str(creator_pkey_data["field_size"]))
                            field.set(
                                "rtable",
                                form_creator_data["schema"] + ".maintable",
                            )
                            field.set("rfield", form_creator_data["form_pkey"])
                            field.set(
                                "rname", "fk_" + str(uuid.uuid4()).replace("-", "_")
                            )
                            field.set("rlookup", "false")
                            # Save the changes in the XML Create file
                            if not os.path.exists(new_create_file + ".case.bk"):
                                shutil.copy(
                                    new_create_file, new_create_file + ".case.bk"
                                )
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
                                    new_form_data["form_caseselector"], new_create_file
                                )
                            )
                            return (
                                1,
                                "The case selector field {} was not found in the ODK form".format(
                                    new_form_data["form_caseselector"]
                                ),
                            )
                    else:  # pragma: no cover
                        #  This might not be possible to happen. Left here just in case
                        log.error(
                            "Main table was not found in {}".format(new_create_file)
                        )
                        return (
                            1,
                            "Main table was not found in {}".format(new_create_file),
                        )

                merged, output = merge_versions(
                    self.request,
                    odk_path,
                    new_form_data["directory"],
                    new_create_file,
                    new_insert_file,
                    old_create_file,
                    old_insert_file,
                    "|".join(survey_data_columns),
                    s_values_to_ignore,
                )
                if merged == 0:

                    task_id = merge_form(
                        self.request,
                        project_details["owner"],
                        project_id,
                        new_form_id,
                        new_form_data["directory"],
                        old_form_data["schema"],
                        old_form_data["directory"],
                        output,
                        old_form_data["form_hexcolor"],
                        discard_testing_data,
                        survey_data_columns,
                    )

                    form_data = {
                        "form_mergetask": task_id,
                        "form_surveycolumns": "|".join(survey_data_columns),
                        "form_choicescolumns": "|".join(choices_data_columns),
                    }
                    update_form(self.request, project_id, new_form_id, form_data)

                    next_page = self.request.route_url(
                        "form_details",
                        userid=project_details["owner"],
                        projcode=project_code,
                        formid=new_form_id,
                    )
                    self.request.session.flash(self._("FormShare is merging the form."))
                    self.returnRawViewResult = True
                    return HTTPFound(next_page)
                else:
                    try:
                        root = etree.fromstring(output)
                        xml_errors = root.findall(".//error")
                        if xml_errors:
                            for a_error in xml_errors:
                                error_code = a_error.get("code")
                                if error_code == "TNS":  # pragma: no cover
                                    # At this stage TNS might not be possible because is
                                    # Checked elsewhere before
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
                                if error_code == "TWP":  # pragma: no cover
                                    #  We leave it here just in case.. TWP might not be possible.
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
                                if error_code == "FNS":  # pragma: no cover
                                    # At this stage TNS might not be possible because is
                                    # Checked elsewhere before
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
                                if error_code == "RNS":  # pragma: no cover
                                    # At this stage TNS might not be possible because is
                                    # Checked elsewhere before
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
                                new_form_id, old_form_id, project_id, user_id, str(e)
                            ),
                        )
                        self.add_error(
                            self._(
                                "Unknown error while merging. A message has been sent to the support team and "
                                "they will contact you ASAP."
                            )
                        )

                        self.returnRawViewResult = True
                        return HTTPFound(self.request.url, headers={"FS_error": "true"})
            else:
                self.add_error(
                    self._(
                        "Unknown error while merging. A message has been sent to the support team and "
                        "they will contact you ASAP."
                    )
                )
                self.returnRawViewResult = True
                return HTTPFound(self.request.url, headers={"FS_error": "true"})

        return {
            "userid": user_id,
            "formData": new_form_data,
            "oldformData": old_form_data,
            "projectDetails": project_details,
            "projcode": project_code,
            "formid": new_form_id,
            "merge_errors": errors,
            "errortype": error_type,
            "valuestoignore": ";".join(values_to_ignore),
            "has_submit_assistant": has_submit_assistant,
            "survey_columns": survey_columns,
            "choices_columns": choices_columns,
        }
