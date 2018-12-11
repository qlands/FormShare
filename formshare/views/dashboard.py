from formshare.views.classes import DashboardView


class UserDashBoardView(DashboardView):
    def process_view(self):

        return {'projectData': self.activeProject}
