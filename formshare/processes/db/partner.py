import logging
from formshare.processes.color_hash import ColorHash
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from formshare.processes.db.form import (
    form_has_subversion,
    get_form_data,
    get_number_of_submissions_in_database,
    get_last_clean_info,
)
from formshare.models import (
    map_to_schema,
    Partner,
    map_from_schema,
    PartnerProject,
    PartnerForm,
    Project,
    Odkform,
    Userproject,
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
    "get_projects_and_forms_by_partner",
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


def get_form_color(form_id, form_color):
    color = ColorHash(form_id)
    if form_color is None:
        return color.hex
    else:
        return form_color


def get_date(time_bound, date_time):
    if time_bound == 1:
        return date_time.date()
    else:
        return None


def get_projects_and_forms_by_partner(request, partner_id):
    res = (
        request.dbsession.query(PartnerProject, Project, Userproject, Odkform)
        .filter(PartnerProject.project_id == Project.project_id)
        .filter(PartnerProject.project_id == Odkform.project_id)
        .filter(PartnerProject.project_id == Userproject.project_id)
        .filter(Userproject.access_type == 1)
        .filter(PartnerProject.partner_id == partner_id)
        .filter(Odkform.form_schema.isnot(None))
        .all()
    )
    res = map_from_schema(res)
    projects_and_forms = []
    for a_form in res:
        project_found = None
        for a_project in projects_and_forms:
            if a_project["project_id"] == a_form["project_id"]:
                project_found = a_project
                break
        if project_found is None:
            projects_and_forms.append(
                {
                    "project_id": a_form["project_id"],
                    "project_code": a_form["project_code"],
                    "project_name": a_form["project_name"],
                    "project_abstract": a_form["project_abstract"],
                    "time_bound": a_form["time_bound"],
                    "access_from": get_date(
                        a_form["time_bound"], a_form["access_from"]
                    ),
                    "access_to": get_date(a_form["time_bound"], a_form["access_to"]),
                    "project_access": True,
                    "project_forms": [
                        {
                            "form_id": a_form["form_id"],
                            "form_name": a_form["form_name"],
                            "form_cdate": a_form["form_cdate"],
                            "form_schema": a_form["form_schema"],
                            "form_accsub": a_form["form_accsub"],
                            "form_geopoint": a_form["form_geopoint"],
                            "form_casetype": a_form["form_casetype"],
                            "has_sub_version": form_has_subversion(
                                request,
                                a_form["user_id"],
                                a_form["project_id"],
                                a_form["form_id"],
                            ),
                            "parent_form": a_form["parent_form"],
                            "parent_form_data": get_form_data(
                                request, a_form["parent_project"], a_form["parent_form"]
                            ),
                            "stats": get_number_of_submissions_in_database(
                                request, a_form["project_id"], a_form["form_id"]
                            ),
                            "form_target": a_form["form_target"],
                            "clean_stats": get_last_clean_info(
                                request, a_form["project_id"], a_form["form_id"]
                            ),
                            "_xid_color": get_form_color(
                                a_form["form_id"], a_form["form_hexcolor"]
                            ),
                            "time_bound": 0,
                            "access_from": None,
                            "access_to": None,
                        }
                    ],
                }
            )
        else:
            project_found["project_forms"].append(
                {
                    "form_id": a_form["form_id"],
                    "form_name": a_form["form_name"],
                    "form_cdate": a_form["form_cdate"],
                    "form_schema": a_form["form_schema"],
                    "form_accsub": a_form["form_accsub"],
                    "form_geopoint": a_form["form_geopoint"],
                    "form_casetype": a_form["form_casetype"],
                    "has_sub_version": form_has_subversion(
                        request,
                        a_form["user_id"],
                        a_form["project_id"],
                        a_form["form_id"],
                    ),
                    "parent_form": a_form["parent_form"],
                    "parent_form_data": get_form_data(
                        request, a_form["parent_project"], a_form["parent_form"]
                    ),
                    "stats": get_number_of_submissions_in_database(
                        request, a_form["project_id"], a_form["form_id"]
                    ),
                    "form_target": a_form["form_target"],
                    "clean_stats": get_last_clean_info(
                        request, a_form["project_id"], a_form["form_id"]
                    ),
                    "_xid_color": get_form_color(
                        a_form["form_id"], a_form["form_hexcolor"]
                    ),
                    "time_bound": 0,
                    "access_from": None,
                    "access_to": None,
                }
            )

    res = (
        request.dbsession.query(PartnerForm, Odkform, Project, Userproject)
        .filter(PartnerForm.project_id == Odkform.project_id)
        .filter(PartnerForm.form_id == Odkform.form_id)
        .filter(Odkform.project_id == Project.project_id)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.access_type == 1)
        .filter(PartnerForm.partner_id == partner_id)
        .filter(Odkform.form_schema.isnot(None))
        .all()
    )
    res = map_from_schema(res)

    for a_form in res:
        project_found = None
        for a_project in projects_and_forms:
            if a_project["project_id"] == a_form["project_id"]:
                project_found = a_project
                break
        if project_found is None:
            projects_and_forms.append(
                {
                    "project_id": a_form["project_id"],
                    "project_code": a_form["project_code"],
                    "project_name": a_form["project_name"],
                    "project_abstract": a_form["project_abstract"],
                    "access_from": None,
                    "access_to": None,
                    "time_bound": 0,
                    "project_access": False,
                    "project_forms": [
                        {
                            "form_id": a_form["form_id"],
                            "form_name": a_form["form_name"],
                            "form_cdate": a_form["form_cdate"],
                            "form_schema": a_form["form_schema"],
                            "form_accsub": a_form["form_accsub"],
                            "form_geopoint": a_form["form_geopoint"],
                            "form_casetype": a_form["form_casetype"],
                            "has_sub_version": form_has_subversion(
                                request,
                                a_form["user_id"],
                                a_form["project_id"],
                                a_form["form_id"],
                            ),
                            "parent_form": a_form["parent_form"],
                            "parent_form_data": get_form_data(
                                request, a_form["parent_project"], a_form["parent_form"]
                            ),
                            "stats": get_number_of_submissions_in_database(
                                request, a_form["project_id"], a_form["form_id"]
                            ),
                            "form_target": a_form["form_target"],
                            "clean_stats": get_last_clean_info(
                                request, a_form["project_id"], a_form["form_id"]
                            ),
                            "_xid_color": get_form_color(
                                a_form["form_id"], a_form["form_hexcolor"]
                            ),
                            "time_bound": a_form["time_bound"],
                            "access_from": get_date(
                                a_form["time_bound"], a_form["access_from"]
                            ),
                            "access_to": get_date(
                                a_form["time_bound"], a_form["access_to"]
                            ),
                        }
                    ],
                }
            )
        else:
            a_child_form_found = None
            for a_child_form in project_found["project_forms"]:
                if a_child_form["form_id"] == a_form["form_id"]:
                    a_child_form_found = a_child_form
                    break
            if a_child_form_found is None:
                project_found["project_forms"].append(
                    {
                        "form_id": a_form["form_id"],
                        "form_name": a_form["form_name"],
                        "form_cdate": a_form["form_cdate"],
                        "form_schema": a_form["form_schema"],
                        "form_accsub": a_form["form_accsub"],
                        "form_geopoint": a_form["form_geopoint"],
                        "form_casetype": a_form["form_casetype"],
                        "has_sub_version": form_has_subversion(
                            request,
                            a_form["user_id"],
                            a_form["project_id"],
                            a_form["form_id"],
                        ),
                        "parent_form": a_form["parent_form"],
                        "parent_form_data": get_form_data(
                            request, a_form["parent_project"], a_form["parent_form"]
                        ),
                        "stats": get_number_of_submissions_in_database(
                            request, a_form["project_id"], a_form["form_id"]
                        ),
                        "form_target": a_form["form_target"],
                        "clean_stats": get_last_clean_info(
                            request, a_form["project_id"], a_form["form_id"]
                        ),
                        "_xid_color": get_form_color(
                            a_form["form_id"], a_form["form_hexcolor"]
                        ),
                        "time_bound": a_form["time_bound"],
                        "access_from": get_date(
                            a_form["time_bound"], a_form["access_from"]
                        ),
                        "access_to": get_date(
                            a_form["time_bound"], a_form["access_to"]
                        ),
                    }
                )
            else:
                a_child_form_found["time_bound"] = a_form["time_bound"]
                a_child_form_found["access_from"] = get_date(
                    a_form["time_bound"], a_form["access_from"]
                )
                a_child_form_found["access_to"] = get_date(
                    a_form["time_bound"], a_form["access_to"]
                )
    return projects_and_forms
