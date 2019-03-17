from formshare.products.formshare_products import register_product_instance
from .celery_task import import_json_files


def formshare_one_import_json(request, user, project, form, odk_dir, form_directory, schema, assistant, path_to_files,
                              project_code, geopoint_variable, project_of_assistant, ignore_xform_check=False):

    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    task = import_json_files.delay(user, project, form, odk_dir, form_directory, schema, assistant, path_to_files,
                                   project_code, geopoint_variable, project_of_assistant, settings, ignore_xform_check,
                                   sse_project_id=project, sse_form_id=form)
    register_product_instance(request, project, form, 'fs1import', '', '', 'fs1import', task.id, True)
