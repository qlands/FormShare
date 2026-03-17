"""
formshare.middleware.auth
~~~~~~~~~~~~~~~~~~~~~~~~~~

Authentication policies that replace pyramid_authstack +
AuthTktAuthenticationPolicy.

FormShare has three independent login types, each with its own signed
cookie:

    main       – platform users    (was auth.main.*)
    assistant  – ODK assistants    (was auth.assistant.*)
    partner    – external partners (was auth.partner.*)

Each is backed by an AuthPolicy instance.  The policies are initialised
once at application startup and stored in app state so that
request.policies() can return them.

Migration note:
    The SSO plugin and basic_views.py call:
        policy = get_policy("main", request)
        login_data = policy.authenticated_userid(request)
        headers = policy.remember(request, userid)
        headers = policy.forget(request)

    All of that continues to work unchanged.

Cookie format
-------------
The cookie value is an itsdangerous TimestampSigner-signed string.
The payload is a JSON object:  {"login": "<userid>", "group": "<group>"}
– matching the literal_eval'd dict that the existing SSO plugin expects.
"""

import json
import logging
from typing import Optional

log = logging.getLogger("formshare")

try:
    from itsdangerous import TimestampSigner, SignatureExpired, BadSignature
except ImportError:  # pragma: no cover
    raise ImportError(
        "itsdangerous is required for formshare.middleware.auth. "
        "Add it to your requirements: itsdangerous>=2.0"
    )


class AuthPolicy:
    """Cookie-based authentication policy backed by itsdangerous.

    Replaces pyramid.authentication.AuthTktAuthenticationPolicy.

    Args:
        cookie_name: Name of the browser cookie (e.g. "formshare_auth_tkt").
        secret:      Signing secret from the .ini file.
        timeout:     Cookie max-age in seconds.  None means session cookie.
        group:       The group name embedded in the cookie payload
                     (e.g. "mainApp", "assistant", "partner").
        secure:      Set the Secure flag on the cookie.
        http_only:   Set the HttpOnly flag on the cookie (default True).
        same_site:   SameSite cookie attribute (default "Lax").
    """

    def __init__(
        self,
        cookie_name: str,
        secret: str,
        timeout: Optional[int] = None,
        group: str = "mainApp",
        secure: bool = False,
        http_only: bool = True,
        same_site: str = "Lax",
    ):
        self.cookie_name = cookie_name
        self.timeout = timeout
        self.group = group
        self.secure = secure
        self.http_only = http_only
        self.same_site = same_site
        self._signer = TimestampSigner(secret)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def authenticated_userid(self, request) -> Optional[str]:
        """Return the signed cookie payload string, or None.

        The returned string is a repr() / JSON of the login dict so that
        existing code using literal_eval() continues to work:

            login_data = literal_eval(policy.authenticated_userid(request))
            # login_data == {"login": "carlos", "group": "mainApp"}
        """
        raw = request.cookies.get(self.cookie_name)
        if not raw:
            return None
        try:
            payload = self._signer.unsign(raw, max_age=self.timeout)
            return payload.decode("utf-8")
        except SignatureExpired:
            log.debug("Auth cookie '%s' has expired.", self.cookie_name)
            return None
        except BadSignature:
            log.debug("Auth cookie '%s' has bad signature.", self.cookie_name)
            return None

    # ------------------------------------------------------------------
    # Write – return header lists (Pyramid remember/forget API)
    # ------------------------------------------------------------------

    def remember(self, request, userid: str):
        """Return a list of (header-name, header-value) tuples that set the
        auth cookie.

        Pyramid's remember() returns headers; callers pass them to HTTPFound:
            headers = policy.remember(request, userid)
            raise HTTPFound(location=url, headers=headers)

        The payload mirrors what the SSO plugin expects from literal_eval():
            {"login": "<userid>", "group": "<group>"}
        """
        payload = json.dumps({"login": userid, "group": self.group})
        token = self._signer.sign(payload.encode("utf-8")).decode("utf-8")

        parts = [
            f"{self.cookie_name}={token}",
            "Path=/",
        ]
        if self.timeout:
            parts.append(f"Max-Age={self.timeout}")
        if self.http_only:
            parts.append("HttpOnly")
        if self.secure:
            parts.append("Secure")
        if self.same_site:
            parts.append(f"SameSite={self.same_site}")

        return [("Set-Cookie", "; ".join(parts))]

    def forget(self, request):
        """Return headers that expire the auth cookie."""
        cookie = (
            f"{self.cookie_name}=; Path=/; Max-Age=0; "
            f"HttpOnly; SameSite={self.same_site}"
        )
        return [("Set-Cookie", cookie)]


# ---------------------------------------------------------------------------
# Helper used by SSO plugin and views  (replaces the local get_policy())
# ---------------------------------------------------------------------------


def get_policy(policy_name: str, request) -> Optional[AuthPolicy]:
    """Return the AuthPolicy with the given name from request.policies().

    Usage (unchanged from Pyramid version):
        policy = get_policy("main", request)
        userid = policy.authenticated_userid(request)
    """
    for entry in request.policies():
        if entry["name"] == policy_name:
            return entry["policy"]
    return None


# ---------------------------------------------------------------------------
# Startup helper
# ---------------------------------------------------------------------------


def build_policies(settings: dict) -> list:
    """Build the three standard FormShare auth policies from .ini settings.

    Returns a list of dicts in the format request.policies() returns:
        [{"name": "main", "policy": AuthPolicy(...)}, ...]

    Call this once at application startup and store the result in app state.
    """

    def _timeout(key):
        val = settings.get(key)
        if val is None:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    main_policy = AuthPolicy(
        cookie_name=settings["auth.main.cookie"],
        secret=settings["auth.main.secret"],
        timeout=_timeout("auth.main.cookie.timeout"),
        group="mainApp",
    )

    assistant_policy = AuthPolicy(
        cookie_name=settings["auth.assistant.cookie"],
        secret=settings["auth.assistant.secret"],
        timeout=_timeout("auth.assistant.cookie.timeout"),
        group="assistant",
    )

    partner_policy = AuthPolicy(
        cookie_name=settings["auth.partner.cookie"],
        secret=settings["auth.partner.secret"],
        timeout=_timeout("auth.partner.cookie.timeout"),
        group="partner",
    )

    policies = [
        {"name": "main", "policy": main_policy},
        {"name": "assistant", "policy": assistant_policy},
        {"name": "partner", "policy": partner_policy},
    ]
    return policies
