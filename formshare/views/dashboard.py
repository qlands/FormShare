from .classes import privateView

class dashboard_view(privateView):
    def processView(self):
        self.request.h.setActiveMenu("dashboard")
        return {}