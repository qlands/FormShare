from formshare.views.classes import dashboardView
from formshare.processes import get_user_projects

class dashboard_view(dashboardView):
    def processView(self):
        # userID = self.request.matchdict['userid']
        # if userID == self.user.login:
        #     projectList = get_user_projects(self.request,userID)
        # else:
        #     projectList = get_user_projects(self.request, userID, True)
        # return {'projectList':projectList}
        return {}