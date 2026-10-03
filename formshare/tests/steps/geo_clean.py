"""The data grids on a form with a trace and a shape.

RSTools derives a GEOMETRY column beside every geotrace and geoshape answer,
``<name>_geom``, which MySQL generates and stores (RSTools'
docs/geometry-in-the-repository.md). Both grids selected every column of the
dictionary as it was, so MySQL handed the geometry back as bytes and
json.dumps failed the request: neither the cleaning interface nor the
submissions page could load the data of a form with a geo question. This
checks what makes them work:

- both grids read the geometry as WKT, for the main table and a repeat;
- a search on the geometry searches its WKT, and sorting by it works;
- the cleaning interface offers the geometry read-only, since MySQL refuses
  any write to it (3105), while the answer it is derived from stays
  editable, and an edit of the answer moves the geometry with it.
"""

import json
import os
import shutil
import time
import uuid

import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .sql import get_form_details

FORM = "geo_clean"
CALLBACK = "jQuery35108899366494545082_1791040558000"
GRID = {
    "_search": "false",
    "nd": "1791040558000",
    "rows": "10",
    "page": "1",
    "sidx": "",
    "sord": "asc",
}
ROUTE = "0.1 0.2 0 0;0.3 0.4 0 0"
PLOT = "0.1 0.1 0 0;0.1 0.2 0 0;0.2 0.2 0 0;0.1 0.1 0 0"
AREA = "1.1 1.1 0 0;1.1 1.2 0 0;1.2 1.2 0 0;1.1 1.1 0 0"


def _workbook(path):
    wb = openpyxl.Workbook()
    survey = wb.active
    survey.title = "survey"
    survey.append(["type", "name", "label"])
    survey.append(["text", "i_d", "ID"])
    survey.append(["geotrace", "route", "Route"])
    survey.append(["geoshape", "plot", "Plot"])
    survey.append(["begin_repeat", "visits", "Visits"])
    survey.append(["text", "visit_name", "Visit name"])
    survey.append(["geoshape", "visit_area", "Visit area"])
    survey.append(["end_repeat", "", ""])
    settings = wb.create_sheet("settings")
    settings.append(["form_title", "form_id", "version"])
    settings.append(["Geometry in the grids", FORM, "1"])
    wb.save(path)


def _submission(path):
    xml = (
        "<?xml version='1.0'?>"
        '<data id="{form}" version="1">'
        "<i_d>G1</i_d><route>{route}</route><plot>{plot}</plot>"
        "<visits><visit_name>First</visit_name><visit_area>{area}</visit_area>"
        "</visits>"
        "<meta><instanceID>uuid:{uuid}</instanceID></meta></data>"
    ).format(form=FORM, route=ROUTE, plot=PLOT, area=AREA, uuid=uuid.uuid4())
    with open(path, "w", encoding="utf-8") as a_file:
        a_file.write(xml)


def _query(config, sql):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        return engine.execute(sql).fetchall()
    finally:
        engine.dispose()


def _grid(res):
    """The data a jqGrid request returned, out of its JSONP wrapper."""
    body = res.body.decode("utf-8")
    assert body.startswith(CALLBACK + "(") and body.endswith(")"), body[:300]
    return json.loads(body[len(CALLBACK) + 1 : -1])


