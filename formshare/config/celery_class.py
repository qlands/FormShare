from celery.app.task import Task
from sqlalchemy import create_engine
from formshare.config.celery_app import get_ini_value


class CeleryTask(Task):
    def run(self, *args, **kwargs):
        pass

    def on_success(self, retval, task_id, args, kwargs):
        engine = create_engine(get_ini_value('sqlalchemy.url'))
        engine.execute("INSERT INTO finishedtask(task_id,task_enumber) VALUES ('{}',{})".format(str(task_id), 0))
        engine.dispose()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        engine = create_engine(get_ini_value('sqlalchemy.url'))
        engine.execute(
            "INSERT INTO finishedtask(task_id,task_enumber,task_error) VALUES ('{}','{}','{}')".format(str(task_id), 1,
                                                                                                       ""))
        engine.dispose()
