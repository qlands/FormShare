from ...models import FinishedTask, Product
import datetime
from formshare.processes.db.user import get_user_name

__all__ = ['cancel_task', 'get_task_status', 'task_exists', 'get_output_by_task']


def cancel_task(request, user, task_id):
    new_cancelled_task = FinishedTask(task_id=task_id, task_enumber=-2, task_error="Task canceled by {} on {}".
                                      format(get_user_name(request, user),
                                             datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')))
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


def get_output_by_task(request, project, form, task):
    res = request.dbsession.query(Product).filter(Product.project_id == project).filter(Product.form_id == form).\
        filter(Product.celery_taskid == task).first()
    if res is not None:
        return res.product_id, res.output_id
    return None, None


def get_task_status(request, task_id):
    res = request.dbsession.query(FinishedTask).filter(FinishedTask.task_id == task_id).first()
    if res is not None:
        return res.task_enumber, res.task_error
    else:
        return -1, ""
