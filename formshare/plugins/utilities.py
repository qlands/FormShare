"""
These series of functions help plugin developers
to manipulate the host behaviour without the trouble if dealing with it
"""

import inspect
import os

from pyramid.httpexceptions import HTTPNotFound

from formshare.processes.db import (
    get_project_id_from_name,
    get_project_details,
    get_form_data,
    get_project_owner,
)
from formshare.processes.settings.settings import (
    store_settings,
    update_settings,
    delete_settings,
    get_settings,
)
from formshare.views.classes import (
    PublicView,
    PrivateView,
    APIView,
    ProjectsView,
    AssistantView,
    PartnerView,
)

__all__ = [
    "add_templates_directory",
    "add_static_view",
    "add_js_resource",
    "add_css_resource",
    "add_library",
    "add_route",
    "add_field_to_user_schema",
    "add_field_to_project_schema",
    "add_field_to_assistant_schema",
    "add_field_to_assistant_group_schema",
    "add_field_to_form_schema",
    "FormSharePublicView",
    "FormSharePrivateView",
    "FormShareAPIView",
    "FormShareProjectsView",
    "FormShareAssistantView",
    "FormShareSettings",
    "FormShareFormEditorView",
    "FormShareFormAdminView",
    "add_field_to_form_access_schema",
    "add_field_to_form_group_access_schema",
]


def __return_current_path():  # pragma: no cover - Tested by loading testing plugins but not Covered
    """
    This code is based on CKAN
    :Copyright (C) 2007 Open Knowledge Foundation
    :license: AGPL V3, see LICENSE for more details.
    :return:
    """
    frame, filename, line_number, function_name, lines, index = inspect.getouterframes(
        inspect.currentframe()
    )[2]
    return os.path.dirname(filename)


def add_templates_directory(
    config, relative_path, prepend=True
):  # pragma: no cover - Tested by loading
    # testing plugins but not Covered
    if not os.path.isabs(relative_path):
        caller_path = __return_current_path()
        templates_path = os.path.join(caller_path, relative_path)
    else:
        templates_path = relative_path
    if os.path.exists(templates_path):
        config.add_jinja2_search_path(searchpath=templates_path, prepend=prepend)
        if prepend:
            config.registry.settings["templatesPaths"].insert(0, templates_path)
        else:
            config.registry.settings["templatesPaths"].append(templates_path)
    else:
        raise Exception("Templates path {} does not exists".format(relative_path))


def add_static_view(
    config, view_name, relative_path, cache_max_age=3600
):  # pragma: no cover - Tested by loading
    # testing plugins but not Covered
    if not os.path.isabs(relative_path):
        caller_path = __return_current_path()
        static_path = os.path.join(caller_path, relative_path)
    else:
        static_path = relative_path
    if os.path.exists(static_path):
        introspector = config.introspector
        if introspector.get("static views", view_name, None) is None:
            config.add_static_view(view_name, static_path, cache_max_age=cache_max_age)
    else:
        raise Exception("Static path {} does not exists".format(relative_path))


def add_js_resource(library_name, resource_id, resource_file, depends="CHAIN"):
    return {
        "libraryname": library_name,
        "id": resource_id,
        "file": resource_file,
        "depends": depends,
    }


def add_css_resource(library_name, resource_id, resource_file, depends="CHAIN"):
    return {
        "libraryname": library_name,
        "id": resource_id,
        "file": resource_file,
        "depends": depends,
    }


def add_library(
    name, path
):  # pragma: no cover - Tested by loading testing plugins but not Covered
    if not os.path.isabs(path):
        caller_path = __return_current_path()
        library_path = os.path.join(caller_path, path)
    else:
        library_path = path
    if os.path.exists(library_path):
        return {"name": name, "path": library_path}
    else:
        raise Exception("Library path {} does not exists".format(path))


def add_route(name, path, view, renderer):
    return {"name": name, "path": path, "view": view, "renderer": renderer}


def add_field_to_user_schema(field_name, field_desc):
    return {"schema": "fsuser", "fieldname": field_name, "fielddesc": field_desc}


def add_field_to_project_schema(field_name, field_desc):
    return {"schema": "project", "fieldname": field_name, "fielddesc": field_desc}


