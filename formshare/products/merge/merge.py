from formshare.products import register_product_instance
from .celery_task import merge_into_repository


def merge_form(
    request,
    user,
    project_id,
    a_form_id,
    a_form_directory,
    b_schema_name,
    b_form_directory,
    odk_merge_string,
    b_hex_color,
):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value
    project_code = request.matchdict["projcode"]
    task = merge_into_repository.apply_async(
        (
            settings,
            user,
            project_id,
            project_code,
            a_form_id,
            a_form_directory,
            b_form_directory,
            b_schema_name,
            odk_merge_string,
            b_hex_color,
            request.locale_name,
        )
    )
    register_product_instance(
        request, user, project_id, a_form_id, "merge_form", task.id, None, None, True
    )
    return task.id
