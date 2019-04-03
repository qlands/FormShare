from .classes import PrivateView, PublicView
from formshare.processes.db import get_project_id_from_name
from pyramid.httpexceptions import HTTPNotFound


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






