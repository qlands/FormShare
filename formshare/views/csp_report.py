"""Where browsers report what FormShare's Content-Security-Policy blocked, or
would block (formshare/config/csp.py).

With security.csp = report, the policy only reports: this is how a script
that would break under enforcement shows itself -- a plugin's inline event
handler, a library that evaluates strings -- before anyone enforces. Each
distinct violation is logged once per process, so that a page seen a
thousand times does not fill the log.
"""

import json
import logging
from collections import OrderedDict

from formshare.processes.logging.loggerclass import SecretLogger
from formshare.views.classes import PublicView

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

_SEEN = OrderedDict()
_SEEN_MAX = 1000
_FIELD_MAX = 300


def _violations(payload):
    """The violations a report holds, whichever format the browser used:
    report-uri's {"csp-report": {...}}, or the Reporting API's list of
    {"type": "csp-violation", "body": {...}}."""
    if isinstance(payload, dict) and isinstance(payload.get("csp-report"), dict):
        return [payload["csp-report"]]
    if isinstance(payload, list):
        return [
            an_item["body"]
            for an_item in payload
            if isinstance(an_item, dict)
            and an_item.get("type") == "csp-violation"
            and isinstance(an_item.get("body"), dict)
        ]
    return []


def _field(violation, *names):
    for name in names:
        value = violation.get(name)
        if value not in (None, ""):
            return str(value)[:_FIELD_MAX]
    return ""


def log_violation(violation):
    """Logs a violation unless the same one was logged already. Returns
    whether it was logged."""
    directive = _field(
        violation, "effective-directive", "effectiveDirective", "violated-directive"
    )
    blocked = _field(violation, "blocked-uri", "blockedURL")
    page = _field(violation, "document-uri", "documentURL").split("?")[0]
    source = "{}:{}".format(
        _field(violation, "source-file", "sourceFile"),
        _field(violation, "line-number", "lineNumber"),
    )
    key = (directive, blocked, page, source)
    if key in _SEEN:
        return False
    _SEEN[key] = True
    if len(_SEEN) > _SEEN_MAX:
        _SEEN.popitem(last=False)
    log.warning(
        "Content-Security-Policy ({}): {} blocked {} on {} at {} {}".format(
            _field(violation, "disposition") or "report",
            directive,
            blocked or "inline code",
            page,
            source,
            _field(violation, "script-sample", "sample"),
        )
    )
    return True


class CSPReportView(PublicView):
    def __init__(self, request):
        PublicView.__init__(self, request)
        self.returnRawViewResult = True

    def process_view(self):
        if self.request.method != "POST":
            return {}
        try:
            payload = json.loads(self.request.body or b"null")
        except ValueError:
            return {}
        for violation in _violations(payload):
            log_violation(violation)
        return {}
