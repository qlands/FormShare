import os
import formshare.products as p
from formshare.processes.db import add_task
import logging

log = logging.getLogger(__name__)


def create_product_directory(request, project, form, product):
    try:
        if p.product_found(product):
            path = os.path.join(request.registry.settings['repository.path'], *['products', project, form, product])
            if not os.path.exists(path):
                os.makedirs(path)
                output_path = os.path.join(path, "outputs")
                os.makedirs(output_path)
                return path
            else:
                return get_product_directory(request, project, product)
        else:
            return None
    except Exception as e:
        log.error("Unable to create product directory for product {} in project {} form {}. Error: {}".
                  format(product, project, form, str(e)))
        return None


def get_product_directory(request, project, form, product):
    try:
        if p.product_found(product):
            path = os.path.join(request.registry.settings['repository.path'], *['products', project, form, product])
            return path
        else:
            return None
    except Exception as e:
        log.error(
            "Unable to retrieve product directory for product {} in project {} form {}. Error: {}".
                format(product, project, form, str(e)))
        return None


def add_product(name, description):
    return {"name": name, "description": description, "metadata": {}}


def add_metadata_to_product(product, key, value):
    try:
        product["metadata"][key] = value
        return True, product
    except Exception as e:
        log.error(
            "Unable to add metadata to product {}. Key: {}. Value {}. Error: {}".format(product, key, value, str(e)))
        return False, product


def register_product_instance(request, project, form, product, output, mime_type, process_name, instance_id,
                              process_only=False):
    p.register_product_instance(request, project, form, product, output, mime_type, process_name, instance_id,
                                process_only)


def get_products():
    return p.get_products()


def register_celery_task(request, task_id):
    add_task(request, task_id)


def register_products():
    products = []
    # A new product
    new_product = add_product('fs1import', 'Import JSON data from FormShare 1.0')
    add_metadata_to_product(new_product, 'author', 'QLands Technology Consultants')
    add_metadata_to_product(new_product, 'version', '1.0')
    add_metadata_to_product(new_product, 'Licence', 'LGPL')
    products.append(new_product)

    return products
