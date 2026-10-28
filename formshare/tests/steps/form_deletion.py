"""Deleting a form from a step (owner, 2026-10-28;
processes/db/form_deletion.py). The form's ID is typed, and the deletion
runs in the worker: a step that needs the form gone waits for it, and one
that looks at a refusal reads it at once."""

import time

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

WAIT_SECONDS = 180


def confirmed(form_id, data=None):
    """What the page posts to delete a form: its ID, typed."""
    data = dict(data or {})
    data["confirm_form_id"] = form_id
    return data


def deletion_state(config, login, project_code, form_id):
    """(form_deleting, form_deleteerror) of a form, or None once it is gone."""
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        row = engine.execute(
            "SELECT f.form_deleting, f.form_deleteerror FROM odkform f "
            "JOIN project p ON p.project_id = f.project_id "
            "JOIN userproject u ON u.project_id = f.project_id "
            "AND u.access_type = 1 "
            "WHERE u.user_id = %s AND p.project_code = %s AND f.form_id = %s",
            (login, project_code, form_id),
        ).fetchone()
        return tuple(row) if row is not None else None
    finally:
        engine.dispose()


def wait_until_deleted(config, login, project_code, form_id, seconds=WAIT_SECONDS):
    """Waits for the worker to delete a form, and fails on a deletion that
    stopped."""
    deadline = time.time() + seconds
    while True:
        state = deletion_state(config, login, project_code, form_id)
        if state is None:
            return
        assert state[1] is None, "The deletion of {} stopped: {}".format(
            form_id, state[1]
        )
        assert time.time() < deadline, "{} is still being deleted".format(form_id)
        time.sleep(0.5)


def delete_form(test_object, project_code, form_id, login=None, wait=True, **kwargs):
    """Deletes a form as the page does, and by default waits for it to go."""
    login = login or test_object.randonLogin
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(login, project_code, form_id),
        confirmed(form_id),
        status=302,
        **kwargs
    )
    assert "FS_error" not in res.headers
    if wait:
        wait_until_deleted(test_object.server_config, login, project_code, form_id)
    return res


def refused_deletion(test_object, project_code, form_id, login=None):
    """Posts a deletion the step expects refused, the ID typed, and returns
    the page it goes back to, which says why. A page shows the first error
    queued and drops the rest, so the queue is emptied first."""
    login = login or test_object.randonLogin
    test_object.testapp.get("/user/{}/project/{}".format(login, project_code))
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/delete".format(login, project_code, form_id),
        confirmed(form_id),
        status=302,
    )
    assert "FS_error" in res.headers
    return res.follow()
