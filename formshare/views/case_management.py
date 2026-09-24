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

import datetime
import json
import os
import re
import uuid

from sqlalchemy import text

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
    invalidate_list_copies,
    sync_form_consumers,
    update_published_list,
    valid_list_filename,
    write_list_csv,
    list_has_active_consumers,
    get_project_workflow,
    get_table_properties,
    get_list_source_tables,
    PROPERTY_TYPES,
    add_table_property,
    delete_table_property,
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
from formshare.plugins.helpers import feature_exists
from formshare.processes.actions.compiler import (
    CompileError,
    compile_module,
    describe_when,
)
from formshare.processes.actions.server import (
    get_form_runs,
    retry_run,
    run_for_submission,
)
from formshare.processes.db.actions import (
    add_form_action,
    build_catalogue,
    catalogue_for_querybuilder,
    delete_form_action,
    get_action_mode,
    get_action_module,
    get_form_actions,
    move_form_action,
    set_action_mode,
    set_expert_module,
    update_form_action,
)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ListSection(PrivateView):
    """Shared access control: the section belongs to owners and editors."""

    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def project_or_404(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if not feature_exists("workflows"):
            raise HTTPNotFound

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
        if project_details["project_case"] == 1:
            raise HTTPNotFound
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
                key_column = (
                    str(list_data.get("list_key_column", "") or "").strip() or None
                )
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
                        "list_key_column": key_column,
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
        # Every definition change below marks the served copies stale
        # (invalidate_list_copies): the devices get the new shape on their
        # next pull, not when the source next receives data.
        if self.request.method == "POST":
            post_data = self.get_post_dict()
            if "add_column" in post_data.keys():
                column_name = post_data.get("column_name", "")
                column_as = str(post_data.get("column_as", "") or "").strip()
                # A property is offered as "property:<name>": it is served
                # from <table>_properties rather than from the table.
                column_source = "table"
                if column_name.startswith("property:"):
                    column_name = column_name[len("property:") :]
                    column_source = "property"
                current = [
                    (
                        a_column["column_name"],
                        a_column["column_as"],
                        a_column["column_source"],
                    )
                    for a_column in get_list_columns(self.request, project_id, list_id)
                ]
                current.append((column_name, column_as or None, column_source))
                updated, message = set_list_columns(
                    self.request, project_id, list_id, current
                )
                if not updated:
                    self.append_to_errors(message)
                else:
                    invalidate_list_copies(self.request, project_id, list_id)
                    self.returnRawViewResult = True
                    return HTTPFound(self.request.url)
            if "remove_column" in post_data.keys():
                column_name = post_data.get("column_name", "")
                current = [
                    (
                        a_column["column_name"],
                        a_column["column_as"],
                        a_column["column_source"],
                    )
                    for a_column in get_list_columns(self.request, project_id, list_id)
                    if a_column["column_name"] != column_name
                ]
                updated, message = set_list_columns(
                    self.request, project_id, list_id, current
                )
                if not updated:
                    self.append_to_errors(message)
                else:
                    invalidate_list_copies(self.request, project_id, list_id)
                    self.returnRawViewResult = True
                    return HTTPFound(self.request.url)
            if "change_key" in post_data.keys():
                key_column = (
                    str(post_data.get("list_key_column", "") or "").strip() or None
                )
                # A built consumer's foreign key (or lack of one) was shaped by
                # the key; switching a row list to a value list under it, or
                # back, would leave the schema disagreeing with the list.
                if list_has_active_consumers(self.request, project_id, list_id):
                    self.append_to_errors(
                        self._(
                            "The key cannot change while a form with a repository "
                            "uses this list"
                        )
                    )
                else:
                    updated, message = update_published_list(
                        self.request,
                        project_id,
                        list_id,
                        {"list_key_column": key_column},
                    )
                    if not updated:
                        self.append_to_errors(message)
                    else:
                        invalidate_list_copies(self.request, project_id, list_id)
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
                    invalidate_list_copies(self.request, project_id, list_id)
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
                        invalidate_list_copies(self.request, project_id, list_id)
                        self.returnRawViewResult = True
                        return HTTPFound(self.request.url)
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "listData": list_data,
            "listColumns": get_list_columns(self.request, project_id, list_id),
            "tableColumns": table_columns,
            "tableProperties": get_table_properties(
                self.request,
                list_data["source_project"],
                list_data["source_form"],
                list_data["source_table"],
            ),
        }


