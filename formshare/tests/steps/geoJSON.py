import os
import time

from .sql import count_lookup_rows, get_form_details, get_lookup_choice


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

    # Generate the repository using celery
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        {"form_pkey": "id", "start_stage1": ""},
        status=302,
    )
    assert "FS_error" not in res.headers

    print("Generating repository for GeoJSON form")
    time.sleep(60)  # Wait for Celery to finish
    print("Repository for GeoJSON form is ready")

    # Get the details of a form. The form now should have a repository
    res = test_object.testapp.get(
        "/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        status=200,
    )
    test_object.root.assertTrue(b"With repository" in res.body)

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
    assert "FS_error" in res.headers

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
    assert "FS_error" in res.headers

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
    assert "FS_error" in res.headers

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
    assert "FS_error" in res.headers

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
    assert "FS_error" in res.headers

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
    assert "FS_error" in res.headers

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
    assert "FS_error" in res.headers

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

    # From here the file update has to be looked at in the lookup table rather
    # than in the response. An update that MySQL discarded still comes back as
    # a success: geometry_json is NOT NULL with no default, so a row missing it
    # is dropped with a warning and nothing is raised.
    form_details = get_form_details(
        test_object.server_config, test_object.projectID, "example_geojson"
    )
    form_schema = form_details["form_schema"]
    choice = get_lookup_choice(
        test_object.server_config,
        form_schema,
        "lkpmuseum",
        "museum_cod",
        "museum_des",
        "fs87b",
    )
    test_object.root.assertIsNotNone(choice)
    test_object.root.assertEqual(choice["geometry_type"], "POINT")
    test_object.root.assertEqual(
        count_lookup_rows(test_object.server_config, form_schema, "lkpmuseum"), 1
    )

    # The same file again. The code column of a lookup carries no unique index
    # any more, so nothing but the merge itself stops the whole file from being
    # appended a second time.
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "example_geojson"
        ),
        {"overwrite": ""},
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers
    test_object.root.assertEqual(
        count_lookup_rows(test_object.server_config, form_schema, "lkpmuseum"), 1
    )

    # A file whose features carry their identifier where the GeoJSON spec puts
    # it, on the feature rather than in its properties. It has to reach the same
    # choice, not a new one.
    paths = [
        "resources",
        "forms",
        "GeoJSON",
        "jsons",
        "top_level_id",
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
    choice = get_lookup_choice(
        test_object.server_config,
        form_schema,
        "lkpmuseum",
        "museum_cod",
        "museum_des",
        "fs87b",
    )
    test_object.root.assertEqual(choice["description"], "HR Giger Museum renamed")
    test_object.root.assertEqual(
        count_lookup_rows(test_object.server_config, form_schema, "lkpmuseum"), 1
    )

    # A lookup holds the geometries ODK reads, which are Point, LineString and
    # Polygon. The new feature has to arrive as the shape it was.
    paths = ["resources", "forms", "GeoJSON", "jsons", "polygon", "museums.geojson"]
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
    choice = get_lookup_choice(
        test_object.server_config,
        form_schema,
        "lkpmuseum",
        "museum_cod",
        "museum_des",
        "fs99p",
    )
    test_object.root.assertIsNotNone(choice)
    test_object.root.assertEqual(choice["geometry_type"], "POLYGON")
    test_object.root.assertEqual(
        count_lookup_rows(test_object.server_config, form_schema, "lkpmuseum"), 2
    )


def t_e_s_t_generated_geo_json(test_object):
    """A GeoJSON a plugin generates, the way a generated CSV already works.

    FormShare asks IFormFileGenerator plugins for a form's files when a device
    fetches the manifest. If what comes back is a lookup's file and it has
    changed, the lookup is brought in step with it - which the CSV path has
    always done and the GeoJSON path did not, it being two `pass` statements
    until now.

    This needs formshare_test_plugin to answer for "generated.geojson" in
    generate_form_file, the way it answers for "generated.csv". The contract the
    assertions below expect: a FeatureCollection holding the original feature
    "gp1" unchanged, plus a second Point feature with id "gp2" and title
    "Second place".
    """
    paths = ["resources", "forms", "GeoJSON", "generated_geojson.xlsx"]
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

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(
            test_object.randonLogin, test_object.project, "generated_geojson"
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

    paths = ["resources", "forms", "GeoJSON", "generated.geojson"]
    resource_file = os.path.join(test_object.path, *paths)
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(
            test_object.randonLogin, test_object.project, "generated_geojson"
        ),
        status=302,
        upload_files=[("filetoupload", resource_file)],
    )
    assert "FS_error" not in res.headers

    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            test_object.randonLogin, test_object.project, "generated_geojson"
        ),
        {"form_pkey": "id", "start_stage1": ""},
        status=302,
    )
    assert "FS_error" not in res.headers

    print("Generating repository for the generated GeoJSON form")
    time.sleep(60)  # Wait for Celery to finish

    form_details = get_form_details(
        test_object.server_config, test_object.projectID, "generated_geojson"
    )
    form_schema = form_details["form_schema"]
    assert form_schema is not None
    test_object.root.assertEqual(
        count_lookup_rows(test_object.server_config, form_schema, "lkpplace"), 1
    )

    # Fetching the manifest is what asks the plugin for the file. The lookup
    # has to follow what comes back.
    test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, test_object.project, "generated_geojson"
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true",
            FS_user_for_testing=test_object.assistantLogin,
        ),
    )

    choice = get_lookup_choice(
        test_object.server_config,
        form_schema,
        "lkpplace",
        "place_cod",
        "place_des",
        "gp2",
    )
    test_object.root.assertIsNotNone(choice)
    test_object.root.assertEqual(choice["description"], "Second place")
    test_object.root.assertEqual(choice["geometry_type"], "POINT")
    test_object.root.assertEqual(
        count_lookup_rows(test_object.server_config, form_schema, "lkpplace"), 2
    )
