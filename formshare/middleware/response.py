"""
formshare.middleware.response
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Response classes that replace pyramid.response.

Migration note:
    from formshare.middleware.response import Response, FileResponse
    becomes:
    from formshare.middleware.response import Response, FileResponse
"""

import os


class Response:
    """Mutable HTTP response.

    Mimics the subset of pyramid.response.Response used by FormShare:
        response = Response(body=b"...", status=200, content_type="text/html")
        response.body = b"new body"
        response.status = 404
        response.headers["X-Custom"] = "value"

    The view dispatcher converts this to a Starlette Response before
    returning to the client.
    """

    def __init__(
        self,
        body=None,
        status=200,
        headerlist=None,
        app_iter=None,
        content_type="text/html",
        charset="UTF-8",
        text=None,
    ):
        self.body = body if body is not None else b""
        self._status_code = int(str(status).split()[0]) if status else 200
        self.content_type = content_type
        self.charset = charset
        self.headers = {}
        if headerlist:
            for name, value in headerlist:
                if name.lower() == "content-type":
                    self.content_type = value
                else:
                    self.headers[name] = value
        if text is not None:
            self.text = text

    # ------------------------------------------------------------------
    # status property – accept both int (200) and str ("200 OK")
    # ------------------------------------------------------------------

    @property
    def status(self):
        return self._status_code

    @status.setter
    def status(self, value):
        if isinstance(value, str):
            self._status_code = int(value.split()[0])
        else:
            self._status_code = int(value)

    @property
    def status_code(self):
        return self._status_code

    @status_code.setter
    def status_code(self, value):
        self._status_code = int(value)

    # ------------------------------------------------------------------
    # text / body duality (Pyramid allows setting either)
    # ------------------------------------------------------------------

    @property
    def text(self):
        if self.body:
            return self.body.decode(self.charset or "utf-8", errors="replace")
        return ""

    @text.setter
    def text(self, value):
        if isinstance(value, str):
            self.body = value.encode(self.charset or "utf-8")
        else:
            self.body = value

    # ------------------------------------------------------------------
    # Conversion to Starlette response
    # ------------------------------------------------------------------

    def to_starlette(self):
        from starlette.responses import Response as StarletteResponse

        media_type = self.content_type
        if self.charset and "text/" in media_type:
            media_type = f"{media_type}; charset={self.charset}"

        r = StarletteResponse(
            content=self.body,
            status_code=self._status_code,
            media_type=media_type,
            headers=self.headers,
        )
        return r

    def __repr__(self):
        return (
            f"<Response status={self._status_code} content_type={self.content_type!r}>"
        )


class FileResponse:
    """Serve a file from disk.

    Mimics pyramid.response.FileResponse.

    Usage:
        return FileResponse("/path/to/file.zip", content_type="application/zip")
    """

    def __init__(
        self,
        path,
        request=None,
        cache_max_age=None,
        content_type=None,
        content_encoding=None,
    ):
        self.path = path
        self.cache_max_age = cache_max_age
        self.content_type = content_type or _guess_content_type(path)
        self.content_encoding = content_encoding
        self.headers = {}
        self._status_code = 200

    @property
    def status_code(self):
        return self._status_code

    @status_code.setter
    def status_code(self, value):
        self._status_code = int(value)

    def to_starlette(self):
        from starlette.responses import FileResponse as StarletteFileResponse

        headers = dict(self.headers)
        if self.cache_max_age:
            headers["Cache-Control"] = f"max-age={self.cache_max_age}"

        return StarletteFileResponse(
            path=self.path,
            media_type=self.content_type,
            headers=headers,
        )

    def __repr__(self):
        return f"<FileResponse path={self.path!r}>"


# ---------------------------------------------------------------------------
# Request-scoped mutable response (request.response)
# ---------------------------------------------------------------------------


class MutableResponse:
    """The object exposed as request.response.

    Views mutate it directly:
        self.request.response.headers["FS_error"] = "true"
        self.request.response.status = 404

    The dispatcher merges these mutations into the final Starlette response
    after the view returns.
    """

    def __init__(self):
        self._status_code = 200
        self.headers = {}
        self.body = b""
        self.content_type = "text/html"
        self.charset = "UTF-8"
        self._cookies: list = []  # list of (name, kwargs) tuples

    @property
    def status(self):
        return self._status_code

    @status.setter
    def status(self, value):
        if isinstance(value, str):
            self._status_code = int(value.split()[0])
        else:
            self._status_code = int(value)

    @property
    def status_code(self):
        return self._status_code

    @status_code.setter
    def status_code(self, value):
        self._status_code = int(value)

    def set_cookie(self, name: str, value: str = "", **kwargs):
        """Queue a Set-Cookie header to be applied to the final response.

        Accepted kwargs match Starlette's Response.set_cookie signature:
        max_age, expires, path, domain, secure, httponly, samesite.
        """
        self._cookies.append((name, value, kwargs))

    def apply_cookies(self, starlette_response):
        """Apply any queued Set-Cookie headers to *starlette_response*."""
        for cookie_name, cookie_value, cookie_kwargs in self._cookies:
            starlette_response.set_cookie(cookie_name, cookie_value, **cookie_kwargs)
        return starlette_response

    def apply_to_starlette(self, starlette_response):
        """Merge headers, status, and cookies into *starlette_response*."""
        for name, value in self.headers.items():
            starlette_response.headers[name] = value
        if self._status_code != 200:
            starlette_response.status_code = self._status_code
        self.apply_cookies(starlette_response)
        return starlette_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _guess_content_type(path):
    import mimetypes

    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"
