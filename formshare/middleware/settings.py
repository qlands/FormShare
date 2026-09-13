"""
formshare.middleware.settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Global application settings store.

Replaces request.registry (Pyramid's component registry) for the
settings-access use case:

    # Old Pyramid code:
    path = request.registry.settings["repository.path"]
    key  = request.registry.settings.get("aes.key", None)

    # Unchanged – works via the shim:
    path = request.registry.settings["repository.path"]

The settings dict is populated once at startup by calling init_settings()
and is then available anywhere via get_settings() or through
FormShareRequest.registry.settings.
"""

import threading

_settings: dict = {}
_lock = threading.Lock()


def init_settings(settings: dict) -> None:
    """Make *settings* the global settings store.

    Call this once during application startup before any request is handled.
    The dict is kept, not copied: it is the same object every request reads
    through request.registry.settings, so a value changed at runtime (the
    test suite flips deployment switches this way) is seen everywhere.
    """
    global _settings
    with _lock:
        _settings = settings


def get_settings() -> dict:
    """Return the global settings dict."""
    return _settings


class _Registry:
    """Minimal stand-in for Pyramid's registry object.

    Only the .settings attribute is used in FormShare code.
    """

    def __init__(self, settings: dict):
        self.settings = settings

    def __repr__(self):
        return f"<FormShareRegistry keys={list(self.settings.keys())!r}>"
