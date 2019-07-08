from .classes import PrivateView, PublicView, APIView
from formshare.processes.db import get_project_id_from_name, get_product_output, update_download_counter, \
    get_user_projects, output_exists, set_output_public_state, delete_product
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
import formshare.plugins as p
from pyramid.response import FileResponse
import os


class DownloadPrivateProduct(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        product_id = self.request.matchdict['productid']
        output_id = self.request.matchdict['outputid']
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

        if project_details["access_type"] == 5:
            raise HTTPNotFound

        output_id, output_file, mime_type = get_product_output(self.request, project_id, form_id, product_id, output_id,
                                                               False)
        if output_id is not None:
            continue_download = True
            # Load connected plugins and check if they modify the download process
            for plugin in p.PluginImplementations(p.IProduct):
                continue_download = plugin.before_download_private_product(self.request, project_id, form_id,
                                                                           product_id, output_id, output_file,
                                                                           mime_type)
                break  # Only one plugging will be called to extend before_download_product
            if continue_download:
                filename, file_extension = os.path.splitext(output_file)
                if file_extension == '':
                    file_extension = 'unknown'
                response = FileResponse(output_file, request=self.request, content_type=mime_type)
                response.content_disposition = 'attachment; filename="' + form_id + file_extension + '"'
                update_download_counter(self.request, project_id, form_id, product_id, output_id)
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
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        product_id = self.request.matchdict['productid']
        output_id = self.request.matchdict['outputid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        output_id, output_file, mime_type = get_product_output(self.request, project_id, form_id, product_id, output_id,
                                                               True)
        if output_id is not None:
            continue_download = True
            # Load connected plugins and check if they modify the download process
            for plugin in p.PluginImplementations(p.IProduct):
                continue_download = plugin.before_download_public_product(self.request, project_id, form_id,
                                                                          product_id, output_id, output_file, mime_type)
                break  # Only one plugging will be called to extend before_download_product
            if continue_download:
                filename, file_extension = os.path.splitext(output_file)
                if file_extension == '':
                    file_extension = 'unknown'
                response = FileResponse(output_file, request=self.request, content_type=mime_type)
                response.content_disposition = 'attachment; filename="' + form_id + file_extension + '"'
                update_download_counter(self.request, project_id, form_id, product_id, output_id)
                return response
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class DownloadPrivateProductByAPI(APIView):
    def __init__(self, request):
        APIView.__init__(self, request)

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        product_id = self.request.matchdict['productid']
        output_id = self.request.matchdict['outputid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)

        api_projects = get_user_projects(self.request, user_id, self.user['user_id'], True)
        project_found = False
        project_details = {}
        for project in api_projects:
            if project["project_id"] == project_id:
                project_found = True
                project_details = project
        if not project_found:
            raise HTTPNotFound

        if project_details["access_type"] == 5:
            raise HTTPNotFound

        output_id, output_file, mime_type = get_product_output(self.request, project_id, form_id, product_id, output_id,
                                                               False)
        if output_id is not None:
            continue_download = True
            # Load connected plugins and check if they modify the download process
            for plugin in p.PluginImplementations(p.IProduct):
                continue_download = plugin.before_download_product_by_api(self.request, project_id, form_id,
                                                                          product_id, output_id, output_file, mime_type)
                break  # Only one plugging will be called to extend before_download_product
            if continue_download:
                filename, file_extension = os.path.splitext(output_file)
                if file_extension == '':
                    file_extension = 'unknown'
                response = FileResponse(output_file, request=self.request, content_type=mime_type)
                response.content_disposition = 'attachment; filename="' + form_id + file_extension + '"'
                update_download_counter(self.request, project_id, form_id, product_id, output_id)
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
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        product_id = self.request.matchdict['productid']
        output_id = self.request.matchdict['outputid']
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

        if project_details["access_type"] == 5:
            raise HTTPNotFound

        if self.request.method == 'POST':
            if output_exists(self.request, project_id, form_id, product_id, output_id):
                set_output_public_state(self.request, project_id, form_id, product_id, output_id, True, self.userID)
                next_page = self.request.route_url('form_details', userid=user_id,
                                                   projcode=project_code, formid=form_id,
                                                   _query={'tab': 'task', 'product': product_id})
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
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        product_id = self.request.matchdict['productid']
        output_id = self.request.matchdict['outputid']
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

        if project_details["access_type"] == 5:
            raise HTTPNotFound

        if self.request.method == 'POST':
            if output_exists(self.request, project_id, form_id, product_id, output_id):
                set_output_public_state(self.request, project_id, form_id, product_id, output_id, False, self.userID)
                next_page = self.request.route_url('form_details', userid=user_id,
                                                   projcode=project_code, formid=form_id,
                                                   _query={'tab': 'task', 'product': product_id})
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
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        product_id = self.request.matchdict['productid']
        output_id = self.request.matchdict['outputid']
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

        if project_details["access_type"] == 5:
            raise HTTPNotFound

        if self.request.method == 'POST':
            if output_exists(self.request, project_id, form_id, product_id, output_id):
                deleted, message = delete_product(self.request, project_id, form_id, product_id, output_id)
                if deleted:
                    self.request.session.flash(self._('The product was deleted successfully'))
                else:
                    self.request.session.flash(self._('Unable to delete the product') + "|error")

                next_page = self.request.route_url('form_details', userid=user_id,
                                                   projcode=project_code, formid=form_id,
                                                   _query={'tab': 'task', 'product': product_id})
                return HTTPFound(location=next_page)
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound
