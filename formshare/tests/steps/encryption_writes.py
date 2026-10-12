"""Writing to a repository whose form encrypts answers (formshare.md section 7).

A column a form marks fs_encrypted takes an envelope or NULL, and MySQL itself
refuses anything else (error 3819, README 6). FormShare reports that refusal
wherever a write can fail -- the cleaning grid, the API -- instead of the grid
being told nothing, as it was. And a value goes into the UPDATE only as a
parameter: the grid and the API used to paste it into the statement, so a
quote broke the write and could do worse.

The project's public key is given to anyone who works with the project, so
that an API client can seal for itself.

An assistant's rights through a group come from that group's rights on the
form asked about, not from whichever form the group happens to have.
"""

import json
import os
import shutil
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from formshare.processes.db.encryption import (
    enroll_member,
    get_member,
    seal,
    set_up_project_encryption,
)
from formshare.processes.odk.processes import get_assistant_permissions_on_a_form
from .encryption_forms import (
    MARKED_FORM,
    _assistant,
    _built,
    _give,
    _new_project,
    _project_id,
    _query,
    _upload,
    _workbook,
)
from .encryption_keys import _Person, _Request, _grant, _project_key
from .encryption_submissions import _open, _push_xml, _xml

CODE = "enc_writes"
PLAIN = "enc_writes_plain"


def t_e_s_t_encryption_writes(test_object):
    login = test_object.randonLogin
    testapp = test_object.testapp
    config = test_object.server_config
    work = os.path.join(test_object.working_dir, "encryption_writes")
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    session = sessionmaker(bind=engine)()
    try:
        _run(login, testapp, config, work, engine, session)
    finally:
        session.close()
        engine.dispose()


