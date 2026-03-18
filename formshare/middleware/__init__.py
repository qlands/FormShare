"""
formshare.middleware
~~~~~~~~~~~~~~~~~~~~~

FormShare 3.0 – framework compatibility layer.

FormShareRequest wraps a Starlette Request and exposes the same interface
that FormShare views and process modules used under Pyramid.  This lets
existing code continue to work while the application runs on FastAPI.

Key design decisions
--------------------
- All Pyramid-specific attributes are provided as properties / cached_property
  so the call-sites stay identical.
- The SQLAlchemy session is created per-request from the connection pool.
  There is NO automatic begin/commit around the entire request (unlike
  pyramid_tm).  Views that need a transaction use  ``with session.begin():``
  or call ``request.tm.commit()`` explicitly.
- Body data (form fields, JSON, raw bytes) is pre-read by the async factory
  method ``FormShareRequest.from_starlette()`` before the sync view runs in
  FastAPI's thread-pool executor.
- ``request.response`` is a MutableResponse that views can mutate directly.
  The dispatcher applies those mutations to the final Starlette response.

Usage in views (unchanged from Pyramid):
    class MyView(PrivateView):
        def process_view(self):
            user_id = self.request.matchdict["userid"]
            rows = self.request.dbsession.query(MyModel).all()
            return {"rows": rows}
"""

import logging
from formshare.processes.logging.loggerclass import SecretLogger
import os
from functools import cached_property
from urllib.parse import urlencode

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


# ---------------------------------------------------------------------------
# Post data wrapper
# ---------------------------------------------------------------------------


class _PostData:
    """Thin wrapper that makes Starlette FormData behave like WebOb's
    MultiDict so that formencode.variabledecode continues to work."""

    def __init__(self, form_data):
        # form_data is a Starlette FormData object or a plain dict
        self._data = form_data

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __bool__(self):
        return bool(self._data)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        # Return unique keys only (same as WebOb MultiDict.keys())
        seen = set()
        result = []
        for k in (
            self._data.multi_items()
            if hasattr(self._data, "multi_items")
            else self._data.items()
        ):
            if k[0] not in seen:
                seen.add(k[0])
                result.append(k[0])
        return result

    def items(self):
        # Return ALL (key, value) pairs including duplicates — matches WebOb
        # MultiDict.items() behaviour, which variable_decode depends on to
        # collect multiple values for the same field (e.g. <select multiple>).
        if hasattr(self._data, "multi_items"):
            return self._data.multi_items()
        return self._data.items()

    def getall(self, key):
        """Return a list of all values for *key* (needed by variable_decode)."""
        if hasattr(self._data, "getlist"):
            return self._data.getlist(key)
        val = self._data.get(key)
        return [] if val is None else [val]

    def dict_of_lists(self):
        if hasattr(self._data, "multi_items"):
            result = {}
            for k, v in self._data.multi_items():
                result.setdefault(k, []).append(v)
            return result
        return {k: [v] for k, v in self._data.items()}


# ---------------------------------------------------------------------------
# Matched-route stub
# ---------------------------------------------------------------------------


class _MatchedRoute:
    """Provides request.matched_route.name without pulling in Pyramid."""

    def __init__(self, starlette_request):
        route = starlette_request.scope.get("route")
        self.name = getattr(route, "name", None)

    def __bool__(self):
        return self.name is not None


# ---------------------------------------------------------------------------
# _SessionMultiProxy  (pyramid_session_multi drop-in)
# ---------------------------------------------------------------------------


class _SessionMultiProxy:
    """Allows request.session_multi["secondary_session"] to return a persistent
    sub-dict backed by the main session store.

    Only "secondary_session" is supported (matches pyramid_session_multi usage).
    """

    _KEY_MAP = {"secondary_session": "_secondary"}

    def __init__(self, session_data: dict):
        self._data = session_data

    def __getitem__(self, name: str) -> dict:
        key = self._KEY_MAP.get(name, f"_multi_{name}")
        return self._data.setdefault(key, {})


# ---------------------------------------------------------------------------
# FormShareRequest
# ---------------------------------------------------------------------------


