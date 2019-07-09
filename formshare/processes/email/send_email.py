import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from formshare.config.jinja_extensions import jinjaEnv, ExtendThis
from jinja2 import ext
import logging
log = logging.getLogger(__name__)


def render_template(template_filename, context):
    return jinjaEnv.get_template(template_filename).render(context)


def send_email(request, mail_to, current_password, user_dict):
    jinjaEnv.add_extension(ext.i18n)
    jinjaEnv.add_extension(ExtendThis)
    _ = request.translate
    email_from = request.registry.settings.get('mail.from', None)
    if email_from is None:
        return False
    if email_from == "":
        return False
    msg = MIMEMultipart()
    msg['From'] = email_from
    msg['To'] = mail_to
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = _("FormShare - Password request")
    text = render_template('email/recover_email.jinja2',
                           {'recovery_date': formatdate(localtime=True), 'current_password': current_password,
                            'user_dict': user_dict, '_': _})
    msg.attach(MIMEText(text.encode('utf-8'), 'plain', 'utf-8'))
    server = request.registry.settings.get('mail.server', None)
    if server is not None:
        if server != "":
            try:
                port = request.registry.settings.get('mail.port', '587')
                if port != "":
                    port = int(port)
                    smtp = smtplib.SMTP(server, port)
                    login = request.registry.settings.get('mail.login', None)
                    if login is not None:
                        if login != "":
                            password = request.registry.settings.get('mail.password', None)
                            if password is not None:
                                if password != "":
                                    start_tls = request.registry.settings.get('mail.starttls', 'false')
                                    if start_tls == 'true':
                                        smtp.ehlo()
                                        smtp.starttls()
                                        smtp.ehlo()
                                    smtp.login(login, password)
                                    smtp.sendmail(email_from, mail_to, msg.as_string())
                                    smtp.close()
                                    return True

                return False
            except Exception as e:
                log.error("Error {} while sending email".format(str(e)))
                return False
    return False
