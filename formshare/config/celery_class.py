from celery.app.task import Task
from sqlalchemy import create_engine
from formshare.config.celery_app import get_ini_value
from formshare.processes.rabbitmq.messaging import send_task_status_to_form


class CeleryTask(Task):
    def run(self, *args, **kwargs):
        pass

    def send_sse_event(self, kwargs, task_id, status):
        """
        This function looks for sse_project_id and sse_form_id in the kwargs of the task. If both are present
        then send a message to RabbitMq with queue = formshare_sse_project_id_sse_form_id with the task id and
        whether the task was successful or failed. FormShare will monitor this queue in various places

        Creating a Celery task with this feature is very simple:
        @celeryApp.task(base=CeleryTask)
        def my_celery_task(arg1, arg2, **kwargs):

        Execute the Celery task with apply_async
        my_celery_task.apply_async(('faa','boo'),
                                   {'sse_project_id': 'the_project_id', 'sse_form_id': 'the_form_id'})

        :param kwargs: kwargs passed to the task
        :param task_id: Celery task ID
        :param status: Status of the task
        :return:
        """
        try:
            sse_project_id = None
            sse_form_id = None
            if kwargs is not None:
                for key, value in kwargs.items():
                    if key == 'sse_project_id':
                        sse_project_id = value
                    if key == 'sse_form_id':
                        sse_form_id = value
            send_task_status_to_form(sse_project_id, sse_form_id, task_id, status)

        except Exception as e:
            print(str(e))

    def on_success(self, retval, task_id, args, kwargs):
        engine = create_engine(get_ini_value('sqlalchemy.url'))
        engine.execute("INSERT INTO finishedtask(task_id,task_enumber) VALUES ('{}',{})".format(str(task_id), 0))
        engine.dispose()
        self.send_sse_event(kwargs, task_id, "success")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        engine = create_engine(get_ini_value('sqlalchemy.url'))
        trace_back = einfo.traceback
        if trace_back is None:
            trace_back = ""
        engine.execute(
            "INSERT INTO finishedtask(task_id,task_enumber,task_error) "
            "VALUES ('{}','{}','{}')".format(str(task_id), 1, trace_back.replace("'", "")))
        engine.dispose()
        self.send_sse_event(kwargs, task_id, "failure")
