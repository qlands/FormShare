from formshare.products import register_product_instance
from .celery_task import create_mysql_repository


def create_database_repository(
    request,
    user,
    project,
    form,
    odk_dir,
    form_directory,
    schema,
    primary_key,
    cnf_file,
    create_file,
    insert_file,
    create_xml_file,
    insert_xml_file,
    repository_string,
    discard_testing_data,
):
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value
    project_code = request.matchdict["projcode"]
    task = create_mysql_repository.apply_async(
        (
            settings,
            user,
            project,
            project_code,
            form,
            odk_dir,
            form_directory,
            schema,
            primary_key,
            cnf_file,
            create_file,
            insert_file,
            create_xml_file,
            insert_xml_file,
            repository_string,
            request.locale_name,
            discard_testing_data,
        )
    )
    register_product_instance(
        request, user, project, form, "repository", task.id, None, None, True
    )
    return task.id
