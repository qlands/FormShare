from formshare.products.deletion.celery_task import delete_form_task


def queue_form_deletion(request, project_id, form_id, task_id=None):
    """Queues the deletion of a form the request marked for deletion
    (processes/db/form_deletion.py), under the ID the request stored on the
    forms when there is one. Returns the task's ID."""
    settings = {}
    for key, value in request.registry.settings.items():
        if isinstance(value, str):
            settings[key] = value
    task = delete_form_task.apply_async(
        (settings, project_id, form_id, request.locale_name),
        queue="FormShare",
        task_id=task_id,
    )
    return task.id
