from formshare.products import register_product_instance
from .celery_task import build_xlsx
import uuid
import os


def generate_xlsx_file(request, user, project, form, odk_dir, form_directory, form_schema, include_sensitive=False):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    uid = str(uuid.uuid4())
    paths = ['products', uid + ".xlsx"]
    repo_dir = request.registry.settings['repository.path']
    xlsx_file = os.path.join(repo_dir, *paths)

    task = build_xlsx.apply_async((settings, odk_dir, form_directory, form_schema, xlsx_file, include_sensitive),
                                  countdown=2)
    register_product_instance(request, user, project, form, 'xlsx_export', task.id, xlsx_file,
                              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', False)
