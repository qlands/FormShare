import logging

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from formshare.models import (
    map_to_schema,
    Partner,
    map_from_schema,
)

__all__ = [
    "partner_exists",
    "register_partner",
    "get_partner_details",
    "partner_email_exists",
    "update_partner",
    "update_partner_password",
    "delete_partner",
]

log = logging.getLogger("formshare")


def partner_exists(request, partner_email):
    res = (
        request.dbsession.query(Partner)
        .filter(Partner.partner_email == partner_email)
        .first()
    )
    if res is None:
        return False
    return True


def register_partner(request, partner_data):
    _ = request.translate
    partner_data.pop("partner_password2", None)
    mapped_data = map_to_schema(Partner, partner_data)
    res = (
        request.dbsession.query(Partner)
        .filter(Partner.partner_email == mapped_data["partner_email"])
        .first()
    )
    if res is None:
        new_partner = Partner(**mapped_data)
        try:
            request.dbsession.add(new_partner)
            request.dbsession.flush()
            return True, ""
        except IntegrityError:
            request.dbsession.rollback()
            log.error("Duplicated partner {}".format(mapped_data["partner_email"]))
            return False, _("Partner email is already taken")
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} when inserting partner {}".format(
                    str(e), mapped_data["partner_email"]
                )
            )
            return False, str(e)
    else:
        log.error(
            "Duplicated partner with email {}".format(mapped_data["partner_email"])
        )
        return False, _("Email is invalid")


def get_partner_details(request, partner_id):
    res = (
        request.dbsession.query(Partner)
        .filter(Partner.partner_id == partner_id)
        .first()
    )
    if res is not None:
        result = map_from_schema(res)
        return result
    return {}


def partner_email_exists(request, partner_id, email):
    res = (
        request.dbsession.query(Partner)
        .filter(Partner.partner_id != partner_id)
        .filter(func.lower(Partner.partner_email) == func.lower(email))
        .first()
    )
    if res is None:
        return False
    else:
        return True


def update_partner(request, partner_id, partner_data):
    mapped_data = map_to_schema(Partner, partner_data)
    try:
        request.dbsession.query(Partner).filter(
            Partner.partner_id == partner_id
        ).update(mapped_data)
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} when updating partner {}".format(str(e), partner_id))
        return False, str(e)


def update_partner_password(request, partner_id, password):
    try:
        request.dbsession.query(Partner).filter(
            Partner.partner_id == partner_id
        ).update({"partner_password": password})
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} when changing password for partner {}".format(str(e), partner_id)
        )
        return False, str(e)


def delete_partner(request, partner_id):
    try:
        request.dbsession.query(Partner).filter(
            Partner.partner_id == partner_id
        ).delete()
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} when updating partner {}".format(str(e), partner_id))
        return False, str(e)
