import datetime
import json
import logging
import uuid

from celery.app.task import Task
from sqlalchemy import create_engine

from formshare.config.celery_app import get_ini_value

log = logging.getLogger("formshare")


def send_sse_event(connection, task_id, task_name, message):
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


class CeleryTask(Task):
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
        return Task.apply_async(
            self, args, kwargs, task_id, producer, link, link_error, shadow, **options
        )
