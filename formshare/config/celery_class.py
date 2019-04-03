from celery.app.task import Task
from sqlalchemy import create_engine
from formshare.config.celery_app import get_ini_value
import uuid
import datetime
import logging
import json

log = logging.getLogger(__name__)


def send_sse_event(engine, task_id, message):
    dict_body = {'task': task_id, 'status': message}
    body_string = json.dumps(dict_body)
    engine.execute("INSERT INTO taskmessages(message_id,celery_taskid,message_date,message_content) "
                   "VALUES ('{}','{}','{}','{}')".format(str(uuid.uuid4()), str(task_id),
                                                         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                                                         body_string))


class CeleryTask(Task):
    def run(self, *args, **kwargs):
        pass

    def on_success(self, retval, task_id, args, kwargs):
        engine = create_engine(get_ini_value('sqlalchemy.url'))
        try:
            engine.execute("INSERT INTO finishedtask(task_id,task_enumber) VALUES ('{}',{})".format(str(task_id), 0))
        except Exception as e:
            log.error("Error {} reporting success for task {}").format(str(e), task_id)
        send_sse_event(engine, task_id, "success")
        engine.dispose()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        engine = create_engine(get_ini_value('sqlalchemy.url'))
        trace_back = einfo.traceback
        if trace_back is None:
            trace_back = ""
        try:
            engine.execute(
                "INSERT INTO finishedtask(task_id,task_enumber,task_error) "
                "VALUES ('{}','{}','{}')".format(str(task_id), 1, trace_back.replace("'", "")))
        except Exception as e:
            log.error("Error {} reporting failure for task {}").format(str(e), task_id)
        send_sse_event(engine, task_id, "failure")
        engine.dispose()