def t_e_s_t_geo_clean(test_object):
    login = test_object.randonLogin
    project = test_object.project
    testapp = test_object.testapp
    config = test_object.server_config
    work = os.path.join(test_object.working_dir, "geo_clean")
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)

    # --- The form, built, with one submission ---------------------------------
    xlsx = os.path.join(work, FORM + ".xlsx")
    _workbook(xlsx)
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, project),
        {"form_pkey": "i_d"},
        status=302,
        upload_files=[("xlsx", xlsx)],
    )
    assert "FS_error" not in res.headers
    testapp.post(
        "/user/{}/project/{}/form/{}/assistants/add".format(login, project, FORM),
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
    testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(login, project, FORM),
        {"form_pkey": "i_d", "start_stage1": ""},
        status=302,
    )
    schema = None
    for _ in range(100):
        schema = get_form_details(config, test_object.projectID, FORM)["form_schema"]
        if (
            schema
            and _query(
                config,
                "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{}' "
                "AND TABLE_NAME = 'visits'".format(schema),
            )[0][0]
        ):
            break
        time.sleep(3)
    assert schema, "the geo form's repository did not build"
    generated = {
        (r[0], r[1])
        for r in _query(
            config,
            "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = '{}' AND EXTRA LIKE '%GENERATED%'".format(schema),
        )
    }
    for a_column in (
        ("maintable", "route_geom"),
        ("maintable", "plot_geom"),
        ("visits", "visit_area_geom"),
    ):
        assert a_column in generated, generated

    xml = os.path.join(work, "sub1.xml")
    _submission(xml)
    res = testapp.post(
        "/user/{}/project/{}/push".format(login, project),
        status=201,
        upload_files=[("filetoupload", xml)],
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    )
    assert "FS_error" not in res.headers
    main = _query(
        config, "SELECT rowuuid FROM `{}`.maintable WHERE i_d = 'G1'".format(schema)
    )[0][0]

    # --- The submissions page -------------------------------------------------
    data = _grid(
        testapp.post(
            "/user/{}/project/{}/form/{}/submissions/get?callback={}".format(
                login, project, FORM, CALLBACK
            ),
            GRID,
            status=200,
        )
    )
    assert data["records"] == 1, data
    assert data["rows"][0]["route_geom"] == "LINESTRING(0.1 0.2,0.3 0.4)", data
    assert (
        data["rows"][0]["plot_geom"] == "POLYGON((0.1 0.1,0.1 0.2,0.2 0.2,0.1 0.1))"
    ), data

    # --- The cleaning interface, as the assistant -------------------------------
    res = testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(login, project),
        {"login": test_object.assistantLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers
    page = testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/clean?table=maintable".format(
            login, project, FORM
        ),
        status=200,
    )
    # The geometry is shown and not editable; the answer it comes from is.
    assert b"name: 'plot_geom' , key: false, editable: false" in page.body
    assert b"name: 'route_geom' , key: false, editable: false" in page.body
    assert b"name: 'plot' , key: false, editable: true" in page.body

    request = "/user/{}/project/{}/assistantaccess/form/{}/{}/request?callback={}"
    maintable = request.format(login, project, FORM, "maintable", CALLBACK)
    data = _grid(testapp.post(maintable, GRID, status=200))
    assert data["rows"][0]["route_geom"] == "LINESTRING(0.1 0.2,0.3 0.4)", data
    assert (
        data["rows"][0]["plot_geom"] == "POLYGON((0.1 0.1,0.1 0.2,0.2 0.2,0.1 0.1))"
    ), data

    # A search on the geometry searches what the grid shows, its WKT
    search = dict(GRID, searchField="plot_geom", searchString="POLYGON")
    data = _grid(testapp.post(maintable, dict(search, searchOper="like"), status=200))
    assert data["records"] == 1, data
    data = _grid(
        testapp.post(maintable, dict(search, searchOper="not like"), status=200)
    )
    assert data["records"] == 0, data

    # A search on any other column is as it was
    search = dict(GRID, searchField="i_d", searchString="g1", searchOper="like")
    data = _grid(testapp.post(maintable, search, status=200))
    assert data["records"] == 1, data

    # Sorted by the geometry
    data = _grid(testapp.post(maintable, dict(GRID, sidx="plot_geom"), status=200))
    assert data["records"] == 1, data

    # A repeat has its geometry too
    visits = request.format(login, project, FORM, "visits", CALLBACK)
    data = _grid(testapp.post(visits, GRID, status=200))
    assert (
        data["rows"][0]["visit_area_geom"]
        == "POLYGON((1.1 1.1,1.1 1.2,1.2 1.2,1.1 1.1))"
    ), data

    # An edit of the answer moves the geometry MySQL derives from it -- once
    # RSTools' audit triggers leave generated columns out. Until then
    # createaudittriggers' UPDATE trigger copies the geometry's bytes into
    # audit_log's TEXT columns, MySQL refuses the whole UPDATE (1366), and the
    # cleaning interface, which does not report a failed update, keeps the
    # old answer (docs/formshare_case_management/rstools.md 25).
    audits_geometry = _query(
        config,
        "SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = '{}' "
        "AND EVENT_OBJECT_TABLE = 'maintable' AND EVENT_MANIPULATION = 'UPDATE' "
        "AND ACTION_STATEMENT LIKE '%audit_log%' "
        "AND ACTION_STATEMENT LIKE '%NEW.route_geom%'".format(schema),
    )[0][0]
    res = testapp.post(
        "/user/{}/project/{}/assistantaccess/form/{}/maintable/action".format(
            login, project, FORM
        ),
        {"route": "0.5 0.6 0 0;0.7 0.8 0 0", "oper": "edit", "id": main},
        status=200,
    )
    assert "FS_error" not in res.headers
    moved = _query(
        config,
        "SELECT ST_AsText(route_geom) FROM `{}`.maintable WHERE rowuuid = '{}'".format(
            schema, main
        ),
    )[0][0]
    if audits_geometry:
        assert moved == "LINESTRING(0.1 0.2,0.3 0.4)", moved
    else:
        assert moved == "LINESTRING(0.5 0.6,0.7 0.8)", moved

    res = testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(login, project),
        status=302,
    )
    assert "FS_error" not in res.headers
