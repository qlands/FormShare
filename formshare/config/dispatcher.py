"""
formshare.config.dispatcher
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

View dispatcher: wraps class-based FormShare views as async FastAPI endpoints.

``make_endpoint(view_class, renderer, db_session_factory, jinja_env, app_state)``
returns an async callable suitable as a FastAPI route handler.

Flow per request
----------------
1. Open a SQLAlchemy session from *db_session_factory*.
2. Build a ``FormShareRequest`` via the async factory (pre-reads body).
3. Run the sync view class in FastAPI's thread-pool executor.
4. Convert the return value to a Starlette response:
     - dict + .jinja2 renderer  →  render template, return HTMLResponse
     - dict + "json" renderer   →  JSONResponse
     - Response / FileResponse  →  .to_starlette()
     - HTTPException raised     →  appropriate Starlette response
5. Apply ``request.response`` header/status mutations.
6. Run response callbacks (e.g. the JS-inlining ``resource_callback``).
7. Close the session.
"""

import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor
from formshare.processes.logging.loggerclass import SecretLogger
from starlette.requests import Request
from starlette.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response as StarletteResponse,
)

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

# Shared thread pool for all sync views.
_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor()
    return _executor


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def make_async_endpoint(view_class, app_state):
    """Return an async FastAPI endpoint for an ``AsyncView`` subclass.

    The endpoint is truly async — no thread pool, no FormShareRequest, no
    SQLAlchemy session.  The view receives the raw Starlette ``Request`` and
    must return a Starlette ``Response``.
    """

    async def endpoint(request: Request):
        view = view_class(app_state)
        return await view(request)

    endpoint.__name__ = view_class.__name__ + "_async_endpoint"
    return endpoint


def make_endpoint(view_class, renderer, db_session_factory, jinja_env, app_state):
    """Return an async FastAPI endpoint for *view_class*.

    Parameters
    ----------
    view_class :
        A FormShare view class whose ``__init__`` accepts ``(request,)`` and
        whose ``__call__`` returns a dict, ``Response``, or ``FileResponse``.
    renderer : str | None
        A Jinja2 template path (``"user/profile.jinja2"``), ``"json"``,
        or ``None`` (raw response passthrough).
    db_session_factory :
        Zero-arg callable that returns a new ``sqlalchemy.orm.Session``.
    jinja_env : jinja2.Environment
        The module-level ``jinjaEnv`` from ``jinja_extensions``.
    app_state : dict
        Must contain ``"settings"``, ``"policies"``, ``"helpers"``.
    """

    async def endpoint(request: Request):
        from formshare.middleware import FormShareRequest
        from formshare.middleware.httpexceptions import (
            HTTPException as FSHTTPException,
        )

        db_session = db_session_factory()
        try:
            fs_request = await FormShareRequest.from_starlette(
                request, db_session, app_state
            )

            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(
                    _get_executor(),
                    functools.partial(_run_view, view_class, fs_request),
                )
            except FSHTTPException as exc:
                return _http_exc_to_starlette(exc)
            except Exception:
                log.exception("Unhandled exception in view %s", view_class.__name__)
                raise

            # Convert to an intermediate FSResponse so that response callbacks
            # (e.g. the JS-extraction resource_callback) can read/write .body
            # and .content_type before we produce the final Starlette response.
            try:
                fs_response = _result_to_fs_response(
                    result, renderer, jinja_env, fs_request
                )

                # Merge any header/status mutations the view made via request.response,
                # but only for rendered responses — NOT for HTTPException passthroughs
                # (redirects, 404s raised by the view, etc.) which are self-contained.
                if not hasattr(fs_response, "_starlette_passthrough"):
                    for name, value in fs_request.response.headers.items():
                        fs_response.headers[name] = value
                    if fs_request.response.status_code != 200:
                        fs_response.status_code = fs_request.response.status_code

                # Run response callbacks on the FSResponse
                fs_request.run_response_callbacks(fs_response)

                # Final conversion to Starlette
                from formshare.middleware.response import FileResponse as FSFileResponse

                if isinstance(fs_response, FSFileResponse):
                    sr = fs_response.to_starlette()
                    fs_request.response.apply_cookies(sr)
                    return sr

                # Starlette passthrough case – flush any accumulated headers into it
                if hasattr(fs_response, "_starlette_passthrough"):
                    sr = fs_response._starlette_passthrough
                    for name, value in fs_response.headers.items():
                        sr.headers[name] = value
                    return sr

                sr = fs_response.to_starlette()
                fs_request.response.apply_cookies(sr)
                return sr
            except Exception:
                log.exception(
                    "Exception in response pipeline for view %s",
                    view_class.__name__,
                )
                raise

        finally:
            # Roll back any uncommitted state (e.g. from reads that autobegin'd
            # a transaction). Each write in process functions commits immediately,
            # so this is a no-op for successful writes.
            _rollback(db_session)
            try:
                db_session.close()
            except Exception:
                pass

    # FastAPI uses the function name for route identification
    endpoint.__name__ = view_class.__name__ + "_endpoint"
    return endpoint


