from formshare.products import register_product_instance
from formshare.products.merge.celery_task import merge_into_repository
from formshare.processes.db.form import get_form_xml_create_file


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
    discard_testing_data,
):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value
    project_code = request.matchdict["projcode"]
    b_create_xml_file = get_form_xml_create_file(request, project_id, a_form_id)
    task = merge_into_repository.apply_async(
        (
            settings,
            user,
            project_id,
            project_code,
            a_form_id,
            a_form_directory,
            b_form_directory,
            b_create_xml_file,
            b_schema_name,
            odk_merge_string,
            b_hex_color,
            request.locale_name,
            discard_testing_data,
        )
    )
    register_product_instance(
        request, user, project_id, a_form_id, "merge_form", task.id, None, None, True
    )
    return task.id
