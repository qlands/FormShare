from formshare.views.classes import PrivateView
from pyramid.httpexceptions import HTTPNotFound


class PartnersListView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.set_active_menu("partners")

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        if self.user.id != user_id:
            raise HTTPNotFound
        return {"userid": user_id}
