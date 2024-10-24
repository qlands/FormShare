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
    save_point = request.tm.savepoint()
    try:
        request.dbsession.add(new_settings)
        request.dbsession.flush()
    except IntegrityError:
        save_point.rollback()
        log.error("Duplicated setting key {}".format(key))
        return (
            False,
            _("Error storing setting for key {}. The key already exits.".format(key)),
        )
    except Exception as e:
        save_point.rollback()
        log.error("Error {} while while storing key {}".format(str(e), key))
        return False, str(e)


def update_settings(request, key, value):
    try:
        json.dumps(value)
    except Exception as e:
        return False, str(e)

    request.dbsession.query(Settings).filter(Settings.settings_key == key).update(
        {"settings_value": value}
    )


def delete_settings(request, key):
    request.dbsession.query(Settings).filter(Settings.settings_key == key).delete()


def get_settings(request, key):
    res = request.dbsession.query(Settings).filter(Settings.settings_key == key).first()
    if res is not None:
        return res.settings_value
    else:
        return {}