class DeletePublishedListView(ListSection):
    def __init__(self, request):
        ListSection.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        if self.request.method != "POST":
            raise HTTPNotFound
        list_id = self.request.matchdict["listid"]
        list_data = get_published_list(self.request, project_id, list_id)
        if list_data is None:
            raise HTTPNotFound
        if list_has_active_consumers(self.request, project_id, list_id):
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
            (
                a_column["column_name"],
                a_column["column_as"],
                a_column.get("column_source") or "table",
            )
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
                key_column=list_data.get("list_key_column"),
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
        # The links are fixed once the schema depends on them: a form with a
        # repository has its foreign keys and trigger already, and a new
        # version being merged keeps the links of the version it replaces.
        links_locked = bool(form_data.get("form_schema")) or bool(
            form_data.get("parent_form")
        )
        if form_data.get("parent_form"):
            lock_reason = self._(
                "This is a new version of {}: it keeps that version's links, "
                "and a merge cannot change them."
            ).format(form_data["parent_form"])
        elif links_locked:
            lock_reason = self._(
                "This form has a repository: its links are built into the schema."
            )
        else:
            lock_reason = ""
        if self.request.method == "POST":
            post_data = self.get_post_dict()
            if "case_link" in post_data.keys():
                list_id = post_data.get("list_id", "")
                if links_locked:
                    self.append_to_errors(lock_reason)
                elif list_id != "":
                    changed, message = set_case_link(
                        self.request, project_id, form_id, list_id
                    )
                    if not changed:
                        self.append_to_errors(message)
                    else:
                        self.returnRawViewResult = True
                        return HTTPFound(self.request.url)
        consumers = get_form_consumers(self.request, project_id, form_id)
        for a_consumer in consumers:
            a_list = get_published_list(
                self.request, a_consumer["list_project"], a_consumer["list_id"]
            )
            # A value list (distinct districts) has no row identity and cannot
            # be the case link; the page offers no radio for it.
            a_consumer["is_value_list"] = bool(a_list and a_list.get("list_key_column"))
            # The file name is what the form's select_one_from_file names and
            # what the owner recognises; the code is only the registry's key.
            a_consumer["list_filename"] = (
                a_list["list_filename"] if a_list else a_consumer["list_id"]
            )
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "formData": form_data,
            "consumers": consumers,
            "caseLink": get_case_link_consumer(self.request, project_id, form_id),
            "hasCreateXml": create_xml is not None,
            "linksLocked": links_locked,
            "lockReason": lock_reason,
        }


class WorkflowDiagramView(ListSection):
    """The longitudinal workflow of the project, drawn from the registry and
    the built schemas (docs/formshare_case_management/formshare.md 3.9)."""

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "workflow": get_project_workflow(
                self.request,
                project_id,
                {"code": project_code, "name": project_details["project_name"]},
            ),
        }


class WorkflowModelApiView(ListSection):
    """The same model as JSON, for anything else that wants to draw it."""

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        self.returnRawViewResult = True
        return get_project_workflow(
            self.request,
            project_id,
            {"code": project_code, "name": project_details["project_name"]},
        )


