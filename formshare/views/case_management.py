"""The published-lists registry UI: publish, edit and retire real-time lists.

Stage 1 of native case management (docs/formshare_case_management/
formshare.md section 4.1). The wizard is deliberately two steps -- create the
list, then manage its served columns on the edit page -- mirroring how the
case fields screen already works, so the owner meets one interaction pattern,
not two.

Only sources from this project are offered here; cross-project sourcing
arrives with the dependency guards of stage 4, because offering it without
the guards would let a source be deleted out from under its consumers.
"""

import os
import uuid

from formshare.middleware.httpexceptions import HTTPFound, HTTPNotFound
from formshare.middleware.response import FileResponse
from formshare.processes.db.case_management import (
    add_published_list,
    build_list_select,
    delete_published_list,
    get_case_link_consumer,
    get_form_consumers,
    get_form_data_tables,
    get_list_columns,
    get_list_source_schema,
    get_project_published_lists,
    get_published_list,
    get_table_columns,
    set_case_link,
    set_list_columns,
    sync_form_consumers,
    update_published_list,
    valid_list_filename,
    write_list_csv,
)
from formshare.processes.db.form import get_form_data, get_form_directory
from formshare.processes.odk.api import (
    get_fields_from_table_in_file,
    get_odk_path,
)
from formshare.processes.db.form import get_project_forms
from formshare.processes.db.project import (
    get_project_access_type,
    get_project_details,
    get_project_id_from_name,
)
from formshare.views.classes import PrivateView


class ListSection(PrivateView):
    """Shared access control: the section belongs to owners and editors."""

    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def project_or_404(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject.get("project_id", None) == project_id:
            self.set_active_menu("assistants")
        else:
            self.set_active_menu("projects")
        if project_id is None:
            raise HTTPNotFound
        access_type = get_project_access_type(
            self.request, project_id, user_id, self.user.login
        )
        if access_type >= 4:
            # Members can see the project; only owners and editors shape what
            # its devices receive.
            raise HTTPNotFound
        project_details = get_project_details(self.request, project_id)
        project_details["access_type"] = access_type
        return user_id, project_code, project_id, project_details


class PublishedListsView(ListSection):
    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "lists": get_project_published_lists(self.request, project_id),
        }


class AddPublishedListView(ListSection):
    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        forms = get_project_forms(self.request, user_id, project_id)
        # Only a form with a repository has tables to publish from.
        forms = [a_form for a_form in forms if a_form.get("form_schema")]
        list_data = {}
        if self.request.method == "POST":
            list_data = self.get_post_dict()
            list_id = str(list_data.get("list_id", "") or "").strip().lower()
            file_name = str(list_data.get("list_filename", "") or "").strip()
            source_form = list_data.get("source_form", "")
            source_table = list_data.get("source_table", "")
            label_column = list_data.get("label_column", "")
            # add, tablesof and fieldsof are path segments under /caselists;
            # a list with one of those ids would shadow them.
            if list_id in ("add", "tablesof", "fieldsof"):
                list_id = ""
            if list_id == "" or not valid_list_filename(file_name):
                self.append_to_errors(
                    self._(
                        "The file name must be lower case, start with a letter, "
                        "and end in .csv"
                    )
                )
            elif source_form == "" or source_table == "" or label_column == "":
                self.append_to_errors(
                    self._("Select the form, the table and the label column")
                )
            else:
                list_active = 0 if list_data.get("list_active") == "0" else 1
                added, message = add_published_list(
                    self.request,
                    project_id,
                    {
                        "list_id": list_id,
                        "list_filename": file_name,
                        "list_format": "csv",
                        "source_project": project_id,
                        "source_form": source_form,
                        "source_table": source_table,
                        "label_column": label_column,
                        "list_active": list_active,
                    },
                )
                if added:
                    self.request.session.flash(
                        self._("The list was created. Now choose its columns.")
                    )
                    self.returnRawViewResult = True
                    return HTTPFound(
                        location=self.request.route_url(
                            "project_case_list_edit",
                            userid=user_id,
                            projcode=project_code,
                            listid=list_id,
                        )
                    )
                self.append_to_errors(message)
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "forms": forms,
            "listData": list_data,
        }


class EditPublishedListView(ListSection):
    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        list_id = self.request.matchdict["listid"]
        list_data = get_published_list(self.request, project_id, list_id)
        if list_data is None:
            raise HTTPNotFound
        table_columns = get_table_columns(
            self.request,
            list_data["source_project"],
            list_data["source_form"],
            list_data["source_table"],
        )
        if self.request.method == "POST":
            post_data = self.get_post_dict()
            if "add_column" in post_data.keys():
                column_name = post_data.get("column_name", "")
                column_as = str(post_data.get("column_as", "") or "").strip()
                current = [
                    (a_column["column_name"], a_column["column_as"], "table")
                    for a_column in get_list_columns(self.request, project_id, list_id)
                ]
                current.append((column_name, column_as or None, "table"))
                updated, message = set_list_columns(
                    self.request, project_id, list_id, current
                )
                if not updated:
                    self.append_to_errors(message)
                else:
                    self.returnRawViewResult = True
                    return HTTPFound(self.request.url)
            if "remove_column" in post_data.keys():
                column_name = post_data.get("column_name", "")
                current = [
                    (a_column["column_name"], a_column["column_as"], "table")
                    for a_column in get_list_columns(self.request, project_id, list_id)
                    if a_column["column_name"] != column_name
                ]
                updated, message = set_list_columns(
                    self.request, project_id, list_id, current
                )
                if not updated:
                    self.append_to_errors(message)
                else:
                    self.returnRawViewResult = True
                    return HTTPFound(self.request.url)
            if "change_active" in post_data.keys():
                list_active = 0 if post_data.get("list_active") == "0" else 1
                updated, message = update_published_list(
                    self.request,
                    project_id,
                    list_id,
                    {"list_active": list_active},
                )
                if not updated:
                    self.append_to_errors(message)
                else:
                    self.returnRawViewResult = True
                    return HTTPFound(self.request.url)
            if "change_label" in post_data.keys():
                label_column = post_data.get("label_column", "")
                if label_column != "":
                    updated, message = update_published_list(
                        self.request,
                        project_id,
                        list_id,
                        {"label_column": label_column},
                    )
                    if not updated:
                        self.append_to_errors(message)
                    else:
                        self.returnRawViewResult = True
                        return HTTPFound(self.request.url)
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "listData": list_data,
            "listColumns": get_list_columns(self.request, project_id, list_id),
            "tableColumns": table_columns,
        }


