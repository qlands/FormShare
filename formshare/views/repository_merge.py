import logging
import os

from lxml import etree
from pyramid.httpexceptions import HTTPNotFound, HTTPFound

from formshare.processes.db import get_project_id_from_name, update_form
from formshare.processes.email.send_email import send_error_to_technical_team
from formshare.processes.odk.api import get_odk_path, merge_versions
from formshare.processes.odk.processes import get_form_data
from formshare.products.merge import merge_form
from formshare.views.classes import PrivateView

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

        new_form_data = get_form_data(project_id, new_form_id, self.request)
        old_form_data = get_form_data(project_id, old_form_id, self.request)

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

            old_create_file = old_form_data["form_createxmlfile"]
            old_insert_file = old_form_data["form_insertxmlfile"]

            new_create_file = os.path.join(
                odk_path,
                *["forms", new_form_data["directory"], "repository", "create.xml"]
            )
            new_insert_file = os.path.join(
                odk_path,
                *["forms", new_form_data["directory"], "repository", "insert.xml"]
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
                )

                form_data = {"form_mergetask": task_id}
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
                                values_to_ignore.append(table_name + ":" + value_code)
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
        }
