from celery import Task
from sqlalchemy import create_engine
from climmob.config.celery_app import get_ini_value

class celeryTask(Task):
    def on_success(self, retval, task_id, args, kwargs):
        engine = create_engine(get_ini_value('sqlalchemy.url'))
        engine.execute("INSERT INTO finishedtasks(taskid,taskerror) VALUES ('" + str(task_id) + "',0)")
        engine.dispose()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        engine = create_engine(get_ini_value('sqlalchemy.url'))
        engine.execute("INSERT INTO finishedtasks(taskid,taskerror) VALUES ('" + str(task_id) + "',1)")
        engine.dispose()