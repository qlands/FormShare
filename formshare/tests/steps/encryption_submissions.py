"""Answers a form encrypts, from the device to the repository (formshare.md
section 5).

FormShare keeps every XML and JSON of a submission, and none may hold an
answer the form encrypts in clear. So the XML is sealed in memory right after
tidy and a pushed JSON on arrival, before anything is written; xmltojson and
jsontomysql get the project's key and only ever see envelopes; a resend is
recognised with its envelopes masked, since sealing is random; a form that
encrypts takes no submission in a project without a key; and an import seals
what it brings in.

The answers typed here carry this run's own marker, so that looking for them
in the files and the database cannot be fooled by an earlier run. They are
looked for in the form's directory, the staging directories and the
repository's tables: they must be nowhere, and every envelope must open to
the answer as given.

The repository is built before any submission, so that no Celery worker has
testing data to bring in: the steps here run in the web process, whatever
code a worker holds. The import is called the same way.
"""

import glob
import json
import os
import shutil
import time
import uuid

from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from formshare.processes.db.encryption import (
    member_name,
    b64u_decode,
    enroll_member,
    get_member,
    is_envelope,
    set_up_project_encryption,
)
from formshare.products.fs1import.celery_task import internal_import_json_files
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
from .encryption_keys import _Person, _Request, _grant, _project_key, _signed
from .sql import get_form_details

CODE = "enc_subs"
NO_KEY = "enc_subs_nokey"


def _open(envelope, project_private):
    from nacl.bindings import sodium_unpad
    from nacl.public import SealedBox

    box = b64u_decode(envelope.split(":")[3])
    return sodium_unpad(SealedBox(project_private).decrypt(box), 32).decode()


def _xml(form_id, pid, farmer, member, version="1"):
    return (
        '<?xml version="1.0"?>\n<data id="{}" version="{}"><pid>{}</pid>'
        "<farmer_name>{}</farmer_name><age>34</age><phone>0722</phone>"
        "<notes>kept in clear</notes><member><mem_name>{}</mem_name></member>"
        "<meta><instanceID>uuid:{}</instanceID></meta></data>"
    ).format(form_id, version, pid, farmer, member, uuid.uuid4())


def _push_xml(testapp, login, code, path, assistant, status):
    return testapp.post(
        "/user/{}/project/{}/push".format(login, code),
        status=status,
        upload_files=[("filetoupload", path)],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing=assistant[0]),
    )


def _push_json(testapp, login, code, path, assistant, status):
    return testapp.post(
        "/user/{}/project/{}/push_json".format(login, code),
        status=status,
        upload_files=[("filetoupload", path)],
        extra_environ=dict(FS_for_testing="true", FS_user_for_testing=assistant[0]),
    )


def _since(staging, started):
    """The staging directories made since the step started: the only ones a
    submission of this run can have touched."""
    return [
        a_directory
        for a_directory in glob.glob(os.path.join(staging, "*"))
        if os.path.getmtime(a_directory) >= started
    ]


def _nowhere(directories, *answers):
    """No file under the directories holds any of the answers."""
    for a_directory in directories:
        for a_path in glob.glob(os.path.join(a_directory, "**", "*"), recursive=True):
            if not os.path.isfile(a_path):
                continue
            with open(a_path, "rb") as a_file:
                content = a_file.read()
            for an_answer in answers:
                assert an_answer.encode() not in content, (an_answer, a_path)


