from ..processes.db import add_product_instance, get_running_tasks_by_process_name, cancel_task, delete_product
from formshare.config.celery_app import celeryApp
import logging

__all__ = [
    'add_product', 'register_product_instance', 'product_found', 'get_products', 'stop_tasks_by_process_name']

log = logging.getLogger(__name__)

_PRODUCTS = []


def product_found(name):
    for product in _PRODUCTS:
        if product["name"] == name:
            return True
    return False


def output_found(product, output):
    for p in _PRODUCTS:
        if p["name"] == product:
            for o in p["outputs"]:
                if o["filename"] == output:
                    return True
    return False


def add_product(product):
    if not product_found(product["name"]):
        _PRODUCTS.append(product)
    else:
        raise Exception("Product name {} is already in use".format(product["name"]))


def register_product_instance(request, project, form, product, output, mime_type, process_name, instance_id,
                              process_only=False):
    if product_found(product):
        add_product_instance(request, project, form, product, output, mime_type, process_name, instance_id,
                             process_only)


def get_products():
    return list(_PRODUCTS)


def stop_tasks_by_process_name(request, project, form, process_name="ALL"):
    tasks = get_running_tasks_by_process_name(request, project, form, process_name)
    for task in tasks:
        log.warning("*****stop_tasks_by_process_name. Revoking task " + task)
        celeryApp.control.revoke(task, terminate=True)
        log.warning("*****stop_tasks_by_process_name. Cancelling task from database " + task)
        cancel_task(request, task)

    delete_product(request, project, form, process_name)
