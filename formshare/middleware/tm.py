"""
formshare.middleware.tm
~~~~~~~~~~~~~~~~~~~~~~~~

Transaction manager shim that replaces pyramid_tm / zope.transaction.

FormShare 2.x used pyramid_tm which automatically began a transaction when
a request arrived and committed (or rolled back) when the request finished.
This caused long-held locks when any I/O happened during the request.

FormShare 3.x removes that implicit lifecycle.  Instead:
  - A SQLAlchemy Session is created per-request from the connection pool.
  - Views that need a transaction call session.begin() / with session.begin():
  - request.tm is kept as a compatibility shim so existing code continues
    to work without modification.

Existing usage in processes/db/*.py:
    save_point = request.tm.savepoint()
    ...
    save_point.rollback()

    request.dbsession.flush()
    request.tm.commit()   # or request.tm.abort()

All of that continues to work through this shim.
"""

import logging
from formshare.processes.logging.loggerclass import SecretLogger

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


class TransactionManager:
    """Thin wrapper over a SQLAlchemy Session that mimics the
    zope.transaction / pyramid_tm interface used in FormShare."""

    def __init__(self, session):
        self._session = session

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def commit(self):
        """Commit the current transaction."""
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def abort(self):
        """Roll back the current transaction."""
        self._session.rollback()

    # Pyramid / zope.transaction also exposes .get() on the manager
    def get(self):
        return self

    # ------------------------------------------------------------------
    # Savepoints  (replaces request.tm.savepoint())
    # ------------------------------------------------------------------

    def savepoint(self):
        """Return a savepoint context that supports .rollback().

        Usage (unchanged from FormShare 2.x):
            save_point = request.tm.savepoint()
            try:
                ...
            except Exception:
                save_point.rollback()
        """
        return _Savepoint(self._session)

    # ------------------------------------------------------------------
    # Context manager  (with request.tm: ...)
    # ------------------------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.abort()
        return False  # do not suppress exceptions


class _Savepoint:
    """Wraps SQLAlchemy's nested transaction (SAVEPOINT)."""

    def __init__(self, session):
        self._session = session
        self._nested = session.begin_nested()

    def rollback(self):
        try:
            self._nested.rollback()
        except Exception as e:
            log.error("Savepoint rollback failed: %s", e)

    def commit(self):
        try:
            self._nested.commit()
        except Exception as e:
            log.error("Savepoint commit failed: %s", e)
            raise
