from formshare.plugins.utilities import FormSharePrivateView
from formshare.processes.db.project import get_owned_project


class TestOwnedProjectView(FormSharePrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        owned_project = get_owned_project(self.request, user_id)
        return {"owned_project": owned_project}
