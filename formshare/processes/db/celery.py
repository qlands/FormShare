from ...models import Task, FinishedTask, Product
import datetime

__all__ = [
    'add_task', 'cancel_task', 'get_task_status', 'task_exists']


def add_task(request, task_id):
    new_task = Task(task_id=task_id)
    try:
        request.dbsession.add(new_task)
        return True, ""
    except Exception as e:
        return False, str(e)


def cancel_task(request, user, task_id):
    new_cancelled_task = FinishedTask(task_id=task_id, task_enumber=-2, task_error="Task canceled by {} on {}".
                                      format(user, datetime.datetime.now().isoformat()))
    try:
        request.dbsession.add(new_cancelled_task)
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        return False, str(e)


def task_exists(request, project, form, task):
    res = request.dbsession.query(Product).filter(Product.project_id == project).filter(Product.form_id == form).\
        filter(Product.celery_taskid == task).first()
    if res is None:
        return False
    return True


def get_task_status(request, task_id):
    res = request.dbsession.query(FinishedTask).filter(FinishedTask.task_id == task_id).first()
    if res is not None:
        return res.task_enumber, res.task_error
    else:
        return -1, ""
