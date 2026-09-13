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

from formshare.middleware.httpexceptions import HTTPFound, HTTPNotFound
from formshare.processes.db.case_management import (
    add_published_list,
    delete_published_list,
    get_form_data_tables,
    get_list_columns,
    get_project_published_lists,
    get_published_list,
    get_table_columns,
    set_list_columns,
    update_published_list,
    valid_list_filename,
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