def add_field_to_assistant_schema(field_name, field_desc):
    return {"schema": "collaborator", "fieldname": field_name, "fielddesc": field_desc}


def add_field_to_assistant_group_schema(field_name, field_desc):
    return {"schema": "collgroup", "fieldname": field_name, "fielddesc": field_desc}


def add_field_to_form_schema(field_name, field_desc):
    return {"schema": "odkform", "fieldname": field_name, "fielddesc": field_desc}


def add_field_to_form_access_schema(field_name, field_desc):
    return {"schema": "formaccess", "fieldname": field_name, "fielddesc": field_desc}


def add_field_to_form_group_access_schema(field_name, field_desc):
    return {"schema": "formgrpaccess", "fieldname": field_name, "fielddesc": field_desc}


class FormSharePublicView(
    PublicView
):  # pragma: no cover - Tested by loading testing plugins but not Covered
    """
    A view class for plugins which require a public (not login required) view.
    """

    def process_view(self):
        raise NotImplementedError("process_view must be implemented in subclasses")


class FormSharePrivateView(
    PrivateView
):  # pragma: no cover - Tested by loading testing plugins but not Covered
    """
    A view class for plugins which require a private (login required) view.
    """


class FormShareAPIView(
    APIView
):  # pragma: no cover - Tested by loading testing plugins but not Covered
    """
    A view class for plugins which require an API view.
    """

    def process_view(self):
        raise NotImplementedError("process_view must be implemented in subclasses")


class FormShareProjectsView(
    ProjectsView
):  # pragma: no cover - Tested by loading testing plugins but not Covered
    """
    A view class for plugins which require an Project view.
    """

    def process_view(self):
        raise NotImplementedError("process_view must be implemented in subclasses")


class FormShareAssistantView(
    AssistantView
):  # pragma: no cover - Tested by loading testing plugins but not Covered
    """
    A view class for plugins which require an Assistant view.
    """

    def process_view(self):
        raise NotImplementedError("process_view must be implemented in subclasses")


class FormSharePartnerView(
    PartnerView
):  # pragma: no cover - Tested by loading testing plugins but not Covered
    """
    A view class for plugins which require an Partner view.
    """

    def process_view(self):
        raise NotImplementedError("process_view must be implemented in subclasses")


class FormShareFormEditorView(
    PrivateView
):  # pragma: no cover - Tested by loading testing plugins but not Covered
    """
    A view class for plugins which require a private Form View with editor+ privileges.
    """

    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True
        self.user_id = ""
        self.project_code = ""
        self.project_id = ""
        self.form_id = ""

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
            raise HTTPNotFound  # Don't edit a public or a project that I am just a member
        self.user_id = user_id
        self.project_code = project_code
        self.project_id = project_id
        self.form_id = form_id


class FormShareFormAdminView(
    PrivateView
):  # pragma: no cover - Tested by loading testing plugins but not Covered
    """
    A view class for plugins which require a private Form View with admin privileges.
    """

    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True
        self.user_id = ""
        self.project_code = ""
        self.project_id = ""
        self.form_id = ""
        self.project_details = None
        self.form_details = None

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

        if project_details["access_type"] >= 3:
            raise HTTPNotFound  # Don't edit a public or a project that I am just a member
        self.user_id = user_id
        self.project_code = project_code
        self.project_id = project_id
        self.form_id = form_id
        self.project_details = get_project_details(self.request, self.project_id)
        self.form_details = get_form_data(self.request, self.project_id, self.form_id)
        self.classResult["projectDetails"] = self.project_details
        self.classResult["projectDetails"]["owner"] = get_project_owner(
            self.request, project_id
        )
        self.classResult["formDetails"] = self.form_details


class FormShareSettings(
    object
):  # pragma: no cover - Tested by loading testing plugins but not Covered
    def __init__(self, request):
        self.request = request

    def store(self, key, value):
        return store_settings(self.request, key, value)

    def update(self, key, value):
        return update_settings(self.request, key, value)

    def delete(self, key):
        return delete_settings(self.request, key)

    def get(self, key):
        return get_settings(self.request, key)
