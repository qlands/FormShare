"""Exporting and importing published lists as JSON or YAML.

The document and its rules are in processes/db/list_transfer.py. These views
belong to the Published lists section and share its access control: the
project's owners and editors.
"""

from formshare.middleware.httpexceptions import HTTPFound, HTTPNotFound
from formshare.middleware.response import Response
from formshare.processes.db.case_management import get_published_list
from formshare.processes.db.list_transfer import (
    MAX_BYTES,
    dump_document,
    import_lists,
    list_document,
    load_document,
)
from formshare.views.case_management import ListSection

# An error message shows this many problems, then says how many more there are.
_SHOWN_ERRORS = 10


class ExportPublishedListsView(ListSection):
    """The project's lists, or the one in the URL, as a JSON or YAML file."""

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        list_id = self.request.matchdict.get("listid")
        if list_id is not None:
            if get_published_list(self.request, project_id, list_id) is None:
                raise HTTPNotFound
            list_ids = [list_id]
            file_name = list_id
        else:
            list_ids = None
            file_name = project_code + "_lists"
        file_format = "yaml" if self.request.params.get("format") == "yaml" else "json"
        document = list_document(self.request, project_id, list_ids)
        self.returnRawViewResult = True
        response = Response(
            body=dump_document(document, file_format).encode("utf-8"),
            content_type=(
                "application/yaml" if file_format == "yaml" else "application/json"
            ),
        )
        response.content_disposition = 'attachment; filename="{}.{}"'.format(
            file_name, file_format
        )
        return response


class ImportPublishedListsView(ListSection):
    """Imports the lists of a JSON or YAML file into the project.

    Nothing is written unless the whole file can be imported; the page then
    says what was created, or every reason it was not.
    """

    def process_view(self):
        user_id, project_code, project_id, project_details = self.project_or_404()
        if self.request.method != "POST":
            raise HTTPNotFound
        self.returnRawViewResult = True
        next_page = self.request.route_url(
            "project_case_lists", userid=user_id, projcode=project_code
        )
        files = [
            a_file
            for a_file in self.request.POST.getall("listfile")
            if str(getattr(a_file, "filename", "") or "").strip() != ""
        ]
        if not files:
            self.add_error(self._("Choose a JSON or YAML file to import"))
            return HTTPFound(location=next_page, headers={"FS_error": "true"})
        content = files[0].file.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            self.add_error(self._("The file is too large to be a list export"))
            return HTTPFound(location=next_page, headers={"FS_error": "true"})
        document, error = load_document(content, self._)
        if document is None:
            self.add_error(error)
            return HTTPFound(location=next_page, headers={"FS_error": "true"})

        done, errors, warnings = import_lists(
            self.request, project_id, document, self.user.login
        )
        if errors:
            reasons = " ".join(
                "({}) {}.".format(number, an_error)
                for number, an_error in enumerate(errors[:_SHOWN_ERRORS], start=1)
            )
            if len(errors) > _SHOWN_ERRORS:
                reasons += " " + self._("And {} more.").format(
                    len(errors) - _SHOWN_ERRORS
                )
            if done["lists"] or done["properties"]:
                message = self._(
                    "The import stopped. {} Created before it: {}."
                ).format(reasons, ", ".join(done["properties"] + done["lists"]))
            else:
                message = self._("Nothing was imported. {}").format(reasons)
            self.add_error(message)
            return HTTPFound(location=next_page, headers={"FS_error": "true"})

        # The message is shown as JavaScript text, so it carries no quotes.
        message = self._("Imported {} list(s): {}.").format(
            len(done["lists"]), ", ".join(done["lists"])
        )
        if done["properties"]:
            message += " " + self._("Created {} propert(ies): {}.").format(
                len(done["properties"]), ", ".join(done["properties"])
            )
        if done["kept"]:
            message += " " + self._("Kept the existing properties {}.").format(
                ", ".join(done["kept"])
            )
        if warnings:
            message += " " + " ".join(
                a_warning.replace('"', "") + "." for a_warning in warnings
            )
            message += "|warning"
        self.request.session.flash(message)
        return HTTPFound(location=next_page)
