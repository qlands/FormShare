import os
import uuid

from formshare.products import register_product_instance
from .celery_task import build_csv


def generate_public_csv_file(
    request,
    user,
    project,
    form,
    form_schema,
    maps_directory,
    create_xml_file,
    insert_xml_file,
):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    uid = str(uuid.uuid4())
    paths = ["products", uid + ".csv"]
    repo_dir = request.registry.settings["repository.path"]
    csv_file = os.path.join(repo_dir, *paths)
    task = build_csv.apply_async(
        (
            settings,
            maps_directory,
            create_xml_file,
            insert_xml_file,
            form_schema,
            csv_file,
            True,
            request.locale_name,
        )
    )
    register_product_instance(
        request,
        user,
        project,
        form,
        "csv_public_export",
        task.id,
        csv_file,
        "text/csv",
        False,
        True,
    )


def generate_private_csv_file(
    request,
    user,
    project,
    form,
    form_schema,
    maps_directory,
    create_xml_file,
    insert_xml_file,
):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    uid = str(uuid.uuid4())
    paths = ["products", uid + ".csv"]
    repo_dir = request.registry.settings["repository.path"]
    csv_file = os.path.join(repo_dir, *paths)
    task = build_csv.apply_async(
        (
            settings,
            maps_directory,
            create_xml_file,
            insert_xml_file,
            form_schema,
            csv_file,
            False,
            request.locale_name,
        )
    )
    register_product_instance(
        request,
        user,
        project,
        form,
        "csv_private_export",
        task.id,
        csv_file,
        "text/csv",
        False,
        False,
    )
