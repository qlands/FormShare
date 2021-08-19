import logging

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from formshare.models import (
    map_to_schema,
    Partner,
    map_from_schema,
    PartnerProject,
    PartnerForm,
)

__all__ = [
    "partner_exists",
    "register_partner",
    "get_partner_details",
    "partner_email_exists",
    "update_partner",
    "update_partner_password",
    "delete_partner",
    "add_partner_to_project",
    "get_project_partners",
    "update_partner_options",
    "remove_partner_from_project",
    "get_form_partners",
    "add_partner_to_form",
    "update_partner_form_options",
    "remove_partner_from_form",
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


def add_partner_to_project(request, link_data):
    _ = request.translate
    mapped_data = map_to_schema(PartnerProject, link_data)
    new_link = PartnerProject(**mapped_data)
    try:
        request.dbsession.add(new_link)
        request.dbsession.flush()
        return True, ""
    except IntegrityError:
        request.dbsession.rollback()
        log.error(
            "Duplicated partner {} for project {}".format(
                mapped_data["partner_id"], mapped_data["project_id"]
            )
        )
        return False, _("The partner is already linked to this project")
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} when inserting partner {} to project {}".format(
                str(e), mapped_data["partner_id"], mapped_data["project_id"]
            )
        )
        return False, str(e)


def get_project_partners(request, project_id):
    res = (
        request.dbsession.query(PartnerProject, Partner)
        .filter(PartnerProject.project_id == project_id)
        .filter(PartnerProject.partner_id == Partner.partner_id)
        .all()
    )
    res = map_from_schema(res)
    return res


def update_partner_options(request, project_id, partner_id, partner_data):
    mapped_data = map_to_schema(PartnerProject, partner_data)
    try:
        request.dbsession.query(PartnerProject).filter(
            PartnerProject.project_id == project_id
        ).filter(PartnerProject.partner_id == partner_id).update(mapped_data)
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} when updating partner {} in project {}".format(
                str(e), partner_id, project_id
            )
        )
        return False, str(e)


def remove_partner_from_project(request, project_id, partner_id):
    try:
        request.dbsession.query(PartnerProject).filter(
            PartnerProject.project_id == project_id
        ).filter(PartnerProject.partner_id == partner_id).delete()
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} when removing the partner partner {} from {}".format(
                str(e), partner_id, project_id
            )
        )
        return False, str(e)


def get_form_partners(request, project_id, form_id):
    res = (
        request.dbsession.query(PartnerForm, Partner)
        .filter(PartnerForm.project_id == project_id)
        .filter(PartnerForm.form_id == form_id)
        .filter(PartnerForm.partner_id == Partner.partner_id)
        .all()
    )
    res = map_from_schema(res)
    return res


def add_partner_to_form(request, link_data):
    _ = request.translate
    mapped_data = map_to_schema(PartnerForm, link_data)
    new_link = PartnerForm(**mapped_data)
    try:
        request.dbsession.add(new_link)
        request.dbsession.flush()
        return True, ""
    except IntegrityError:
        request.dbsession.rollback()
        log.error(
            "Duplicated partner {} for form {} in project {}".format(
                mapped_data["partner_id"],
                mapped_data["form_id"],
                mapped_data["project_id"],
            )
        )
        return False, _("The partner is already linked to this form")
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} when inserting partner {} to form {} in project {}".format(
                str(e),
                mapped_data["partner_id"],
                mapped_data["form_id"],
                mapped_data["project_id"],
            )
        )
        return False, str(e)


def update_partner_form_options(request, project_id, form_id, partner_id, partner_data):
    mapped_data = map_to_schema(PartnerForm, partner_data)
    try:
        request.dbsession.query(PartnerForm).filter(
            PartnerForm.project_id == project_id
        ).filter(PartnerForm.form_id == form_id).filter(
            PartnerForm.partner_id == partner_id
        ).update(
            mapped_data
        )
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} when updating partner {} in form {} of project {}".format(
                str(e), partner_id, form_id, project_id
            )
        )
        return False, str(e)


def remove_partner_from_form(request, project_id, form_id, partner_id):
    try:
        request.dbsession.query(PartnerForm).filter(
            PartnerForm.project_id == project_id
        ).filter(PartnerForm.form_id == form_id).filter(
            PartnerForm.partner_id == partner_id
        ).delete()
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} when removing the partner partner {} from form {} of project {}".format(
                str(e), partner_id, form_id, project_id
            )
        )
        return False, str(e)
