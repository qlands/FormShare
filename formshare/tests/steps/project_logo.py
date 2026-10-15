"""A project's logo (processes/project_logo.py, docs/project-logo.md). It is
uploaded in the project form, served at a public URL whose ETag is its MD5,
named in the QR codes and carried in every form's manifest. A project that
has none shows nothing of it. The step leaves the project as it found it."""

import io
from hashlib import md5

from lxml import etree
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

OPENROSA_MANIFEST = "{http://openrosa.org/xforms/xformsManifest}"
LOGO = "_fs_project_logo.png"


def _image(size, fmt="PNG"):
    mode = "RGBA" if fmt == "PNG" else "RGB"
    output = io.BytesIO()
    Image.new(mode, size, (20, 110, 190, 255)[: len(mode)]).save(output, fmt)
    return output.getvalue()


def _project(config, login, code):
    """The project's row: its id, its logo's MD5 and what its form posts."""
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        return engine.execute(
            "SELECT p.project_id, p.project_logo_md5, p.project_name, "
            "p.project_icon, p.project_hexcolor, p.project_abstract, "
            "p.project_formlist_auth FROM project p JOIN userproject u "
            "ON u.project_id = p.project_id "
            "WHERE u.user_id = %s AND u.access_type = 1 AND p.project_code = %s",
            (login, code),
        ).fetchone()
    finally:
        engine.dispose()


def _posted(row, code, **more):
    """The project form as the edit page sends it, with the project's values."""
    fields = {
        "project_code": code,
        "project_name": row["project_name"],
        "project_abstract": row["project_abstract"] or "",
        "project_icon": row["project_icon"] or "",
        "project_hexcolor": row["project_hexcolor"] or "",
    }
    if row["project_formlist_auth"] == 1:
        fields["project_formlist_auth"] = "on"
    fields.update(more)
    return fields


def _manifest(test_object):
    """{filename: (hash, downloadUrl)} of the step's form, as its device sees it."""
    body = test_object.testapp.get(
        "/user/{}/project/{}/{}/manifest".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
        extra_environ=dict(
            FS_for_testing="true", FS_user_for_testing=test_object.assistantLogin
        ),
    ).body
    return {
        e.findtext(OPENROSA_MANIFEST + "filename"): (
            e.findtext(OPENROSA_MANIFEST + "hash"),
            e.findtext(OPENROSA_MANIFEST + "downloadUrl"),
        )
        for e in etree.fromstring(body).findall(OPENROSA_MANIFEST + "mediaFile")
    }


def t_e_s_t_project_logo(test_object):
    testapp = test_object.testapp
    config = test_object.server_config
    login, project = test_object.randonLogin, test_object.project
    edit = "/user/{}/project/{}/edit".format(login, project)
    row = _project(config, login, project)
    project_id = row["project_id"]
    public = "/project/{}/_fs_project_logo.png".format(project_id)

    # No logo: nothing anywhere.
    assert row["project_logo_md5"] is None
    before = _manifest(test_object)
    assert LOGO not in before
    testapp.get(public, status=404)

    # A logo that cannot be fixed is refused, and nothing else is saved.
    res = testapp.post(
        edit,
        _posted(row, project),
        upload_files=[("project_logo_file", "logo.jpg", _image((1200, 300), "JPEG"))],
        status=200,
    )
    assert "FS_error" in res.headers
    assert b"This file is a JPEG" in res.body
    assert _project(config, login, project)["project_logo_md5"] is None

    # A logo within the specification is stored ...
    res = testapp.post(
        edit,
        _posted(row, project),
        upload_files=[("project_logo_file", "logo.png", _image((1200, 300)))],
        status=302,
    )
    assert "FS_error" not in res.headers
    logo_md5 = _project(config, login, project)["project_logo_md5"]
    assert logo_md5

    # ... served without login, its ETag the MD5 ...
    res = testapp.get(public, status=200)
    assert res.content_type == "image/png"
    assert md5(res.body).hexdigest() == logo_md5
    assert res.headers["ETag"] == '"{}"'.format(logo_md5)
    testapp.get(public, headers={"If-None-Match": '"{}"'.format(logo_md5)}, status=304)

    # ... shown on the edit page ...
    res = testapp.get(edit, status=200)
    assert b"project_logo_current" in res.body
    assert "v={}".format(logo_md5).encode() in res.body

    # ... and carried in every form's manifest, the rest of it unchanged.
    after = _manifest(test_object)
    assert after[LOGO][0] == "md5:" + logo_md5
    assert after[LOGO][1].endswith(public)
    assert {name: entry for name, entry in after.items() if name != LOGO} == before

    # The QR codes name it. A QR cannot be read back here, so test_15 holds
    # their project section; these must still come out as images.
    res = testapp.get("/user/{}/project/{}/qr".format(login, project), status=200)
    assert res.content_type == "image/png"
    res = testapp.get(
        "/user/{}/project/{}/assistantaccess/form/{}/qrcode".format(
            login, project, test_object.formID
        ),
        status=200,
    )
    assert res.content_type == "image/png"

    # A form file cannot take the logo's name.
    res = testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(login, project, test_object.formID),
        {},
        upload_files=[("filetoupload", LOGO, _image((600, 300)))],
        status=302,
    )
    assert "FS_error" in res.headers

    # A form's own logo.png is the form's: both sit in its manifest.
    own_logo = _image((640, 160))
    res = testapp.post(
        "/user/{}/project/{}/form/{}/upload".format(login, project, test_object.formID),
        {},
        upload_files=[("filetoupload", "logo.png", own_logo)],
        status=302,
    )
    assert "FS_error" not in res.headers
    entries = _manifest(test_object)
    assert entries["logo.png"][0] == "md5:" + md5(own_logo).hexdigest()
    assert entries[LOGO][0] == "md5:" + logo_md5
    testapp.post(
        "/user/{}/project/{}/form/{}/uploads/{}/remove".format(
            login, project, test_object.formID, "logo.png"
        ),
        status=302,
    )
    assert "logo.png" not in _manifest(test_object)

    # Removed: nothing anywhere again.
    res = testapp.post(edit, _posted(row, project, remove_logo="1"), status=302)
    assert "FS_error" not in res.headers
    assert _project(config, login, project)["project_logo_md5"] is None
    testapp.get(public, status=404)
    assert _manifest(test_object) == before

    # A new project gets its logo as it is made, and one refused stops it.
    add = "/user/{}/projects/add".format(login)
    new_project = {
        "project_name": "Logo",
        "project_abstract": "",
        "project_icon": "",
        "project_hexcolor": "",
        "project_formlist_auth": "on",
    }
    res = testapp.post(
        add,
        dict(new_project, project_code="logo_refused"),
        upload_files=[("project_logo_file", "tall.png", _image((300, 600)))],
        status=200,
    )
    assert "FS_error" in res.headers
    assert _project(config, login, "logo_refused") is None
    res = testapp.post(
        add,
        dict(new_project, project_code="logo_project"),
        upload_files=[("project_logo_file", "wide.png", _image((2400, 600)))],
        status=302,
    )
    created = _project(config, login, "logo_project")
    assert created["project_logo_md5"]
    res = testapp.get(
        "/project/{}/_fs_project_logo.png".format(created["project_id"]), status=200
    )
    assert Image.open(io.BytesIO(res.body)).size == (1600, 400)
    testapp.post("/user/{}/project/{}/delete".format(login, "logo_project"), status=302)
    testapp.get(
        "/project/{}/_fs_project_logo.png".format(created["project_id"]), status=404
    )
