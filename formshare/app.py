"""
formshare.app
~~~~~~~~~~~~~~

FastAPI application factory for FormShare 3.0.

Replaces the old ``formshare/__init__.py`` Pyramid entry point.

Usage (uvicorn)::

    uvicorn formshare.app:create_app --factory --host 0.0.0.0 --port 6543

Or in code::

    from formshare.app import create_app
    app = create_app(settings)

``settings`` is a plain ``dict`` with the same keys that used to come from the
Pyramid ``.ini`` file (``sqlalchemy.url``, ``auth.main.secret``, etc.).  The
``load_settings_from_ini()`` helper can read them from a file if needed.
"""

import logging
import os
from configparser import ConfigParser, NoOptionError

import formshare.plugins as p
from formshare.config.fastapi_config import FormShareConfig
from formshare.config.environment import load_environment
from formshare.config.config_indexes import configure_indexes
from formshare.models import get_engine, get_session_factory
from formshare.middleware.auth import build_policies
from formshare.middleware.settings import init_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("formshare")


# ---------------------------------------------------------------------------
# Settings loader (replaces paste.deploy / configparser glue in __init__.py)
# ---------------------------------------------------------------------------


def load_settings_from_ini(ini_path: str) -> dict:
    """Read an old-style FormShare .ini file and return a flat settings dict."""
    cfg = ConfigParser()
    cfg.read(ini_path)

    settings: dict = {}

    # Merge [app:formshare] section
    if cfg.has_section("app:formshare"):
        settings.update(dict(cfg.items("app:formshare")))

    apppath = os.path.dirname(os.path.abspath(__file__))
    settings.setdefault("apppath", apppath)
    settings["global:config:file"] = ini_path

    # Pull server info
    try:
        settings["server:main:host"] = cfg.get("server:main", "host")
    except Exception:
        settings.setdefault("server:main:host", "0.0.0.0")
    try:
        settings["server:main:port"] = cfg.get("server:main", "port")
    except Exception:
        settings.setdefault("server:main:port", "6543")
    try:
        settings["server:threads"] = cfg.get("app:formshare", "odk.threads")
    except NoOptionError:
        settings.setdefault("server:threads", "1")

    return settings


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(settings: dict | None = None, ini_path: str | None = None):
    """Build and return the FastAPI application.

    Parameters
    ----------
    settings :
        A flat dict of configuration values.  Either *settings* or *ini_path*
        must be provided.
    ini_path :
        Path to a FormShare .ini configuration file.  Ignored when *settings*
        is provided.
    """
    if settings is None:
        if ini_path is None:
            ini_path = os.environ.get("FORMSHARE_INI", "formshare.ini")
        settings = load_settings_from_ini(ini_path)

    apppath = settings.get("apppath", os.path.dirname(os.path.abspath(__file__)))
    settings["apppath"] = apppath

    # ------------------------------------------------------------------
    # 1. Load plugins
    # ------------------------------------------------------------------
    plugin_list = settings.get("formshare.plugins", "").split()
    plugin_list.reverse()
    log.info(
        "FormShare plugins (load order): %s",
        ", ".join(plugin_list) if plugin_list else "(none)",
    )
    settings["active_plugins"] = plugin_list
    p.load_all(settings)

    # ------------------------------------------------------------------
    # 2. Build auth policies (itsdangerous-based, replaces AuthTkt)
    # ------------------------------------------------------------------
    policy_array = build_policies(settings)

    # Allow plugins to register additional auth policies
    policy_used = {pol["name"] for pol in policy_array}
    for plugin in p.PluginImplementations(p.IAuthenticationPolicy):
        policy_class, policy_name = plugin.create_policy(settings)
        if policy_name not in policy_used:
            policy_array.append({"name": policy_name, "policy": policy_class})
            policy_used.add(policy_name)
        else:
            log.warning("Policy name %r already in use – skipping.", policy_name)

    # ------------------------------------------------------------------
    # 3. Database engine + session factory
    # ------------------------------------------------------------------
    engine = get_engine(settings)
    db_session_factory = get_session_factory(engine)

    # ------------------------------------------------------------------
    # 4. Persist settings globally (request.registry.settings shim)
    # ------------------------------------------------------------------
    init_settings(settings)

    # ------------------------------------------------------------------
    # 5. Run FormShare's environment bootstrap via the config adapter
    # ------------------------------------------------------------------
    fs_config = FormShareConfig(settings)

    configure_indexes(settings)

    # load_environment populates fs_config.template_paths, fs_config.static_views,
    # and calls all IConfig / IResource / IDatabase / IRoutes plugin hooks.
    # It also fills route_list and api_route_list in their respective modules.
    load_environment(settings, fs_config, apppath, policy_array)

    # ------------------------------------------------------------------
    # 6. Grab jinjaEnv reference (already initialised by load_environment)
    # ------------------------------------------------------------------
    from formshare.config.jinja_extensions import jinjaEnv

    # ------------------------------------------------------------------
    # 7. Helpers reference (already loaded by load_environment)
    # ------------------------------------------------------------------
    import formshare.plugins.helpers as helpers_module

    # ------------------------------------------------------------------
    # 8. App state dict (passed to every request via FormShareRequest.from_starlette)
    # ------------------------------------------------------------------
    app_state: dict = {
        "settings": settings,
        "policies": policy_array,
        "helpers": helpers_module.helper_functions,
    }

    # ------------------------------------------------------------------
    # 9. Create FastAPI app and register routes
    # ------------------------------------------------------------------
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from starlette.middleware.sessions import SessionMiddleware

    from formshare.config.dispatcher import (
        make_endpoint,
        make_error_endpoint,
    )
    from formshare.config.routes import route_list
    from formshare.config.api_routes import api_route_list

    fastapi_app = FastAPI(title="FormShare", docs_url=None, redoc_url=None)

    # -- Session middleware (cookie-based; swap for Redis when SSO is needed) --
    session_secret = settings.get(
        "auth.main.secret", "changeme-replace-with-a-real-secret"
    )
    fastapi_app.add_middleware(SessionMiddleware, secret_key=session_secret)

    # -- Static file mounts --
    for sv in fs_config.static_views:
        path = sv["path"]
        name = sv["name"]
        if os.path.isdir(path):
            try:
                fastapi_app.mount(
                    "/" + name,
                    StaticFiles(directory=path),
                    name=name,
                )
            except Exception as e:
                log.warning("Could not mount static view %r at %r: %s", name, path, e)
        else:
            log.warning("Static view %r skipped – directory not found: %s", name, path)

    # -- Register all collected routes --
    def _register_routes(rlist):
        for route in rlist:
            view_class = route["view"]
            renderer = route["renderer"]
            path = route["path"]
            name = route["name"]

            # Convert Pyramid-style path params  {userid}  →  FastAPI  {userid}
            # (they use the same syntax, so no conversion is needed)

            endpoint = make_endpoint(
                view_class, renderer, db_session_factory, jinjaEnv, app_state
            )

            # Register for both GET and POST (FormShare views typically handle
            # both; the view itself decides based on request.method).
            fastapi_app.add_api_route(
                path,
                endpoint,
                methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"],
                name=name,
                include_in_schema=False,
            )

    _register_routes(route_list)
    _register_routes(api_route_list)

    # -- Error handlers --
    from starlette.requests import Request
    from starlette.responses import JSONResponse as _JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    if fs_config._404_handler:
        view_cls, tmpl = fs_config._404_handler
        _404 = make_error_endpoint(
            view_cls, tmpl, db_session_factory, jinjaEnv, app_state
        )

        @fastapi_app.exception_handler(404)
        async def not_found_handler(request: Request, exc):
            return await _404(request, exc)

    if fs_config._403_handler:
        view_cls, tmpl = fs_config._403_handler
        _403 = make_error_endpoint(
            view_cls, tmpl, db_session_factory, jinjaEnv, app_state
        )

        @fastapi_app.exception_handler(403)
        async def forbidden_handler(request: Request, exc):
            return await _403(request, exc)

    if fs_config._500_handler:
        view_cls, tmpl = fs_config._500_handler
        _500 = make_error_endpoint(
            view_cls, tmpl, db_session_factory, jinjaEnv, app_state
        )

        @fastapi_app.exception_handler(Exception)
        async def server_error_handler(request: Request, exc):
            return await _500(request, exc)

    # Note: IEnvironment.after_environment_load() was already called inside
    # load_environment() above.  No need to repeat it here.

    log.info(
        "FormShare 3.0 ready – %d routes registered.",
        len(route_list) + len(api_route_list),
    )

    return fastapi_app