class DeletePublishedListView(ListSection):
    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        if self.request.method != "POST":
            raise HTTPNotFound
        list_id = self.request.matchdict["listid"]
        list_data = get_published_list(self.request, project_id, list_id)
        if list_data is None:
            raise HTTPNotFound
        self.returnRawViewResult = True
        deleted, message = delete_published_list(self.request, project_id, list_id)
        next_page = self.request.route_url(
            "project_case_lists", userid=user_id, projcode=project_code
        )
        if deleted:
            self.request.session.flash(self._("The list was deleted"))
            return HTTPFound(location=next_page)
        self.append_to_errors(message)
        return HTTPFound(location=next_page, headers={"FS_error": "true"})


class FormTablesApiView(ListSection):
    """The tables of a form, as JSON, for the wizard's cascading combo."""

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        form_id = self.request.matchdict["formid"]
        self.returnRawViewResult = True
        return {
            "tables": [
                {
                    "table_name": a_table["table_name"],
                    "table_desc": a_table["table_desc"],
                }
                for a_table in get_form_data_tables(self.request, project_id, form_id)
            ]
        }


class TableFieldsApiView(ListSection):
    """The columns of a table, as JSON, for the label and column combos."""

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        form_id = self.request.matchdict["formid"]
        table_name = self.request.matchdict["tablename"]
        self.returnRawViewResult = True
        return {
            "fields": [
                a_field["field_name"]
                for a_field in get_table_columns(
                    self.request, project_id, form_id, table_name
                )
            ]
        }


class SampleListView(ListSection):
    """A ten-row sample of a published list, to design forms against."""

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        list_id = self.request.matchdict["listid"]
        list_data = get_published_list(self.request, project_id, list_id)
        if list_data is None:
            raise HTTPNotFound
        self.returnRawViewResult = True
        next_page = self.request.route_url(
            "project_case_lists", userid=user_id, projcode=project_code
        )
        schema = get_list_source_schema(self.request, list_data)
        if schema is None or schema == "":
            self.add_error(
                self._(
                    "The source form has no repository yet, so there is no data to sample"
                )
            )
            return HTTPFound(location=next_page, headers={"FS_error": "true"})
        columns = [
            (a_column["column_name"], a_column["column_as"])
            for a_column in get_list_columns(self.request, project_id, list_id)
        ]
        try:
            sql, headers = build_list_select(
                schema,
                list_data["source_table"],
                list_data["label_column"],
                columns,
                list_data.get("filter_sql"),
                limit=10,
                active=list_data.get("list_active", 1),
            )
            rows = self.request.dbsession.execute(sql).fetchall()
        except Exception as e:
            self.add_error(str(e))
            return HTTPFound(location=next_page, headers={"FS_error": "true"})
        repository_path = self.request.registry.settings["repository.path"]
        temp_dir = os.path.join(repository_path, *["tmp"])
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        csv_file = os.path.join(temp_dir, str(uuid.uuid4()) + ".csv")
        write_list_csv(headers, rows, csv_file)
        response = FileResponse(
            csv_file, request=self.request, content_type="text/csv", cache_max_age=0
        )
        response.content_disposition = 'attachment; filename="{}"'.format(
            list_data["list_filename"]
        )
        return response


class CaseLinksView(ListSection):
    """Which published list a follow-up form links its rows to.

    A form can consume several lists (a cascade: pick a school, then a staff
    member of it). Exactly one is the *case link* -- the list whose rows the
    form is about -- and it is that link which becomes a foreign key and a
    membership trigger when the repository is built. The others are read-only
    references. Open this before building the repository.
    """

    def _create_xml(self, project_id, form_id):
        directory = get_form_directory(self.request, project_id, form_id)
        if directory is None:
            return None
        create_xml = os.path.join(
            get_odk_path(self.request),
            *["forms", directory, "repository", "create.xml"]
        )
        if not os.path.exists(create_xml):
            return None
        return create_xml

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        form_id = self.request.matchdict["formid"]
        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound
        # Reconcile the stored consumers with what the form references now, so
        # the page reflects the uploaded form even if it changed.
        create_xml = self._create_xml(project_id, form_id)
        if create_xml is not None:
            sync_form_consumers(
                self.request,
                project_id,
                form_id,
                get_fields_from_table_in_file(create_xml, "maintable"),
            )
        if self.request.method == "POST":
            post_data = self.get_post_dict()
            if "case_link" in post_data.keys():
                list_id = post_data.get("list_id", "")
                if list_id != "":
                    changed, message = set_case_link(
                        self.request, project_id, form_id, list_id
                    )
                    if not changed:
                        self.append_to_errors(message)
                    else:
                        self.returnRawViewResult = True
                        return HTTPFound(self.request.url)
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "formData": form_data,
            "consumers": get_form_consumers(self.request, project_id, form_id),
            "caseLink": get_case_link_consumer(self.request, project_id, form_id),
            "hasCreateXml": create_xml is not None,
        }
