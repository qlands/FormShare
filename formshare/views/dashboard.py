from formshare.views.classes import DashboardView


class UserDashBoardView(DashboardView):
    def process_view(self):
        user_id = self.request.matchdict['userid']
        return {}
