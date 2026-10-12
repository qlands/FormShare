"""Field encryption's record of keys (processes/db/encryption.py), against
the suite's MySQL.

docs/formshare_field_encryption/: the server keeps public keys, member keys
locked in a browser, grants sealed in a browser, and the record of who did
what. The plugin's pages call these functions; core has no page of its own,
so this step calls them directly, playing the browser with PyNaCl: it makes
the key pairs, locks the member keys and seals the grants, and at the end
opens a grant the way the vault does, to check that what the server handed
back is what the browser gave it.

A project of its own: its owner (the suite's user), the suite's collaborator
as an editor and then an admin, an assistant who may clean its form and one
who may only submit.
"""

import json
import os
import shutil
import uuid

import openpyxl
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.secret import SecretBox
from nacl.utils import random as random_bytes
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from formshare.models import EncryptionProjectKey, Project
from formshare.processes.db.encryption import (
    add_grants,
    add_unlock_method,
    b64u_decode,
    b64u_encode,
    enroll_member,
    format_public_key,
    get_active_project_key,
    get_member,
    get_project_keys,
    get_recovery_bundle,
    get_unlock_bundle,
    grant_with_recovery,
    list_encryption_events,
    list_project_access,
    list_unlock_methods,
    log_encryption_event,
    parse_public_key,
    remove_unlock_method,
    rename_unlock_method,
    replace_recovery_member,
    retire_member,
    revoke_ineligible_members,
    revoke_member,
    rotate_project_key,
    set_up_project_encryption,
    unlock_method_used,
)

CODE = "enc_keys"
FORM = "enc_keys_form"


class _Request:
    """What the functions read from a request."""

    client_addr = "127.0.0.1"
    user_agent = "pytest"

    def __init__(self, session):
        self.dbsession = session

    @staticmethod
    def translate(text):
        return text


class _Person:
    """A member as its browser sees it: its key pair, locked by a passphrase
    (here a random key-encryption key; the browser stretches a passphrase)."""

    def __init__(self):
        self.private = PrivateKey.generate()
        self.public_key = "fsenc-mk:1:" + b64u_encode(bytes(self.private.public_key))
        self.kek = random_bytes(32)

    def unlock(self, label="Laptop"):
        locked = SecretBox(self.kek).encrypt(bytes(self.private))
        return {
            "unlock_method": "passphrase",
            "unlock_label": label,
            "unlock_params": {
                "salt": b64u_encode(random_bytes(16)),
                "opslimit": 3,
                "memlimit": 64 * 1024 * 1024,
                "alg": "argon2id13",
            },
            "locked_key": {
                "nonce": b64u_encode(locked.nonce),
                "box": b64u_encode(locked.ciphertext),
            },
        }

    def open_grant(self, grant):
        return SealedBox(self.private).decrypt(b64u_decode(grant.split(":")[3]))


def _project_key():
    private = PrivateKey.generate()
    return private, format_public_key(bytes(private.public_key))


def _grant(project_private, member_public_key):
    """crypto_box_seal(project sk, member pk), as the vault makes it."""
    member = PublicKey(b64u_decode(member_public_key.split(":")[2]))
    the_key_id = parse_public_key(format_public_key(bytes(project_private.public_key)))[
        0
    ]
    return "fsenc-grant:1:{}:{}".format(
        the_key_id, b64u_encode(SealedBox(member).encrypt(bytes(project_private)))
    )


def _workbook(path):
    book = openpyxl.Workbook()
    survey = book.active
    survey.title = "survey"
    survey.append(["type", "name", "label"])
    survey.append(["text", "pid", "ID"])
    settings = book.create_sheet("settings")
    settings.append(["form_title", "form_id", "version"])
    settings.append(["Encryption keys", FORM, "1"])
    book.save(path)


