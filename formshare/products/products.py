from ..processes import addProductInstance,getRunningTasksByProcess,cancelTask, deleteProducts
from climmob.config.celery_app import celeryApp

__all__ = [
    'addProduct','registerProductInstance','product_found', 'getProducts','stopTasksByProcess'
]

_PRODUCTS = []

def product_found(name):
    for product in _PRODUCTS:
        if product["name"] == name:
            return True
    return False

def output_found(product,output):
    for p in _PRODUCTS:
        if p["name"] == product:
            for o in p["outputs"]:
                if o["filename"] == output:
                    return True
    return False

def addProduct(product):
    if not product_found(product["name"]):
        #if product["outputs"]:
        _PRODUCTS.append(product)
        #else:
        #    raise Exception("The products {} does not have outputs".format(product["name"]))
    else:
        raise Exception("Product name {} is already in use".format(product["name"]))

def registerProductInstance(user,project,product,output,mimeType,processName,instanceID,request):
    if product_found(product):
        addProductInstance(user,project,product,output,mimeType,processName,instanceID,request)

def getProducts():
    return list(_PRODUCTS)

def stopTasksByProcess(request,user,project, processName="ALL"):
    tasks = getRunningTasksByProcess(request,user,project,processName)
    for task in tasks:
        print "*****stopTasksByProcess. Revoking task " + task
        celeryApp.control.revoke(task, terminate=True)
        print "*****stopTasksByProcess. Cancelling task from database " + task
        cancelTask(request,task)

    deleteProducts(request,user, project, processName)






