from formshare.plugins.utilities import FormSharePrivateView
from formshare.processes.db.project import get_owned_project
from formshare.processes.db.user import (
    get_users,
    get_user_id_with_email,
    get_user_details,
)


class TestOwnedProjectView(FormSharePrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        owned_project = get_owned_project(self.request, user_id)
        users = get_users(self.request)
        user_details = get_user_details(self.request, user_id)
        user = get_user_id_with_email(self.request, user_details["user_email"])
        return {"owned_project": owned_project, "users": users, "user": user}
