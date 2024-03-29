import os

from formshare.products import register_product_instance
from formshare.products.xmlimport.celery_task import import_xml_files


def xml_import(
    request,
    user,
    project_id,
    project_code,
    form,
    assistant,
    assistant_password,
    path_to_files,
):
    _ = request.translate
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value
    task = import_xml_files.apply_async(
        (
            settings,
            user,
            project_code,
            assistant,
            assistant_password.decode(),
            path_to_files,
            request.locale_name,
        ),
        queue="FormShare",
    )

    paths = ["report.txt"]
    report_file = os.path.join(path_to_files, *paths)

    register_product_instance(
        request,
        user,
        project_id,
        form,
        "xmlimport",
        task.id,
        report_file,
        "text/plain",
        False,
        False,
        False,
        _("Report of the XML import"),
    )
