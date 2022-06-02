import datetime
import os
import shutil
import time
import uuid

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .sql import get_form_details, store_task_status


def t_e_s_t_import_data(test_object):
    def mimic_celery_test_xml_import():
        from formshare.products.xmlimport.celery_task import (
            internal_import_xml_files,
        )

        engine = create_engine(
            test_object.server_config["sqlalchemy.url"], poolclass=NullPool
        )
        task_id = str(uuid.uuid4())

        output_file_paths = [
            "resources",
            "forms",
            "complex_form",
            "for_import",
            "xml",
            "output.txt",
        ]
        output_file = os.path.join(test_object.path, *output_file_paths)

        sql = (
            "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
            "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
            "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                test_object.projectID,
                test_object.formID,
                "xmlimport",
                output_file,
                "text/plain",
                task_id,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                test_object.randonLogin,
                task_id[-12:],
                0,
                0,
            )
        )
        engine.execute(sql)
        engine.dispose()

        paths_to_xml = [
            "resources",
            "forms",
            "complex_form",
            "for_import",
            "xml",
        ]
        xml_directory = os.path.join(test_object.path, *paths_to_xml)
        internal_import_xml_files(
            test_object.server_config,
            test_object.randonLogin,
            test_object.project,
            test_object.assistantLogin,
            "123",
            xml_directory,
            "en",
            task_id,
        )
        store_task_status(task_id, test_object.server_config)

    def mimic_celery_test_import():
        from formshare.products.fs1import.celery_task import (
            internal_import_json_files,
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
        odk_dir = test_object.server_config["repository.path"] + "/odk"

        file_paths = [
            "resources",
            "forms",
            "complex_form",
            "for_import",
            "files2",
            "tmp",
        ]
        path_to_files = os.path.join(test_object.path, *file_paths)

        file_to_import = os.path.join(
            test_object.path,
            *[
                "resources",
                "forms",
                "complex_form",
                "for_import",
                "files2",
                "file1B.json",
            ]
        )
        file_to_import_target = os.path.join(
            test_object.path,
            *[
                "resources",
                "forms",
                "complex_form",
                "for_import",
                "files2",
                "tmp",
                "file1B.json",
            ]
        )
        shutil.copyfile(file_to_import, file_to_import_target)

        file_to_import = os.path.join(
            test_object.path,
            *[
                "resources",
                "forms",
                "complex_form",
                "for_import",
                "files2",
                "file2B.json",
            ]
        )
        file_to_import_target = os.path.join(
            test_object.path,
            *[
                "resources",
                "forms",
                "complex_form",
                "for_import",
                "files2",
                "tmp",
                "file2B.json",
            ]
        )
        shutil.copyfile(file_to_import, file_to_import_target)

        file_to_import = os.path.join(
            test_object.path,
            *[
                "resources",
                "forms",
                "complex_form",
                "for_import",
                "files2",
                "file3B.json",
            ]
        )
        file_to_import_target = os.path.join(
            test_object.path,
            *[
                "resources",
                "forms",
                "complex_form",
                "for_import",
                "files2",
                "tmp",
                "file3B.json",
            ]
        )
        shutil.copyfile(file_to_import, file_to_import_target)

        file_to_import = os.path.join(
            test_object.path,
            *[
                "resources",
                "forms",
                "complex_form",
                "for_import",
                "files2",
                "file4B.json",
            ]
        )
        file_to_import_target = os.path.join(
            test_object.path,
            *[
                "resources",
                "forms",
                "complex_form",
                "for_import",
                "files2",
                "tmp",
                "file4B.json",
            ]
        )
        shutil.copyfile(file_to_import, file_to_import_target)

        # -------------------
        file_to_import = os.path.join(
            test_object.path,
            *[
                "resources",
                "forms",
                "complex_form",
                "for_import",
                "files2",
                "file5B.json",
            ]
        )
        file_to_import_target = os.path.join(
            test_object.path,
            *[
                "resources",
                "forms",
                "complex_form",
                "for_import",
                "files2",
                "tmp",
                "file5B.json",
            ]
        )
        shutil.copyfile(file_to_import, file_to_import_target)
        # ---

        sql = (
            "INSERT INTO product (project_id,form_id,product_id,output_file,output_mimetype,"
            "celery_taskid,datetime_added,created_by,output_id,process_only,publishable) "
            "VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}',{})".format(
                test_object.projectID,
                test_object.formID,
                "fs1import",
                None,
                None,
                task_id,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                test_object.randonLogin,
                task_id[-12:],
                1,
                0,
            )
        )
        engine.execute(sql)
        engine.dispose()

        internal_import_json_files(
            test_object.randonLogin,
            test_object.projectID,
            test_object.formID,
            odk_dir,
            form_directory,
            form_schema,
            test_object.assistantLogin,
            path_to_files,
            test_object.project,
            "si_participa/SECTION/GPS",
            test_object.projectID,
            test_object.server_config,
            "en",
            False,
            task_id,
        )
        store_task_status(task_id, test_object.server_config)

    # Test import a simple file

    # Add a group to a form again
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/groups/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "group_id": test_object.assistantGroupID,
            "group_can_submit": 1,
            "group_can_clean": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin2
            ),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Loads import data for a project that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/import".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Loads import data for a form that does not exist goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/import".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/import".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    paths = [
        "resources",
        "forms",
        "complex_form",
        "for_import",
        "simple_file.json",
    ]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/import".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "import_type": "1",
            "ignore_xform": "",
            "assistant": "{}@{}".format(
                test_object.assistantLogin, test_object.projectID
            ),
        },
        status=302,
        upload_files=[("file", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Test import a zip file that is bad
    paths = [
        "resources",
        "forms",
        "complex_form",
        "for_import",
        "zip_file_bad.zip",
    ]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/import".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "import_type": "1",
            "assistant": "{}@{}".format(
                test_object.assistantLogin, test_object.projectID
            ),
        },
        status=200,
        upload_files=[("file", resource_file)],
    )
    assert "FS_error" in res.headers

    # Test import a zip file using a plugin
    paths = ["resources", "forms", "complex_form", "for_import", "zip_file.zip"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/import".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "import_type": "3",
            "assistant": "{}@{}".format(
                test_object.assistantLogin, test_object.projectID
            ),
        },
        status=302,
        upload_files=[("file", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Test import a zip file
    paths = ["resources", "forms", "complex_form", "for_import", "zip_file.zip"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/import".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "import_type": "1",
            "assistant": "{}@{}".format(
                test_object.assistantLogin, test_object.projectID
            ),
        },
        status=302,
        upload_files=[("file", resource_file)],
    )
    assert "FS_error" not in res.headers
    time.sleep(40)
    mimic_celery_test_import()

    # Test import a zip xml file fails. File must be zip
    paths = [
        "resources",
        "forms",
        "complex_form",
        "for_import",
        "simple_file.json",
    ]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/import".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "import_type": "2",
            "assistant": "{}@{}".format(
                test_object.assistantLogin, test_object.projectID
            ),
        },
        status=200,
        upload_files=[("file", resource_file)],
    )
    assert "FS_error" in res.headers

    # Test import a zip xml file pass
    paths = [
        "resources",
        "forms",
        "complex_form",
        "for_import",
        "xml",
        "xml_submission.zip",
    ]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/import".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "import_type": "2",
            "assistant": "{}@{}".format(
                test_object.assistantLogin, test_object.projectID
            ),
        },
        status=302,
        upload_files=[("file", resource_file)],
    )
    assert "FS_error" not in res.headers
    time.sleep(40)
    print("Testing xml import")
    mimic_celery_test_xml_import()
