from celery.app.task import Task
from sqlalchemy import create_engine
from formshare.config.celery_app import get_ini_value
import pika


class CeleryTask(Task):
    def run(self, *args, **kwargs):
        pass

    @staticmethod
    def send_sse_event(kwargs, task_id, status):
        try:
            sse_project_id = None
            sse_form_id = None
            for key, value in kwargs.items():
                if key == 'sse_project_id':
                    sse_project_id = value
                if key == 'sse_form_id':
                    sse_form_id = value
            if sse_project_id is not None and sse_form_id is not None:
                connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
                channel = connection.channel()
                parts = ['formshare', sse_project_id, sse_form_id]
                channel.queue_declare(queue='_'.join(parts))
                channel.basic_publish(exchange='', routing_key='_'.join(parts), body="{}:{}".format(str(task_id), status))
                connection.close()
        except Exception as e:
            print(str(e))

    def on_success(self, retval, task_id, args, kwargs):
        engine = create_engine(get_ini_value('sqlalchemy.url'))
        engine.execute("INSERT INTO finishedtask(task_id,task_enumber) VALUES ('{}',{})".format(str(task_id), 0))
        engine.dispose()
        self.send_sse_event(kwargs, task_id, "success")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        engine = create_engine(get_ini_value('sqlalchemy.url'))
        engine.execute(
            "INSERT INTO finishedtask(task_id,task_enumber,task_error) VALUES ('{}','{}','{}')".format(str(task_id), 1,
                                                                                                       einfo.replace(
                                                                                                           "'", "")))
        engine.dispose()
        self.send_sse_event(kwargs, task_id, "failure")
