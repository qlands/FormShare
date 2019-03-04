from formshare.products.formshare_products import register_product_instance
from .celery_task import import_json_files
from formshare.processes.db import get_project_code_from_id, get_form_geopoint, get_project_from_assistant


def formshare_one_import_json(request, user, project, form, odk_dir, form_directory, schema, assistant, path_to_files):
    project_code = get_project_code_from_id(request, user, project)
    geopoint_variable = get_form_geopoint(request, project, form)
    project_of_assistant = get_project_from_assistant(request, user, project, assistant)

    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    task = import_json_files.delay(user, project, form, odk_dir, form_directory, schema, assistant, path_to_files,
                                   project_code, geopoint_variable, project_of_assistant, settings)
    register_product_instance(request, project, form, 'fs1import', '', '', 'fs1import', task.id, True)
