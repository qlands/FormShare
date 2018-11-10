from formshare.views.classes import PrivateView


class CollaboratorsListView(PrivateView):
    def process_view(self):
        # self.request.h.setActiveMenu("projects")
        return {}
