from formshare.views.classes import dashboardView

class dashboard_view(dashboardView):
    def processView(self):
        userID = self.request.matchdict['userid']
        return {}