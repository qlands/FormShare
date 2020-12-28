from formshare.plugins.utilities import FormSharePrivateView
from formshare.processes.db.project import get_owned_project
from formshare.processes.db.user import (
    get_users,
    get_user_id_with_email,
    get_user_details,
)
from formshare.processes.db import get_project_id_from_name, get_form_details
from pyramid.httpexceptions import HTTPNotFound
from formshare.processes.elasticsearch.repository_index import get_all_datasets_with_gps
from formshare.processes.elasticsearch.user_index import configure_user_index_manager


class TestUserView(FormSharePrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        owned_project = get_owned_project(self.request, user_id)
        users = get_users(self.request)
        user_details = get_user_details(self.request, user_id)
        user = get_user_id_with_email(self.request, user_details["user_email"])
        return {"owned_project": owned_project, "users": users, "user": user}


class TestFormView(FormSharePrivateView):
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

        if project_details["access_type"] > 4:
            raise HTTPNotFound

        form_data = get_form_details(self.request, user_id, project_id, form_id)
        datasets = get_all_datasets_with_gps(
            self.request.registry.settings, form_data["form_index"], 10000
        )
        return {"datasets": datasets}


class TestRemoveUserView(FormSharePrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        index_manager = configure_user_index_manager(self.request.registry.settings)
        index_manager.remove_user(user_id)
        return {}
