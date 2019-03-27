from ..processes.db import add_product_instance, cancel_task, task_exists
from formshare.config.celery_app import celeryApp
import logging

__all__ = [
    'add_product', 'register_product_instance', 'product_found', 'get_products', 'stop_task']

log = logging.getLogger(__name__)

_PRODUCTS = []


def product_found(name):
    for product in _PRODUCTS:
        if product["code"] == name:
            return True
    return False


def add_product(product):
    if not product_found(product["code"]):
        _PRODUCTS.append(product)
    else:
        raise Exception("Product code {} is already in use".format(product["code"]))


def register_product_instance(request, project, form, product, output, mime_type, process_name, instance_id,
                              process_only=False):
    if product_found(product):
        add_product_instance(request, project, form, product, output, mime_type, process_name, instance_id,
                             process_only)


def get_products():
    return list(_PRODUCTS)


def stop_task(request, user, project, form, task):
    if task_exists(request, project, form, task):
        log.warning("Stopping task {}".format(task))
        celeryApp.control.revoke(task, terminate=True)
        log.warning("Cancelling task {} in database ".format(task))
        return cancel_task(request, user, task)
    return False, ""

