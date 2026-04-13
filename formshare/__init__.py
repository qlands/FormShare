"""
formshare
~~~~~~~~~

FormShare 3.0 – FastAPI-based application.

The old Pyramid entry point (gevent monkey-patching, AuthTktAuthenticationPolicy,
Configurator) has been replaced by formshare.app.create_app().

This module is kept as a thin shim so that any external code that calls
``formshare.main()`` (e.g. paste.app_factory consumers) continues to work
during the transition period.
"""

from formshare.app import create_app, load_settings_from_ini


def main(global_config, **settings):
    """PasteDeploy-style entry point.

    Delegates to the FastAPI app factory.  The returned object is an ASGI
    application (not WSGI), so it must be served with an ASGI server such as
    Uvicorn instead of Gunicorn+Gevent.
    """
    import os

    apppath = os.path.dirname(os.path.abspath(__file__))
    settings.setdefault("apppath", apppath)

    if global_config is not None:
        from configparser import ConfigParser, NoOptionError

        cfg = ConfigParser()
        cfg.read(global_config["__file__"])

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

        try:
            plugins = cfg.get("app:formshare", "formshare.plugins")
            plugins = plugins.split(" ")
            settings["active_plugins"] = plugins
        except NoOptionError:
            settings.setdefault("active_plugins", [])

        settings["global:config:file"] = global_config["__file__"]

    return create_app(settings=settings)
