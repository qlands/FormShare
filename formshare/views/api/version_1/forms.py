from formshare.views.classes import APIView
from pyramid.httpexceptions import HTTPNotFound

__all__ = [
    "API1UploadFileToForm",
]


class API1UploadFileToForm(APIView):
    def __init__(self, request):
        APIView.__init__(self, request)

    def process_view(self):
        if self.request.method == "POST":
            required_keys = ["user_id", "project_code", "form_id"]
            self.check_keys(required_keys)

            return {}
        else:
            raise HTTPNotFound
