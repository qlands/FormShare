"""
formshare.middleware.httpexceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

HTTP exception classes that replace pyramid.httpexceptions.

All exceptions carry status_code, detail, and headers so the view
dispatcher can convert them to proper Starlette/FastAPI responses.

Migration note:
    from formshare.middleware.httpexceptions import HTTPFound, HTTPNotFound
    becomes:
    from formshare.middleware.httpexceptions import HTTPFound, HTTPNotFound
"""


class HTTPException(Exception):
    """Base HTTP exception.  Carries enough information for the dispatcher
    to build a proper response without knowing about the framework."""

    status_code: int = 500
    title: str = "HTTP Exception"

    def __init__(
        self, detail=None, headers=None, body=None, content_type=None, **kwargs
    ):
        self.detail = detail
        self.headers = dict(headers) if headers else {}
        self.body = body
        self.content_type = content_type
        super().__init__(detail)


# ---------------------------------------------------------------------------
# Redirects
# ---------------------------------------------------------------------------


class HTTPFound(HTTPException):
    """302 Found – redirect to *location*."""

    status_code = 302
    title = "Found"

    def __init__(self, location, headers=None):
        super().__init__(detail=location, headers=headers)
        self.location = location
        self.headers["Location"] = location


class HTTPMovedPermanently(HTTPException):
    """301 Moved Permanently."""

    status_code = 301
    title = "Moved Permanently"

    def __init__(self, location, headers=None):
        super().__init__(detail=location, headers=headers)
        self.location = location
        self.headers["Location"] = location


class HTTPSeeOther(HTTPException):
    """303 See Other."""

    status_code = 303
    title = "See Other"

    def __init__(self, location, headers=None):
        super().__init__(detail=location, headers=headers)
        self.location = location
        self.headers["Location"] = location


# ---------------------------------------------------------------------------
# Client errors
# ---------------------------------------------------------------------------


class HTTPBadRequest(HTTPException):
    """400 Bad Request."""

    status_code = 400
    title = "Bad Request"


class HTTPUnauthorized(HTTPException):
    """401 Unauthorized."""

    status_code = 401
    title = "Unauthorized"


class HTTPForbidden(HTTPException):
    """403 Forbidden."""

    status_code = 403
    title = "Forbidden"


class HTTPNotFound(HTTPException):
    """404 Not Found."""

    status_code = 404
    title = "Not Found"


class HTTPMethodNotAllowed(HTTPException):
    """405 Method Not Allowed."""

    status_code = 405
    title = "Method Not Allowed"


class HTTPConflict(HTTPException):
    """409 Conflict."""

    status_code = 409
    title = "Conflict"


class HTTPGone(HTTPException):
    """410 Gone."""

    status_code = 410
    title = "Gone"


class HTTPUnprocessableEntity(HTTPException):
    """422 Unprocessable Entity."""

    status_code = 422
    title = "Unprocessable Entity"


class HTTPTooManyRequests(HTTPException):
    """429 Too Many Requests."""

    status_code = 429
    title = "Too Many Requests"


# ---------------------------------------------------------------------------
# Server errors
# ---------------------------------------------------------------------------


class HTTPInternalServerError(HTTPException):
    """500 Internal Server Error."""

    status_code = 500
    title = "Internal Server Error"


class HTTPNotImplemented(HTTPException):
    """501 Not Implemented."""

    status_code = 501
    title = "Not Implemented"


class HTTPServiceUnavailable(HTTPException):
    """503 Service Unavailable."""

    status_code = 503
    title = "Service Unavailable"


# ---------------------------------------------------------------------------
# Factory (replaces pyramid.httpexceptions.exception_response)
# ---------------------------------------------------------------------------

_STATUS_MAP = {
    301: HTTPMovedPermanently,
    302: HTTPFound,
    303: HTTPSeeOther,
    400: HTTPBadRequest,
    401: HTTPUnauthorized,
    403: HTTPForbidden,
    404: HTTPNotFound,
    405: HTTPMethodNotAllowed,
    409: HTTPConflict,
    410: HTTPGone,
    422: HTTPUnprocessableEntity,
    429: HTTPTooManyRequests,
    500: HTTPInternalServerError,
    501: HTTPNotImplemented,
    503: HTTPServiceUnavailable,
}


def exception_response(status_code, **kwargs):
    """Factory that returns an HTTPException subclass for the given status code.

    Replaces pyramid.httpexceptions.exception_response().

    Usage:
        raise exception_response(400, detail="Bad input")
        raise exception_response(404)
    """
    cls = _STATUS_MAP.get(status_code)
    if cls is None:
        exc = HTTPException(**kwargs)
        exc.status_code = status_code
        return exc
    # Redirects require a location kwarg
    if status_code in (301, 302, 303):
        location = kwargs.pop("location", kwargs.pop("detail", "/"))
        return cls(location=location, **kwargs)
    return cls(**kwargs)
