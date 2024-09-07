import datetime
import os
import time
import uuid

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .sql import get_form_details, store_task_status, get_last_task


def t_e_s_t_repository_downloads(test_object):
    def mimic_celery_xlsx_process(
        protect, resolve, include_multiselect, include_lookup
    ):
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
            create_xml_file,
            test_object.server_config["auth.opaque"],
            test_object.working_dir + "/{}.xlsx".format(task_id),
            protect,
            "en",
            resolve,
            include_multiselect,
            include_lookup,
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

    def mimic_celery_zip_csv_process(
        protect, resolve, include_multiselects, include_lookups
    ):
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
            protect,
            "en",
            resolve,
            include_multiselects,
            include_lookups,
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

    def mimic_celery_zip_json_process(
        protect, resolve, include_multiselects, include_lookups
    ):
        from formshare.products.export.zip_json.celery_task import (
            internal_build_zip_json,
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
                "zip_json_public_export",
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
        internal_build_zip_json(
            test_object.server_config,
            test_object.server_config["repository.path"] + "/odk",
            form_schema,
            test_object.formID,
            create_xml_file,
            test_object.server_config["auth.opaque"],
            test_object.working_dir + "/{}.zip".format(task_id),
            protect,
            "en",
            resolve,
            include_multiselects,
            include_lookups,
        )
        store_task_status(task_id, test_object.server_config)
        test_object.testapp.get(
            "/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
                test_object.randonLogin,
                test_object.project,
                test_object.formID,
                "zip_json_public_export",
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

    # Generate public zip JSON for a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_zip_json".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Generate private zip JSON for a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_zip_json".format(
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

    # Generate public ZIP JSON for a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_zip_json".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Generate private ZIP JSON for a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_zip_json".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Generate public ZIP JSON
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/public_zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
    )
    assert "FS_error" not in res.headers

    # Generate public ZIP JSON
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/private_zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
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

    # Export to excel publishable just codes
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
        },
        status=302,
    )

    # Export to excel publishable just codes and multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
            "multiselects": "1",
        },
        status=302,
    )

    # Export to excel publishable just codes and lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
            "lookups": "1",
        },
        status=302,
    )

    # Export to excel publishable just codes with multiselects and lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
            "multiselects": "1",
            "lookups": "1",
        },
        status=302,
    )

    # Export to excel publishable labels instead of codes
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "2",
        },
        status=302,
    )

    # Export to excel publishable labels and codes
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

    # Export to excel not publishable. Just codes
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
        },
        status=302,
    )

    # Export to excel not publishable. Just codes with multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
            "multiselects": "1",
        },
        status=302,
    )

    # Export to excel not publishable. Just codes with lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
            "lookups": "1",
        },
        status=302,
    )

    # Export to excel not publishable. Just codes with multiselects and lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
            "multiselects": "1",
            "lookups": "1",
        },
        status=302,
    )

    # Export to excel not publishable. Labels instead of codes
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/xlsx".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "2",
        },
        status=302,
    )

    # Export to excel not publishable. Labels and codes
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

    # -------Public CSV

    # Export to zip CSV publishable no resolve with multiselect and lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
            "lookups": 1,
            "multiselects": 1,
        },
        status=302,
    )

    # Export to zip CSV publishable no resolve with lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
            "lookups": 1,
        },
        status=302,
    )

    # Export to zip CSV publishable no resolve with multiselecy
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
            "multiselects": 1,
        },
        status=302,
    )

    # Export to zip CSV publishable no resolve no lookups no multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
        },
        status=302,
    )

    # Export to zip CSV publishable no resolve no lookups no multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "2",
        },
        status=302,
    )

    # Export to zip CSV publishable no resolve no lookups no multiselects
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

    # ---- Private zip csv
    # Export to zip CSV publishable no resolve with multiselect and lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
            "lookups": 1,
            "multiselects": 1,
        },
        status=302,
    )

    # Export to zip CSV publishable no resolve with lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
            "lookups": 1,
        },
        status=302,
    )

    # Export to zip CSV publishable no resolve with multiselecy
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
            "multiselects": 1,
        },
        status=302,
    )

    # Export to zip CSV publishable no resolve no lookups no multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
        },
        status=302,
    )

    # Export to zip CSV publishable no resolve no lookups no multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_csv".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "2",
        },
        status=302,
    )

    # Export to zip CSV publishable no resolve no lookups no multiselects
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

    # -------Public JSON

    # Export to zip JSON publishable no resolve with multiselect and lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
            "lookups": 1,
            "multiselects": 1,
        },
        status=302,
    )

    # Export to zip JSON publishable no resolve with lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
            "lookups": 1,
        },
        status=302,
    )

    # Export to zip JSON publishable no resolve with multiselecy
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
            "multiselects": 1,
        },
        status=302,
    )

    # Export to zip JSON publishable no resolve no lookups no multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "1",
        },
        status=302,
    )

    # Export to zip JSON publishable no resolve no lookups no multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "2",
        },
        status=302,
    )

    # Export to zip JSON publishable no resolve no lookups no multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "yes",
            "labels": "3",
        },
        status=302,
    )

    # ---- Private zip json
    # Export to zip JSON private no resolve with multiselect and lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
            "lookups": 1,
            "multiselects": 1,
        },
        status=302,
    )

    # Export to zip JSON private no resolve with lookups
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
            "lookups": 1,
        },
        status=302,
    )

    # Export to zip JSON private no resolve with multiselecy
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
            "multiselects": 1,
        },
        status=302,
    )

    # Export to zip JSON private no resolve no lookups no multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "1",
        },
        status=302,
    )

    # Export to zip JSON private no resolve no lookups no multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "2",
        },
        status=302,
    )

    # Export to zip JSON private no resolve no lookups no multiselects
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/export/zip_json".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "publishable": "no",
            "labels": "3",
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

    # Download private csv from a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/generate/repo_private_csv".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

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

    mimic_celery_xlsx_process(True, 1, False, False)
    mimic_celery_xlsx_process(True, 1, True, False)
    mimic_celery_xlsx_process(True, 1, False, True)
    mimic_celery_xlsx_process(True, 1, True, True)
    mimic_celery_xlsx_process(True, 2, False, False)
    mimic_celery_xlsx_process(True, 3, False, False)

    mimic_celery_xlsx_process(False, 1, False, False)
    mimic_celery_xlsx_process(False, 1, True, False)
    mimic_celery_xlsx_process(False, 1, False, True)
    mimic_celery_xlsx_process(False, 1, True, True)
    mimic_celery_xlsx_process(False, 2, False, False)
    mimic_celery_xlsx_process(False, 3, False, False)

    mimic_celery_zip_csv_process(True, 1, True, True)
    mimic_celery_zip_csv_process(True, 1, False, True)
    mimic_celery_zip_csv_process(True, 1, False, False)
    mimic_celery_zip_csv_process(True, 2, False, False)
    mimic_celery_zip_csv_process(True, 3, False, False)
    mimic_celery_zip_csv_process(False, 1, True, True)
    mimic_celery_zip_csv_process(False, 1, False, True)
    mimic_celery_zip_csv_process(False, 1, False, False)
    mimic_celery_zip_csv_process(False, 2, False, False)
    mimic_celery_zip_csv_process(False, 3, False, False)

    mimic_celery_zip_json_process(True, 1, True, True)
    mimic_celery_zip_json_process(True, 1, False, True)
    mimic_celery_zip_json_process(True, 1, False, False)
    mimic_celery_zip_json_process(True, 2, False, False)
    mimic_celery_zip_json_process(True, 3, False, False)
    mimic_celery_zip_json_process(False, 1, True, True)
    mimic_celery_zip_json_process(False, 1, False, True)
    mimic_celery_zip_json_process(False, 1, False, False)
    mimic_celery_zip_json_process(False, 2, False, False)
    mimic_celery_zip_json_process(False, 3, False, False)

    mimic_celery_kml_process()
    mimic_celery_media_process()
    print("Testing repository downloads step 3 finished")
