import os
import uuid
import time
from .sql import get_form_details
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import datetime


def t_e_s_t_form_merge_mimic(test_object):
    # Adds a mimic2 project
    merge_project = "mergemimic1"
    merge_project_id = str(uuid.uuid4())
    mimic_res = test_object.testapp.post(
        "/user/{}/projects/add".format(test_object.randonLogin),
        {
            "project_id": merge_project_id,
            "project_code": merge_project,
            "project_name": "Test project",
            "project_abstract": "",
            "project_icon": "",
            "project_hexcolor": "",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    paths = ["resources", "forms", "merge", "A", "A.xls"]
    a_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(test_object.randonLogin, merge_project),
        {"form_pkey": "numero_de_cedula"},
        status=302,
        upload_files=[("xlsx", a_resource_file)],
    )
    assert "FS_error" not in res.headers

    paths = ["resources", "forms", "merge", "A", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, merge_project, "tormenta20201105"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    paths = ["resources", "forms", "merge", "A", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, merge_project, "tormenta20201105"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/assistants/add".format(
            test_object.randonLogin, merge_project
        ),
        {
            "coll_id": "merge001",
            "coll_password": "123",
            "coll_password2": "123",
            "coll_prjshare": 1,
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    # Generate the repository using celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, merge_project, "tormenta20201105"
        ),
        {"form_pkey": "numero_de_cedula", "start_stage1": ""},
        status=302,
    )
    assert "FS_error" not in res.headers

    time.sleep(60)  # Wait for celery to generate the repository

    # Upload B***********************************************

    paths = ["resources", "forms", "merge", "B", "B.xls"]
    b_resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/merge".format(
            test_object.randonLogin, merge_project, "tormenta20201105"
        ),
        {
            "for_merging": "",
            "parent_project": merge_project_id,
            "parent_form": "tormenta20201105",
        },
        status=302,
        upload_files=[("xlsx", b_resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, merge_project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Merge check pending" in res.body)

    paths = ["resources", "forms", "merge", "B", "cantones.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, merge_project, "tormenta20201117"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    paths = ["resources", "forms", "merge", "B", "distritos.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, merge_project, "tormenta20201117"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    mimic_res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, merge_project, "tormenta20201117"
        ),
        {
            "coll_id": "{}|{}".format(merge_project_id, "merge001"),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in mimic_res.headers

    # Upload submission 1
    paths = [
        "resources",
        "forms",
        "merge",
        "submission001.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)
    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, merge_project),
        status=201,
        upload_files=[("filetoupload", submission_file)],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing="merge001"),
    )
    time.sleep(5)  # Wait for ElasticSearch to store this

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, merge_project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertFalse(b"Merge check pending" in res.body)

    # Show the merge repository page
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/merge/into/{}".format(
            test_object.randonLogin,
            merge_project,
            "tormenta20201117",
            "tormenta20201105",
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    from formshare.products.merge.celery_task import (
        internal_merge_into_repository,
    )

    form_details_a = get_form_details(
        test_object.server_config, merge_project_id, "tormenta20201117"
    )

    form_details_b = get_form_details(
        test_object.server_config, merge_project_id, "tormenta20201105"
    )

    engine = create_engine(
        test_object.server_config["sqlalchemy.url"], poolclass=NullPool
    )
    task_id = str(uuid.uuid4())
    sql = (
        "INSERT INTO product (project_id,form_id,product_id,"
        "celery_taskid,datetime_added,created_by,process_only,output_id) "
        "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
            merge_project_id,
            "tormenta20201117",
            "merge_form",
            task_id,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            test_object.randonLogin,
            1,
            task_id[-12:],
        )
    )
    engine.execute(sql)
    engine.dispose()

    internal_merge_into_repository(
        test_object.server_config,
        test_object.randonLogin,
        merge_project_id,
        merge_project,
        "tormenta20201117",
        form_details_a["form_directory"],
        form_details_b["form_directory"],
        form_details_b["form_createxmlfile"],
        form_details_b["form_schema"],
        "",
        form_details_b["form_hexcolor"],
        "en",
        False,
        task_id,
    )

    # Get the details of a form tormenta20201117
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, merge_project, "tormenta20201117"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"This is the sub-version of" in res.body)

    # Get the details of a form tormenta20201105
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, merge_project, "tormenta20201105"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"is the sub-version of this form" in res.body)
