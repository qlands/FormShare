"""
formshare.config.fastapi_config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``FormShareConfig`` – a drop-in adapter that accepts the same method calls
that FormShare's ``load_environment()`` and plugin hooks make on Pyramid's
``Configurator``, but stores the results in plain Python data structures for
the FastAPI app factory to consume.

Methods that have no FastAPI equivalent (``set_session_factory``,
``add_subscriber``, ``add_request_method``, …) are accepted silently so
existing plugin code continues to run without modification.

Data collected
--------------
config.template_paths   list of template directory paths (Jinja2 search path)
config.static_views     list of {"name": str, "path": str, "max_age": int}
config._404_handler     (view_class, renderer) or None
config._403_handler     (view_class, renderer) or None
config._500_handler     (view_class, renderer) or None
config.settings         the live settings dict (mutable)
config.registry         _RegistryAdapter wrapping settings
"""

import importlib
import logging

log = logging.getLogger("formshare")


class _RegistryAdapter:
    """Minimal stand-in for Pyramid's registry, exposing only .settings."""

    def __init__(self, settings: dict):
        self.settings = settings

    def __repr__(self):
        return f"<FormShareRegistry keys={list(self.settings.keys())!r}>"


class FormShareConfig:
    """Collects configuration from FormShare's environment bootstrap and
    plugin hooks, without touching any Pyramid or FastAPI objects directly.

    Usage::

        config = FormShareConfig(settings)
        load_environment(settings, config, apppath, policy_array)
        # Now read config.template_paths, config.static_views, etc.
    """

    def __init__(self, settings: dict):
        self.settings = settings
        self.registry = _RegistryAdapter(settings)
        self.template_paths: list[str] = []
        self.static_views: list[dict] = []
        self._404_handler: tuple | None = None
        self._403_handler: tuple | None = None
        self._500_handler: tuple | None = None

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_settings(self) -> dict:
        return self.settings

    def add_settings(self, **kwargs):
        """Merge extra keys into settings (e.g. templatesPaths)."""
        self.settings.update(kwargs)

    # ------------------------------------------------------------------
    # Jinja2 / templates
    # ------------------------------------------------------------------

    def add_jinja2_search_path(
        self,
        searchpath: str = None,
        path: str = None,
        name: str = ".jinja2",
        prepend: bool = False,
        **kwargs,
    ):
        """Append *searchpath* (or *path*) to the Jinja2 search path list.

        Accepts both Pyramid's ``searchpath`` keyword and our own ``path``
        positional argument for backwards compatibility.
        """
        actual_path = searchpath or path
        if not actual_path:
            return
        if prepend:
            if actual_path not in self.template_paths:
                self.template_paths.insert(0, actual_path)
        else:
            if actual_path not in self.template_paths:
                self.template_paths.append(actual_path)

    def get_jinja2_environment(self):
        """No-op shim (Pyramid returns the environment; we handle it later)."""
        return None

    # ------------------------------------------------------------------
    # Static views
    # ------------------------------------------------------------------

    def add_static_view(self, name: str, path: str, **kwargs):
        """Record a static file mount for the app factory to handle."""
        cache_max_age = kwargs.get("cache_max_age", 0)
        # Avoid duplicate registrations
        for sv in self.static_views:
            if sv["name"] == name:
                return
        self.static_views.append({"name": name, "path": path, "max_age": cache_max_age})

    # ------------------------------------------------------------------
    # Routes and views  (no-ops – routes go into route_list / api_route_list)
    # ------------------------------------------------------------------

    def add_route(self, name: str, path: str, **kwargs):
        """No-op: routes are collected in route_list by append_to_routes()."""
        pass

    def add_view(self, view, **kwargs):
        """No-op: views are paired with routes via route_list."""
        pass

    # ------------------------------------------------------------------
    # Error / exception views
    # ------------------------------------------------------------------

    def add_notfound_view(self, view, **kwargs):
        self._404_handler = (view, kwargs.get("renderer"))

    def add_forbidden_view(self, view, **kwargs):
        self._403_handler = (view, kwargs.get("renderer"))

    def add_view_for_exception(self, view, context, **kwargs):
        """Handle config.add_view(ErrorView, context=Exception, ...)."""
        if context is Exception or (
            isinstance(context, type) and issubclass(context, Exception)
        ):
            self._500_handler = (view, kwargs.get("renderer"))

    # ------------------------------------------------------------------
    # module include  (replaces config.include(".models"))
    # ------------------------------------------------------------------

    def include(self, module_dotted: str):
        """Load *module_dotted* and call its ``includeme(config)`` if present.

        Relative dotted names (e.g. ``".models"``) are resolved relative to
        the ``formshare`` package.
        """
        if module_dotted.startswith("."):
            module_dotted = "formshare" + module_dotted
        try:
            mod = importlib.import_module(module_dotted)
        except ImportError as e:
            log.warning("config.include(%r) – import failed: %s", module_dotted, e)
            return
        if hasattr(mod, "includeme"):
            try:
                mod.includeme(self)
            except Exception as e:
                log.warning(
                    "config.include(%r) – includeme() failed: %s",
                    module_dotted,
                    e,
                )

    # ------------------------------------------------------------------
    # Pyramid-specific no-ops  (keep plugin code from crashing)
    # ------------------------------------------------------------------

    def add_request_method(self, *args, **kwargs):
        """No-op: request methods are properties on FormShareRequest."""
        pass

    def set_session_factory(self, *args, **kwargs):
        """No-op: session is handled by Starlette SessionMiddleware."""
        pass

    def set_csrf_storage_policy(self, *args, **kwargs):
        """No-op: CSRF is handled by FormShareSession."""
        pass

    def add_subscriber(self, *args, **kwargs):
        """No-op: Pyramid events are replaced by direct calls in the shim."""
        pass

    def set_default_csrf_options(self, *args, **kwargs):
        pass

    def make_wsgi_app(self):
        """No-op: the app factory builds the ASGI app directly."""
        return None
