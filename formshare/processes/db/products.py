from ...models import Products,Tasks, finishedTasks
import datetime

__all__ = [
    'addProductInstance','deleteProducts'
]

def addProductInstance(user,project,product,output,mimeType,processName,instanceID,request):
    newInstance = Products(user_name=user,project_cod=project,product_id=product,output_id=output,output_mimetype=mimeType,process_name=processName,celery_taskid=instanceID,datetime_added=datetime.datetime.now())
    newTask = Tasks(taskid=instanceID)
    try:
        request.dbsession.add(newInstance)
        request.dbsession.add(newTask)
        return True, ""
    except Exception, e:
        return False, str(e)

def deleteProducts(request, user, project, processName="ALL"):

    if processName == "ALL":
        result = request.dbsession.query(Products).filter(Products.user_name == user).filter(Products.project_cod == project).all()
    else:
        result = request.dbsession.query(Products).filter(Products.user_name == user).filter(Products.project_cod == project).filter(Products.process_name == processName).all()

    for product in result:
        request.dbsession.query(finishedTasks).filter(finishedTasks.taskid == product.celery_taskid).delete()

    request.dbsession.query(Products).filter(Products.user_name == user).filter(Products.project_cod == project).delete()