from ...models import Product, Task, FinishedTask
import datetime
import logging

__all__ = [
    'add_product_instance', 'delete_product']

log = logging.getLogger(__name__)


def add_product_instance(request, project, form, product, output, mime, process_name, instance, process_only=False):
    if not process_only:
        process_only_int = 0
    else:
        process_only_int = 1
    new_instance = Product(project_id=project, form_id=form, product_id=product, output_id=output, output_mimetype=mime,
                           process_name=process_name, celery_taskid=instance, datetime_added=datetime.datetime.now(),
                           process_only=process_only_int)
    new_task = Task(task_id=instance)
    try:
        request.dbsession.add(new_instance)
        request.dbsession.add(new_task)
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while adding product instance".format(str(e)))
        return False, str(e)


def delete_product(request, project, form, process_name="ALL"):
    if process_name == "ALL":
        result = request.dbsession.query(Product).filter(Product.project_id == project).filter(
            Product.form_id == form).all()
    else:
        result = request.dbsession.query(Product).filter(Product.project_id == project).filter(
            Product.form_id == form).filter(Product.process_name == process_name).all()

    for product in result:
        request.dbsession.query(FinishedTask).filter(FinishedTask.task_id == product.celery_taskid).delete()

    request.dbsession.query(Product).filter(Product.project_id == project).filter(Product.form_id == form).delete()
