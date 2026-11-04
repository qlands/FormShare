import os

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .form_deletion import delete_form


def _sql(config, sql, params=()):
    """Runs a statement on FormShare's database: the rows of a SELECT, or
    None once anything else is committed."""
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        with engine.begin() as connection:
            result = connection.exec_driver_sql(sql, params)
            return result.fetchall() if result.returns_rows else None
    finally:
        engine.dispose()


def _access(config, project_id, form_id):
    """Who has access to a form: {assistant: (submit, clean, supervises)}
    and {group: (submit, clean, supervises)}."""
    assistants = _sql(
        config,
        "SELECT coll_uuid, coll_can_submit, coll_can_clean, coll_is_supervisor "
        "FROM formaccess WHERE form_project = %s AND form_id = %s",
        (project_id, form_id),
    )
    groups = _sql(
        config,
        "SELECT group_id, group_can_submit, group_can_clean, group_is_supervisor "
        "FROM formgrpaccess WHERE form_project = %s AND form_id = %s",
        (project_id, form_id),
    )
    return (
        {row[0]: tuple(row[1:]) for row in assistants},
        {row[0]: tuple(row[1:]) for row in groups},
    )


def t_e_s_t_form_merge_delete(test_object):
    paths = ["resources", "forms", "merge", "B", "B.xls"]
    b_resource_file = os.path.join(test_object.path, *paths)
    config = test_object.server_config

    # An assistant on the head form, for the new version to inherit
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "tormenta20201105"
        ),
        {
            "coll_id": "{}|{}|{}".format(
                test_object.projectID,
                test_object.assistantLogin,
                test_object.assistantLoginUUID,
            ),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # And a group of assistants. Both supervise the form, which only the DQ
    # plugin's page sets: the new version keeps that too
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, test_object.project, "tormenta20201105"
        ),
        {
            "group_id": test_object.assistantGroupID,
            "group_can_submit": 1,
            "group_can_clean": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    _sql(
        config,
        "UPDATE formaccess SET coll_is_supervisor = 1 "
        "WHERE form_project = %s AND form_id = %s AND coll_uuid = %s",
        (test_object.projectID, "tormenta20201105", test_object.assistantLoginUUID),
    )
    _sql(
        config,
        "UPDATE formgrpaccess SET group_is_supervisor = 1 "
        "WHERE form_project = %s AND form_id = %s AND group_id = %s",
        (test_object.projectID, "tormenta20201105", test_object.assistantGroupID),
    )

    # A new version that keeps the assistants and the files of its parent
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, test_object.project, "tormenta20201105"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "tormenta20201105",
            "keep_assistants": "",
            "keep_files": "",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" not in res.headers

    # The assistant came along: it cannot be added a second time
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        {
            "coll_id": "{}|{}|{}".format(
                test_object.projectID,
                test_object.assistantLogin,
                test_object.assistantLoginUUID,
            ),
            "coll_can_submit": "1",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # The group came along too, and both with what they may do: groups used
    # to be left behind (2026-11-03)
    kept = _access(config, test_object.projectID, "tormenta20201117")
    assert kept == _access(config, test_object.projectID, "tormenta20201105")
    assert kept[0][test_object.assistantLoginUUID] == (1, 1, 1)
    assert kept[1][test_object.assistantGroupID] == (1, 1, 1)

    # So did the files: the same file is refused without overwrite
    paths = ["resources", "forms", "merge", "B", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" in res.headers

    # Delete this version, the assistant and the group, then start over
    # without them
    res = delete_form(test_object, test_object.project, "tormenta20201117")
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistant/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201105",
            test_object.assistantLoginUUID,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/group/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "tormenta20201105",
            test_object.assistantGroupID,
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, test_object.project, "tormenta20201105"
        ),
        {
            "for_merging": "",
            "parent_project": test_object.projectID,
            "parent_form": "tormenta20201105",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Merge check pending" in res.body)

    paths = ["resources", "forms", "merge", "B", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    paths = ["resources", "forms", "merge", "B", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertFalse(b"Merge check pending" in res.body)

    res = delete_form(test_object, test_object.project, "tormenta20201117")
