import datetime
import logging
import os

from formshare.models import Product, FinishedTask, map_from_schema
from formshare.processes.db.celery import get_task_status
from sqlalchemy import func

__all__ = [
    "add_product_instance",
    "delete_product",
    "get_form_used_products",
    "get_form_outputs",
    "get_form_processing_products",
    "get_product_output",
    "update_download_counter",
    "set_output_public_state",
    "output_exists",
]

log = logging.getLogger("formshare")


def add_product_instance(
    request,
    user,
    project,
    form,
    product,
    task,
    output_file,
    file_mime,
    process_only=False,
    publishable=False,
    report_updates=True,
    product_description=None,
):
    if not process_only:
        process_only_int = 0
    else:
        process_only_int = 1
        output_file = None
        file_mime = None
    if publishable:
        publishable = 1
    else:
        publishable = 0
    if report_updates:
        report_updates = 1
    else:
        report_updates = 0
    new_instance = Product(
        project_id=project,
        form_id=form,
        product_id=product,
        output_file=output_file,
        output_mimetype=file_mime,
        celery_taskid=task,
        datetime_added=datetime.datetime.now(),
        created_by=user,
        output_id=task[-12:],
        process_only=process_only_int,
        publishable=publishable,
        report_updates=report_updates,
        product_desc=product_description,
    )
    try:
        request.dbsession.add(new_instance)
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while adding product instance".format(str(e)))
        return False, str(e)


def delete_product(request, project, form, product, output):
    _ = request.translate
    res = (
        request.dbsession.query(Product)
        .filter(Product.project_id == project)
        .filter(Product.form_id == form)
        .filter(Product.product_id == product)
        .filter(Product.output_id == output)
        .one()
    )
    if res is not None:
        file_deleted = False
        try:
            os.remove(res.output_file)
            file_deleted = True
        except Exception as e:
            if os.path.exists(res.output_file):
                log.error(
                    "Unable to delete file {} for product {} output ()".format(
                        str(e), product, output
                    )
                )
            else:
                file_deleted = True
        if file_deleted:
            try:
                request.dbsession.query(Product).filter(
                    Product.project_id == project
                ).filter(Product.form_id == form).filter(
                    Product.product_id == product
                ).filter(
                    Product.output_id == output
                ).delete()
                request.dbsession.flush()
                return True, ""
            except Exception as e:
                request.dbsession.rollback()
                log.error(
                    "Error {} while updating setting public access for product {} output ()".format(
                        str(e), product, output
                    )
                )
                return False, str(e)
        else:
            return False, _("Unable to delete product file")
    else:
        return False, _("The output does not exist")


def get_form_used_products(request, project, form):
    products = []
    res = (
        request.dbsession.query(Product.product_id, func.max(Product.datetime_added))
        .filter(Product.project_id == project)
        .filter(Product.form_id == form)
        .group_by(Product.product_id)
        .order_by(func.max(Product.datetime_added).desc())
        .all()
    )
    for product in res:
        products.append({"code": product.product_id})
    return products


def get_form_processing_products(request, project, form, repository_task):
    finished_tasks = request.dbsession.query(FinishedTask.task_id)
    if repository_task is not None:
        processing_products = (
            request.dbsession.query(Product)
            .filter(Product.project_id == project)
            .filter(Product.form_id == form)
            .filter(Product.celery_taskid != repository_task)
            .filter(Product.celery_taskid.notin_(finished_tasks))
            .count()
        )
    else:
        processing_products = (
            request.dbsession.query(Product)
            .filter(Product.project_id == project)
            .filter(Product.form_id == form)
            .filter(Product.celery_taskid.notin_(finished_tasks))
            .count()
        )
    return processing_products


def get_form_outputs(request, project, form, product):
    res = (
        request.dbsession.query(Product)
        .filter(Product.project_id == project)
        .filter(Product.form_id == form)
        .filter(Product.product_id == product)
        .order_by(Product.datetime_added.desc())
        .all()
    )
    if res is not None:
        outputs = map_from_schema(res)
        for output in outputs:
            status, error = get_task_status(request, output["celery_taskid"])
            output["status"] = status
            output["error"] = error
        return outputs
    else:
        return []


def get_product_output(request, project, form, product, output, public=False):
    if not public:
        public = 0
    else:
        public = 1
    if output != "latest":
        res = (
            request.dbsession.query(Product)
            .filter(Product.project_id == project)
            .filter(Product.form_id == form)
            .filter(Product.product_id == product)
            .filter(Product.output_id == output)
            .filter(Product.product_published == public)
            .first()
        )
        if res is not None:
            return output, res.output_file, res.output_mimetype
        else:
            return None, None, None
    else:
        if public:
            res = (
                request.dbsession.query(Product)
                .filter(Product.project_id == project)
                .filter(Product.form_id == form)
                .filter(Product.product_id == product)
                .filter(Product.product_published == public)
                .order_by(Product.date_published.desc())
                .first()
            )
        else:
            res = (
                request.dbsession.query(Product)
                .filter(Product.project_id == project)
                .filter(Product.form_id == form)
                .filter(Product.product_id == product)
                .filter(Product.product_published == public)
                .order_by(Product.datetime_added.desc())
                .first()
            )
        if res is not None:
            return res.output_id, res.output_file, res.output_mimetype
        else:
            return None, None, None


def output_exists(request, project, form, product, output):
    res = (
        request.dbsession.query(Product)
        .filter(Product.project_id == project)
        .filter(Product.form_id == form)
        .filter(Product.product_id == product)
        .filter(Product.output_id == output)
        .first()
    )
    if res is not None:
        return True
    return False


def update_download_counter(request, project, form, product, output):
    try:
        request.dbsession.query(Product).filter(Product.project_id == project).filter(
            Product.form_id == form
        ).filter(Product.product_id == product).filter(
            Product.output_id == output
        ).update(
            {
                "downloads": Product.downloads + 1,
                "last_download": datetime.datetime.now(),
            }
        )
        request.dbsession.flush()
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while updating product download counter for product {} output ()".format(
                str(e), product, output
            )
        )
        return False, str(e)


def set_output_public_state(request, project, form, product, output, public, by):
    if not public:
        public = 0
    else:
        public = 1
    try:
        request.dbsession.query(Product).filter(Product.project_id == project).filter(
            Product.form_id == form
        ).filter(Product.product_id == product).filter(
            Product.output_id == output
        ).update(
            {
                "product_published": public,
                "date_published": datetime.datetime.now(),
                "published_by": by,
            }
        )
        request.dbsession.flush()
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while updating setting public access for product {} output ()".format(
                str(e), product, output
            )
        )
        return False, str(e)
