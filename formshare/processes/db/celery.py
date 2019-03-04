from ...models import Task, FinishedTask, Product

__all__ = [
    'add_task', 'get_running_tasks_by_process_name', 'cancel_task']


def add_task(request, task_id):
    new_task = Task(task_id=task_id)
    try:
        request.dbsession.add(new_task)
        return True, ""
    except Exception as e:
        return False, str(e)


def get_running_tasks_by_process_name(request, project, form, process_name):

    if process_name != "ALL":
        tasks = request.query(Product).filter(Product.project_id == project).filter(Product.form_id == form).filter(
            Product.process_name == process_name).filter(
            Product.celery_taskid.notin_(request.query(FinishedTask.task_id).all())).all()
        # sql = "SELECT celery_taskid FROM products WHERE user_name='"+user+"' and project_cod = '"+project+"'
        # and process_name = '" + processName + "' AND celery_taskid NOT IN (SELECT taskid FROM finishedtasks)"
    else:
        tasks = request.query(Product).filter(Product.project_id == project).filter(Product.form_id == form).filter(
            Product.celery_taskid.notin_(request.query(FinishedTask.task_id).all())).all()
        # sql = "SELECT celery_taskid FROM products WHERE user_name='" + user + "' and project_cod = '" + project +
        # "' AND celery_taskid NOT IN (SELECT taskid FROM finishedtasks)"
    # tasks = request.dbsession.execute(sql).fetchall()
    result = []
    for task in tasks:
        result.append(task.celery_taskid)
    return result


def cancel_task(request, task_id):
    new_cancelled_task = FinishedTask(task_id=task_id, task_enumber=2)
    try:
        request.dbsession.add(new_cancelled_task)
        return True, ""
    except Exception as e:
        return False, str(e)