def t_e_s_t_encryption_keys(test_object):
    login = test_object.randonLogin
    collaborator = test_object.collaboratorLogin
    testapp = test_object.testapp
    config = test_object.server_config
    work = os.path.join(test_object.working_dir, "encryption_keys")
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)

    # --- The project, its people and its form ---------------------------------
    res = testapp.post(
        "/user/{}/projects/add".format(login),
        {
            "project_code": CODE,
            "project_name": "Encryption keys",
            "project_abstract": "",
            "project_icon": "🔒",
            "project_hexcolor": "#9bbb59",
            "project_formlist_auth": 1,
        },
        status=302,
    )
    assert "FS_error" not in res.headers
    collaborators = "/user/{}/project/{}/collaborators".format(login, CODE)
    res = testapp.post(
        collaborators,
        {"add_collaborator": "", "collaborator": collaborator},
        status=302,
    )
    assert "FS_error" not in res.headers

    def set_role(role):
        res = testapp.post(
            collaborators,
            {
                "change_role": "",
                "collaborator_id": collaborator,
                "role_collaborator": role,
            },
            status=302,
        )
        assert "FS_error" not in res.headers

    set_role(3)
    xlsx = os.path.join(work, FORM + ".xlsx")
    _workbook(xlsx)
    res = testapp.post(
        "/user/{}/project/{}/forms/add".format(login, CODE),
        {"form_pkey": "pid"},
        status=302,
        upload_files=[("xlsx", xlsx)],
    )
    assert "FS_error" not in res.headers
    cleaner, submitter = str(uuid.uuid4()), str(uuid.uuid4())
    for coll_uuid, coll_id in ((cleaner, "enc_cleaner"), (submitter, "enc_submitter")):
        res = testapp.post(
            "/user/{}/project/{}/assistants/add".format(login, CODE),
            {
                "coll_uuid": coll_uuid,
                "coll_id": coll_id,
                "coll_name": coll_id,
                "coll_password": "123",
                "coll_password2": "123",
                "coll_prjshare": 0,
            },
            status=302,
        )
        assert "FS_error" not in res.headers

    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    session = sessionmaker(bind=engine)()
    request = _Request(session)
    try:
        project_id = [
            row[0]
            for row in session.execute(
                "SELECT p.project_id FROM project p JOIN userproject u ON "
                "u.project_id = p.project_id WHERE p.project_code = :code AND "
                "u.user_id = :user AND u.access_type = 1",
                {"code": CODE, "user": login},
            ).fetchall()
        ][0]
        # A checkbox: present means checked, whatever its value.
        for coll_uuid, coll_id, rights in (
            (cleaner, "enc_cleaner", {"coll_can_submit": "1", "coll_can_clean": "1"}),
            (submitter, "enc_submitter", {"coll_can_submit": "1"}),
        ):
            rights["coll_id"] = "{}|{}|{}".format(project_id, coll_id, coll_uuid)
            res = testapp.post(
                "/user/{}/project/{}/form/{}/assistants/add".format(login, CODE, FORM),
                rights,
                status=302,
            )
            assert "FS_error" not in res.headers
        _run(
            request,
            session,
            project_id,
            login,
            collaborator,
            cleaner,
            submitter,
            set_role,
        )

        # Losing the right to clean loses the key (section 9).
        res = testapp.post(
            "/user/{}/project/{}/form/{}/assistant/{}/edit".format(
                login, CODE, FORM, cleaner
            ),
            {"coll_can_submit": "1"},
            status=302,
        )
        assert "FS_error" not in res.headers
        # A new transaction, to see what the request just committed.
        session.rollback()
        assert revoke_ineligible_members(request, project_id) == 1
        access = {
            person.get("coll_uuid") or person.get("user_id"): person
            for person in list_project_access(request, project_id)["people"]
        }
        assert cleaner not in access
        assert revoke_ineligible_members(request, project_id) == 0
        revoked = list_encryption_events(request, project_id, "revoke")[0]
        assert revoked["actor_type"] == "system"
        assert revoked["event_detail"]["reason"] == "not eligible"
    finally:
        session.close()
        engine.dispose()


