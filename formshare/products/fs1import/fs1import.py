from formshare.products import register_product_instance
from formshare.products.fs1import.celery_task import import_json_files


def formshare_one_import_json(
    request,
    user,
    project,
    form,
    odk_dir,
    form_directory,
    schema,
    assistant,
    path_to_files,
    project_code,
    geopoint_variables,
    project_of_assistant,
    ignore_xform_check=False,
):

    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value

    task = import_json_files.apply_async(
        (
            user,
            project,
            form,
            odk_dir,
            form_directory,
            schema,
            assistant,
            path_to_files,
            project_code,
            geopoint_variables,
            project_of_assistant,
            settings,
            request.locale_name,
            ignore_xform_check,
        ),
        queue="FormShare",
    )
    register_product_instance(
        request, user, project, form, "fs1import", task.id, None, None, True
    )
