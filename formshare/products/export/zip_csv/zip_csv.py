import os
import uuid

from formshare.processes.db.form import (
    get_form_xml_create_file,
)
from formshare.products import register_product_instance
from formshare.products.export.zip_csv.celery_task import build_zip_csv


def generate_public_zip_csv_file(
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
    paths = ["products", uid + ".zip"]
    repo_dir = request.registry.settings["repository.path"]
    zip_file = os.path.join(repo_dir, *paths)

    create_xml_file = get_form_xml_create_file(request, project, form)

    task = build_zip_csv.apply_async(
        (
            settings,
            odk_dir,
            form_schema,
            form,
            create_xml_file,
            request.registry.settings["auth.opaque"],
            zip_file,
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
        "zip_csv_public_export",
        task.id,
        zip_file,
        "application/zip",
        False,
        True,
    )


def generate_private_zip_csv_file(
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
    paths = ["products", uid + ".zip"]
    repo_dir = request.registry.settings["repository.path"]
    zip_file = os.path.join(repo_dir, *paths)

    create_xml_file = get_form_xml_create_file(request, project, form)

    task = build_zip_csv.apply_async(
        (
            settings,
            odk_dir,
            form_schema,
            form,
            create_xml_file,
            request.registry.settings["auth.opaque"],
            zip_file,
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
        "zip_csv_private_export",
        task.id,
        zip_file,
        "application/zip",
        False,
        False,
    )
