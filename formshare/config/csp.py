"""A Content-Security-Policy for FormShare's own pages.

Field encryption opens answers in the browser, and its vault serves any page
of the origin (docs/formshare_field_encryption/README.md 2 and 9). A script
that ought not to be on a page -- injected, or come from another origin --
could read what the page shows and ask the vault for more. A strict policy
lets a page run only the scripts FormShare gave it:

- every <script> a template writes carries a nonce, made afresh for each
  request. The nonce is put in the template's source as it is compiled
  (CSPNonceExtension in jinja_extensions.py), so that templates -- core's and
  plugins' -- need not know of it, and a <script> that reaches a page through
  data -- a form's label printed raw, a JSON breaking out of its script --
  has none and does not run. Writing the nonce into the rendered page instead
  would give it to those too;
- 'strict-dynamic' trusts what a trusted script loads or inserts, from
  wherever it comes: a fragment htmx or jQuery puts into a page, a library
  loading its parts. A library that fetches a script from a CDN brings the
  CDN in, so core bundles what its libraries would fetch (mainresources.py:
  EmojioneArea did, 2026-10-14);
- nothing else runs: no inline event handler (onclick="..."), no eval, no
  <script> a template did not write -- none from another origin either --
  no plugin object.

The setting security.csp chooses how: "report" (the default) sends the policy
as Content-Security-Policy-Report-Only, so that browsers only report what it
would block, to /csp/report, where FormShare logs it; "enforce" sends it as
Content-Security-Policy; "off" sends nothing. A plugin whose pages set a
policy of their own keeps it.
"""

import re
import secrets

from jinja2 import pass_context
from markupsafe import Markup

CSP_MODES = ("off", "report", "enforce")
REPORT_PATH = "/csp/report"

# An opening <script> tag that has no nonce yet. A tag is matched whatever
# its case, and only as a tag: "<script" followed by a space, a ">" or "/".
_SCRIPT_TAG = re.compile(r"<script(?=[\s>/])(?![^>]*\bnonce\s*=)", re.IGNORECASE)

# What a template's <script> becomes: the attribute is written when the page
# is rendered, from the request in the template's context.
NONCE_IN_TEMPLATE = "<script{{ csp_nonce_attribute() }}"


def csp_mode(settings):
    """How the policy is sent: off, report or enforce. Anything else, or
    nothing, is "report"."""
    mode = str(settings.get("security.csp", "report") or "report").strip().lower()
    return mode if mode in CSP_MODES else "report"


def content_security_policy(nonce, report_uri):
    """The policy of a FormShare page whose scripts carry the nonce."""
    return "; ".join(
        [
            "default-src 'self'",
            "script-src 'self' 'nonce-{}' 'strict-dynamic'".format(nonce),
            # Inline styles are everywhere in the templates; the theme imports
            # its fonts from Google.
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' data: https://fonts.gstatic.com",
            # Map tiles, avatars and the like.
            "img-src 'self' data: blob: https:",
            "connect-src 'self'",
            "worker-src 'self' blob:",
            "object-src 'none'",
            "base-uri 'self'",
            "frame-ancestors 'self'",
            "report-uri {}".format(report_uri),
        ]
    )


def nonce_template_source(source):
    """A template's source with every <script> it writes asking for the
    request's nonce, but those that name one already."""
    return _SCRIPT_TAG.sub(NONCE_IN_TEMPLATE, source)


@pass_context
def csp_nonce_attribute(context):
    """The nonce attribute of a template's <script>: the nonce of the request
    the page is rendered for, or nothing when there is none -- the policy is
    off, or the template is rendered for no request, as an email is."""
    nonce = getattr(context.get("request"), "csp_nonce", None)
    if not nonce:
        return Markup("")
    return Markup(' nonce="{}"').format(nonce)


def _policy_set(headers):
    names = {name.lower() for name in headers.keys()}
    return bool(
        names & {"content-security-policy", "content-security-policy-report-only"}
    )


def content_security_callback(request, response):
    """Sends the policy with an HTML page rendered for a request that has a
    nonce (apply_content_security_policy registers it)."""
    if response.content_type != "text/html":
        return
    nonce = getattr(request, "csp_nonce", None)
    if not nonce or _policy_set(response.headers):
        return
    if csp_mode(request.registry.settings) == "enforce":
        header = "Content-Security-Policy"
    else:
        header = "Content-Security-Policy-Report-Only"
    response.headers[header] = content_security_policy(
        nonce, request.application_url + REPORT_PATH
    )


def apply_content_security_policy(request):
    """Called by every view class that renders pages: a nonce for this
    request, and the callback that sends the policy. Nothing when the setting
    is off."""
    if csp_mode(request.registry.settings) == "off":
        return
    request.csp_nonce = secrets.token_urlsafe(18)
    request.add_response_callback(content_security_callback)
