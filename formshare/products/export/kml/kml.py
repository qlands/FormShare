import os
import uuid

from formshare.products import register_product_instance
from formshare.products.export.kml.celery_task import build_kml


def generate_kml_file(request, user, project, form, form_schema):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    uid = str(uuid.uuid4())
    paths = ["products", uid + ".kml"]
    repo_dir = request.registry.settings["repository.path"]
    kml_file = os.path.join(repo_dir, *paths)

    task = build_kml.apply_async(
        (settings, form_schema, kml_file, request.locale_name), queue="FormShare",
    )
    register_product_instance(
        request,
        user,
        project,
        form,
        "kml_export",
        task.id,
        kml_file,
        "application/vnd.google-earth.kml+xml",
        False,
    )
