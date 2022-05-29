import uuid
import os
from .sql import get_form_details, store_task_status, get_last_task
import datetime
import time
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


def t_e_s_t_repository_downloads(test_object):
    def mimic_celery_public_csv_process():
        from formshare.products.export.csv.celery_task import internal_build_csv

        engine = create_engine(
            test_object.server_config["sqlalchemy.url"], poolclass=NullPool
        )

        form_details = get_form_details(
            test_object.server_config, test_object.projectID, test_object.formID
        )

        paths = [
            "odk",
            "forms",
            form_details["form_directory"],
            "submissions",
            "maps",
        ]
        maps_directory = os.path.join(
            test_object.server_config["repository.path"], *paths
        )
        create_xml_file = form_details["form_createxmlfile"]
        insert_xml_file = form_details["form_insertxmlfile"]
        form_schema = form_details["form_schema"]
        task_id = str(uuid.uuid4())
        sql = (
            "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
            "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
            "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                test_object.projectID,
                test_object.formID,
                "csv_public_export",
                test_object.working_dir + "/{}.csv".format(task_id),
                "text/csv",
                task_id,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                test_object.randonLogin,
                task_id[-12:],
                0,
                1,
            )
        )
        engine.execute(sql)
        engine.dispose()
        internal_build_csv(
            test_object.server_config,
            maps_directory,
            create_xml_file,
            insert_xml_file,
            form_schema,
            test_object.working_dir + "/{}.csv".format(task_id),
            True,
            "en",
            task_id,
        )
        store_task_status(task_id, test_object.server_config)

        # Download unpublished product fails
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/public_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                task_id[-12:],
            ),
            status=404,
        )

        # Publish with not exist project goes to 404
        test_object.testapp.post(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/publish".format(
                test_object.randonLogin,
                "not_exist",
                test_object.formID,
                "csv_public_export",
                task_id[-12:],
            ),
            status=404,
        )

        # Publish with not exist output goes to 404
        test_object.testapp.post(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/publish".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                "not_exist",
            ),
            status=404,
        )

        # Publis with get goes to 404
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/publish".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                task_id[-12:],
            ),
            status=404,
        )

        # Publish the product
        res2 = test_object.testapp.post(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/publish".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                task_id[-12:],
            ),
            status=302,
        )
        assert "FS_error" not in res2.headers

        # Download published product pass
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/public_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                task_id[-12:],
            ),
            status=200,
        )

        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/public_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                "latest",
            ),
            status=200,
        )

        # Unpublish product with not exist project goes to 404
        test_object.testapp.post(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/unpublish".format(
                test_object.randonLogin,
                "not_exist",
                test_object.formID,
                "csv_public_export",
                task_id[-12:],
            ),
            status=404,
        )

        # Unpublish product with not exist output goes to 404
        test_object.testapp.post(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/unpublish".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                "not_exist",
            ),
            status=404,
        )

        # Unpublish with get goes to 404
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/unpublish".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                task_id[-12:],
            ),
            status=404,
        )

        # Unpublish the product
        res2 = test_object.testapp.post(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/unpublish".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                task_id[-12:],
            ),
            status=302,
        )
        assert "FS_error" not in res2.headers

        # Delete product goes to 404
        test_object.testapp.post(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/delete".format(
                test_object.randonLogin,
                "not_exist",
                test_object.formID,
                "csv_public_export",
                task_id[-12:],
            ),
            status=404,
        )

        # Delete product goes to 404
        test_object.testapp.post(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/delete".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                "na",
            ),
            status=404,
        )

        # Delete product goes to 404
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/delete".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                task_id[-12:],
            ),
            status=404,
        )

        # Delete the product
        res2 = test_object.testapp.post(
            "/user/{}/project/{}/form/{}/products/{}/output/{}/delete".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_public_export",
                task_id[-12:],
            ),
            status=302,
        )
        assert "FS_error" not in res2.headers

    def mimic_celery_private_csv_process():
        from formshare.products.export.csv.celery_task import internal_build_csv

        engine = create_engine(
            test_object.server_config["sqlalchemy.url"], poolclass=NullPool
        )

        form_details = get_form_details(
            test_object.server_config, test_object.projectID, test_object.formID
        )

        paths = [
            "odk",
            "forms",
            form_details["form_directory"],
            "submissions",
            "maps",
        ]
        maps_directory = os.path.join(
            test_object.server_config["repository.path"], *paths
        )
        create_xml_file = form_details["form_createxmlfile"]
        insert_xml_file = form_details["form_insertxmlfile"]

        form_schema = form_details["form_schema"]
        task_id = str(uuid.uuid4())
        test_object.product_id = task_id
        sql = (
            "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
            "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
            "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                test_object.projectID,
                test_object.formID,
                "csv_private_export",
                test_object.working_dir + "/{}.csv".format(task_id),
                "text/csv",
                task_id,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                test_object.randonLogin,
                task_id[-12:],
                0,
                1,
            )
        )
        engine.execute(sql)
        engine.dispose()
        internal_build_csv(
            test_object.server_config,
            maps_directory,
            create_xml_file,
            insert_xml_file,
            form_schema,
            test_object.working_dir + "/{}.csv".format(task_id),
            False,
            "en",
            task_id,
        )
        store_task_status(task_id, test_object.server_config)

        # Download an output that does not exist goes to 404
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_private_export",
                "not_exist",
            ),
            status=404,
        )

        # Download private product of a project that does not exist goes to 404
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                test_object.randonLogin,
                "not_exist",
                test_object.formID,
                "csv_private_export",
                task_id[-12:],
            ),
            status=404,
        )

        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_private_export",
                task_id[-12:],
            ),
            status=200,
        )
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_private_export",
                "latest",
            ),
            status=200,
        )

        # API download goes to 401. No API key
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/api_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_private_export",
                task_id[-12:],
            ),
            status=401,
        )

        # API download goes to 401. Wrong API key
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/api_download/{}/output/{}?apikey={}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_private_export",
                task_id[-12:],
                "wrongAPIKey",
            ),
            status=401,
        )

        # Download project not exist
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/api_download/{}/output/{}?apikey={}".format(
                test_object.randonLogin,
                "not_exist",
                test_object.formID,
                "csv_private_export",
                task_id[-12:],
                test_object.randonLoginKey,
            ),
            status=404,
        )

        # Download output not exist
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/api_download/{}/output/{}?apikey={}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_private_export",
                "not_exist",
                test_object.randonLoginKey,
            ),
            status=404,
        )

        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/api_download/{}/output/{}?apikey={}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "csv_private_export",
                task_id[-12:],
                test_object.randonLoginKey,
            ),
            status=200,
        )

    def mimic_celery_xlsx_process():
        from formshare.products.export.xlsx.celery_task import (
            internal_build_xlsx,
        )

        engine = create_engine(
            test_object.server_config["sqlalchemy.url"], poolclass=NullPool
        )
        form_details = get_form_details(
            test_object.server_config, test_object.projectID, test_object.formID
        )
        form_schema = form_details["form_schema"]
        create_xml_file = form_details["form_createxmlfile"]
        task_id = str(uuid.uuid4())

        sql = (
            "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
            "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
            "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                test_object.projectID,
                test_object.formID,
                "xlsx_public_export",
                test_object.working_dir + "/{}.xlsx".format(task_id),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                task_id,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                test_object.randonLogin,
                task_id[-12:],
                0,
                1,
            )
        )
        engine.execute(sql)
        engine.dispose()
        internal_build_xlsx(
            test_object.server_config,
            test_object.server_config["repository.path"] + "/odk",
            form_schema,
            test_object.formID,
            create_xml_file,
            test_object.server_config["auth.opaque"],
            test_object.working_dir + "/{}.xlsx".format(task_id),
            True,
            "en",
        )
        store_task_status(task_id, test_object.server_config)
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "xlsx_public_export",
                task_id[-12:],
            ),
            status=200,
        )

    def mimic_celery_zip_csv_process():
        from formshare.products.export.zip_csv.celery_task import (
            internal_build_zip_csv,
        )

        engine = create_engine(
            test_object.server_config["sqlalchemy.url"], poolclass=NullPool
        )
        form_details = get_form_details(
            test_object.server_config, test_object.projectID, test_object.formID
        )
        form_schema = form_details["form_schema"]
        create_xml_file = form_details["form_createxmlfile"]
        task_id = str(uuid.uuid4())

        sql = (
            "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
            "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
            "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                test_object.projectID,
                test_object.formID,
                "zip_csv_public_export",
                test_object.working_dir + "/{}.zip".format(task_id),
                "application/zip",
                task_id,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                test_object.randonLogin,
                task_id[-12:],
                0,
                1,
            )
        )
        engine.execute(sql)
        engine.dispose()
        internal_build_zip_csv(
            test_object.server_config,
            test_object.server_config["repository.path"] + "/odk",
            form_schema,
            test_object.formID,
            create_xml_file,
            test_object.server_config["auth.opaque"],
            test_object.working_dir + "/{}.zip".format(task_id),
            True,
            "en",
        )
        store_task_status(task_id, test_object.server_config)
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "zip_csv_public_export",
                task_id[-12:],
            ),
            status=200,
        )

    def mimic_celery_kml_process():
        from formshare.products.export.kml.celery_task import internal_build_kml

        engine = create_engine(
            test_object.server_config["sqlalchemy.url"], poolclass=NullPool
        )

        form_details = get_form_details(
            test_object.server_config, test_object.projectID, test_object.formID
        )

        form_schema = form_details["form_schema"]
        create_file = form_details["form_createxmlfile"]
        primary_key = form_details["form_pkey"]
        task_id = str(uuid.uuid4())

        sql = (
            "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
            "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
            "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                test_object.projectID,
                test_object.formID,
                "kml_export",
                test_object.working_dir + "/{}.kml".format(task_id),
                "application/vnd.google-earth.kml+xml",
                task_id,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                test_object.randonLogin,
                task_id[-12:],
                0,
                1,
            )
        )
        engine.execute(sql)
        engine.dispose()
        internal_build_kml(
            test_object.server_config,
            form_schema,
            test_object.working_dir + "/{}.kml".format(task_id),
            "en",
            test_object.formID,
            create_file,
            [
                primary_key,
                "_geopoint",
                "rowuuid",
                "_latitude",
                "_longitude",
                "surveyid",
                "originid",
                "_submitted_by",
                "_xform_id_string",
                "submitted_date",
            ],
            3,
            task_id,
        )
        store_task_status(task_id, test_object.server_config)
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "kml_export",
                task_id[-12:],
            ),
            status=200,
        )

    def mimic_celery_media_process():
        from formshare.products.export.media.celery_task import (
            internal_build_media_zip,
        )

        engine = create_engine(
            test_object.server_config["sqlalchemy.url"], poolclass=NullPool
        )
        form_details = get_form_details(
            test_object.server_config, test_object.projectID, test_object.formID
        )
        form_directory = form_details["form_directory"]
        form_schema = form_details["form_schema"]
        task_id = str(uuid.uuid4())

        sql = (
            "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
            "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
            "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                test_object.projectID,
                test_object.formID,
                "media_export",
                test_object.working_dir + "/{}.zip".format(task_id),
                "application/zip",
                task_id,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                test_object.randonLogin,
                task_id[-12:],
                0,
                1,
            )
        )
        engine.execute(sql)
        engine.dispose()
        internal_build_media_zip(
            test_object.server_config,
            test_object.server_config["repository.path"] + "/odk",
            [form_directory],
            form_schema,
            test_object.working_dir + "/{}.zip".format(task_id),
            "I_D",
            "en",
            task_id,
        )
        store_task_status(task_id, test_object.server_config)
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "media_export",
                task_id[-12:],
            ),
            status=200,
        )

    # Generate submitted media files
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/media".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Generate public XLSX for a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_zip_csv".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Generate public XLSX for a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_zip_csv".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Generate public XLSX
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Generate public XLSX for a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_xlsx".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Generate public XLSX for a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_xlsx".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Generate public XLSX
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    print("Testing cancel a task")
    time.sleep(4)
    last_task = get_last_task(
        test_object.server_config,
        test_object.projectID,
        test_object.formID,
        "xlsx_public_export",
    )
    print("Task to cancel: {}".format(last_task))

    # Stop task for a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/task/{}/stop".format(
            test_object.randonLogin, "not_exist", test_object.formID, last_task
        ),
        status=404,
    )

    # Stop task for a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/task/{}/stop".format(
            test_object.randonLogin, test_object.project, "not_exist", last_task
        ),
        status=404,
    )

    # Stop task for a task that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/task/{}/stop".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "not_exist",
        ),
        status=404,
    )

    # Stop task with a get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/task/{}/stop".format(
            test_object.randonLogin, test_object.project, test_object.formID, last_task
        ),
        status=404,
    )

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/task/{}/stop".format(
            test_object.randonLogin, test_object.project, test_object.formID, last_task
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Generate public XLSX
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Download a private xls for a project that does not exist goes tot 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_xlsx".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Download a private xls for a form that does not exist goes tot 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_xlsx".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Private public XLSX
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Download a private zip csv for a project that does not exist goes tot 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_zip_csv".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Download a private zip csv for a form that does not exist goes tot 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_zip_csv".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Private private zip CSV
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Export data of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Export data of a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Export data with get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Call export to XLSX without type goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {},
        status=404,
    )

    # Call export to XLSX
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "export_type": "XLSX",
        },
        status=302,
    )

    # Call export to CSV
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "export_type": "CSV",
        },
        status=302,
    )

    # Call export to KML
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "export_type": "KML",
        },
        status=302,
    )

    # Call export to MEDIA
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "export_type": "MEDIA",
        },
        status=302,
    )

    # Call export to ZIP CSV
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "export_type": "ZIP_CSV",
        },
        status=302,
    )

    # Call export to plugin
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "export_type": "TEST",
        },
        status=302,
    )

    # Call export to a type that is not handled goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "export_type": "NONE",
        },
        status=404,
    )

    # ------Excel-----------------------
    # Export data to excel of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Export data  to exel of a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Export to excel goes to 200
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Export to excel publishable
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "3",
        },
        status=302,
    )

    # Export to excel not publishable
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "3",
        },
        status=302,
    )

    # ------Zip CSV-----------------------
    # Export data to zip csv of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Export data to zip csv of a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Export to zip csv goes to 200
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Export to zip CSV publishable
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "3",
        },
        status=302,
    )

    # Export to zip CSV not publishable
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "3",
        },
        status=302,
    )

    # ------CSV-----------------------
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/csv".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Export data  to exel of a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/csv".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Export to excel goes to 200
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    # Export to excel publishable
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "3",
        },
        status=302,
    )

    # Export to excel not publishable
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "2",
        },
        status=302,
    )
    # ---------------

    # Download KML of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/kml".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Download KML of a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/kml".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Download KML - Show page
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/export/kml".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    assert "FS_error" not in res.headers

    # Export KML pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/kml".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "fields": [
                "surveyid",
                "originid",
                "_submitted_by",
                "_xform_id_string",
                "submitted_date",
            ],
            "labels": "3",
        },
        status=302,
    )
    test_object.root.assertNotIn(b"The process generated an error", res.body)

    # Public CSV of a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/repo_public_csv".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Public CSV of a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/repo_public_csv".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Public CSV
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/repo_public_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Download private csv from a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/repo_private_csv".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Download private csv from a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/repo_private_csv".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Private CSV
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/repo_private_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
    )
    assert "FS_error" not in res.headers
    print("Testing repository downloads step1 finished")
    time.sleep(40)  # Wait 5 seconds so celery finished this

    # Get the details of a form. The form now should have a repository with products
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
    test_object.root.assertNotIn(b"The process generated an error", res.body)
    print("Testing repository downloads step 2 finished")
    time.sleep(40)
    mimic_celery_public_csv_process()
    mimic_celery_private_csv_process()
    mimic_celery_xlsx_process()
    mimic_celery_zip_csv_process()
    mimic_celery_kml_process()
    mimic_celery_media_process()
    print("Testing repository downloads step 3 finished")
