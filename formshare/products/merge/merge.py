from formshare.processes.odk.api import get_odk_path
from formshare.processes.db import block_forms_with_schema
import os
from formshare.products import register_product_instance
from formshare.products.merge.celery_task import merge_into_repository


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
    survey_data_columns,
):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value
    project_code = request.matchdict["projcode"]
    odk_dir = get_odk_path(request)
    b_create_xml_file = os.path.join(
        odk_dir, *["forms", b_form_directory, "repository", "create.xml"]
    )
    block_forms_with_schema(request, b_schema_name)
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
            survey_data_columns,
        ),
        queue="FormShare",
    )
    register_product_instance(
        request, user, project_id, a_form_id, "merge_form", task.id, None, None, True
    )
    return task.id