def _run(
    request, session, project_id, login, collaborator, cleaner, submitter, set_role
):
    owner, editor, assistant, other = _Person(), _Person(), _Person(), _Person()

    # --- Nothing yet ------------------------------------------------------------
    assert get_active_project_key(request, project_id) is None
    assert get_project_keys(request, project_id) == []
    assert get_member(request, "user", login) is None
    assert get_unlock_bundle(request, "user", login, project_id) is None

    # --- Enrolling --------------------------------------------------------------
    ok, owner_id = enroll_member(
        request, "user", login, owner.public_key, owner.unlock()
    )
    assert ok, owner_id
    ok, message = enroll_member(
        request, "user", login, _Person().public_key, _Person().unlock()
    )
    assert not ok and "already" in message
    weak = owner.unlock()
    weak["unlock_params"]["opslimit"] = 1
    for bad_key, bad_unlock in (
        ("fsenc-mk:1:short", editor.unlock()),
        (editor.public_key, weak),
    ):
        ok, message = enroll_member(request, "user", collaborator, bad_key, bad_unlock)
        assert not ok and message.startswith("The encryption key is not valid")
    assert not enroll_member(
        request, "recovery", project_id, other.public_key, other.unlock()
    )[0]
    assert not enroll_member(
        request, "user", "nobody_" + uuid.uuid4().hex, other.public_key, other.unlock()
    )[0]
    ok, editor_id = enroll_member(
        request, "user", collaborator, editor.public_key, editor.unlock()
    )
    assert ok, editor_id
    ok, assistant_id = enroll_member(
        request, "assistant", cleaner, assistant.public_key, assistant.unlock()
    )
    assert ok, assistant_id
    ok, other_id = enroll_member(
        request, "assistant", submitter, other.public_key, other.unlock()
    )
    assert ok, other_id
    assert get_member(request, "user", login)["member_id"] == owner_id

    # --- Unlock methods -----------------------------------------------------------
    ok, second = add_unlock_method(request, owner_id, owner.unlock("YubiKey"))
    assert ok, second
    methods = list_unlock_methods(request, owner_id)
    assert [a_method["unlock_label"] for a_method in methods] == ["Laptop", "YubiKey"]
    assert "locked_key" not in methods[0]
    assert rename_unlock_method(request, owner_id, second, "Security key")[0]
    assert not rename_unlock_method(request, owner_id, "nope", "x")[0]
    assert unlock_method_used(request, owner_id, second)
    first = methods[0]["unlock_id"]
    assert remove_unlock_method(request, owner_id, first)[0]
    ok, message = remove_unlock_method(request, owner_id, second)
    assert not ok and "at least one" in message
    assert not add_unlock_method(request, "nope", owner.unlock())[0]

    # --- Setting up ------------------------------------------------------------------
    recovery = _Person()
    project_private, public_key = _project_key()
    the_key_id = parse_public_key(public_key)[0]
    ok, message = set_up_project_encryption(
        request,
        project_id,
        public_key,
        editor_id,
        _grant(project_private, editor.public_key),
        recovery.public_key,
        _grant(project_private, recovery.public_key),
        collaborator,
    )
    assert not ok and "owner" in message
    stranger, _ = _project_key()
    ok, message = set_up_project_encryption(
        request,
        project_id,
        public_key,
        owner_id,
        _grant(stranger, owner.public_key),
        recovery.public_key,
        _grant(project_private, recovery.public_key),
        login,
    )
    assert not ok and "not of the new key" in message
    ok, key_id = set_up_project_encryption(
        request,
        project_id,
        public_key,
        owner_id,
        _grant(project_private, owner.public_key),
        recovery.public_key,
        _grant(project_private, recovery.public_key),
        login,
    )
    assert ok and key_id == the_key_id, key_id
    assert get_active_project_key(request, project_id) == public_key
    # A new transaction, to see what the request just committed.
    session.rollback()
    assert session.query(Project).get(project_id).project_encrypted == 1
    ok, message = set_up_project_encryption(
        request,
        project_id,
        public_key,
        owner_id,
        _grant(project_private, owner.public_key),
        recovery.public_key,
        _grant(project_private, recovery.public_key),
        login,
    )
    assert not ok and "already" in message
    # The database itself keeps one active version per project.
    session.add(
        EncryptionProjectKey(
            project_id=project_id,
            key_id="0" * 16,
            public_key="x",
            key_status="active",
        )
    )
    try:
        session.commit()
        raise AssertionError("a second active key was accepted")
    except IntegrityError:
        session.rollback()

    # --- Who may hold it ------------------------------------------------------------
    access = list_project_access(request, project_id)
    people = {
        person.get("coll_uuid") or person.get("user_id"): person
        for person in access["people"]
    }
    assert people[login]["role"] == 1 and people[login]["key_ids"] == [key_id]
    assert people[collaborator]["role"] == 3 and people[collaborator]["key_ids"] == []
    assert people[cleaner]["member"]["member_id"] == assistant_id
    assert submitter not in people
    assert access["recovery"]["key_ids"] == [key_id]
    assert [key["key_status"] for key in access["keys"]] == ["active"]

    # --- Granting ----------------------------------------------------------------------
    for_editor = {
        "member_id": editor_id,
        "grant": _grant(project_private, editor.public_key),
    }
    for_assistant = {
        "member_id": assistant_id,
        "grant": _grant(project_private, assistant.public_key),
    }
    ok, message = add_grants(request, project_id, [for_assistant], collaborator)
    assert not ok and "owner or an admin" in message
    ok, message = add_grants(
        request,
        project_id,
        [{"member_id": other_id, "grant": _grant(project_private, other.public_key)}],
        login,
    )
    assert not ok and "may not hold" in message
    ok, message = add_grants(
        request,
        project_id,
        [{"member_id": editor_id, "grant": _grant(stranger, editor.public_key)}],
        login,
    )
    assert not ok and "does not have" in message
    assert add_grants(request, project_id, [for_editor, for_assistant], login) == (
        True,
        2,
    )
    # An admin who holds the key may give it.
    set_role(2)
    # A new transaction, to see what the request just committed.
    session.rollback()
    assert add_grants(request, project_id, [for_assistant], collaborator) == (True, 1)

    # --- Unlocking, as the vault does -----------------------------------------------
    bundle = get_unlock_bundle(request, "assistant", cleaner, project_id)
    assert bundle["member"]["member_id"] == assistant_id
    assert bundle["unlock_methods"][0]["locked_key"].keys() == {"nonce", "box"}
    (grant,) = bundle["project"]["grants"]
    opened = PrivateKey(assistant.open_grant(grant["grant"]))
    server_key = {key["key_id"]: key for key in bundle["project"]["keys"]}[
        grant["key_id"]
    ]["public_key"]
    assert format_public_key(bytes(opened.public_key)) == server_key
    locked = bundle["unlock_methods"][0]["locked_key"]
    member_private = SecretBox(assistant.kek).decrypt(
        b64u_decode(locked["box"]), b64u_decode(locked["nonce"])
    )
    assert member_private == bytes(assistant.private)
    assert (
        list_encryption_events(request, project_id, "unlock")[0]["actor_id"] == cleaner
    )
    assert get_unlock_bundle(request, "recovery", project_id, project_id) is None

    # --- A new version of the key ----------------------------------------------------
    new_private, new_public = _project_key()
    holders = {
        owner_id: owner,
        editor_id: editor,
        assistant_id: assistant,
    }
    recovery_id = access["recovery"]["member"]["member_id"]
    grants = [
        {"member_id": member_id, "grant": _grant(new_private, person.public_key)}
        for member_id, person in holders.items()
    ]
    for_recovery = {
        "member_id": recovery_id,
        "grant": _grant(new_private, recovery.public_key),
    }
    ok, message = rotate_project_key(request, project_id, new_public, grants, login)
    assert not ok and "recovery kit included" in message
    ok, message = rotate_project_key(
        request, project_id, new_public, grants + [for_recovery], collaborator
    )
    assert not ok and "owner" in message
    ok, new_key_id = rotate_project_key(
        request, project_id, new_public, grants + [for_recovery], login
    )
    assert ok, new_key_id
    assert get_active_project_key(request, project_id) == new_public
    statuses = {
        key["key_id"]: key["key_status"]
        for key in get_project_keys(request, project_id)
    }
    assert statuses == {key_id: "retired", new_key_id: "active"}
    assert not rotate_project_key(request, project_id, public_key, grants, login)[0]

    # --- Revoking ------------------------------------------------------------------------
    ok, message = revoke_member(request, project_id, owner_id, collaborator)
    assert not ok and "owner" in message
    ok, message = revoke_member(request, project_id, recovery_id, login)
    assert not ok and "replaced" in message
    assert revoke_member(request, project_id, editor_id, login) == (True, 2)
    ok, message = revoke_member(request, project_id, assistant_id, collaborator)
    assert not ok and "holds the project's key" in message

    # --- A new recovery kit, and the kit used ----------------------------------------
    new_recovery = _Person()
    ok, message = replace_recovery_member(
        request,
        project_id,
        new_recovery.public_key,
        [_grant(new_private, new_recovery.public_key)],
        login,
    )
    assert not ok and "every version" in message
    ok, new_recovery_id = replace_recovery_member(
        request,
        project_id,
        new_recovery.public_key,
        [
            _grant(project_private, new_recovery.public_key),
            _grant(new_private, new_recovery.public_key),
        ],
        login,
    )
    assert ok, new_recovery_id
    assert get_member(request, "recovery", project_id)["member_id"] == new_recovery_id
    assert get_recovery_bundle(request, project_id, collaborator) is None
    kit = get_recovery_bundle(request, project_id, login)
    assert sorted(grant["key_id"] for grant in kit["project"]["grants"]) == sorted(
        [key_id, new_key_id]
    )
    ok, count = grant_with_recovery(
        request,
        project_id,
        [
            {
                "member_id": editor_id,
                "grant": _grant(project_private, editor.public_key),
            },
            {"member_id": editor_id, "grant": _grant(new_private, editor.public_key)},
        ],
        login,
    )
    assert (ok, count) == (True, 2)
    used = list_encryption_events(request, project_id, "recovery_used")[0]
    assert used["event_detail"]["member_ids"] == [editor_id]

    # --- Starting again --------------------------------------------------------------------
    assert retire_member(request, "user", collaborator) == (True, 1)
    assert get_member(request, "user", collaborator) is None
    ok, editor_id = enroll_member(
        request, "user", collaborator, editor.public_key, editor.unlock()
    )
    assert ok, editor_id
    assert not retire_member(request, "user", "nobody_" + uuid.uuid4().hex)[0]

    # --- The record --------------------------------------------------------------------------
    assert log_encryption_event(
        request, project_id, "user", login, "key_alarm", {"key_id": new_key_id}
    ) == (True, "")
    # Only what happens in a browser, and only from someone with the key: a
    # grant or a revocation is recorded by what made it, not made up here.
    for actor, kind in (
        (login, "opened"),
        (login, "grant"),
        (login, "revoke"),
        (collaborator, "key_alarm"),
    ):
        assert not log_encryption_event(request, project_id, "user", actor, kind)[0]
    assert log_encryption_event(
        request, project_id, "assistant", cleaner, "decrypted", {"answers": 3}
    ) == (True, "")
    kinds = {
        event["event_type"] for event in list_encryption_events(request, project_id)
    }
    assert {
        "setup",
        "grant",
        "unlock",
        "rotate",
        "revoke",
        "recovery_replaced",
        "recovery_used",
        "key_alarm",
    } <= kinds
    setup = list_encryption_events(request, project_id, "setup")[0]
    assert (setup["actor_id"], setup["ip"], setup["user_agent"]) == (
        login,
        "127.0.0.1",
        "pytest",
    )
    assert json.loads(json.dumps(setup["event_detail"]))["key_id"] == key_id
