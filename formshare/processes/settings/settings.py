import json
import logging
from formshare.processes.logging.loggerclass import SecretLogger

from formshare.models import Settings
from sqlalchemy.exc import IntegrityError

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

__all__ = ["store_settings", "update_settings", "delete_settings", "get_settings"]


def store_settings(request, key, value):
    try:
        json.dumps(value)
    except Exception as e:
        return False, str(e)
    new_settings = Settings(settings_key=key, settings_value=value)
    _ = request.translate
    try:
        request.dbsession.add(new_settings)
        request.dbsession.commit()
    except IntegrityError:
        request.dbsession.rollback()
        log.error("Duplicated setting key {}".format(key))
        return (
            False,
            _("Error storing setting for key {}. The key already exits.".format(key)),
        )
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while while storing key {}".format(str(e), key))
        return False, str(e)


def update_settings(request, key, value):
    try:
        json.dumps(value)
    except Exception as e:
        return False, str(e)
    try:
        request.dbsession.query(Settings).filter(Settings.settings_key == key).update(
            {"settings_value": value}
        )
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error updating setting for key {}. Error {}.".format(key, str(e)))


def delete_settings(request, key):
    try:
        request.dbsession.query(Settings).filter(Settings.settings_key == key).delete()
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error deleting setting for key {}. Error {}.".format(key, str(e)))


def get_settings(request, key):
    res = request.dbsession.query(Settings).filter(Settings.settings_key == key).first()
    if res is not None:
        return res.settings_value
    else:
        return {}