class PropertiesView(ListSection):
    """Properties of a source table (feature 2): defined here, fed at
    creation from a variable of the table, served by any list of it."""

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        # Only the tables a published list draws from can carry properties:
        # a property is what a follow-up sets on a case it selected from a
        # list, so a table no list serves has nothing to gain from one.
        sources = get_list_source_tables(self.request, project_id)
        forms = [
            a_form
            for a_form in get_project_forms(self.request, user_id, project_id)
            if a_form.get("form_schema") and a_form["form_id"] in sources
        ]
        form_id = self.request.params.get("form", "")
        table_name = self.request.params.get("table", "")
        if form_id and form_id not in [a_form["form_id"] for a_form in forms]:
            raise HTTPNotFound
        tables = (
            [
                a_table
                for a_table in get_form_data_tables(self.request, project_id, form_id)
                if a_table["table_name"] in sources[form_id]
            ]
            if form_id
            else []
        )
        if table_name and table_name not in [t["table_name"] for t in tables]:
            raise HTTPNotFound
        here = self.request.route_url(
            "project_case_properties",
            userid=user_id,
            projcode=project_code,
            _query={"form": form_id, "table": table_name},
        )
        if self.request.method == "POST" and form_id and table_name:
            post_data = self.get_post_dict()
            if "add_property" in post_data.keys():
                added, message = add_table_property(
                    self.request,
                    project_id,
                    form_id,
                    table_name,
                    post_data.get("property_name", ""),
                    post_data.get("property_type", ""),
                    post_data.get("property_default", ""),
                    str(post_data.get("property_desc", "") or "").strip(),
                    self.user.login,
                )
                if added:
                    self.returnRawViewResult = True
                    return HTTPFound(location=here)
                self.add_error(message)
                self.returnRawViewResult = True
                return HTTPFound(location=here, headers={"FS_error": "true"})
            if "delete_property" in post_data.keys():
                deleted, message = delete_table_property(
                    self.request,
                    project_id,
                    form_id,
                    table_name,
                    post_data.get("property_name", ""),
                )
                if deleted:
                    self.returnRawViewResult = True
                    return HTTPFound(location=here)
                self.add_error(message)
                self.returnRawViewResult = True
                return HTTPFound(location=here, headers={"FS_error": "true"})
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "forms": forms,
            "formId": form_id,
            "tableName": table_name,
            "tables": tables,
            "propertyTypes": [(code, label) for code, label, _ in PROPERTY_TYPES],
            # For reference beside the default box: what the server calls now.
            "serverTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "properties": (
                get_table_properties(self.request, project_id, form_id, table_name)
                if form_id and table_name
                else []
            ),
        }


