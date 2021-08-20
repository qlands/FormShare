from formshare.views.classes import PartnerView
from formshare.processes.db.partner import get_projects_and_forms_by_partner
import datetime


class PartnerForms(PartnerView):
    def process_view(self):
        return {
            "projects": get_projects_and_forms_by_partner(self.request, self.partnerID),
            "today": datetime.date.today(),
        }
