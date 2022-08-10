from pyramid.httpexceptions import HTTPNotFound

from formshare.plugins.utilities import FormSharePrivateView
from formshare.processes.db import get_project_id_from_name, get_project_access_type
from formshare.processes.db.project import get_owned_project
from formshare.processes.db.user import (
    get_users,
    get_user_id_with_email,
    get_user_details,
)
from formshare.processes.elasticsearch.repository_index import get_all_datasets_with_gps
from formshare.processes.elasticsearch.user_index import configure_user_index_manager
from formshare.processes.settings import (
    store_settings,
    update_settings,
    delete_settings,
    get_settings,
)
from formshare.views.classes import PartnerView, AssistantView


class TestUserView(FormSharePrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        owned_project = get_owned_project(self.request, user_id)
        users = get_users(self.request)
        user_details = get_user_details(self.request, user_id)
        user = get_user_id_with_email(self.request, user_details["user_email"])
        user_none = get_user_id_with_email(self.request, "not_exist@qlands.com")
        store_settings(self.request, "testing", {"test": "a_test_value"})
        update_settings(self.request, "testing", {"test": "new_testing_value"})
        settings = get_settings(self.request, "testing")
        empty_settings = get_settings(self.request, "testing2")
        delete_settings(self.request, "testing")
        return {
            "owned_project": owned_project,
            "users": users,
            "user": user,
            "user_none": user_none,
            "settings": settings,
            "empty_settings": empty_settings,
        }


class TestFormView(FormSharePrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        self.get_project_access_level()

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

        datasets = get_all_datasets_with_gps(
            self.request.registry.settings, project_id, form_id, 10000
        )
        return {"datasets": datasets}


class TestRemoveUserView(FormSharePrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        index_manager = configure_user_index_manager(self.request.registry.settings)
        index_manager.remove_user(user_id)
        return {}


class TestErrorView(FormSharePrivateView):
    def process_view(self):
        return {"data": 1 / 0}


class TestAssistantErrorView(AssistantView):
    def process_view(self):
        return {"data": 1 / 0}


class TestPartnerErrorView(PartnerView):
    def process_view(self):
        return {"data": 1 / 0}
