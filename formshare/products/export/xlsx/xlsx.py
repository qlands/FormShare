from formshare.products import register_product_instance
from .celery_task import build_xlsx
import uuid
import os


def generate_public_xlsx_file(
    request, user, project, form, odk_dir, form_directory, form_schema
):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    uid = str(uuid.uuid4())
    paths = ["products", uid + ".xlsx"]
    repo_dir = request.registry.settings["repository.path"]
    xlsx_file = os.path.join(repo_dir, *paths)

    task = build_xlsx.apply_async(
        (
            settings,
            odk_dir,
            form_directory,
            form_schema,
            form,
            xlsx_file,
            True,
            request.locale_name,
        ),
        countdown=2,
    )
    register_product_instance(
        request,
        user,
        project,
        form,
        "xlsx_public_export",
        task.id,
        xlsx_file,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        False,
        True,
    )


def generate_private_xlsx_file(
    request, user, project, form, odk_dir, form_directory, form_schema
):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    uid = str(uuid.uuid4())
    paths = ["products", uid + ".xlsx"]
    repo_dir = request.registry.settings["repository.path"]
    xlsx_file = os.path.join(repo_dir, *paths)

    task = build_xlsx.apply_async(
        (
            settings,
            odk_dir,
            form_directory,
            form_schema,
            form,
            xlsx_file,
            False,
            request.locale_name,
        ),
        countdown=2,
    )
    register_product_instance(
        request,
        user,
        project,
        form,
        "xlsx_private_export",
        task.id,
        xlsx_file,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        False,
        False,
    )
