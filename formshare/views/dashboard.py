from formshare.views.classes import dashboardView
from formshare.processes import get_user_projects

class dashboard_view(dashboardView):
    def processView(self):
        return {}