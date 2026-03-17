from formshare.views.classes import PublicView


class NotFoundView(PublicView):  # pragma: no cover
    def process_view(self):
        self.request.response.status = 404
        return {}