# ---------------------------------------------------------------------------
# Error view endpoints (404, 403, 500)
# ---------------------------------------------------------------------------


def make_error_endpoint(view_class, renderer, db_session_factory, jinja_env, app_state):
    """Like make_endpoint but intended for exception/error views.

    Returns an async handler that accepts (request, exc) so it can be
    registered with FastAPI's exception_handler decorator.
    """

    async def handler(request: Request, exc):
        from formshare.middleware import FormShareRequest
        from formshare.middleware.httpexceptions import (
            HTTPException as FSHTTPException,
        )

        db_session = db_session_factory()
        try:
            fs_request = await FormShareRequest.from_starlette(
                request, db_session, app_state
            )

            # Pass the exception traceback to the error view so it can
            # log/email it.  Set on the FormShareRequest so the view
            # can access it via self.request.error_traceback.
            error_tb = getattr(request.state, "error_traceback", None)
            if error_tb:
                fs_request.error_traceback = error_tb

            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(
                    _get_executor(),
                    functools.partial(_run_view, view_class, fs_request),
                )
            except FSHTTPException as http_exc:
                return _http_exc_to_starlette(http_exc)
            except Exception:
                log.exception("Error view %s raised", view_class.__name__)
                return StarletteResponse(
                    content=b"Internal Server Error", status_code=500
                )

            fs_response = _result_to_fs_response(
                result, renderer, jinja_env, fs_request
            )

            # Apply header/status mutations set by the error view
            # (e.g. NotFoundView sets self.request.response.status = 404)
            for name, value in fs_request.response.headers.items():
                fs_response.headers[name] = value
            if fs_request.response.status_code != 200:
                fs_response.status_code = fs_request.response.status_code

            from formshare.middleware.response import FileResponse as FSFileResponse

            if isinstance(fs_response, FSFileResponse):
                return fs_response.to_starlette()
            if hasattr(fs_response, "_starlette_passthrough"):
                sr = fs_response._starlette_passthrough
                for name, value in fs_response.headers.items():
                    sr.headers[name] = value
                return sr
            return fs_response.to_starlette()

        finally:
            _rollback(db_session)
            try:
                db_session.close()
            except Exception:
                pass

    handler.__name__ = view_class.__name__ + "_error_handler"
    return handler


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _rollback(db_session):
    try:
        db_session.rollback()
    except Exception:
        pass


def _run_view(view_class, fs_request):
    """Instantiate and call the view class in the thread pool."""
    view_instance = view_class(fs_request)
    return view_instance()


