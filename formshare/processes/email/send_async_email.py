import gettext
import logging
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

from formshare.config.celery_app import celeryApp
from formshare.config.celery_class import CeleryTask

log = logging.getLogger("formshare")


@celeryApp.task(bind=True, base=CeleryTask)
def send_async_email(
    self, settings, email_from, email_to, subject, message, reply_to, locale
):
    parts = __file__.split("/processes/")
    this_file_path = parts[0] + "/locale"
    es = gettext.translation("formshare", localedir=this_file_path, languages=[locale])
    es.install()
    _ = es.gettext

    message = MIMEText(message.encode("utf-8"), "plain", "utf-8")
    message["From"] = email_from
    message["To"] = email_to
    message["Date"] = formatdate(localtime=True)
    message["Subject"] = subject
    if reply_to is not None:
        message.add_header("reply-to", reply_to)

    server = settings.get("mail.server", None)
    if server is not None:
        if server != "":
            try:
                port = settings.get("mail.port", "587")
                if port != "":
                    port = int(port)
                    ssl = settings.get("mail.ssl", "false")
                    if ssl == "false":
                        smtp = smtplib.SMTP(server, port)
                    else:
                        smtp = smtplib.SMTP_SSL(server, port)
                    login = settings.get("mail.login", None)
                    if login is not None:
                        if login != "":
                            password = settings.get("mail.password", None)
                            if password is not None:
                                if password != "":
                                    start_tls = settings.get("mail.starttls", "false")
                                    if start_tls == "true":
                                        smtp.ehlo()
                                        smtp.starttls()
                                        smtp.ehlo()
                                    smtp.login(login, password)
                                    smtp.sendmail(
                                        email_from, email_to, message.as_string()
                                    )
                                    smtp.close()

            except Exception as e:
                log.error("Error {} while sending email".format(str(e)))
