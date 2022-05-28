import uuid
import time
import os
from .sql import get_form_details
import datetime
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


def t_e_s_t_repository(test_object):
    def mimic_create_repository():
        from formshare.products.repository.celery_task import (
            internal_create_mysql_repository,
        )

        # Adds a mimic project
        mimic_project = "mimic"
        mimic_project_id = str(uuid.uuid4())
        mimic_res = test_object.testapp.post(
            "/user/{}/projects/add".format(test_object.randonLogin),
            {
                "project_id": mimic_project_id,
                "project_code": mimic_project,
                "project_name": "Test project",
                "project_abstract": "",
                "project_icon": "",
                "project_hexcolor": "",
                "project_formlist_auth": 1,
            },
            status=302,
        )
        assert "FS_error" not in mimic_res.headers
        # Add the mimic form
        mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
        resource_file = os.path.join(test_object.path, *mimic_paths)
        mimic_res = test_object.testapp.post(
            "/user/{}/project/{}/forms/add".format(
                test_object.randonLogin, mimic_project
            ),
            {"form_pkey": "I_D"},
            status=302,
            upload_files=[("xlsx", resource_file)],
        )
        assert "FS_error" not in mimic_res.headers
        mimic_form = "LB_Sequia_MAG_20190123"

        mimic_res = test_object.testapp.post(
            "/user/{}/project/{}/assistants/add".format(
                test_object.randonLogin, mimic_project
            ),
            {
                "coll_id": "mimic000",
                "coll_password": "123",
                "coll_password2": "123",
            },
            status=302,
        )
        assert "FS_error" not in mimic_res.headers

        # Add an assistant to a form succeeds
        mimic_res = test_object.testapp.post(
            "/user/{}/project/{}/form/{}/assistants/add".format(
                test_object.randonLogin, mimic_project, mimic_form
            ),
            {
                "coll_id": "{}|{}".format(mimic_project_id, "mimic000"),
                "coll_can_submit": "1",
                "coll_can_clean": "1",
            },
            status=302,
        )
        assert "FS_error" not in mimic_res.headers

        # Test submission
        paths4 = ["resources", "forms", "mimic_complex", "submission001.xml"]
        submission_file4 = os.path.join(test_object.path, *paths4)

        paths4 = ["resources", "forms", "complex_form", "image001.png"]
        image_file4 = os.path.join(test_object.path, *paths4)

        paths4 = ["resources", "forms", "complex_form", "sample.mp3"]
        sound_file4 = os.path.join(test_object.path, *paths4)

        test_object.testapp.post(
            "/user/{}/project/{}/push".format(test_object.randonLogin, mimic_project),
            status=201,
            upload_files=[
                ("filetoupload", submission_file4),
                ("image", image_file4),
                ("sound", sound_file4),
            ],
            extra_environ=dict(FS_for_testing="true", FS_user_for_testing="mimic000"),
        )
        time.sleep(5)  # Wait for ElasticSearch to store this

        form_details = get_form_details(
            test_object.server_config, mimic_project_id, mimic_form
        )
        form_directory = form_details["form_directory"]

        form_reptask = str(uuid.uuid4())

        engine = create_engine(
            test_object.server_config["sqlalchemy.url"], poolclass=NullPool
        )
        sql = (
            "INSERT INTO product (project_id,form_id,product_id,"
            "celery_taskid,datetime_added,created_by,process_only,output_id) "
            "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
                mimic_project_id,
                mimic_form,
                "repository",
                form_reptask,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                test_object.randonLogin,
                1,
                form_reptask[-12:],
            )
        )
        engine.execute(sql)
        engine.dispose()

        form_schema = "FS_" + str(uuid.uuid4()).replace("-", "_")

        paths2 = ["resources", "forms", "mimic_complex", "create.sql"]
        create_sql = os.path.join(test_object.path, *paths2)

        paths2 = ["resources", "forms", "mimic_complex", "insert.sql"]
        insert_sql = os.path.join(test_object.path, *paths2)

        paths2 = ["resources", "forms", "mimic_complex", "create.xml"]
        create_xml = os.path.join(test_object.path, *paths2)

        paths2 = ["resources", "forms", "mimic_complex", "insert.xml"]
        insert_xml = os.path.join(test_object.path, *paths2)

        here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
        paths2 = ["mysql.cnf"]
        mysql_cnf = os.path.join(here, *paths2)

        paths2 = [test_object.server_config["repository.path"], "odk"]
        odk_dir = os.path.join(test_object.path, *paths2)

        internal_create_mysql_repository(
            test_object.server_config,
            test_object.randonLogin,
            mimic_project_id,
            mimic_project,
            mimic_form,
            odk_dir,
            form_directory,
            form_schema,
            "I_D",
            mysql_cnf,
            create_sql,
            insert_sql,
            create_xml,
            insert_xml,
            "",
            "en",
            True,
            form_reptask,
        )

    def mimic_create_repository_with_data():
        from formshare.products.repository.celery_task import (
            internal_create_mysql_repository,
        )

        # Adds a mimic2 project
        mimic_project = "mimic2"
        mimic_project_id = str(uuid.uuid4())
        mimic_res = test_object.testapp.post(
            "/user/{}/projects/add".format(test_object.randonLogin),
            {
                "project_id": mimic_project_id,
                "project_code": mimic_project,
                "project_name": "Test project",
                "project_abstract": "",
                "project_icon": "",
                "project_hexcolor": "",
                "project_formlist_auth": 1,
            },
            status=302,
        )
        assert "FS_error" not in mimic_res.headers
        # Add the mimic form
        mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
        resource_file = os.path.join(test_object.path, *mimic_paths)
        mimic_res = test_object.testapp.post(
            "/user/{}/project/{}/forms/add".format(
                test_object.randonLogin, mimic_project
            ),
            {"form_pkey": "I_D"},
            status=302,
            upload_files=[("xlsx", resource_file)],
        )
        assert "FS_error" not in mimic_res.headers
        mimic_form = "LB_Sequia_MAG_20190123"

        mimic_res = test_object.testapp.post(
            "/user/{}/project/{}/assistants/add".format(
                test_object.randonLogin, mimic_project
            ),
            {
                "coll_id": "mimic001",
                "coll_password": "123",
                "coll_password2": "123",
                "coll_prjshare": 1,
            },
            status=302,
        )
        assert "FS_error" not in mimic_res.headers

        # Add an assistant to a form succeeds
        mimic_res = test_object.testapp.post(
            "/user/{}/project/{}/form/{}/assistants/add".format(
                test_object.randonLogin, mimic_project, mimic_form
            ),
            {
                "coll_id": "{}|{}".format(mimic_project_id, "mimic001"),
                "coll_can_submit": "1",
                "coll_can_clean": "1",
            },
            status=302,
        )
        assert "FS_error" not in mimic_res.headers

        # Test submission
        paths2 = ["resources", "forms", "mimic_complex", "submission001.xml"]
        submission_file3 = os.path.join(test_object.path, *paths2)

        paths2 = ["resources", "forms", "complex_form", "image001.png"]
        image_file3 = os.path.join(test_object.path, *paths2)

        paths2 = ["resources", "forms", "complex_form", "sample.mp3"]
        sound_file3 = os.path.join(test_object.path, *paths2)

        test_object.testapp.post(
            "/user/{}/project/{}/push".format(test_object.randonLogin, mimic_project),
            status=201,
            upload_files=[
                ("filetoupload", submission_file3),
                ("image", image_file3),
                ("sound", sound_file3),
            ],
            extra_environ=dict(FS_for_testing="true", FS_user_for_testing="mimic001"),
        )
        time.sleep(5)  # Wait for ElasticSearch to store this

        form_details = get_form_details(
            test_object.server_config, mimic_project_id, mimic_form
        )
        form_directory = form_details["form_directory"]

        form_reptask = str(uuid.uuid4())

        engine = create_engine(
            test_object.server_config["sqlalchemy.url"], poolclass=NullPool
        )
        sql = (
            "INSERT INTO product (project_id,form_id,product_id,"
            "celery_taskid,datetime_added,created_by,process_only,output_id) "
            "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
                mimic_project_id,
                mimic_form,
                "repository",
                form_reptask,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                test_object.randonLogin,
                1,
                form_reptask[-12:],
            )
        )
        engine.execute(sql)
        engine.dispose()

        form_schema = "FS_" + str(uuid.uuid4()).replace("-", "_")

        paths2 = ["resources", "forms", "mimic_complex", "create.sql"]
        create_sql = os.path.join(test_object.path, *paths2)

        paths2 = ["resources", "forms", "mimic_complex", "insert.sql"]
        insert_sql = os.path.join(test_object.path, *paths2)

        paths2 = ["resources", "forms", "mimic_complex", "create.xml"]
        create_xml = os.path.join(test_object.path, *paths2)

        paths2 = ["resources", "forms", "mimic_complex", "insert.xml"]
        insert_xml = os.path.join(test_object.path, *paths2)

        here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
        paths2 = ["mysql.cnf"]
        mysql_cnf = os.path.join(here, *paths2)

        paths2 = [test_object.server_config["repository.path"], "odk"]
        odk_dir = os.path.join(test_object.path, *paths2)

        internal_create_mysql_repository(
            test_object.server_config,
            test_object.randonLogin,
            mimic_project_id,
            mimic_project,
            mimic_form,
            odk_dir,
            form_directory,
            form_schema,
            "I_D",
            mysql_cnf,
            create_sql,
            insert_sql,
            create_xml,
            insert_xml,
            "",
            "en",
            False,
            form_reptask,
        )

    def mimic_create_repository_with_data_grp():
        from formshare.products.repository.celery_task import (
            internal_create_mysql_repository,
        )

        # Adds a mimic3 project
        mimic_grp_project = "mimic3"
        mimic_grp_project_id = str(uuid.uuid4())
        mimic_res = test_object.testapp.post(
            "/user/{}/projects/add".format(test_object.randonLogin),
            {
                "project_id": mimic_grp_project_id,
                "project_code": mimic_grp_project,
                "project_name": "Test project",
                "project_abstract": "",
                "project_icon": "",
                "project_hexcolor": "",
                "project_formlist_auth": 1,
            },
            status=302,
        )
        assert "FS_error" not in mimic_res.headers
        # Add the mimic form
        mimic_paths = ["resources", "forms", "complex_form", "B.xlsx"]
        resource_file = os.path.join(test_object.path, *mimic_paths)
        mimic_res = test_object.testapp.post(
            "/user/{}/project/{}/forms/add".format(
                test_object.randonLogin, mimic_grp_project
            ),
            {"form_pkey": "I_D"},
            status=302,
            upload_files=[("xlsx", resource_file)],
        )
        assert "FS_error" not in mimic_res.headers
        mimic_form = "LB_Sequia_MAG_20190123"

        mimic_res = test_object.testapp.post(
            "/user/{}/project/{}/assistants/add".format(
                test_object.randonLogin, mimic_grp_project
            ),
            {
                "coll_id": "mimic003",
                "coll_password": "123",
                "coll_password2": "123",
                "coll_prjshare": 1,
            },
            status=302,
        )
        assert "FS_error" not in mimic_res.headers

        res3 = test_object.testapp.post(
            "/user/{}/project/{}/groups/add".format(
                test_object.randonLogin, mimic_grp_project
            ),
            {"group_desc": "Mimic group 1", "group_id": "grpmimic001"},
            status=302,
        )
        assert "FS_error" not in res3.headers

        res3 = test_object.testapp.post(
            "/user/{}/project/{}/group/{}/members".format(
                test_object.randonLogin, mimic_grp_project, "grpmimic001"
            ),
            {
                "add_assistant": "",
                "coll_id": "{}|{}".format(mimic_grp_project_id, "mimic003"),
            },
            status=302,
        )
        assert "FS_error" not in res3.headers

        # Add an group to a form succeeds
        res3 = test_object.testapp.post(
            "/user/{}/project/{}/form/{}/groups/add".format(
                test_object.randonLogin, mimic_grp_project, "LB_Sequia_MAG_20190123"
            ),
            {
                "group_id": "grpmimic001",
                "group_can_submit": 1,
                "group_can_clean": 1,
            },
            status=302,
        )
        assert "FS_error" not in res3.headers

        # Test submission
        paths5 = ["resources", "forms", "mimic_complex", "submission001.xml"]
        submission_file5 = os.path.join(test_object.path, *paths5)

        paths5 = ["resources", "forms", "complex_form", "image001.png"]
        image_file5 = os.path.join(test_object.path, *paths5)

        paths5 = ["resources", "forms", "complex_form", "sample.mp3"]
        sound_file5 = os.path.join(test_object.path, *paths5)

        test_object.testapp.post(
            "/user/{}/project/{}/push".format(
                test_object.randonLogin, mimic_grp_project
            ),
            status=201,
            upload_files=[
                ("filetoupload", submission_file5),
                ("image", image_file5),
                ("sound", sound_file5),
            ],
            extra_environ=dict(FS_for_testing="true", FS_user_for_testing="mimic003"),
        )
        time.sleep(5)  # Wait for ElasticSearch to store this

        form_details = get_form_details(
            test_object.server_config, mimic_grp_project_id, mimic_form
        )
        form_directory = form_details["form_directory"]

        form_reptask = str(uuid.uuid4())

        engine = create_engine(
            test_object.server_config["sqlalchemy.url"], poolclass=NullPool
        )
        sql = (
            "INSERT INTO product (project_id,form_id,product_id,"
            "celery_taskid,datetime_added,created_by,process_only,output_id) "
            "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}')".format(
                mimic_grp_project_id,
                mimic_form,
                "repository",
                form_reptask,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                test_object.randonLogin,
                1,
                form_reptask[-12:],
            )
        )
        engine.execute(sql)
        engine.dispose()

        form_schema = "FS_" + str(uuid.uuid4()).replace("-", "_")

        paths2 = ["resources", "forms", "mimic_complex", "create.sql"]
        create_sql = os.path.join(test_object.path, *paths2)

        paths2 = ["resources", "forms", "mimic_complex", "insert.sql"]
        insert_sql = os.path.join(test_object.path, *paths2)

        paths2 = ["resources", "forms", "mimic_complex", "create.xml"]
        create_xml = os.path.join(test_object.path, *paths2)

        paths2 = ["resources", "forms", "mimic_complex", "insert.xml"]
        insert_xml = os.path.join(test_object.path, *paths2)

        here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
        paths2 = ["mysql.cnf"]
        mysql_cnf = os.path.join(here, *paths2)

        paths2 = [test_object.server_config["repository.path"], "odk"]
        odk_dir = os.path.join(test_object.path, *paths2)

        internal_create_mysql_repository(
            test_object.server_config,
            test_object.randonLogin,
            mimic_grp_project_id,
            mimic_grp_project,
            mimic_form,
            odk_dir,
            form_directory,
            form_schema,
            "I_D",
            mysql_cnf,
            create_sql,
            insert_sql,
            create_xml,
            insert_xml,
            "",
            "en",
            False,
            form_reptask,
        )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Gets the repository page
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Gets the repository page
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Generate the repository using celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"form_pkey": "I_D", "start_stage1": ""},
        status=302,
    )
    assert "FS_error" not in res.headers

    time.sleep(60)  # Wait for Celery to finish

    # Get the details of a form. The form now should have a repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    test_object.assertTrue(b"With repository" in res.body)

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Removes a required file from a form fails as it is required by repository
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "distritos.csv",
        ),
        status=302,
    )
    assert "FS_error" in res.headers

    # Test submission storing into repository
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_repo",
        "submission001.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    time.sleep(5)  # Wait for ElasticSearch to store this

    # Test submission storing a second identical submission to mimic an incomplete submission
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_repo",
        "submission001.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "image002.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image2", image_file),
            ("sound2", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    time.sleep(5)  # Wait for ElasticSearch to store this

    # Gets the GPS Points of a project
    res = test_object.testapp.get(
        "/user/{}/project/{}/download/gpspoints".format(
            test_object.randonLogin, test_object.project
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Get GPS point of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/get/gpspoints".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Get GPS point of a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/get/gpspoints".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Gets the GPS Points of a Form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/get/gpspoints".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Test access to the dashboard
    res = test_object.testapp.get(
        "/user/{}".format(test_object.randonLogin), status=200
    )
    assert "FS_error" not in res.headers

    # Gets the details of a project
    res = test_object.testapp.get(
        "/user/{}/project/{}".format(test_object.randonLogin, test_object.project),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Test submitting the same data into the repository storing it into the logs
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_repo",
        "submission004.xml",
    ]
    submission_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file),
            ("image", image_file),
            ("sound", sound_file),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    time.sleep(5)  # Wait for ElasticSearch to store this

    # Add a second submission to test downloads
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_repo",
        "submission005.xml",
    ]
    submission_file2 = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file2 = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file2 = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file2),
            ("image", image_file2),
            ("sound", sound_file2),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    time.sleep(5)  # Wait for ElasticSearch to store this

    # Add a third submission without GPS precision
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_repo",
        "submission002.xml",
    ]
    submission_file2 = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file2 = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file2 = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file2),
            ("image", image_file2),
            ("sound", sound_file2),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )

    time.sleep(5)  # Wait for ElasticSearch to store this

    # Add a forth submission without elevation
    paths = [
        "resources",
        "forms",
        "complex_form",
        "submissions_repo",
        "submission003.xml",
    ]
    submission_file2 = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "image001.png"]
    image_file2 = os.path.join(test_object.path, *paths)

    paths = ["resources", "forms", "complex_form", "sample.mp3"]
    sound_file2 = os.path.join(test_object.path, *paths)

    test_object.testapp.post(
        "/user/{}/project/{}/push".format(test_object.randonLogin, test_object.project),
        status=201,
        upload_files=[
            ("filetoupload", submission_file2),
            ("image", image_file2),
            ("sound", sound_file2),
        ],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    time.sleep(5)  # Wait for ElasticSearch to store this
    mimic_create_repository()
    mimic_create_repository_with_data()
    mimic_create_repository_with_data_grp()
