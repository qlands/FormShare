import datetime
import logging

from jinja2 import ext

from formshare.config.jinja_extensions import jinjaEnv, ExtendThis
from formshare.plugins.helpers import readble_date
from formshare.processes.email.send_async_email import send_async_email

log = logging.getLogger("formshare")


def render_template(template_filename, context):
    return jinjaEnv.get_template(template_filename).render(context)


def send_email(request, email_from, email_to, subject, message, reply_to=None):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str) or isinstance(value, int):
            settings[key] = value

    send_async_email.apply_async(
        (
            settings,
            email_from,
            email_to,
            subject,
            message,
            reply_to,
            request.locale_name,
        ),
        queue="FormShare",
    )
    return True


def send_password_email(request, email_to, current_password, user_dict):
    jinjaEnv.add_extension(ext.i18n)
    jinjaEnv.add_extension(ExtendThis)
    _ = request.translate
    email_from = request.registry.settings.get("mail.from", None)
    if email_from is None:
        log.error(
            "FormShare has no email settings in place. Email service is disabled."
        )
        return False
    if email_from == "":
        return False
    date_string = readble_date(datetime.datetime.now(), request.locale_name)
    text = render_template(
        "email/recover_email.jinja2",
        {
            "recovery_date": date_string,
            "current_password": current_password,
            "user_dict": user_dict,
            "_": _,
        },
    )
    return send_email(
        request, email_from, email_to, _("FormShare - Password request"), text
    )


def send_error_to_technical_team(request, error_message):
    email_from = request.registry.settings.get("mail.from", None)
    email_to = request.registry.settings.get("mail.error", None)
    if email_from is not None and email_to is not None:
        return send_email(request, email_from, email_to, "500 Error", error_message)
    else:
        log.error(
            "FormShare has no email settings in place. Email service is disabled."
        )
        return False


def send_collaboration_email(
    request, email_to, reply_to, requested_by, project_name, owner, project_code
):
    jinjaEnv.add_extension(ext.i18n)
    jinjaEnv.add_extension(ExtendThis)
    _ = request.translate
    email_from = request.registry.settings.get("mail.from", None)
    if email_from is None:
        log.error(
            "FormShare has no email settings in place. Email service is disabled."
        )
        return False
    if email_from == "":
        return False

    request_url = request.route_url(
        "accept_collaboration", userid=owner, projcode=project_code
    )
    text = render_template(
        "email/collaborate_email.jinja2",
        {
            "_": _,
            "requested_by": requested_by,
            "project_name": project_name,
            "request_url": request_url,
        },
    )
    return send_email(
        request,
        email_from,
        email_to,
        _("FormShare - Request for collaboration"),
        text,
        reply_to,
    )
