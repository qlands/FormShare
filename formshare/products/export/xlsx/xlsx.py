import os
import uuid

from formshare.processes.db.form import (
    get_form_xml_create_file,
)
from formshare.products import register_product_instance
from formshare.products.export.xlsx.celery_task import build_xlsx


def generate_public_xlsx_file(
    request,
    user,
    project,
    form,
    odk_dir,
    form_schema,
    options=1,
    include_multiselect=False,
    include_lookups=False,
):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    uid = str(uuid.uuid4())
    paths = ["products", uid + ".xlsx"]
    repo_dir = request.registry.settings["repository.path"]
    xlsx_file = os.path.join(repo_dir, *paths)

    create_xml_file = get_form_xml_create_file(request, project, form)

    task = build_xlsx.apply_async(
        (
            settings,
            odk_dir,
            form_schema,
            create_xml_file,
            request.registry.settings["auth.opaque"],
            xlsx_file,
            True,
            request.locale_name,
            options,
            include_multiselect,
            include_lookups,
        ),
        queue="FormShare",
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
    request,
    user,
    project,
    form,
    odk_dir,
    form_schema,
    options=1,
    include_multiselect=False,
    include_lookups=False,
):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    uid = str(uuid.uuid4())
    paths = ["products", uid + ".xlsx"]
    repo_dir = request.registry.settings["repository.path"]
    xlsx_file = os.path.join(repo_dir, *paths)

    create_xml_file = get_form_xml_create_file(request, project, form)

    task = build_xlsx.apply_async(
        (
            settings,
            odk_dir,
            form_schema,
            create_xml_file,
            request.registry.settings["auth.opaque"],
            xlsx_file,
            False,
            request.locale_name,
            options,
            include_multiselect,
            include_lookups,
        ),
        queue="FormShare",
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