class ActionsView(ListSection):
    """Form → Case actions (feature 3, decision 16): the decision table in
    table mode, the module editor in expert mode, the preview, the test with
    a submission and the run log. The module the server runs is what this
    page last saved; actions.json serves the same text."""

    def _submissions(self, form_data, limit=50):
        """The most recent rows of the form, to dry-run against."""
        schema = form_data.get("form_schema")
        if not schema:
            return []
        label = form_data.get("form_pkey") or "rowuuid"
        try:
            rows = self.request.dbsession.execute(
                text(
                    "SELECT rowuuid, `{}` AS label, _submitted_by, _submitted_date "
                    "FROM `{}`.maintable ORDER BY _submitted_date DESC LIMIT {}".format(
                        label if _IDENTIFIER.match(label) else "rowuuid",
                        schema,
                        int(limit),
                    )
                )
            ).fetchall()
        except Exception:
            self.request.dbsession.rollback()
            return []
        return [
            {
                "rowuuid": r[0],
                "label": "" if r[1] is None else str(r[1]),
                "by": r[2],
                "date": "" if r[3] is None else str(r[3]),
            }
            for r in rows
        ]

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        form_id = self.request.matchdict["formid"]
        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound
        here = self.request.route_url(
            "form_case_actions", userid=user_id, projcode=project_code, formid=form_id
        )
        if self.request.method == "POST":
            post_data = self.get_post_dict()
            ok, message = True, ""
            if "add_action" in post_data or "update_action" in post_data:
                data = {
                    "target_scope": post_data.get("target_scope", "case"),
                    "target_kind": post_data.get("target_kind", ""),
                    "target_name": post_data.get("target_name", ""),
                    "value_kind": post_data.get("value_kind", "constant"),
                    "value": post_data.get("value", ""),
                    "when_rules": post_data.get("when_rules", ""),
                }
                if data["value_kind"] == "computed":
                    data["value"] = json.dumps(
                        {
                            "aggregate": post_data.get("computed_aggregate", ""),
                            "repeat": post_data.get("computed_repeat", ""),
                            "column": post_data.get("computed_column", ""),
                        }
                    )
                if "update_action" in post_data and post_data.get("action_id"):
                    ok, message = update_form_action(
                        self.request, project_id, form_id, post_data["action_id"], data
                    )
                else:
                    ok, message = add_form_action(
                        self.request, project_id, form_id, data
                    )
                    if ok:
                        message = ""
            elif "delete_action" in post_data:
                ok, message = delete_form_action(
                    self.request, project_id, form_id, post_data.get("action_id", "")
                )
            elif "move_up" in post_data or "move_down" in post_data:
                ok, message = move_form_action(
                    self.request,
                    project_id,
                    form_id,
                    post_data.get("action_id", ""),
                    -1 if "move_up" in post_data else 1,
                )
            elif "set_mode" in post_data:
                ok, message = set_action_mode(
                    self.request,
                    project_id,
                    form_id,
                    post_data.get("action_mode", "table"),
                )
            elif "save_module" in post_data:
                ok, message = set_expert_module(
                    self.request,
                    project_id,
                    form_id,
                    post_data.get("action_module", ""),
                )
            elif "retry_run" in post_data:
                outcome = retry_run(
                    self.request,
                    post_data.get("run_id", ""),
                    form_data.get("form_schema"),
                    self.user.login,
                )
                ok, message = outcome.get("ok", False), outcome.get("error") or ""
            self.returnRawViewResult = True
            if ok:
                return HTTPFound(location=here)
            self.add_error(message)
            return HTTPFound(location=here, headers={"FS_error": "true"})

        catalogue = build_catalogue(self.request, project_id, form_id)
        rows = get_form_actions(self.request, project_id, form_id)
        for a_row in rows:
            try:
                a_row["when_words"] = describe_when(a_row.get("when_rules"), catalogue)
            except CompileError:
                a_row["when_words"] = "?"
        mode = get_action_mode(self.request, project_id, form_id)
        module = get_action_module(self.request, project_id, form_id)
        try:
            compiled = compile_module(rows, catalogue)
        except CompileError as e:
            compiled = "// " + str(e)
        targets = {}
        for (scope, kind, name), a_type in catalogue.targets.items():
            targets.setdefault(scope, {}).setdefault(kind, []).append(
                {"name": name, "type": a_type}
            )
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "formData": form_data,
            "rows": rows,
            "mode": mode,
            "module": module,
            "compiled": compiled,
            "filters": json.dumps(catalogue_for_querybuilder(catalogue)),
            "targets": json.dumps(targets),
            "variables": json.dumps(catalogue.variables),
            "repeats": json.dumps(catalogue.repeats),
            "hasCase": catalogue.source is not None,
            "source": catalogue.source,
            "submissions": self._submissions(form_data),
            "runs": get_form_runs(self.request, project_id, form_id, limit=50),
            "failedRuns": len(
                get_form_runs(self.request, project_id, form_id, status=1)
            ),
        }


class ActionsTestView(ListSection):
    """The dry run (actions-api.md section 11): POST {rowuuid, module?} as
    JSON, returns {ok, changes, log, error}; nothing is written."""

    def __init__(self, request):
        ListSection.__init__(self, request)
        # A fetch from the page: the token travels in the X-CSRF-Token
        # header, and the referer is the page rather than this address.
        self.checkCrossPost = False

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        form_id = self.request.matchdict["formid"]
        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound
        self.returnRawViewResult = True
        if self.request.method != "POST":
            raise HTTPNotFound
        try:
            data = json.loads(self.request.body.decode("utf-8") or "{}")
        except ValueError:
            data = self.get_post_dict()
        rowuuid = str(data.get("rowuuid", "") or "").strip()
        module = data.get("module")
        if module is not None and str(module).strip() == "":
            module = None
        if rowuuid == "" or not form_data.get("form_schema"):
            return {
                "ok": False,
                "error": self._("Choose a submission to test with"),
                "changes": [],
                "log": [],
            }
        outcome = run_for_submission(
            self.request,
            project_id,
            form_id,
            form_data["form_schema"],
            rowuuid,
            None,
            self.user.login,
            dry_run=True,
            module=module,
        )
        return {
            "ok": outcome["ok"],
            "skipped": outcome.get("skipped", False),
            "error": outcome["error"],
            "changes": outcome["changes"],
            "log": outcome["log"],
        }