def t_e_s_t_encryption_submissions(test_object):
    login = test_object.randonLogin
    testapp = test_object.testapp
    config = test_object.server_config
    work = os.path.join(test_object.working_dir, "encryption_submissions")
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
    marker = uuid.uuid4().hex[:8]
    started = time.time()
    odk = os.path.join(config["repository.path"], "odk")
    staging = os.path.join(odk, "submissions")

    # --- A project without a key takes nothing for a form that encrypts -------
    _new_project(testapp, login, NO_KEY)
    no_key_project = _project_id(engine, login, NO_KEY)
    no_key_assistant = _assistant(testapp, login, NO_KEY)
    _upload(
        testapp,
        login,
        NO_KEY,
        _workbook(os.path.join(work, "enc_nokey.xlsx"), "enc_nokey", MARKED_FORM),
    )
    _give(testapp, login, NO_KEY, "enc_nokey", no_key_project, no_key_assistant)
    refused = os.path.join(work, "refused.xml")
    with open(refused, "w") as a_file:
        a_file.write(_xml("enc_nokey", "R1", "Refused " + marker, "None " + marker))
    res = _push_xml(testapp, login, NO_KEY, refused, no_key_assistant, 403)
    assert b"encryption is not set up" in res.body
    refused_json = os.path.join(work, "refused.json")
    with open(refused_json, "w") as a_file:
        json.dump(
            {
                "_xform_id_string": "enc_nokey",
                "pid": "R2",
                "farmer_name": "Refused " + marker,
            },
            a_file,
        )
    res = _push_json(testapp, login, NO_KEY, refused_json, no_key_assistant, 403)
    assert b"encryption is not set up" in res.body
    no_key_directory = get_form_details(config, no_key_project, "enc_nokey")[
        "form_directory"
    ]
    _nowhere(
        _since(staging, started) + [os.path.join(odk, "forms", no_key_directory)],
        "Refused " + marker,
    )

    # --- A project with a key: a form in testing and a form with a repository --
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
        _grant(project_private, member_name("user", login), owner_public),
        recovery.public_key,
        _grant(
            project_private,
            member_name("recovery", project_id),
            recovery.public_key,
        ),
        login,
        **_signed(project_private),
    )
    assert ok, key_id
    for form_id in ("enc_testing", "enc_sub"):
        res = _upload(
            testapp,
            login,
            CODE,
            _workbook(os.path.join(work, form_id + ".xlsx"), form_id, MARKED_FORM),
        )
        assert "FS_error" not in res.headers
        _give(testapp, login, CODE, form_id, project_id, assistant)
    res = testapp.post(
        "/user/{}/project/{}/form/{}/repository/create".format(login, CODE, "enc_sub"),
        {"form_pkey": "pid", "start_stage1": ""},
        status=302,
    )
    assert "FS_error" not in res.headers
    schema = _built(engine, config, project_id, "enc_sub")
    testing_directory = os.path.join(
        odk,
        "forms",
        get_form_details(config, project_id, "enc_testing")["form_directory"],
    )
    repository_directory = os.path.join(
        odk, "forms", get_form_details(config, project_id, "enc_sub")["form_directory"]
    )

    # --- Testing: the XML and its JSON are kept sealed --------------------------
    farmer, member = "Wanjiru " + marker, "Otieno " + marker
    testing_xml = os.path.join(work, "testing.xml")
    with open(testing_xml, "w") as a_file:
        a_file.write(_xml("enc_testing", "T1", farmer, member))
    _push_xml(testapp, login, CODE, testing_xml, assistant, 201)
    kept = [
        a_path
        for a_path in glob.glob(os.path.join(testing_directory, "submissions", "*.xml"))
    ]
    assert len(kept) == 1, kept
    with open(kept[0], "rb") as a_file:
        root = etree.fromstring(a_file.read())
    assert _open(root.findtext("farmer_name"), project_private) == farmer
    assert _open(root.findtext("age"), project_private) == "34"
    assert _open(root.findtext("member/mem_name"), project_private) == member
    assert root.findtext("notes") == "kept in clear"
    with open(kept[0].replace(".xml", ".json")) as a_file:
        testing_json = json.load(a_file)
    assert is_envelope(testing_json["farmer_name"])
    assert testing_json["notes"] == "kept in clear"
    # A resend is the same submission, though its envelopes differ.
    _push_xml(testapp, login, CODE, testing_xml, assistant, 201)
    originals = glob.glob(os.path.join(testing_directory, "submissions", "*.original"))
    assert len(originals) == 1, originals
    # A pushed JSON is sealed on arrival.
    pushed = os.path.join(work, "testing.json")
    achieng = "Achieng " + marker
    with open(pushed, "w") as a_file:
        json.dump(
            {
                "_xform_id_string": "enc_testing",
                "pid": "T2",
                "farmer_name": achieng,
                "notes": "kept in clear",
                "meta/instanceID": "uuid:{}".format(uuid.uuid4()),
            },
            a_file,
        )
    _push_json(testapp, login, CODE, pushed, assistant, 201)
    _nowhere([testing_directory] + _since(staging, started), farmer, member, achieng)

    # --- A repository: the rows hold envelopes ----------------------------------
    kamau, njeri = "Kamau " + marker, "Njeri " + marker
    repository_xml = os.path.join(work, "repository.xml")
    with open(repository_xml, "w") as a_file:
        a_file.write(_xml("enc_sub", "S1", kamau, njeri))
    _push_xml(testapp, login, CODE, repository_xml, assistant, 201)
    _push_xml(testapp, login, CODE, repository_xml, assistant, 201)
    same = _query(
        engine,
        "SELECT COUNT(*) FROM submission WHERE project_id = %(p)s AND "
        "form_id = 'enc_sub' AND sameas IS NOT NULL",
        p=project_id,
    )[0][0]
    assert same == 1, same
    pushed = os.path.join(work, "repository.json")
    with open(pushed, "w") as a_file:
        json.dump(
            {
                "_xform_id_string": "enc_sub",
                "pid": "S2",
                "farmer_name": "Mwangi " + marker,
                "age": 41,
                "notes": "kept in clear",
                "meta/instanceID": "uuid:{}".format(uuid.uuid4()),
            },
            a_file,
        )
    _push_json(testapp, login, CODE, pushed, assistant, 201)

    # --- An import seals what it brings in ---------------------------------------
    to_import = os.path.join(work, "to_import")
    os.makedirs(to_import)
    imported_name = "Imported " + marker
    with open(os.path.join(to_import, str(uuid.uuid4()) + ".json"), "w") as a_file:
        json.dump(
            {
                "_xform_id_string": "enc_sub",
                "pid": "S3",
                "farmer_name": imported_name,
                "notes": "kept in clear",
            },
            a_file,
        )
    details = get_form_details(config, project_id, "enc_sub")
    internal_import_json_files(
        login,
        project_id,
        "enc_sub",
        odk,
        details["form_directory"],
        schema,
        assistant[1],
        to_import,
        CODE,
        [],
        config,
        "en",
        report_task=False,
    )
    _nowhere([to_import], imported_name)

    rows = {
        pid: (farmer_name, age, notes)
        for pid, farmer_name, age, notes in _query(
            engine,
            "SELECT pid, farmer_name, age, notes FROM `{}`.maintable".format(schema),
        )
    }
    expected = {
        "S1": (kamau, "34"),
        "S2": ("Mwangi " + marker, "41"),
        "S3": (imported_name, None),
    }
    for pid, (name, age) in expected.items():
        farmer_name, stored_age, notes = rows[pid]
        assert _open(farmer_name, project_private) == name, pid
        if age is None:
            assert stored_age is None, pid
        else:
            assert _open(stored_age, project_private) == age, pid
        assert notes == "kept in clear", pid
    members = [
        row[0]
        for row in _query(engine, "SELECT mem_name FROM `{}`.member".format(schema))
    ]
    assert [_open(a_value, project_private) for a_value in members] == [njeri]
    _nowhere(
        [repository_directory] + _since(staging, started),
        kamau,
        njeri,
        "Mwangi " + marker,
        imported_name,
    )

    # --- A submission for a form the project does not know is not kept ---------
    unknown = os.path.join(work, "unknown.xml")
    with open(unknown, "w") as a_file:
        a_file.write(_xml("no_such_form", "U1", "Unknown " + marker, "x"))
    _push_xml(testapp, login, CODE, unknown, assistant, 404)
    _nowhere(_since(staging, started), "Unknown " + marker)
