from formshare.views.classes import DashboardView


class MainDashBoardView(DashboardView):
    def process_view(self):
        user_id = self.request.matchdict['userid']
        return {}