def _run(login, testapp, config, work, engine, session):
    # --- A project with a key, a form with a repository, one submission -------
    _new_project(testapp, login, CODE)
    project_id = _project_id(engine, login, CODE)
    assistant = _assistant(testapp, login, CODE)
    request = _Request(session)
    existing = get_member(request, "user", login)
    if existing is None:
        owner = _Person()
        ok, owner_id = enroll_member(
            request, "user", login, owner.public_key, owner.unlock()
        )
        assert ok, owner_id
        owner_public = owner.public_key
    else:
        owner_id, owner_public = existing["member_id"], existing["public_key"]
    project_private, public_key = _project_key()
    recovery = _Person()
    ok, key_id = set_up_project_encryption(
        request,
        project_id,
        public_key,
        owner_id,
        _grant(project_private, owner_public),
        recovery.public_key,
        _grant(project_private, recovery.public_key),
        login,
    )
    assert ok, key_id
    _upload(
        testapp,
        login,
        CODE,
        _workbook(os.path.join(work, "enc_write.xlsx"), "enc_write", MARKED_FORM),
    )
    _give(testapp, login, CODE, "enc_write", project_id, assistant)
    res = testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(
            login, CODE, "enc_write"
        ),
        {"form_pkey": "pid", "start_stage1": ""},
        status=302,
    )
    assert "FS_error" not in res.headers
    schema = _built(engine, config, project_id, "enc_write")
    submission = os.path.join(work, "submission.xml")
    with open(submission, "w") as a_file:
        a_file.write(_xml("enc_write", "W1", "Original Name", "Member"))
    _push_xml(testapp, login, CODE, submission, assistant, 201)
    row_uuid = _query(engine, "SELECT rowuuid FROM `{}`.maintable".format(schema))[0][0]

    def stored(column):
        return _query(
            engine,
            "SELECT `{}` FROM `{}`.maintable WHERE rowuuid = %(r)s".format(
                column, schema
            ),
            r=row_uuid,
        )[0][0]

    # --- The public key, for those who seal --------------------------------------
    keys = testapp.get(
        "/user/{}/project/{}/encryption/keys".format(login, CODE), status=200
    ).json
    assert keys["public_key"] == public_key
    assert [a_key["key_status"] for a_key in keys["keys"]] == ["active"]
    _new_project(testapp, login, PLAIN)
    nothing = testapp.get(
        "/user/{}/project/{}/encryption/keys".format(login, PLAIN), status=200
    ).json
    assert (nothing["public_key"], nothing["keys"]) == (None, [])
    testapp.get(
        "/user/{}/project/{}/encryption/keys".format(login, "no_such_project"),
        status=404,
    )

    # --- The cleaning grid, as the assistant ---------------------------------------
    res = testapp.post(
        "/user/{}/project/{}/assistantaccess/login".format(login, CODE),
        {"login": assistant[0], "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers
    assistant_keys = testapp.get(
        "/user/{}/project/{}/assistantaccess/encryption/keys".format(login, CODE),
        status=200,
    ).json
    assert assistant_keys["public_key"] == public_key
    action = "/user/{}/project/{}/assistantaccess/form/{}/{}/action".format(
        login, CODE, "enc_write", "maintable"
    )

    def edit(**values):
        return testapp.post(
            action, dict(values, oper="edit", id=row_uuid), status=200
        ).json

    # An answer in clear in an encrypted column: refused, and said.
    result = edit(farmer_name="Typed in clear")
    assert result["errors"] == [
        {
            "field": "farmer_name",
            "message": "This answer is encrypted: unlock it to edit.",
        }
    ]
    assert _open(stored("farmer_name"), project_private) == "Original Name"
    # An envelope, as the plugin's browser seals one: saved.
    assert edit(farmer_name=seal("Edited Name", public_key)) == {}
    assert _open(stored("farmer_name"), project_private) == "Edited Name"
    # A value with quotes is a value, not SQL.
    tricky = "O'Brien; \"Jr\" -- ' OR '1'='1"
    assert edit(notes=tricky) == {}
    assert stored("notes") == tricky
    # An empty answer is NULL, as it always was.
    assert edit(notes="") == {}
    assert stored("notes") is None
    # A column the grid does not offer, or no column at all, is not written.
    for field in ("surveyid", "notes` = 'x' WHERE 1=1; --", "no_such_column"):
        result = edit(**{field: "x"})
        assert result["errors"][0]["message"] == "This column cannot be changed", field
    assert stored("notes") is None

    # --- The API --------------------------------------------------------------------
    api_key = str(uuid.uuid4())
    with engine.begin() as connection:
        connection.execute(
            "UPDATE collaborator SET coll_apikey = %(k)s WHERE coll_uuid = %(u)s",
            {"k": api_key, "u": assistant[1]},
        )
    res = testapp.post_json(
        "/api_update",
        {"apikey": api_key, "rowuuid": row_uuid, "farmer_name": "Clear from API"},
        status=500,
    )
    assert "send it sealed with the project's public key" in json.dumps(res.json)
    assert _open(stored("farmer_name"), project_private) == "Edited Name"
    testapp.post_json(
        "/api_update",
        {
            "apikey": api_key,
            "rowuuid": row_uuid,
            "farmer_name": seal("Sealed by the client", public_key),
            "notes": tricky,
        },
        status=200,
    )
    assert _open(stored("farmer_name"), project_private) == "Sealed by the client"
    assert stored("notes") == tricky
    # The assistant's session ends here: a later step logs in its own, and
    # the login page sends a logged-in assistant away.
    res = testapp.post(
        "/user/{}/project/{}/assistantaccess/logout".format(login, CODE), status=302
    )
    assert "FS_error" not in res.headers

    # --- An assistant's rights through a group -----------------------------------
    # The group may clean enc_write and has nothing on enc_other.
    _upload(
        testapp,
        login,
        CODE,
        _workbook(os.path.join(work, "enc_other.xlsx"), "enc_other", MARKED_FORM),
    )
    grouped = _assistant(testapp, login, CODE)
    group_id = uuid.uuid4().hex[:12]
    with engine.begin() as connection:
        connection.execute(
            "INSERT INTO collgroup (project_id, group_id, group_desc, group_active) "
            "VALUES (%(p)s, %(g)s, 'cleaners', 1)",
            {"p": project_id, "g": group_id},
        )
        connection.execute(
            "INSERT INTO collingroup (project_id, group_id, enum_project, coll_id, "
            "coll_uuid) VALUES (%(p)s, %(g)s, %(p)s, %(c)s, %(u)s)",
            {"p": project_id, "g": group_id, "c": grouped[0], "u": grouped[1]},
        )
        connection.execute(
            "INSERT INTO formgrpaccess (project_id, group_id, form_project, form_id, "
            "group_can_submit, group_can_clean) VALUES (%(p)s, %(g)s, %(p)s, "
            "'enc_write', 1, 1)",
            {"p": project_id, "g": group_id},
        )
    on_write = get_assistant_permissions_on_a_form(
        request, login, project_id, grouped[1], "enc_write"
    )
    on_other = get_assistant_permissions_on_a_form(
        request, login, project_id, grouped[1], "enc_other"
    )
    assert (on_write["enum_cansubmit"], on_write["enum_canclean"]) == (1, 1)
    assert (on_other["enum_cansubmit"], on_other["enum_canclean"]) == (0, 0)
