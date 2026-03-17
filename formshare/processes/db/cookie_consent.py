import datetime
import logging
import uuid
from formshare.processes.logging.loggerclass import SecretLogger
from formshare.models import (
    map_from_schema,
    CookieConsent,
    CookieConsentLog,
)

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

__all__ = ["get_consent_by_ip", "save_consent"]


def get_consent_by_ip(request, ip_address):
    res = (
        request.dbsession.query(CookieConsent)
        .filter(CookieConsent.consent_ip == ip_address)
        .first()
    )
    return map_from_schema(res)


def save_consent(request, ip, functional, analytical, marketing, action):
    now = datetime.datetime.now()
    existing = (
        request.dbsession.query(CookieConsent)
        .filter(CookieConsent.consent_ip == ip)
        .first()
    )
    try:
        if existing is None:
            new_consent = CookieConsent(
                consent_id=str(uuid.uuid4()),
                consent_ip=ip,
                consent_cdate=now,
                consent_udate=now,
                consent_essential=1,
                consent_functional=functional,
                consent_analytical=analytical,
                consent_marketing=marketing,
            )
            request.dbsession.add(new_consent)
        else:
            existing.consent_udate = now
            existing.consent_essential = 1
            existing.consent_functional = functional
            existing.consent_analytical = analytical
            existing.consent_marketing = marketing

        log_entry = CookieConsentLog(
            log_id=str(uuid.uuid4()),
            log_ip=ip,
            log_date=now,
            log_action=action,
            log_essential=1,
            log_functional=functional,
            log_analytical=analytical,
            log_marketing=marketing,
        )
        request.dbsession.add(log_entry)
        request.dbsession.commit()
    except Exception as e:
        log.error(
            "Unable to store cookie information for IP {}. Error:\n{}".format(
                ip, str(e)
            )
        )
        request.dbsession.rollback()
