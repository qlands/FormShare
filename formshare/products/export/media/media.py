from formshare.products import register_product_instance
from .celery_task import build_media_zip
import uuid
import os


def generate_media_zip_file(request, user, project, form, odk_dir, form_directory, form_schema, primary_key):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    uid = str(uuid.uuid4())
    paths = ['products', uid + ".zip"]
    repo_dir = request.registry.settings['repository.path']
    media_file = os.path.join(repo_dir, *paths)

    task = build_media_zip.apply_async((settings, odk_dir, form_directory, form_schema, media_file, primary_key,
                                        request.locale_name), countdown=2)
    register_product_instance(request, user, project, form, 'media_export', task.id, media_file,
                              'application/zip', False)
