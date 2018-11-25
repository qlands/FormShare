from formshare.views.classes import DashboardView


class UserDashBoardView(DashboardView):
    def process_view(self):

        error = self.request.params.get('error')
        if error is not None:
            self.errors.append(error)

        return {'projectData': self.activeProject}