def _result_to_fs_response(result, renderer, jinja_env, fs_request):
    """Convert a view return value to a FormShare ``Response``.

    We use FSResponse (not Starlette) here so that response callbacks
    (e.g. ``resource_callback``) can access ``.body`` and ``.content_type``
    before the final Starlette conversion.
    """
    from formshare.middleware.httpexceptions import HTTPException as FSHTTPException
    from formshare.middleware.response import (
        FileResponse as FSFileResponse,
        Response as FSResponse,
    )

    # Views that set returnRawViewResult=True may return an HTTPException directly
    # (rather than raising it).  Convert it to a Starlette response immediately
    # so the rest of the pipeline (callbacks, header merge) can still run.
    if isinstance(result, FSHTTPException):
        starlette_r = _http_exc_to_starlette(result)
        fs = FSResponse(status=starlette_r.status_code)
        fs._starlette_passthrough = starlette_r
        return fs

    # FileResponse is a special case – pass straight through
    if isinstance(result, FSFileResponse):
        return result  # to_starlette() called later

    if isinstance(result, FSResponse):
        return result

    # Direct Starlette response – wrap in FSResponse so callbacks can inspect it
    if isinstance(result, StarletteResponse):
        fs = FSResponse(status=result.status_code)
        fs._starlette_passthrough = result
        return fs

    # dict result – render according to renderer
    if isinstance(result, dict):
        if renderer == "json" or renderer is None:
            import json as _json

            body = _json.dumps(result).encode()
            return FSResponse(body=body, status=200, content_type="application/json")
        if renderer and (renderer.endswith(".jinja2") or renderer.endswith(".html")):
            return _render_jinja2_to_fs(result, renderer, jinja_env, fs_request)
        # Unknown renderer – fall back to JSON
        import json as _json

        body = _json.dumps(result).encode()
        return FSResponse(body=body, status=200, content_type="application/json")

    if result is None:
        return FSResponse(body=b"", status=204)

    return FSResponse(body=str(result).encode(), status=200)


def _render_jinja2_to_fs(context: dict, template_name: str, jinja_env, fs_request):
    """Render a Jinja2 template and return a FormShare ``Response``.

    Uses ``jinja_env.overlay()`` to install a per-request translator without
    mutating the shared environment (thread safety).
    """
    from formshare.middleware.response import Response as FSResponse

    translator = fs_request.translate

    try:
        # overlay() copies the env but shares the template cache and loader
        env = jinja_env.overlay()
        env.install_gettext_callables(translator, translator, newstyle=True)
        template = env.get_template(template_name)
    except Exception as e:
        log.error("Template not found or env error: %s – %s", template_name, e)
        return FSResponse(body=b"Template not found", status=500)

    ctx = dict(context)
    ctx.setdefault("request", fs_request)
    ctx.setdefault("_", translator)

    try:
        html = template.render(**ctx)
    except Exception:
        log.exception("Template render error for %s", template_name)
        return FSResponse(body=b"Template render error", status=500)

    return FSResponse(body=html.encode("utf-8"), status=200, content_type="text/html")


def _http_exc_to_starlette(exc):
    """Convert a ``formshare.middleware.httpexceptions.HTTPException`` to Starlette.

    For error status codes (4xx, 5xx) that are NOT redirects and carry no
    pre-built body, re-raise as a Starlette HTTPException so that FastAPI's
    registered exception handlers (404 → NotFoundView, 403 → ForbiddenView,
    etc.) can render the proper Jinja2 error page.
    """
    from starlette.exceptions import HTTPException as StarletteHTTPException

    status = exc.status_code
    headers = dict(exc.headers or {})

    if status in (301, 302, 303):
        return RedirectResponse(
            url=headers.get("Location", "/"),
            status_code=status,
            headers=headers,
        )

    # If the exception carries a pre-built body (e.g. from return_error()),
    # use it directly instead of building a generic JSON envelope.
    if getattr(exc, "body", None) is not None:
        return StarletteResponse(
            content=exc.body,
            status_code=status,
            headers=headers,
            media_type=getattr(exc, "content_type", None) or "application/octet-stream",
        )

    # Re-raise as a Starlette HTTPException so FastAPI's exception handlers
    # (registered in app.py) can render the Jinja2 error template.
    raise StarletteHTTPException(
        status_code=status,
        detail=exc.detail,
    )
