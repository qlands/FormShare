from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:
    # Python 3.10+
    from importlib.metadata import entry_points, EntryPoint
except ImportError:  # pragma: no cover (very old Python)
    from importlib_metadata import entry_points, EntryPoint  # type: ignore

from pyutilib.component.core import ExtensionPoint as PluginImplementations
from pyutilib.component.core import Plugin as _pca_Plugin
from pyutilib.component.core import SingletonPlugin as _pca_SingletonPlugin
from pyutilib.component.core import implements

__all__ = [
    "PluginImplementations",
    "implements",
    "PluginNotFoundException",
    "Plugin",
    "SingletonPlugin",
    "load",
    "load_all",
    "unload",
    "unload_all",
    "get_plugin",
    "plugin_loaded",
    "load_all_celery",
]

# Entry point groups
PLUGINS_ENTRY_POINT_GROUP = "formshare.plugins"
CELERY_PLUGINS_ENTRY_POINT_GROUP = "formshare.celery.plugins"
TEST_PLUGINS_ENTRY_POINT_GROUP = "formshare.test_plugins"

GROUPS = [
    PLUGINS_ENTRY_POINT_GROUP,
    TEST_PLUGINS_ENTRY_POINT_GROUP,
    CELERY_PLUGINS_ENTRY_POINT_GROUP,
]


class PluginNotFoundException(Exception):
    """Raised when a requested plugin cannot be found."""


class Plugin(_pca_Plugin):
    """
    Base class for plugins which require multiple instances.

    Unless you need multiple instances of your plugin object you should
    probably use SingletonPlugin.
    """


class SingletonPlugin(_pca_SingletonPlugin):
    """
    Base class for plugins which are singletons (i.e. most of them).

    One singleton instance of this class will be created when the plugin is
    loaded. Subsequent calls to the class constructor will always return the
    same singleton instance.
    """


@dataclass
class _Registry:
    # Names in the order they were loaded
    loaded_names: List[str] = field(default_factory=list)

    # Class objects of loaded plugin services (to mirror prior behavior)
    loaded_classes: List[type] = field(default_factory=list)

    # Singleton instances addressable by plugin name
    singletons: Dict[str, Any] = field(default_factory=dict)

    def is_loaded(self, name: str) -> bool:
        return name in self.loaded_names

    def clear(self) -> None:
        self.loaded_names.clear()
        self.loaded_classes.clear()
        self.singletons.clear()


_REGISTRY = _Registry()


def get_plugin(plugin: str):  # pragma: no cover  # Not used
    """
    Get an instance of an active singleton plugin by name. Helpful for testing.
    """
    return _REGISTRY.singletons.get(plugin)


def load_all(settings: dict) -> None:
    """
    Load all plugins listed in the 'formshare.plugins' settings variable.
    :param settings: Pyramid settings dict-like
    """
    unload_all()
    plugins = (settings.get(PLUGINS_ENTRY_POINT_GROUP, "") or "").split()
    load(*plugins)


def load_all_celery(plugin_list: str) -> None:
    """
    Load all celery plugins listed in plugin_list. This is called by celery_app.py.
    :param plugin_list: List of celery plugins separated by space
    """
    unload_all()
    plugins = (plugin_list or "").split()
    load(*plugins)


def load(*plugins: str):
    """
    Load named plugin(s).

    :param plugins: plugin entry point names
    :return: If one plugin requested, return its instance; otherwise a list of instances.
    """
    output: List[Any] = []

    for name in plugins:
        if _REGISTRY.is_loaded(name):  # pragma: no cover
            raise Exception(f"Plugin `{name}` already loaded")

        service = _get_service(name)

        service.activate()

        _REGISTRY.loaded_names.append(name)
        _REGISTRY.loaded_classes.append(service.__class__)

        if isinstance(service, SingletonPlugin):
            _REGISTRY.singletons[name] = service

        output.append(service)

    if len(output) == 1:
        return output[0]
    return output


def unload_all() -> None:
    """
    Unload (deactivate) all loaded plugins in the reverse order that they were loaded.
    """
    unload(*reversed(_REGISTRY.loaded_names))


def unload(*plugins: str):  # pragma: no cover (Not used at the moment)
    """
    Unload named plugin(s).
    :param plugins: plugin names
    """

    for name in plugins:
        if not _REGISTRY.is_loaded(name):
            raise Exception(f"Cannot unload plugin `{name}`")

        service = _get_service(name)

        # Update registry AFTER successful deactivate
        _REGISTRY.loaded_names.remove(name)
        if name in _REGISTRY.singletons:
            del _REGISTRY.singletons[name]
        try:
            _REGISTRY.loaded_classes.remove(service.__class__)
        except ValueError:
            # If service class wasn't recorded for some reason, ignore
            pass


def plugin_loaded(name: str) -> bool:  # pragma: no cover
    """Return True if a particular plugin is loaded."""
    return _REGISTRY.is_loaded(name)


def _iter_entry_points_for(group: str, name: str) -> Iterable[EntryPoint]:
    """
    Yield entry points matching (group, name) across Python versions.
    """
    eps = entry_points()

    # Python 3.10+: entry_points().select(group=..., name=...)
    if hasattr(eps, "select"):
        yield from eps.select(group=group, name=name)  # type: ignore[attr-defined]
        return

    # Older importlib_metadata: mapping-like
    group_eps = eps.get(group, [])  # type: ignore[call-arg]
    for ep in group_eps:
        if getattr(ep, "name", None) == name:
            yield ep


def _get_service(plugin_name: str):  # pragma: no cover
    """
    Return a service (i.e. an instance of a plugin class) from entry points.
    :param plugin_name: entry point name
    :return: plugin service instance
    """
    if not isinstance(plugin_name, str):
        raise TypeError("Expected a plugin name", plugin_name)

    for group in GROUPS:
        for ep in _iter_entry_points_for(group=group, name=plugin_name):
            plugin_cls = ep.load()
            return plugin_cls(name=plugin_name)

    raise PluginNotFoundException(plugin_name)
