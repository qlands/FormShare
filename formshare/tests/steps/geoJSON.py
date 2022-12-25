import glob
import os
import time

from .sql import get_form_details


def t_e_s_t_geo_json(test_object):
    # Upload a complex form succeeds with bad structure
    paths = ["resources", "forms", "GeoJSON", "GeoJSON.xlsx"]
    resource_file = os.path.join(test_object.path, *paths)

    res = test_object.testapp.post(
        "/user/{}/project/{}/forms/add".format(
            test_object.randonLogin, test_object.project
        ),
        {"form_pkey": "id"},
        status=302,
        upload_files=[("xlsx", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Add an assistant to a form succeeds
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        {
            "coll_id": "{}|{}".format(
                test_object.projectID, test_object.assistantLogin
            ),
            "coll_can_submit": "1",
            "coll_can_clean": "1",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Repository check pending" in res.body)

    # Uploads a bad file to the form
    paths = ["resources", "forms", "GeoJSON", "cities.csv"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"Repository check pending" in res.body)

    # Uploads a bad GeoJSON file
    paths = ["resources", "forms", "GeoJSON", "jsons", "bad_file", "museums.geojson"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form. Cannot create repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=200,
    )
    test_object.root.assertIn(b"This form cannot create a repository", res.body)

    # Uploads a GeoJSON file with no features
    paths = ["resources", "forms", "GeoJSON", "jsons", "no_features", "museums.geojson"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form. Cannot create repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=200,
    )
    test_object.root.assertIn(b"This form cannot create a repository", res.body)

    # Uploads a GeoJSON file with no Feature collection
    paths = [
        "resources",
        "forms",
        "GeoJSON",
        "jsons",
        "no_features_collection",
        "museums.geojson",
    ]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form. Cannot create repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=200,
    )
    test_object.root.assertIn(b"This form cannot create a repository", res.body)

    # Uploads a GeoJSON file with no geometry
    paths = ["resources", "forms", "GeoJSON", "jsons", "no_geometry", "museums.geojson"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form. Cannot create repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=200,
    )
    test_object.root.assertIn(b"This form cannot create a repository", res.body)

    # Uploads a GeoJSON file with no id
    paths = ["resources", "forms", "GeoJSON", "jsons", "no_id", "museums.geojson"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form. Cannot create repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=200,
    )
    test_object.root.assertIn(b"This form cannot create a repository", res.body)

    # Uploads a GeoJSON file with features that are no point
    paths = ["resources", "forms", "GeoJSON", "jsons", "no_point", "museums.geojson"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form. Cannot create repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=200,
    )
    test_object.root.assertIn(b"This form cannot create a repository", res.body)

    # Uploads a GeoJSON file with features that have no properties
    paths = [
        "resources",
        "forms",
        "GeoJSON",
        "jsons",
        "no_properties",
        "museums.geojson",
    ]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form. Cannot create repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=200,
    )
    test_object.root.assertIn(b"This form cannot create a repository", res.body)

    # Uploads a GeoJSON file that is OK
    paths = ["resources", "forms", "GeoJSON", "museums.geojson"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    # Get the details of a form. Cannot create repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=200,
    )
    test_object.root.assertNotIn(b"This form cannot create a repository", res.body)
