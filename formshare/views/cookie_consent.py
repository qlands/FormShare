import json
from urllib.parse import quote

from formshare.processes.db.cookie_consent import save_consent
from formshare.views.classes import PublicView


class SaveCookieConsentView(PublicView):
    def process_view(self):
        self.returnRawViewResult = True
        data = self.get_post_dict()
        functional = int(data.get("functional", 0))
        analytical = int(data.get("analytical", 0))
        marketing = int(data.get("marketing", 0))
        action = data.get("action", "custom")
        ip = self.request.client_addr or ""
        save_consent(self.request, ip, functional, analytical, marketing, action)
        cookie_value = quote(
            json.dumps({"e": 1, "f": functional, "a": analytical, "m": marketing})
        )
        self.request.response.set_cookie(
            "_COOKIE_CONSENT_",
            value=cookie_value,
            max_age=365 * 24 * 60 * 60,
            httponly=True,
            samesite="Strict",
        )
        return {"status": "ok"}