class FormShareRequest:
    """Drop-in replacement for Pyramid's Request object.

    Do not instantiate directly – use the async factory:

        fs_request = await FormShareRequest.from_starlette(
            starlette_request, db_session, app_state
        )

    Parameters stored on __init__ are all pre-resolved so that the object
    can be used in sync view code running in a thread-pool executor.
    """

    def __init__(
        self,
        starlette_request,
        db_session,
        settings: dict,
        session_data: dict,
        policies: list,
        helpers,
        locale_name: str,
        form_data,  # _PostData or empty _PostData
        json_body_data,  # parsed JSON dict/list or None
        body_bytes: bytes,  # raw body
    ):
        self._request = starlette_request
        self._db_session = db_session
        self._settings = settings
        self._session_data = session_data
        self._policies = policies
        self._helpers = helpers
        self._locale_name = locale_name
        self._form_data = form_data
        self._json_body_data = json_body_data
        self._body_bytes = body_bytes
        self._response_callbacks = []

        from formshare.middleware.response import MutableResponse

        self._mutable_response = MutableResponse()

    # ------------------------------------------------------------------
    # Async factory  (called by the dispatcher before handing off to sync)
    # ------------------------------------------------------------------

    @classmethod
    async def from_starlette(cls, starlette_request, db_session, app_state: dict):
        """Async factory: pre-read all body data, then build FormShareRequest.

        *app_state* must contain:
            - "settings"   : dict from .ini / environment
            - "policies"   : list of {"name": ..., "policy": AuthPolicy}
            - "helpers"    : helper_functions object
            - "session"    : dict-like session store (already loaded by middleware)
        """
        settings = app_state["settings"]
        policies = app_state["policies"]
        helpers = app_state.get("helpers")
        # starlette_request.session is the live dict managed by SessionMiddleware;
        # mutations to it are automatically persisted at the end of the request.
        session_data = starlette_request.session

        # -- Pre-read body --
        form_data = _PostData({})
        json_body_data = None
        body_bytes = b""

        content_type = starlette_request.headers.get("content-type", "")
        try:
            if "application/json" in content_type:
                body_bytes = await starlette_request.body()
                if body_bytes:
                    import json

                    json_body_data = json.loads(body_bytes)
            elif (
                "application/x-www-form-urlencoded" in content_type
                or "multipart/form-data" in content_type
            ):
                body_bytes = await starlette_request.body()  # cache raw bytes first
                raw_form = await starlette_request.form()  # reuses _body cache
                form_data = _PostData(raw_form)
            else:
                body_bytes = await starlette_request.body()
        except Exception as e:
            log.warning("Could not pre-read request body: %s", e)

        # -- Locale --
        from formshare.middleware.i18n import get_locale_name

        locale_name = get_locale_name(starlette_request)

        return cls(
            starlette_request=starlette_request,
            db_session=db_session,
            settings=settings,
            session_data=session_data,
            policies=policies,
            helpers=helpers,
            locale_name=locale_name,
            form_data=form_data,
            json_body_data=json_body_data,
            body_bytes=body_bytes,
        )

    # ==================================================================
    # Database
    # ==================================================================

    @cached_property
    def dbsession(self):
        """SQLAlchemy Session.  No auto-transaction – manage explicitly."""
        return self._db_session

    @cached_property
    def tm(self):
        """Transaction manager shim (replaces pyramid_tm)."""
        from formshare.middleware.tm import TransactionManager

        return TransactionManager(self._db_session)

    # ==================================================================
    # Routing
    # ==================================================================

    @property
    def matchdict(self) -> dict:
        """URL path parameters (replaces Pyramid's request.matchdict)."""
        return dict(self._request.path_params)

    def route_url(self, route_name: str, *elements, **kw) -> str:
        """Generate an absolute URL for *route_name*.

        Usage (unchanged):
            url = request.route_url("dashboard", userid="carlos")
            url = request.route_url("gravatar", _query={"name": "Carlos", "size": 45})
        """
        _query = kw.pop("_query", None)
        _anchor = kw.pop("_anchor", None)
        try:
            url = str(self._request.url_for(route_name, **kw))
        except Exception:
            # Fallback: build URL manually if url_for is not available
            # (e.g. during testing or when route is not yet registered)
            path = "/" + route_name
            for k, v in kw.items():
                path = path.replace("{" + k + "}", str(v))
            url = self.application_url + path

        if _query:
            url = url + "?" + urlencode(_query)
        if _anchor:
            url = url + "#" + _anchor
        return url

    def route_path(self, route_name: str, *elements, **kw) -> str:
        """Generate a path (no scheme/host) for *route_name*."""
        full = self.route_url(route_name, *elements, **kw)
        # Strip scheme + host
        from urllib.parse import urlparse

        parsed = urlparse(full)
        path = parsed.path
        if parsed.query:
            path += "?" + parsed.query
        if parsed.fragment:
            path += "#" + parsed.fragment
        return path

    @property
    def matched_route(self):
        return _MatchedRoute(self._request)

    # ==================================================================
    # Request data
    # ==================================================================

    @property
    def method(self) -> str:
        return self._request.method

    @property
    def headers(self):
        return self._request.headers

    @property
    def url(self) -> str:
        return str(self._request.url)

    @property
    def application_url(self) -> str:
        """Base URL without path, e.g. "https://formshare.example.com"."""
        return str(self._request.base_url).rstrip("/")

    @property
    def host_url(self) -> str:
        return self.application_url

    @property
    def path_url(self) -> str:
        return self.application_url + str(self._request.url.path)

    @property
    def path(self) -> str:
        return str(self._request.url.path)

    @property
    def user_agent(self) -> str:
        return self._request.headers.get("user-agent", "")

    @property
    def referer(self) -> str:
        """HTTP Referer header (also available as .referrer)."""
        return self._request.headers.get("referer", "")

    @property
    def referrer(self) -> str:
        return self.referer

    @property
    def cookies(self) -> dict:
        return dict(self._request.cookies)

    @property
    def client_addr(self):
        if self._request.client:
            return self._request.client.host
        return None

    @property
    def remote_addr(self):
        return self.client_addr

    @property
    def body(self) -> bytes:
        """Pre-read raw request body."""
        return self._body_bytes

    # -- Parameters --

    @cached_property
    def POST(self) -> _PostData:
        """Form / multipart POST data."""
        return self._form_data

    @cached_property
    def GET(self) -> dict:
        """Query string parameters."""
        return dict(self._request.query_params)

    @cached_property
    def params(self):
        """Combined query-string + POST params (replaces Pyramid's MultiDict)."""
        merged = dict(self._request.query_params)
        # POST values override query-string values (Pyramid behaviour)
        for k in self._form_data.keys():
            merged[k] = self._form_data[k]
        return merged

    @property
    def json_body(self):
        """Pre-parsed JSON body."""
        return self._json_body_data

    # ==================================================================
    # Session
    # ==================================================================

    @cached_property
    def session(self):
        from formshare.middleware.session import FormShareSession

        return FormShareSession(self._session_data)

    # ==================================================================
    # Registry / settings
    # ==================================================================

    @cached_property
    def registry(self):
        from formshare.middleware.settings import _Registry

        return _Registry(self._settings)

    # ==================================================================
    # Authentication
    # ==================================================================

    def policies(self) -> list:
        """Return list of {"name": ..., "policy": AuthPolicy} dicts."""
        return self._policies

    # ==================================================================
    # Helpers  (request.h)
    # ==================================================================

    @cached_property
    def h(self):
        return self._helpers

    # ==================================================================
    # i18n / translation
    # ==================================================================

    @property
    def locale_name(self) -> str:
        return self._locale_name

    @cached_property
    def translate(self):
        """Callable:  _ = request.translate;  _("Hello") -> "Hola" """
        from formshare.middleware.i18n import build_translator

        return build_translator(self._locale_name)

    # ==================================================================
    # Response (request.response)
    # ==================================================================

    @property
    def response(self):
        """Mutable response object for direct header/status manipulation."""
        return self._mutable_response

    def add_response_callback(self, callback):
        """Register a callback(request, response) called after the view.

        Replaces Pyramid's request.add_response_callback().
        The dispatcher runs all callbacks before finalising the response.
        """
        self._response_callbacks.append(callback)

    def run_response_callbacks(self, response):
        """Called by the dispatcher after the view returns."""
        for cb in self._response_callbacks:
            try:
                cb(self, response)
            except Exception as e:
                log.error("Response callback %s raised: %s", cb, e)
        return response

    # ==================================================================
    # Resource management  (request.activeResources)
    # ==================================================================

    @cached_property
    def activeResources(self):
        """Per-request CSS/JS resource tracker."""
        from formshare.config.environment import RequestResources

        return RequestResources(self)

    # ==================================================================
    # Static URLs  (request.url_for_static)
    # ==================================================================

    def url_for_static(self, static_file: str, library: str = "fstatic") -> str:
        return self.application_url + "/" + library + "/" + static_file

    # ==================================================================
    # Testing / environment helpers
    # ==================================================================

    def encget(self, key: str, default=None):
        """Read a value from the WSGI environ (test harness) or os.environ.

        Under Pyramid the test harness passed values via webtest's
        extra_environ dict which became request.environ.  Under FastAPI/a2wsgi
        that same dict is stored in the ASGI scope as ``wsgi_environ``.
        """
        wsgi_environ = self._request.scope.get("wsgi_environ", {})
        if key in wsgi_environ:
            return wsgi_environ[key]
        return os.environ.get(key, default)

    # ==================================================================
    # Secondary session (pyramid_session_multi equivalent)
    # ==================================================================

    def get_secondary_session(self):
        """Return the secondary (non-expiring) session dict.

        pyramid_session_multi registered a secondary session for persistent
        cookies.  Here we store it as a sub-key in the main session.
        """
        return self._session_data.setdefault("_secondary", {})

    @property
    def session_multi(self):
        """Drop-in for pyramid_session_multi: request.session_multi["secondary_session"]."""
        return _SessionMultiProxy(self._session_data)

    # ==================================================================
    # Repr
    # ==================================================================

    def __repr__(self):
        return f"<FormShareRequest {self.method} {self.url}>"
