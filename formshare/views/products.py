import os

import formshare.plugins as p
from formshare.processes.db import (
    get_project_id_from_name,
    get_product_output,
    update_download_counter,
    output_exists,
    set_output_public_state,
    delete_product,
    get_project_access_type,
)
from formshare.views.classes import PrivateView, PublicView
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from pyramid.response import FileResponse


class DownloadPrivateProduct(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        product_id = self.request.matchdict["productid"]
        output_id = self.request.matchdict["outputid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                > 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        output_id, output_file, mime_type = get_product_output(
            self.request, project_id, form_id, product_id, output_id, False
        )
        if output_id is not None:
            continue_download = True
            # Load connected plugins and check if they modify the download process
            for plugin in p.PluginImplementations(p.IProduct):
                continue_download = plugin.before_download_private_product(
                    self.request,
                    project_id,
                    form_id,
                    product_id,
                    output_id,
                    output_file,
                    mime_type,
                )
                break  # Only one plugging will be called to extend before_download_product
            if continue_download:
                filename, file_extension = os.path.splitext(output_file)
                if file_extension == "":
                    file_extension = "unknown"
                response = FileResponse(
                    output_file,
                    request=self.request,
                    content_type=mime_type,
                    cache_max_age=0,
                )
                response.content_disposition = (
                    'attachment; filename="' + form_id + file_extension + '"'
                )
                update_download_counter(
                    self.request, project_id, form_id, product_id, output_id
                )
                return response
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class DownloadPublicProduct(PublicView):
    def __init__(self, request):
        PublicView.__init__(self, request)
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        product_id = self.request.matchdict["productid"]
        output_id = self.request.matchdict["outputid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        output_id, output_file, mime_type = get_product_output(
            self.request, project_id, form_id, product_id, output_id, True
        )
        if output_id is not None:
            continue_download = True
            # Load connected plugins and check if they modify the download process
            for plugin in p.PluginImplementations(p.IProduct):
                continue_download = plugin.before_download_public_product(
                    self.request,
                    project_id,
                    form_id,
                    product_id,
                    output_id,
                    output_file,
                    mime_type,
                )
                break  # Only one plugging will be called to extend before_download_product
            if continue_download:
                filename, file_extension = os.path.splitext(output_file)
                if file_extension == "":
                    file_extension = "unknown"
                response = FileResponse(
                    output_file,
                    request=self.request,
                    content_type=mime_type,
                    cache_max_age=0,
                )
                response.content_disposition = (
                    'attachment; filename="' + form_id + file_extension + '"'
                )
                update_download_counter(
                    self.request, project_id, form_id, product_id, output_id
                )
                return response
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class PublishProduct(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        product_id = self.request.matchdict["productid"]
        output_id = self.request.matchdict["outputid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if self.request.method == "POST":
            if output_exists(self.request, project_id, form_id, product_id, output_id):
                set_output_public_state(
                    self.request,
                    project_id,
                    form_id,
                    product_id,
                    output_id,
                    True,
                    self.user.id,
                )
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query={"tab": "task", "product": product_id},
                )
                return HTTPFound(location=next_page)
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class UnPublishProduct(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        product_id = self.request.matchdict["productid"]
        output_id = self.request.matchdict["outputid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if self.request.method == "POST":
            if output_exists(self.request, project_id, form_id, product_id, output_id):
                set_output_public_state(
                    self.request,
                    project_id,
                    form_id,
                    product_id,
                    output_id,
                    False,
                    self.user.id,
                )
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query={"tab": "task", "product": product_id},
                )
                return HTTPFound(location=next_page)
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class DeleteProduct(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        product_id = self.request.matchdict["productid"]
        output_id = self.request.matchdict["outputid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        if project_id is not None:
            if (
                get_project_access_type(
                    self.request, project_id, user_id, self.user.login
                )
                >= 4
            ):
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if self.request.method == "POST":
            if output_exists(self.request, project_id, form_id, product_id, output_id):
                deleted, message = delete_product(
                    self.request, project_id, form_id, product_id, output_id
                )
                next_page = self.request.route_url(
                    "form_details",
                    userid=user_id,
                    projcode=project_code,
                    formid=form_id,
                    _query={"tab": "task", "product": product_id},
                )
                if deleted:
                    self.request.session.flash(
                        self._("The product was deleted successfully")
                    )
                    return HTTPFound(location=next_page)
                else:
                    self.request.session.flash(
                        self._("Unable to delete the product") + "|error"
                    )
                    return HTTPFound(location=next_page, headers={"FS_error": "true"})
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound
