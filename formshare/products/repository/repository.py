from formshare.products import register_product_instance
from .celery_task import create_mysql_repository


def create_database_repository(request, project, form, odk_dir, form_directory, schema, primary_key, cnf_file,
                               create_file, insert_file, audit_file):

    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value
    user_id = request.matchdict['userid']  # TODO: Maybe add this as part of the function?
    project_code = request.matchdict['projcode']

    task = create_mysql_repository.apply_async((settings, user_id, project, project_code, form, odk_dir,
                                                form_directory, schema, primary_key,
                                                cnf_file, create_file, insert_file,
                                                audit_file), {'sse_project_id': project, 'sse_form_id': form},
                                               countdown=2)
    register_product_instance(request, user_id, project, form, 'repository', task.id, None, None, True)
    return task.id
