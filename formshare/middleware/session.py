"""
formshare.middleware.session
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Session wrapper that adds Pyramid-compatible flash() support on top of a
plain dict-backed session (e.g., starlette-sessions with a Redis backend).

Migration note:
    request.session["key"] = value          # unchanged
    request.session.get("key")              # unchanged
    request.session.flash("message")        # now works without Pyramid
    request.session.pop_flash()             # retrieve and clear flash messages
"""


class FormShareSession:
    """Dict-like wrapper around the underlying session store.

    The backing store (*session_data*) is expected to be a plain mutable
    dict that is persisted by the session middleware (Redis, cookie, etc.).
    """

    def __init__(self, session_data: dict):
        self._data = session_data

    # ------------------------------------------------------------------
    # Standard dict interface
    # ------------------------------------------------------------------

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"FormShareSession({self._data!r})"

    def get(self, key, default=None):
        return self._data.get(key, default)

    def pop(self, key, *args):
        return self._data.pop(key, *args)

    def setdefault(self, key, default=None):
        return self._data.setdefault(key, default)

    def update(self, *args, **kwargs):
        self._data.update(*args, **kwargs)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def clear(self):
        self._data.clear()

    # ------------------------------------------------------------------
    # Flash messages  (Pyramid-compatible API)
    # ------------------------------------------------------------------

    _FLASH_KEY = "_formshare_flash"

    def flash(self, message, queue="", allow_duplicate=True):
        """Store *message* in the flash queue.

        Compatible with Pyramid's request.session.flash().

        Args:
            message: The message string to store.
            queue:   Optional queue name (default: "").
            allow_duplicate: If False, skip storing if the message is
                             already in the queue.
        """
        key = self._flash_key(queue)
        messages = self._data.setdefault(key, [])
        if not allow_duplicate and message in messages:
            return
        messages.append(message)

    def pop_flash(self, queue=""):
        """Return and remove all flash messages in *queue*.

        Compatible with Pyramid's request.session.pop_flash().
        """
        key = self._flash_key(queue)
        return self._data.pop(key, [])

    def peek_flash(self, queue=""):
        """Return flash messages without removing them."""
        key = self._flash_key(queue)
        return list(self._data.get(key, []))

    @staticmethod
    def _flash_key(queue):
        if queue:
            return f"{FormShareSession._FLASH_KEY}_{queue}"
        return FormShareSession._FLASH_KEY

    # ------------------------------------------------------------------
    # Invalidation (Pyramid-compatible)
    # ------------------------------------------------------------------

    def invalidate(self):
        """Clear the entire session (replaces Pyramid's session.invalidate())."""
        self._data.clear()
