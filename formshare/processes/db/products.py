from ...models import Product, FinishedTask, map_from_schema
from formshare.processes.db.celery import get_task_status
import datetime
import logging

__all__ = [
    'add_product_instance', 'delete_product', 'get_form_used_products', 'get_form_outputs',
    'get_form_processing_products']

log = logging.getLogger(__name__)


def add_product_instance(request, user, project, form, product, task, output_file, file_mime, process_only=False):
    if not process_only:
        process_only_int = 0
    else:
        process_only_int = 1
        output_file = None
        file_mime = None
    new_instance = Product(project_id=project, form_id=form, product_id=product, output_file=output_file,
                           output_mimetype=file_mime, celery_taskid=task, datetime_added=datetime.datetime.now(),
                           created_by=user, output_id=task[-12:], process_only=process_only_int)
    try:
        request.dbsession.add(new_instance)
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while adding product instance".format(str(e)))
        return False, str(e)


def delete_product(request, task):
        request.dbsession.query(Product).filter(Product.celery_taskid == task).delete()
        request.dbsession.query(FinishedTask).filter(FinishedTask.task_id == task).delete()


def get_form_used_products(request, project, form):
    products = []
    res = request.dbsession.query(Product).distinct(Product.product_id).filter(Product.project_id == project).filter(
        Product.form_id == form).all()
    for product in res:
        products.append({'code': product.product_id})
    return products


def get_form_processing_products(request, project, form, repository_task):
    finished_tasks = request.dbsession.query(FinishedTask.task_id)
    if repository_task is not None:
        processing_products = request.dbsession.query(Product).filter(Product.project_id == project).filter(
            Product.form_id == form).filter(Product.celery_taskid != repository_task).filter(
            Product.celery_taskid.notin_(finished_tasks)).count()
    else:
        processing_products = request.dbsession.query(Product).filter(Product.project_id == project).filter(
            Product.form_id == form).filter(Product.celery_taskid.notin_(finished_tasks)).count()
    return processing_products


def get_form_outputs(request, project, form, product):
    res = request.dbsession.query(Product).filter(Product.project_id == project).filter(Product.form_id == form).filter(
        Product.product_id == product).order_by(Product.datetime_added.desc()).all()
    if res is not None:
        outputs = map_from_schema(res)
        for output in outputs:
            status, error = get_task_status(request, output['celery_taskid'])
            output['status'] = status
            output['error'] = error
        return outputs
    else:
        return []


