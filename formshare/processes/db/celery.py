from ...models import Tasks,finishedTasks

__all__ = [
    'addTask','getRunningTasksByProcess','cancelTask'
]

def addTask(taskID,request):
    newTask = Tasks(taskid=taskID)
    try:
        request.dbsession.add(newTask)
        return True, ""
    except Exception, e:
        return False, str(e)

def getRunningTasksByProcess(request,user,project,processName):

    if processName != "ALL":
        sql = "SELECT celery_taskid FROM products WHERE user_name='"+user+"' and project_cod = '"+project+"' and process_name = '" + processName + "' AND celery_taskid NOT IN (SELECT taskid FROM finishedtasks)"
    else:
        sql = "SELECT celery_taskid FROM products WHERE user_name='" + user + "' and project_cod = '" + project + "' AND celery_taskid NOT IN (SELECT taskid FROM finishedtasks)"
    tasks = request.dbsession.execute(sql).fetchall()
    result = []
    for task in tasks:
        result.append(task.celery_taskid)
    return result

def cancelTask(request,taskID):
    newCancelledTask = finishedTasks(taskid=taskID,taskerror=2)
    try:
        request.dbsession.add(newCancelledTask)
        return True, ""
    except Exception, e:
        return False, str(e)