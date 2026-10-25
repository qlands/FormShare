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

from jinja2.utils import htmlsafe_json_dumps
from sqlalchemy import text

from formshare.middleware.httpexceptions import HTTPFound, HTTPNotFound
from formshare.middleware.response import FileResponse, Response
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
    forget_list_variants,
    valid_list_mode,
    repository_assigns_cases,
    assign_unassigned_cases,
    get_list_filters,
    get_list_filter,
    save_list_filter,
    delete_list_filter,
    count_list_cases,
    list_coverage,
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
    GEOMETRY_ALIAS,
    geometry_columns,
    geojson_list_select,
    write_list_geojson,
)
from formshare.processes.db.encryption import (
    encrypted_column_message,
    encrypted_columns,
)
from formshare.processes.db.form import get_form_data, get_form_directory
from formshare.processes.odk.api import (
    get_fields_from_table_in_file,
    get_odk_path,
)
from formshare.processes.db.form import get_project_forms
from formshare.processes.db.assistant import get_all_assistants
from formshare.processes.db.assistant_group import get_project_groups
from formshare.processes.db.project import (
    project_has_crowdsourcing,
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
from formshare.processes.list_filter import (
    FilterError,
    compile_filter,
    referenced_columns,
    describe_filter,
    filter_fields,
    querybuilder_filters,
)
from formshare.processes.actions.compiler import (
    CompileError,
    compile_module,
    describe_action,
    names_read,
    rule_module,
)
from formshare.processes.actions.server import (
    dry_run_sample,
    get_form_runs,
    retry_run,
    run_for_submission,
)
from formshare.processes.db.actions import (
    _choices as lookup_choices,
    add_code_action,
    add_form_action,
    build_catalogue,
    catalogue_for_editor,
    catalogue_for_querybuilder,
    delete_form_action,
    get_form_action,
    get_form_actions,
    move_form_action,
    update_code_action,
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
            # A GeoJSON list (feature 6) is drawn from a geopoint, geotrace or
            # geoshape of the table, one feature per case.
            list_format = (
                "geojson" if list_data.get("list_format") == "geojson" else "csv"
            )
            geometry_column = (
                str(list_data.get("geometry_column", "") or "").strip() or None
            )
            key_column = str(list_data.get("list_key_column", "") or "").strip() or None
            # A device reads, searches and picks by a list's label and key: a
            # column only FormShare's interface can read cannot be either
            # (field encryption). It may be served, sealed.
            encrypted = (
                encrypted_columns(self.request, project_id, source_form, source_table)
                if source_form and source_table
                else set()
            )
            # add, tablesof and fieldsof are path segments under /caselists;
            # a list with one of those ids would shadow them.
            if list_id in ("add", "tablesof", "fieldsof"):
                list_id = ""
            if (
                list_id == ""
                or not valid_list_filename(file_name)
                or not file_name.endswith("." + list_format)
            ):
                self.append_to_errors(
                    self._(
                        "The file name must be lower case, start with a letter, "
                        "and end in .csv, or in .geojson for a GeoJSON list"
                    )
                )
            elif source_form == "" or source_table == "" or label_column == "":
                self.append_to_errors(
                    self._("Select the form, the table and the label column")
                )
            elif label_column in encrypted:
                self.append_to_errors(
                    encrypted_column_message(
                        self._, label_column, self._("the label of a list")
                    )
                )
            elif key_column is not None and key_column in encrypted:
                self.append_to_errors(
                    encrypted_column_message(
                        self._, key_column, self._("the key of a list")
                    )
                )
            elif list_format == "geojson" and key_column is not None:
                self.append_to_errors(
                    self._(
                        "A GeoJSON list serves each case as a feature on a map, so "
                        "it cannot be a list of values"
                    )
                )
            elif list_format == "geojson" and geometry_column not in geometry_columns(
                get_table_columns(self.request, project_id, source_form, source_table)
            ):
                self.append_to_errors(
                    self._(
                        "Select the geopoint, geotrace or geoshape the GeoJSON list "
                        "is drawn from"
                    )
                )
            else:
                list_active = 0 if list_data.get("list_active") == "0" else 1
                added, message = add_published_list(
                    self.request,
                    project_id,
                    {
                        "list_id": list_id,
                        "list_filename": file_name,
                        "list_format": list_format,
                        "geometry_column": (
                            geometry_column if list_format == "geojson" else None
                        ),
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
                            _query={"tab": "columns"},
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


# The tabs of a list's page (owner, 2026-10-25). ?tab= names the open one:
# the page keeps it in its address as the tabs change, and its forms post
# to that address and are sent back to it, so a change opens the tab it was
# made in. The pages that send back here name theirs.
LIST_TABS = ("definition", "columns", "filters", "access")


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
        table_properties = get_table_properties(
            self.request,
            list_data["source_project"],
            list_data["source_form"],
            list_data["source_table"],
        )
        fields = filter_fields(table_columns, table_properties)
        encrypted = encrypted_columns(
            self.request,
            list_data["source_project"],
            list_data["source_form"],
            list_data["source_table"],
        )
        crowdsourcing = project_has_crowdsourcing(self.request, project_id)
        # A form with a repository uses the list: the schema was built over
        # its key and its rows, so neither can change, and the list cannot be
        # deleted (DeletePublishedListView)
        followed = list_has_active_consumers(self.request, project_id, list_id)
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
                # A name served twice would fail every generation of the
                # list (build_list_select refuses it), and a GeoJSON list
                # carries its location under GEOMETRY_ALIAS.
                taken = {"name", "label"} | {
                    a_column[1] or a_column[0] for a_column in current
                }
                if list_data.get("list_format") == "geojson":
                    taken.add(GEOMETRY_ALIAS)
                if (column_as or column_name) in taken:
                    self.append_to_errors(
                        self._(
                            'The list already serves a column called "{}". '
                            "Serve it under another name"
                        ).format(column_as or column_name)
                    )
                else:
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
                if list_data.get("list_format") == "geojson" and key_column:
                    self.append_to_errors(
                        self._(
                            "A GeoJSON list serves each case as a feature on a "
                            "map, so it cannot be a list of values"
                        )
                    )
                elif key_column is not None and key_column in encrypted:
                    self.append_to_errors(
                        encrypted_column_message(
                            self._, key_column, self._("the key of a list")
                        )
                    )
                elif followed:
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
                # A follow-up's membership trigger accepts only cases with the
                # _active the list served when its repository was built
                # (apply_link_attributes). Serving the other rows would offer
                # its devices cases it refuses.
                if followed:
                    self.append_to_errors(
                        self._(
                            "The rows to serve cannot change while a form with a "
                            "repository uses this list"
                        )
                    )
                else:
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
            if "change_mode" in post_data.keys():
                # Who receives which cases (formshare.md 3.8). The variants of
                # the old mode are deleted, so none of them is served again.
                mode = str(post_data.get("list_filter_mode", "") or "").strip()
                if not valid_list_mode(mode, crowdsourcing):
                    if crowdsourcing:
                        self.append_to_errors(
                            self._(
                                "A crowdsourcing project has no assistants to tell "
                                "apart, so its lists serve every case to everyone"
                            )
                        )
                    else:
                        self.append_to_errors(self._("Select who receives which cases"))
                elif mode == "assigned_to" and not self.assigns_cases(list_data):
                    self.append_to_errors(
                        self._(
                            "The repository of {} was built before cases could be "
                            "assigned. Merge a new version of the form into it: the "
                            "merge adds who each case is assigned to"
                        ).format(list_data["source_form"])
                    )
                elif mode == (list_data.get("list_filter_mode") or "all"):
                    self.returnRawViewResult = True
                    return HTTPFound(self.request.url)
                else:
                    updated, message = update_published_list(
                        self.request,
                        project_id,
                        list_id,
                        {"list_filter_mode": mode},
                    )
                    if not updated:
                        self.append_to_errors(message)
                    else:
                        schema = get_list_source_schema(self.request, list_data)
                        if mode == "assigned_to" and schema:
                            # The cases there before a merge gave the
                            # repository _assigned_to go to whoever registered
                            # them, as every case does
                            assign_unassigned_cases(self.request, schema)
                        forget_list_variants(self.request, project_id, list_id)
                        invalidate_list_copies(self.request, project_id, list_id)
                        self.returnRawViewResult = True
                        return HTTPFound(self.request.url)
            if (
                "change_filter" in post_data.keys()
                or "clear_filter" in post_data.keys()
            ):
                # The filter the owner built (formshare.md 8.1): compiled to
                # the fragment the list's SELECT appends, on the server and in
                # lists.xml, and tried on the source before it is kept.
                rules = ""
                if "change_filter" in post_data.keys():
                    rules = str(post_data.get("filter_rules", "") or "").strip()
                error = None
                filter_sql = None
                read = sorted(referenced_columns(rules) & encrypted)
                if read:
                    error = encrypted_column_message(
                        self._, read[0], self._("read by a list's filter")
                    )
                else:
                    try:
                        filter_sql = compile_filter(rules, fields)
                    except FilterError as e:
                        error = str(e)
                if error is None and filter_sql:
                    error = self.try_filter(project_id, list_id, list_data, filter_sql)
                if error is not None:
                    self.append_to_errors(error)
                else:
                    updated, message = update_published_list(
                        self.request,
                        project_id,
                        list_id,
                        {
                            "filter_rules": rules if filter_sql else None,
                            "filter_sql": filter_sql,
                        },
                    )
                    if not updated:
                        self.append_to_errors(message)
                    else:
                        invalidate_list_copies(self.request, project_id, list_id)
                        self.returnRawViewResult = True
                        return HTTPFound(self.request.url)
            if "change_geometry" in post_data.keys():
                geometry_column = post_data.get("geometry_column", "")
                if list_data.get(
                    "list_format"
                ) == "geojson" and geometry_column in geometry_columns(table_columns):
                    updated, message = update_published_list(
                        self.request,
                        project_id,
                        list_id,
                        {"geometry_column": geometry_column},
                    )
                    if not updated:
                        self.append_to_errors(message)
                    else:
                        invalidate_list_copies(self.request, project_id, list_id)
                        self.returnRawViewResult = True
                        return HTTPFound(self.request.url)
                else:
                    self.append_to_errors(
                        self._(
                            "Select the geopoint, geotrace or geoshape the list is "
                            "drawn from"
                        )
                    )
            if "change_label" in post_data.keys():
                label_column = post_data.get("label_column", "")
                if label_column in encrypted:
                    self.append_to_errors(
                        encrypted_column_message(
                            self._, label_column, self._("the label of a list")
                        )
                    )
                elif label_column != "":
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
        list_tab = self.request.GET.get("tab")
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "listData": list_data,
            "listTab": list_tab if list_tab in LIST_TABS else LIST_TABS[0],
            "listColumns": get_list_columns(self.request, project_id, list_id),
            "tableColumns": table_columns,
            "tableProperties": table_properties,
            "filterFields": querybuilder_filters(
                fields, self.select_choices(list_data, fields)
            ),
            "filterRules": self.stored_rules(list_data),
            "filterWords": describe_filter(list_data.get("filter_rules"), fields),
            "geometryColumns": geometry_columns(table_columns),
            "listFollowed": followed,
            "crowdsourcing": crowdsourcing,
            "listFilters": self.list_filters(user_id, project_id, list_data, fields),
            "listCoverage": (
                None
                if crowdsourcing
                else list_coverage(self.request, project_id, list_data)
            ),
        }

    def list_filters(self, user_id, project_id, list_data, fields):
        """The list's filters as its page shows them, in mode "filters": the
        conditions in words, whom each is given to, and how many cases it
        matches now."""
        if list_data.get("list_filter_mode") != "filters":
            return []
        _, _, names = assignable(self.request, self.user, user_id, project_id)
        filters = get_list_filters(self.request, project_id, list_data["list_id"])
        for a_filter in filters:
            a_filter["words"] = (
                describe_filter(a_filter["filter_rules"], fields)
                if a_filter["filter_rules"]
                else ""
            )
            a_filter["given"] = sorted(
                names.get(
                    (an_assignee["assignee_type"], an_assignee["assignee_id"]),
                    self._("(removed)"),
                )
                for an_assignee in a_filter["assignees"]
            )
            a_filter["cases"] = count_list_cases(
                self.request, list_data, a_filter["filter_sql"]
            )
        return filters

    def assigns_cases(self, list_data):
        """Whether the list's source records who each case is assigned to. A
        source with no repository yet will, when it is built."""
        schema = get_list_source_schema(self.request, list_data)
        if not schema:
            return True
        return repository_assigns_cases(self.request, schema)

    def try_filter(self, project_id, list_id, list_data, filter_sql):
        """Runs the list's SELECT with the new filter over its source, one
        row at most, so that a filter the database refuses is refused here
        and not at the next pull. None when it runs, or when the source has
        no repository yet to try it on."""
        schema = get_list_source_schema(self.request, list_data)
        if not schema:
            return None
        columns = [
            (
                a_column["column_name"],
                a_column["column_as"],
                a_column.get("column_source") or "table",
            )
            for a_column in get_list_columns(self.request, project_id, list_id)
        ]
        try:
            sql, _ = build_list_select(
                schema,
                list_data["source_table"],
                list_data["label_column"],
                columns,
                filter_sql,
                limit=1,
                active=list_data.get("list_active", 1),
                key_column=list_data.get("list_key_column"),
            )
            self.request.dbsession.execute(text(sql)).fetchall()
        except Exception as e:
            self.request.dbsession.rollback()
            return self._("The filter could not run on the list's source: {}").format(
                str(e)
            )
        return None

    def select_choices(self, list_data, fields):
        """The codes of each select column's choice list, for the filter's
        combos."""
        schema = get_list_source_schema(self.request, list_data)
        choices = {}
        for field_id, field in fields.items():
            lookup = field.get("lookup") or ""
            if lookup.startswith("lkp") and field["kind"] in ("text", "number"):
                values = lookup_choices(self.request, schema, lookup, lookup[3:])
                if values:
                    choices[field_id] = values
        return choices

    @staticmethod
    def stored_rules(list_data):
        """The stored rule set as an object for the editor, or None."""
        try:
            return json.loads(list_data.get("filter_rules") or "null")
        except ValueError:
            return None


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


def assignable(request, user, user_id, project_id):
    """Who a list's filter can be given to: (groups, assistants, names). The
    groups are the project's; the assistants are those its forms can be
    given to, grouped by project as the form page offers them. names maps
    (assignee_type, assignee_id) to what the pages show."""
    groups = get_project_groups(request, project_id)
    assistants = get_all_assistants(request, user_id, project_id, user.tenant)
    names = {}
    for a_group in groups:
        names[("group", a_group["group_id"])] = a_group["group_desc"]
    for a_project in assistants:
        for an_assistant in a_project["assistants"]:
            an_assistant["uuid"] = an_assistant["code"].split("|")[-1]
            names[("assistant", an_assistant["uuid"])] = "{} ({})".format(
                an_assistant["name"], an_assistant["id"]
            )
    return groups, assistants, names


class ListFilterView(EditPublishedListView):
    """A filter of a list in mode "filters" (formshare.md 3.8): its name, its
    conditions, built with QueryBuilder over the list's columns and
    properties as the list's own filter is, and the assistants and groups it
    is given to, who receive the cases it matches."""

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        list_id = self.request.matchdict["listid"]
        list_data = get_published_list(self.request, project_id, list_id)
        if list_data is None or list_data.get("list_filter_mode") != "filters":
            raise HTTPNotFound
        # Nothing to give a filter to in crowdsourcing (formshare.md 3.8). A
        # project is not turned to it while a list is in this mode, but one
        # changed outside FormShare's pages may still be
        if project_has_crowdsourcing(self.request, project_id):
            raise HTTPNotFound
        filter_id = self.request.matchdict.get("filterid")
        filter_data = None
        if filter_id is not None:
            filter_data = get_list_filter(self.request, project_id, list_id, filter_id)
            if filter_data is None:
                raise HTTPNotFound
        source = (
            list_data["source_project"],
            list_data["source_form"],
            list_data["source_table"],
        )
        fields = filter_fields(
            get_table_columns(self.request, *source),
            get_table_properties(self.request, *source),
        )
        encrypted = encrypted_columns(self.request, *source)
        groups, assistants, names = assignable(
            self.request, self.user, user_id, project_id
        )
        chosen = [
            (an_assignee["assignee_type"], an_assignee["assignee_id"])
            for an_assignee in (filter_data or {}).get("assignees", [])
        ]
        name = (filter_data or {}).get("filter_name", "")
        rules = (filter_data or {}).get("filter_rules")
        if self.request.method == "POST":
            post_data = self.get_post_dict()
            name = str(post_data.get("filter_name", "") or "").strip()
            rules = str(post_data.get("filter_rules", "") or "").strip()
            given = post_data.get("assignees", [])
            if not isinstance(given, list):
                given = [given]
            chosen = []
            for a_value in given:
                assignee_type, _, assignee_id = str(a_value).partition(":")
                if (assignee_type, assignee_id) in names:
                    chosen.append((assignee_type, assignee_id))
            error = None
            filter_sql = None
            if name == "":
                error = self._("Name the filter")
            elif sorted(referenced_columns(rules) & encrypted):
                error = encrypted_column_message(
                    self._,
                    sorted(referenced_columns(rules) & encrypted)[0],
                    self._("read by a list's filter"),
                )
            else:
                try:
                    # No condition is every case: the filter of a supervisor
                    # who follows the whole study
                    filter_sql = compile_filter(rules, fields) or "1 = 1"
                except FilterError as e:
                    error = str(e)
            if error is None:
                error = self.try_variant(list_data, filter_sql)
            if error is not None:
                self.append_to_errors(error)
            else:
                saved, result = save_list_filter(
                    self.request,
                    project_id,
                    list_id,
                    filter_id,
                    name,
                    rules or None,
                    filter_sql,
                    chosen,
                )
                if not saved:
                    self.append_to_errors(result)
                else:
                    # Who receives what has changed: every variant is made
                    # again at the next pull that asks for it
                    forget_list_variants(self.request, project_id, list_id)
                    self.request.session.flash(self._("The filter was saved"))
                    self.returnRawViewResult = True
                    return HTTPFound(
                        location=self.request.route_url(
                            "project_case_list_edit",
                            userid=user_id,
                            projcode=project_code,
                            listid=list_id,
                            _query={"tab": "access"},
                        )
                    )
        try:
            stored_rules = json.loads(rules) if rules else None
        except ValueError:
            stored_rules = None
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "listData": list_data,
            "filterData": filter_data,
            "filterName": name,
            "filterFields": querybuilder_filters(
                fields, self.select_choices(list_data, fields)
            ),
            "filterRules": stored_rules,
            "filterWords": describe_filter(rules, fields) if rules else "",
            "filterCases": (
                count_list_cases(self.request, list_data, filter_data["filter_sql"])
                if filter_data
                else None
            ),
            "groups": groups,
            "assistants": assistants,
            "chosen": ["{}:{}".format(*an_assignee) for an_assignee in chosen],
        }

    def try_variant(self, list_data, filter_sql):
        """Runs the list's SELECT with the filter as an assistant's clause,
        one row at most, so that a filter the database refuses is refused
        here and not at the next pull."""
        schema = get_list_source_schema(self.request, list_data)
        if not schema:
            return None
        try:
            sql, _ = build_list_select(
                schema,
                list_data["source_table"],
                list_data["label_column"],
                [],
                list_data.get("filter_sql"),
                limit=1,
                active=list_data.get("list_active", 1),
                key_column=list_data.get("list_key_column"),
                variant_sql=filter_sql,
            )
            self.request.dbsession.execute(text(sql)).fetchall()
        except Exception as e:
            self.request.dbsession.rollback()
            return self._("The filter could not run on the list's source: {}").format(
                str(e)
            )
        return None


class DeleteListFilterView(ListSection):
    def __init__(self, request):
        ListSection.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        if self.request.method != "POST":
            raise HTTPNotFound
        list_id = self.request.matchdict["listid"]
        filter_id = self.request.matchdict["filterid"]
        if get_list_filter(self.request, project_id, list_id, filter_id) is None:
            raise HTTPNotFound
        self.returnRawViewResult = True
        deleted, message = delete_list_filter(
            self.request, project_id, list_id, filter_id
        )
        next_page = self.request.route_url(
            "project_case_list_edit",
            userid=user_id,
            projcode=project_code,
            listid=list_id,
            _query={"tab": "access"},
        )
        if deleted:
            forget_list_variants(self.request, project_id, list_id)
            self.request.session.flash(self._("The filter was deleted"))
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
        columns = get_table_columns(self.request, project_id, form_id, table_name)
        return {
            "fields": [a_field["field_name"] for a_field in columns],
            # What a GeoJSON list can be drawn from: {column: point|trace|shape}.
            "geo": geometry_columns(columns),
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
        repository_path = self.request.registry.settings["repository.path"]
        temp_dir = os.path.join(repository_path, *["tmp"])
        if list_data.get("list_format") == "geojson":
            # Ten features, written by caselistgen as the list is: the file to
            # design a form against, and to attach as its placeholder.
            try:
                sql, kind = geojson_list_select(
                    self.request, list_data, schema, columns, limit=10
                )
            except Exception as e:
                self.add_error(str(e))
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
            if sql is None:
                self.add_error(kind)
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            geojson_file = os.path.join(temp_dir, str(uuid.uuid4()) + ".geojson")
            written, message, _ = write_list_geojson(
                self.request.registry.settings, sql, kind, geojson_file
            )
            if not written:
                self.add_error(message)
                return HTTPFound(location=next_page, headers={"FS_error": "true"})
            response = FileResponse(
                geojson_file,
                request=self.request,
                content_type="application/geo+json",
                cache_max_age=0,
            )
            response.content_disposition = 'attachment; filename="{}"'.format(
                list_data["list_filename"]
            )
            return response
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


class ActionsSection(ListSection):
    """What the pages of a form's actions share (feature 3, decision 16):
    the form or a 404, the actions numbered, and the addresses."""

    def form_or_404(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        form_id = self.request.matchdict["formid"]
        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound
        return user_id, project_code, project_id, project_details, form_id, form_data

    def actions_url(self, user_id, project_code, form_id):
        return self.request.route_url(
            "form_case_actions", userid=user_id, projcode=project_code, formid=form_id
        )

    def test_url(self, user_id, project_code, form_id, action_id):
        return self.request.route_url(
            "form_case_action_test",
            userid=user_id,
            projcode=project_code,
            formid=form_id,
            actionid=action_id,
        )

    def numbered(self, rows, catalogue):
        """The actions in their order, each with its number, what it does in
        words and its code: a rule as a module of its own, code as written.
        A rule that cannot be spelled any more (what it names is gone) says
        why instead."""
        out = []
        for number, a_row in enumerate(rows, 1):
            entry = dict(a_row, number=number, broken=None)
            code = (a_row.get("action_kind") or "rule") == "code"
            entry["code"] = (a_row.get("action_code") or "") if code else ""
            try:
                entry["words"] = describe_action(a_row, catalogue)
                if not code:
                    entry["code"] = rule_module(a_row, catalogue)
            except CompileError as e:
                entry["words"] = ""
                entry["broken"] = str(e)
            out.append(entry)
        return out

    def submissions(self, form_data, limit=50):
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


class ActionsView(ActionsSection):
    """Form → Form actions: the form's actions in their order, each a rule
    or code, with what it does, its code, its test, its edit and its
    removal, and the record of their runs. The module the server runs, and
    actions.json serves, is the actions composed (compiler.compile_module)."""

    def process_view(self):
        (
            user_id,
            project_code,
            project_id,
            project_details,
            form_id,
            form_data,
        ) = self.form_or_404()
        here = self.actions_url(user_id, project_code, form_id)
        if self.request.method == "POST":
            post_data = self.get_post_dict()
            ok, message = True, ""
            if "delete_action" in post_data:
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
            elif "retry_run" in post_data:
                outcome = retry_run(
                    self.request,
                    post_data.get("run_id", ""),
                    form_data.get("form_schema"),
                    self.user.login,
                )
                ok, message = outcome.get("ok", False), outcome.get("error") or ""
            self.returnRawViewResult = True
            # The arrows post through htmx, and the page fetches the list
            # again on formshare:actions-updated (actions.jinja2)
            if self.request.headers.get("HX-Request") == "true":
                if ok:
                    self.trigger_client_event("formshare:actions-updated")
                else:
                    self.trigger_client_event(
                        "formshare:notify", {"type": "error", "message": message}
                    )
                return Response(status=204)
            if ok:
                return HTTPFound(location=here)
            self.add_error(message)
            return HTTPFound(location=here, headers={"FS_error": "true"})

        catalogue = build_catalogue(self.request, project_id, form_id)
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "formData": form_data,
            "actions": self.numbered(
                get_form_actions(self.request, project_id, form_id), catalogue
            ),
            "source": catalogue.source,
            "runs": get_form_runs(self.request, project_id, form_id, limit=50),
            "failedRuns": len(
                get_form_runs(self.request, project_id, form_id, status=1)
            ),
        }


class ActionRuleView(ActionsSection):
    """Add an action, or edit a rule: its description, When, Target and
    Value. Saving goes on to the action's test."""

    def process_view(self):
        (
            user_id,
            project_code,
            project_id,
            project_details,
            form_id,
            form_data,
        ) = self.form_or_404()
        action_id = self.request.matchdict.get("actionid")
        rows = get_form_actions(self.request, project_id, form_id)
        existing = None
        number = len(rows) + 1
        if action_id is not None:
            for place, a_row in enumerate(rows, 1):
                if a_row["action_id"] == action_id:
                    existing, number = a_row, place
            if existing is None or (existing.get("action_kind") or "rule") != "rule":
                raise HTTPNotFound
        if self.request.method == "POST":
            post_data = self.get_post_dict()
            data = {
                "action_desc": post_data.get("action_desc", ""),
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
            if existing is not None:
                ok, result = update_form_action(
                    self.request, project_id, form_id, action_id, data
                )
            else:
                ok, result = add_form_action(self.request, project_id, form_id, data)
            self.returnRawViewResult = True
            if ok:
                return HTTPFound(
                    location=self.test_url(user_id, project_code, form_id, result)
                )
            self.add_error(result)
            return HTTPFound(location=self.request.url, headers={"FS_error": "true"})

        catalogue = build_catalogue(self.request, project_id, form_id)
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
            "action": existing,
            "number": number,
            # Printed into the page's script: the names and labels come from
            # the form, and json.dumps would leave a "</script>" in one to
            # close the script. These are escaped for it, and print as they
            # are.
            "filters": htmlsafe_json_dumps(catalogue_for_querybuilder(catalogue)),
            "targets": htmlsafe_json_dumps(targets),
            "variables": htmlsafe_json_dumps(catalogue.variables),
            "repeats": htmlsafe_json_dumps(catalogue.repeats),
            "source": catalogue.source,
        }


# What a new action in code starts from
CODE_START = """export default function run(s, api) {
  // What happens to the case when this form is submitted.
}
"""


class ActionCodeView(ActionsSection):
    """Add an action in code, or edit one: the module in the code editor
    (frontend/actions-editor). Saving goes on to the action's test; a save
    refused shows the page again with the code as it was written."""

    def process_view(self):
        (
            user_id,
            project_code,
            project_id,
            project_details,
            form_id,
            form_data,
        ) = self.form_or_404()
        action_id = self.request.matchdict.get("actionid")
        rows = get_form_actions(self.request, project_id, form_id)
        existing = None
        number = len(rows) + 1
        if action_id is not None:
            for place, a_row in enumerate(rows, 1):
                if a_row["action_id"] == action_id:
                    existing, number = a_row, place
            if existing is None or (existing.get("action_kind") or "rule") != "code":
                raise HTTPNotFound
        code = existing["action_code"] if existing is not None else CODE_START
        description = (existing or {}).get("action_desc") or ""
        if self.request.method == "POST":
            post_data = self.get_post_dict()
            code = post_data.get("action_code", "")
            description = post_data.get("action_desc", "")
            if existing is not None:
                ok, result = update_code_action(
                    self.request, project_id, form_id, action_id, code, description
                )
            else:
                ok, result = add_code_action(
                    self.request, project_id, form_id, code, description
                )
            if ok:
                self.returnRawViewResult = True
                return HTTPFound(
                    location=self.test_url(user_id, project_code, form_id, result)
                )
            self.append_to_errors(result)
        catalogue = build_catalogue(self.request, project_id, form_id)
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "formData": form_data,
            "action": existing,
            "number": number,
            "code": code,
            "description": description,
            "source": catalogue.source,
            # What the editor completes and checks
            "editorCatalogue": htmlsafe_json_dumps(
                catalogue_for_editor(self.request, project_id, form_id, catalogue)
            ),
        }


class ActionTestPageView(ActionsSection):
    """Test an action: over a submission the form received, or over answers
    typed here, before any submission has arrived, the case then being a
    stand-in (server.sample_input). The test is a dry run (actions-api.md
    11), through ActionsTestView: nothing is written."""

    def process_view(self):
        (
            user_id,
            project_code,
            project_id,
            project_details,
            form_id,
            form_data,
        ) = self.form_or_404()
        action_id = self.request.matchdict["actionid"]
        catalogue = build_catalogue(self.request, project_id, form_id)
        actions = self.numbered(
            get_form_actions(self.request, project_id, form_id), catalogue
        )
        matching = [a for a in actions if a["action_id"] == action_id]
        if not matching:
            raise HTTPNotFound
        action = matching[0]
        source = catalogue.source
        own = bool(source and source.get("own"))
        read_questions, read_repeats = names_read(action, own)
        names = catalogue_for_editor(self.request, project_id, form_id, catalogue)
        selector = (source or {}).get("selector_field")
        return {
            "projectDetails": project_details,
            "userid": user_id,
            "projcode": project_code,
            "formData": form_data,
            "action": action,
            "actionId": action_id,
            "code": action["code"],
            "source": source,
            "submissions": self.submissions(form_data),
            # The questions and the repeats the code reads, the only ones the
            # page asks for: anything else is unanswered. The case's selector
            # is answered by the stand-in case (server.sample_input). Printed
            # into the page's script.
            "questions": htmlsafe_json_dumps(
                [
                    q
                    for q in names["questions"]
                    if q["name"] in read_questions
                    and not q.get("system")
                    and not q.get("encrypted")
                    and q["name"] != selector
                ]
            ),
            "repeats": htmlsafe_json_dumps(
                [
                    r
                    for r in names["repeats"]
                    if r["parent"] == "maintable" and r["name"] in read_repeats
                ]
            ),
            "editorCatalogue": htmlsafe_json_dumps(names),
        }


class ActionsTestView(ActionsSection):
    """The dry run (actions-api.md section 11), for the test page: POST
    as JSON {action_id, rowuuid} to run over a submission received, or
    {action_id, sample} over typed answers (server.sample_input); action_id
    runs that action alone, numbered as the list numbers it. "all" runs the
    form's module and "module" code not saved yet: no page asks for either
    since 2026-10-25, and the suite tests the module with them. Returns {ok,
    changes, log, error, failed_action, failed_line}; nothing is written."""

    def __init__(self, request):
        ActionsSection.__init__(self, request)
        # A fetch from the page: the token travels in the X-CSRF-Token
        # header, and the referer is the page rather than this address.
        self.checkCrossPost = False

    def process_view(self):
        (
            user_id,
            project_code,
            project_id,
            project_details,
            form_id,
            form_data,
        ) = self.form_or_404()
        self.returnRawViewResult = True
        if self.request.method != "POST":
            raise HTTPNotFound
        try:
            data = json.loads(self.request.body.decode("utf-8") or "{}")
        except ValueError:
            data = self.get_post_dict()

        def refused(message):
            return {
                "ok": False,
                "error": message,
                "changes": [],
                "log": [],
                "failed_action": None,
                "failed_line": None,
            }

        schema = form_data.get("form_schema")
        if not schema:
            return refused(
                self._("The form has no repository yet: its actions cannot run")
            )
        action_id = str(data.get("action_id") or "all")
        if action_id == "all":
            module = None
        else:
            rows = get_form_actions(self.request, project_id, form_id)
            places = {a["action_id"]: place for place, a in enumerate(rows, 1)}
            if action_id not in places:
                return refused(self._("No such action"))
            row = [a for a in rows if a["action_id"] == action_id][0]
            try:
                module = compile_module(
                    [dict(row, action_number=places[action_id])],
                    build_catalogue(self.request, project_id, form_id),
                )
            except CompileError as e:
                return refused(str(e))
        # Code not saved yet, run as given
        if data.get("module") is not None and str(data["module"]).strip() != "":
            module = str(data["module"])
        sample = data.get("sample")
        if isinstance(sample, dict):
            outcome = dry_run_sample(
                self.request,
                project_id,
                form_id,
                schema,
                self.user.login,
                sample,
                module=module,
            )
        else:
            rowuuid = str(data.get("rowuuid", "") or "").strip()
            if rowuuid == "":
                return refused(self._("Choose a submission to test with"))
            outcome = run_for_submission(
                self.request,
                project_id,
                form_id,
                schema,
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
            "failed_action": outcome.get("failed_action"),
            "failed_line": outcome.get("failed_line"),
        }
