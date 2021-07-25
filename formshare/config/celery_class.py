import datetime
import json
import logging
import smtplib
import uuid
from email.mime.text import MIMEText
from email.utils import formatdate

from celery.contrib.abortable import AbortableTask
from celery.worker.request import Request
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from formshare.config.celery_app import get_ini_value

log = logging.getLogger("formshare")


def send_timeout_email(
    settings, email_from, email_to, subject, message, reply_to
):  # pragma: no cover
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


def send_timeout_error(task_id):  # pragma: no cover
    settings = {
        "mail.from": get_ini_value("mail.from"),
        "mail.error": get_ini_value("mail.error"),
        "mail.server": get_ini_value("mail.server"),
        "mail.port": get_ini_value("mail.port"),
        "mail.ssl": get_ini_value("mail.ssl"),
        "mail.login": get_ini_value("mail.login"),
        "mail.password": get_ini_value("mail.password"),
        "mail.starttls": get_ini_value("mail.starttls"),
    }
    email_from = settings.get("mail.from", None)
    email_to = settings.get("mail.error", None)
    send_timeout_email(
        settings,
        email_from,
        email_to,
        "Celery Timeout",
        "Timeout in task ID: {}".format(task_id),
        None,
    )


def send_sse_event(connection, task_id, task_name, message):  # pragma: no cover
    """
    This function send the SSE Events for the Celery Class
    :param connection: Connection to the MySQL Server
    :param task_id: Task ID
    :param task_name: Task name
    :param message: Message
    :return:
    """
    res = connection.execute(
        "SELECT count(celery_taskid) FROM product WHERE celery_taskid = '{}'".format(
            task_id
        )
    ).fetchone()
    if res[0] == 1:
        dict_body = {"task": task_id, "status": message}
        body_string = json.dumps(dict_body)
        try:
            connection.execute(
                "INSERT INTO taskmessages(message_id,celery_taskid,message_date,message_content) "
                "VALUES ('{}','{}','{}','{}')".format(
                    str(uuid.uuid4()),
                    str(task_id),
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    body_string,
                )
            )
        except Exception as e:
            log.error(
                "Error {} while registering task {} in the message queue".format(
                    str(e), task_id
                )
            )
    else:
        if message == "failure":
            log.error("Task {} with ID {} failed.".format(task_name, task_id))


class CeleryRequest(Request):  # pragma: no cover
    """
    This is the Celery Request used by all Celery decentralized processing. Out of Coverage because processes are
    executed by Celery this is not covered by the testing framework
    """

    def on_timeout(self, soft, timeout):
        super(CeleryRequest, self).on_timeout(soft, timeout)
        task_id = self.task_id
        log.error("Timeout for task {}".format(task_id))
        send_timeout_error(task_id)
        engine = create_engine(get_ini_value("sqlalchemy.url"))
        connection = engine.connect()
        if soft:
            timeout_type = "Soft"
        else:
            timeout_type = "Hard"
        try:
            connection.execute(
                "INSERT INTO finishedtask(task_id,task_enumber,task_error) "
                "VALUES ('{}','{}','{}')".format(
                    str(task_id), 2, "{} timeout".format(timeout_type)
                )
            )
        except Exception as e:
            log.error("Error {} reporting failure for task {}".format(str(e), task_id))
        send_sse_event(connection, task_id, self.name, "failure")
        connection.invalidate()
        engine.dispose()


class CeleryTask(AbortableTask):  # pragma: no cover
    """
    This is the Celery Class used by all Celery decentralized processing. Out of Coverage because processes are
    executed by Celery this is not covered by the testing framework
    """

    Request = CeleryRequest

    def run(self, *args, **kwargs):
        pass

    def on_success(self, retval, task_id, args, kwargs):
        engine = create_engine(get_ini_value("sqlalchemy.url"))
        connection = engine.connect()
        try:

            connection.execute(
                "INSERT INTO finishedtask(task_id,task_enumber) VALUES ('{}',{})".format(
                    str(task_id), 0
                )
            )
        except IntegrityError:
            pass  # Don't do anything because it was aborted
        except Exception as e:
            log.error("Error {} reporting success for task {}".format(str(e), task_id))
        send_sse_event(connection, task_id, self.name, "success")
        connection.invalidate()
        engine.dispose()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        engine = create_engine(get_ini_value("sqlalchemy.url"))
        connection = engine.connect()
        trace_back = einfo.traceback
        if trace_back is None:
            trace_back = ""
        try:
            connection.execute(
                "INSERT INTO finishedtask(task_id,task_enumber,task_error) "
                "VALUES ('{}','{}','{}')".format(
                    str(task_id), 1, trace_back.replace("'", "")
                )
            )
        except IntegrityError:
            pass  # Don't do anything because this was a timeout
        except Exception as e:
            log.error("Error {} reporting failure for task {}".format(str(e), task_id))
        send_sse_event(connection, task_id, self.name, "failure")
        connection.invalidate()
        engine.dispose()

    def apply_async(
        self,
        args=None,
        kwargs=None,
        task_id=None,
        producer=None,
        link=None,
        link_error=None,
        shadow=None,
        **options
    ):
        options["countdown"] = 2
        options["time_limit"] = 600
        options["soft_time_limit"] = 480
        options["retry"] = False
        return AbortableTask.apply_async(
            self, args, kwargs, task_id, producer, link, link_error, shadow, **options
        )
