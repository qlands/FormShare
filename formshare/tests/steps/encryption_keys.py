"""Field encryption's record of keys (processes/db/encryption.py), against
the suite's MySQL.

docs/formshare_field_encryption/: the server keeps public keys, member keys
locked in a browser, grants sealed in a browser, and the record of who did
what. The plugin's pages call these functions; core has no page of its own,
so this step calls them directly, playing the browser with PyNaCl: it makes
the key pairs, locks the member keys and seals the grants, and at the end
opens a grant the way the vault does, to check that what the server handed
back is what the browser gave it.

A key version signs (README 3.6): the step derives its signing key as the
vault does, signs set-up, rotation, grants and the recovery kit, and checks
the chain of versions the way the vault must at every unlock (_chain_holds),
including against a version someone put straight into the database.

A project of its own: its owner (the suite's user), the suite's collaborator
as an editor and then an admin, an assistant who may clean its form and one
who may only submit.
"""

import json
import os
import shutil
import struct
import uuid
from contextlib import contextmanager
from types import SimpleNamespace
from unittest import mock

import openpyxl
from nacl.encoding import RawEncoder
from nacl.hash import blake2b
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.secret import SecretBox
from nacl.signing import SigningKey
from nacl.utils import random as random_bytes
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from formshare.models import EncryptionProjectKey, Project, User
from formshare.processes.db.encryption import (
    EncryptionFormatError,
    add_grants,
    add_unlock_method,
    b64u_decode,
    b64u_encode,
    check_grant,
    check_key_signature,
    enroll_member,
    format_member_key,
    format_public_key,
    format_sign_public_key,
    get_active_project_key,
    get_member,
    get_project_keys,
    get_recovery_bundle,
    get_unlock_bundle,
    grant_message,
    grant_with_recovery,
    key_id as key_id_of,
    key_version_message,
    list_encryption_events,
    list_project_access,
    list_unlock_methods,
    log_encryption_event,
    member_name,
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
from formshare.processes.email.send_async_email import send_async_email
from formshare.scripts.removeprojectencryption import main as remove_encryption

CODE = "enc_keys"
FORM = "enc_keys_form"


class _Request:
    """What the functions read from a request."""

    client_addr = "127.0.0.1"
    user_agent = "pytest"
    # What the security notices read (formshare.md 14.2). No mail.from: a
    # notice is sent only where a test catches it (_notices).
    locale_name = "en"
    application_url = "http://localhost"
    registry = SimpleNamespace(settings={"mail.from": ""})

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


def _kdf(context, key):
    """crypto_kdf_derive_from_key(32, 1, context, key), as libsodium.js
    computes it in the vault: BLAKE2b keyed by the key, the subkey id as its
    salt and the context as its personalisation (test_14 holds the two
    together)."""
    return blake2b(
        b"",
        digest_size=32,
        key=key,
        salt=struct.pack("<Q", 1),
        person=context.encode("ascii"),
        encoder=RawEncoder,
    )


def _signing_key(project_private):
    """A key version's signing key (README 3.6): crypto_sign_seed_keypair
    of crypto_kdf_derive_from_key(32, 1, "fskeysig", the version's sk)."""
    return SigningKey(_kdf("fskeysig", bytes(project_private)))


def _sign_public_key(project_private):
    return format_sign_public_key(
        key_id_of(bytes(project_private.public_key)),
        bytes(_signing_key(project_private).verify_key),
    )


def _key_signature(signer_private, public_key):
    """The signer version's signature of a public key, as the vault makes
    it at set-up (a version signs itself) and at rotation (the current
    version signs the new)."""
    message = key_version_message(
        key_id_of(bytes(signer_private.public_key)), public_key
    )
    return b64u_encode(_signing_key(signer_private).sign(message).signature)


def _signed(project_private, signer_private=None):
    """What set-up and rotation take beside the key: {sign_public_key,
    key_signature}. The signer is the version itself unless given."""
    return {
        "sign_public_key": _sign_public_key(project_private),
        "key_signature": _key_signature(
            signer_private or project_private,
            format_public_key(bytes(project_private.public_key)),
        ),
    }


def _grant(project_private, member, member_public_key, signer_private=None):
    """crypto_box_seal(project sk, member pk), signed by the version for that
    member (member_name) and that key, as the vault makes it: fsenc-grant:3.
    signer_private makes one signed by another key, which the server must
    refuse."""
    key = b64u_decode(member_public_key.split(":")[2])
    the_key_id = key_id_of(bytes(project_private.public_key))
    sealed = b64u_encode(SealedBox(PublicKey(key)).encrypt(bytes(project_private)))
    message = grant_message(the_key_id, sealed, member, format_member_key(key))
    signature = _signing_key(signer_private or project_private).sign(message)
    return "fsenc-grant:3:{}:{}:{}".format(
        the_key_id, sealed, b64u_encode(signature.signature)
    )


def _chain_holds(keys, held):
    """What the vault checks at every unlock (README 3.6), written out as the
    plugin must: one version signs itself; every other is signed by the one
    it replaced, each vouching for one at most; the chain reaches every
    version and ends at the active one; and a version whose private key the
    member holds has the signing key that private key gives. keys: a
    bundle's; held: {key id: private key}."""
    by_id = {key["key_id"]: key for key in keys}
    if any(key["signed_by"] not in by_id for key in keys):
        return False
    roots = [key for key in keys if key["signed_by"] == key["key_id"]]
    vouched = [key["signed_by"] for key in keys if key["signed_by"] != key["key_id"]]
    if len(roots) != 1 or len(vouched) != len(set(vouched)):
        return False
    chain = [roots[0]]
    while chain[-1]["key_id"] in vouched:
        chain.append(
            [
                key
                for key in keys
                if key["signed_by"] == chain[-1]["key_id"] and key is not chain[-1]
            ][0]
        )
    if len(chain) != len(keys) or chain[-1]["key_status"] != "active":
        return False
    for key in keys:
        signer = by_id[key["signed_by"]]
        try:
            check_key_signature(
                key["key_signature"],
                signer["key_id"],
                signer["sign_public_key"],
                key["public_key"],
            )
        except EncryptionFormatError:
            return False
    return all(
        by_id[the_key_id]["sign_public_key"] == _sign_public_key(private)
        for the_key_id, private in held.items()
    )


def _members_unvouched(access, keys, project_id):
    """What the vault checks before sealing a version to members (formshare.md
    14.1 and 15.1), as the plugin must: every grant a holder has verifies,
    with its version's signing key, for that person -- named from the
    listing, user:<user id>, assistant:<uuid> or recovery:<project id> -- and
    the member key listed now. Returns the member ids whose grants do not: a
    key swapped in the database, or someone else's grant copied in."""
    sign_keys = {key["key_id"]: key["sign_public_key"] for key in keys}
    named = [
        (
            entry,
            member_name(
                entry["member_type"], entry.get("user_id") or entry.get("coll_uuid")
            ),
        )
        for entry in access["people"]
        if entry["member"] is not None
    ]
    if access["recovery"]:
        named.append((access["recovery"], member_name("recovery", project_id)))
    failed = []
    for entry, name in named:
        for a_grant in entry["grants"]:
            try:
                check_grant(
                    a_grant["grant"],
                    name,
                    entry["member"]["public_key"],
                    sign_keys[a_grant["key_id"]],
                )
            except EncryptionFormatError:
                failed.append(entry["member"]["member_id"])
                break
    return failed


@contextmanager
def _notices(request):
    """The security notices FormShare dispatches while the block runs, caught
    before Celery would send them: [(to, subject, text)]."""
    sent = []
    request.registry = SimpleNamespace(settings={"mail.from": "noreply@example.org"})
    try:
        with mock.patch.object(send_async_email, "apply_async") as dispatched:
            yield sent
        for call in dispatched.call_args_list:
            sent.append(tuple(call.args[0][2:5]))
    finally:
        del request.registry


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

        # Losing the right to clean loses the key (section 9), in the request
        # that takes the right, and the record names who took it.
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
        access = {
            person.get("coll_uuid") or person.get("user_id"): person
            for person in list_project_access(request, project_id)["people"]
        }
        assert cleaner not in access
        revoked = list_encryption_events(request, project_id, "revoke")[0]
        assert (revoked["actor_type"], revoked["actor_id"]) == ("user", login)
        assert revoked["event_detail"]["reason"] == "not eligible"
        # Nothing is left for a sweep to take.
        assert revoke_ineligible_members(request, project_id) == 0

        _removing(request, session, config, login, project_id)
    finally:
        session.close()
        engine.dispose()


def _removing(request, session, config, login, project_id):
    """A project's encryption removed by the server's administrator, from the
    command line (formshare.md 16.2): what it shows, that it changes nothing
    without --yes, what it removes and records, and that the owner can set
    encryption up again."""
    ini = config["global:config:file"]
    assert remove_encryption([ini, login, "no_such_project"]) == 1
    session.rollback()
    before = sorted(a_key["key_id"] for a_key in get_project_keys(request, project_id))
    assert before
    assert remove_encryption([ini, login, CODE]) == 1
    session.rollback()
    assert sorted(
        a_key["key_id"] for a_key in get_project_keys(request, project_id)
    ) == (before)
    assert remove_encryption(["--yes", "--reason", "the suite", ini, login, CODE]) == 0
    session.rollback()
    assert get_project_keys(request, project_id) == []
    assert get_active_project_key(request, project_id) is None
    assert (
        session.execute(
            "SELECT COUNT(*) FROM encryption_grant WHERE project_id = :p",
            {"p": project_id},
        ).fetchone()[0]
        == 0
    )
    assert get_member(request, "recovery", project_id) is None
    assert session.query(Project).get(project_id).project_encrypted == 0
    removed = list_encryption_events(request, project_id, "encryption_removed")[0]
    assert removed["actor_type"] == "system" and removed["actor_id"]
    assert sorted(removed["event_detail"]["key_ids"]) == before
    assert removed["event_detail"]["reason"] == "the suite"
    assert remove_encryption(["--yes", ini, login, CODE]) == 1
    # Set up again by its owner, with a key of their own.
    owner_member = get_member(request, "user", login)
    project_private, public_key = _project_key()
    kit = _Person()
    ok, key_id = set_up_project_encryption(
        request,
        project_id,
        public_key,
        owner_member["member_id"],
        _grant(project_private, member_name("user", login), owner_member["public_key"]),
        kit.public_key,
        _grant(project_private, member_name("recovery", project_id), kit.public_key),
        login,
        **_signed(project_private),
    )
    assert ok and key_id == key_id_of(bytes(project_private.public_key)), key_id


def _run(
    request, session, project_id, login, collaborator, cleaner, submitter, set_role
):
    owner, editor, assistant, other = _Person(), _Person(), _Person(), _Person()
    # Who each is, as a grant's signature names them (formshare.md 15.1).
    owner.name = member_name("user", login)
    editor.name = member_name("user", collaborator)
    assistant.name = member_name("assistant", cleaner)
    other.name = member_name("assistant", submitter)

    # --- Nothing yet ------------------------------------------------------------
    assert get_active_project_key(request, project_id) is None
    assert get_project_keys(request, project_id) == []
    assert get_member(request, "user", login) is None
    assert get_unlock_bundle(request, "user", login, project_id) is None

    # --- Enrolling --------------------------------------------------------------
    # A person hears of every key registered for them: a stolen session could
    # register one of its own and receive what is given to them (formshare.md
    # 14.2).
    owner_email = (
        session.query(User.user_email).filter(User.user_id == login).first()[0]
    )
    assert owner_email
    with _notices(request) as sent:
        ok, owner_id = enroll_member(
            request, "user", login, owner.public_key, owner.unlock()
        )
    assert ok, owner_id
    assert [(to, subject) for to, subject, _text in sent] == [
        (owner_email, "FormShare - An encryption key was registered for you")
    ]
    assert login in sent[0][2] and "start again" in sent[0][2]
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
    # A mail server that is down does not undo what the notice follows.
    request.registry = SimpleNamespace(settings={"mail.from": "noreply@example.org"})
    with mock.patch.object(
        send_async_email, "apply_async", side_effect=RuntimeError("down")
    ):
        ok, editor_id = enroll_member(
            request, "user", collaborator, editor.public_key, editor.unlock()
        )
    del request.registry
    assert ok, editor_id
    session.execute(
        "UPDATE collaborator SET coll_email = :e WHERE coll_uuid = :u",
        {"e": "enc_cleaner@example.org", "u": cleaner},
    )
    session.commit()
    with _notices(request) as sent:
        ok, assistant_id = enroll_member(
            request, "assistant", cleaner, assistant.public_key, assistant.unlock()
        )
    assert ok, assistant_id
    assert [(to, subject) for to, subject, _text in sent] == [
        (
            "enc_cleaner@example.org",
            "FormShare - An encryption key was registered for you",
        )
    ]
    assert "enc_cleaner" in sent[0][2] and "Encryption keys" in sent[0][2]
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

    # --- The owner's alarm, holding nothing -----------------------------------------
    # An owner using the recovery kit often holds no grant, which is why they
    # use it: their key alarm is recorded all the same (formshare.md 15.2).
    # Nobody else's is, and a browser's other event still needs a grant.
    assert log_encryption_event(
        request, project_id, "user", login, "key_alarm", {"reason": "member key"}
    ) == (True, "")
    assert not log_encryption_event(
        request, project_id, "user", collaborator, "key_alarm"
    )[0]
    assert not log_encryption_event(
        request, project_id, "user", login, "decrypted", {"answers": 1}
    )[0]

    # --- Setting up ------------------------------------------------------------------
    recovery = _Person()
    recovery.name = member_name("recovery", project_id)
    project_private, public_key = _project_key()
    the_key_id = parse_public_key(public_key)[0]
    ok, message = set_up_project_encryption(
        request,
        project_id,
        public_key,
        editor_id,
        _grant(project_private, editor.name, editor.public_key),
        recovery.public_key,
        _grant(project_private, recovery.name, recovery.public_key),
        collaborator,
        **_signed(project_private),
    )
    assert not ok and "owner" in message
    stranger, _ = _project_key()
    ok, message = set_up_project_encryption(
        request,
        project_id,
        public_key,
        owner_id,
        _grant(stranger, owner.name, owner.public_key),
        recovery.public_key,
        _grant(project_private, recovery.name, recovery.public_key),
        login,
        **_signed(project_private),
    )
    assert not ok and "not of the new key" in message

    def set_up(owner_grant, **signed):
        return set_up_project_encryption(
            request,
            project_id,
            public_key,
            owner_id,
            owner_grant,
            recovery.public_key,
            _grant(project_private, recovery.name, recovery.public_key),
            login,
            **signed,
        )

    # The first version comes signed by itself (README 3.6); its grants by it,
    # for the members they are given to.
    ok, message = set_up(_grant(project_private, owner.name, owner.public_key))
    assert not ok and "signing key" in message
    ok, message = set_up(
        _grant(project_private, owner.name, owner.public_key),
        sign_public_key=_sign_public_key(project_private),
        key_signature=_key_signature(stranger, public_key),
    )
    assert not ok and "not signed by its key" in message
    ok, message = set_up(
        _grant(project_private, owner.name, owner.public_key),
        sign_public_key=_sign_public_key(stranger),
        key_signature=_key_signature(project_private, public_key),
    )
    assert not ok and "not of the new key" in message
    for owner_grant in (
        _grant(project_private, editor.name, editor.public_key),
        _grant(project_private, owner.name, owner.public_key, signer_private=stranger),
    ):
        ok, message = set_up(owner_grant, **_signed(project_private))
        assert not ok and "not signed by its key" in message, message
    with _notices(request) as sent:
        ok, key_id = set_up(
            _grant(project_private, owner.name, owner.public_key),
            **_signed(project_private),
        )
    assert ok and key_id == the_key_id, key_id
    # The owner hears of every set-up: a project with no key has no version to
    # vouch for the first, so a stolen session could set up one of its own.
    assert [(to, subject) for to, subject, _text in sent] == [
        (owner_email, "FormShare - Encryption was set up for your project")
    ]
    assert key_id in sent[0][2] and "Encryption keys" in sent[0][2]
    assert get_active_project_key(request, project_id) == public_key
    (first,) = get_project_keys(request, project_id)
    assert first["sign_public_key"] == _sign_public_key(project_private)
    assert first["signed_by"] == key_id
    check_key_signature(
        first["key_signature"], key_id, first["sign_public_key"], public_key
    )
    # A new transaction, to see what the request just committed.
    session.rollback()
    assert session.query(Project).get(project_id).project_encrypted == 1
    ok, message = set_up(
        _grant(project_private, owner.name, owner.public_key),
        **_signed(project_private),
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
        "grant": _grant(project_private, editor.name, editor.public_key),
    }
    for_assistant = {
        "member_id": assistant_id,
        "grant": _grant(project_private, assistant.name, assistant.public_key),
    }
    ok, message = add_grants(request, project_id, [for_assistant], collaborator)
    assert not ok and "owner or an admin" in message
    ok, message = add_grants(
        request,
        project_id,
        [
            {
                "member_id": other_id,
                "grant": _grant(project_private, other.name, other.public_key),
            }
        ],
        login,
    )
    assert not ok and "may not hold" in message
    ok, message = add_grants(
        request,
        project_id,
        [
            {
                "member_id": editor_id,
                "grant": _grant(stranger, editor.name, editor.public_key),
            }
        ],
        login,
    )
    assert not ok and "does not have" in message
    # A grant is signed by the version it gives, for the member it is given
    # to: a session with the right but not the key -- which could otherwise
    # replace every member's grant with one that opens nothing -- gives
    # nothing (formshare.md 13.1).
    sealed = for_editor["grant"].split(":")[3]
    for bad in (
        "fsenc-grant:3:{}:{}:{}".format(key_id, sealed, b64u_encode(bytes(64))),
        _grant(project_private, assistant.name, assistant.public_key),
        _grant(
            project_private, editor.name, editor.public_key, signer_private=stranger
        ),
        # The editor's own key, in a grant made for someone else (15.1).
        _grant(project_private, assistant.name, editor.public_key),
    ):
        ok, message = add_grants(
            request, project_id, [{"member_id": editor_id, "grant": bad}], login
        )
        assert not ok and "not signed by its key" in message, message
    # Version 1 had no signature; version 2 named the key but not the member.
    for old in (
        "fsenc-grant:1:{}:{}".format(key_id, sealed),
        "fsenc-grant:2:{}:{}:{}".format(key_id, sealed, b64u_encode(bytes(64))),
    ):
        ok, message = add_grants(
            request, project_id, [{"member_id": editor_id, "grant": old}], login
        )
        assert not ok and "fsenc-grant:3" in message, message
    assert add_grants(request, project_id, [for_editor, for_assistant], login) == (
        True,
        2,
    )
    # The record names the person, not only the member row (formshare.md 16.1).
    named = {
        event["event_detail"]["member_id"]: event["event_detail"]["member_name"]
        for event in list_encryption_events(request, project_id, "grant")[:2]
    }
    assert named == {editor_id: editor.name, assistant_id: assistant.name}
    # An admin who holds the key may give it.
    set_role(2)
    # A new transaction, to see what the request just committed.
    session.rollback()
    assert add_grants(request, project_id, [for_assistant], collaborator) == (True, 1)

    # --- Member keys, vouched for by their grants (formshare.md 14.1) -----------
    listed = list_project_access(request, project_id)
    by_person = {
        person.get("coll_uuid") or person.get("user_id"): person
        for person in listed["people"]
    }
    assert [a_grant["key_id"] for a_grant in by_person[collaborator]["grants"]] == [
        key_id
    ]
    assert [a_grant["key_id"] for a_grant in listed["recovery"]["grants"]] == [key_id]
    assert _members_unvouched(listed, listed["keys"], project_id) == []
    # Someone who can write the database swaps the editor's member key for one
    # of their own. The server's checks pass, and so does the vault's chain;
    # the editor's grant, signed for the real key, does not, so the browser
    # seals nothing to the swapped one.
    for member_key in (_Person().public_key, editor.public_key):
        session.execute(
            "UPDATE encryption_member SET public_key = :k WHERE member_id = :m",
            {"k": member_key, "m": editor_id},
        )
        session.commit()
        unvouched = _members_unvouched(
            list_project_access(request, project_id), listed["keys"], project_id
        )
        assert unvouched == ([] if member_key == editor.public_key else [editor_id])
    # Someone who can write the database and holds grants of their own -- the
    # assistant here -- copies one onto the editor, with their own key beside
    # it. The key matches the grant; the person does not, so the browser seals
    # nothing to it (formshare.md 15.1).
    (editor_grant,) = by_person[collaborator]["grants"]
    (assistant_grant,) = by_person[cleaner]["grants"]
    for grant_value, member_key in (
        (assistant_grant["grant"], assistant.public_key),
        (editor_grant["grant"], editor.public_key),
    ):
        session.execute(
            "UPDATE encryption_grant SET grant_value = :g WHERE project_id = :p "
            "AND member_id = :m",
            {"g": grant_value, "p": project_id, "m": editor_id},
        )
        session.execute(
            "UPDATE encryption_member SET public_key = :k WHERE member_id = :m",
            {"k": member_key, "m": editor_id},
        )
        session.commit()
        unvouched = _members_unvouched(
            list_project_access(request, project_id), listed["keys"], project_id
        )
        assert unvouched == (
            [] if member_key == editor.public_key else [editor_id]
        ), unvouched

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
    assert _chain_holds(bundle["project"]["keys"], {grant["key_id"]: opened})
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
        {
            "member_id": member_id,
            "grant": _grant(new_private, person.name, person.public_key),
        }
        for member_id, person in holders.items()
    ]
    for_recovery = {
        "member_id": recovery_id,
        "grant": _grant(new_private, recovery.name, recovery.public_key),
    }
    signed = _signed(new_private, project_private)
    everyone = grants + [for_recovery]
    ok, message = rotate_project_key(
        request, project_id, new_public, grants, login, **signed
    )
    assert not ok and "recovery kit included" in message
    ok, message = rotate_project_key(
        request, project_id, new_public, everyone, collaborator, **signed
    )
    assert not ok and "owner" in message
    # The current version vouches for the new one: the owner's session alone
    # -- no signature, the new key vouching for itself, a stranger's key --
    # cannot put in a key of its own (formshare.md 13.1).
    ok, message = rotate_project_key(request, project_id, new_public, everyone, login)
    assert not ok and "signing key" in message
    for signer in (new_private, stranger):
        ok, message = rotate_project_key(
            request,
            project_id,
            new_public,
            everyone,
            login,
            **_signed(new_private, signer),
        )
        assert not ok and "signed by the project's current key" in message, message
    # The new version's grants are signed by the new version.
    ok, message = rotate_project_key(
        request,
        project_id,
        new_public,
        grants
        + [
            {
                "member_id": recovery_id,
                "grant": _grant(
                    new_private,
                    recovery.name,
                    recovery.public_key,
                    signer_private=project_private,
                ),
            }
        ],
        login,
        **signed,
    )
    assert not ok and "not signed by its key" in message
    ok, new_key_id = rotate_project_key(
        request, project_id, new_public, everyone, login, **signed
    )
    assert ok, new_key_id
    rotated = list_encryption_events(request, project_id, "rotate")[0]
    assert rotated["event_detail"]["member_names"] == sorted(
        [owner.name, editor.name, assistant.name, recovery.name]
    )
    assert get_active_project_key(request, project_id) == new_public
    keys = get_project_keys(request, project_id)
    assert {key["key_id"]: (key["key_status"], key["signed_by"]) for key in keys} == {
        key_id: ("retired", key_id),
        new_key_id: ("active", key_id),
    }
    ok, message = rotate_project_key(
        request,
        project_id,
        public_key,
        [
            {
                "member_id": owner_id,
                "grant": _grant(project_private, owner.name, owner.public_key),
            }
        ],
        login,
        **_signed(project_private, new_private),
    )
    assert not ok and "used this key before" in message

    # --- What a vault checks of the chain, at every unlock ------------------------
    held = {key_id: project_private, new_key_id: new_private}
    assert _chain_holds(keys, held)
    # Someone who can write the database puts in a key of their own, with
    # genuine grants for every holder: no session, no API, and the
    # substitution check passes, since that key matches itself. The chain does
    # not: nothing the intruder holds signs for the current version, and a
    # chain of its own beside the project's is no chain.
    intruder, intruder_public = _project_key()
    swapped = [dict(key, key_status="retired") for key in keys] + [
        dict(
            key_id=key_id_of(bytes(intruder.public_key)),
            public_key=intruder_public,
            key_status="active",
            signed_by=new_key_id,
            **_signed(intruder),
        )
    ]
    assert not _chain_holds(swapped, held)
    swapped[-1]["signed_by"] = swapped[-1]["key_id"]
    assert not _chain_holds(swapped, held)
    # Replacing every signing key with one of its own and signing the chain
    # again passes the signatures; a member who holds a version sees that its
    # signing key is not the one its private key gives. That derivation is
    # what ties the chain to the keys.
    fake = SigningKey.generate()

    def resigned(key, signer_key_id):
        return dict(
            key,
            sign_public_key=format_sign_public_key(
                key["key_id"], bytes(fake.verify_key)
            ),
            key_signature=b64u_encode(
                fake.sign(
                    key_version_message(signer_key_id, key["public_key"])
                ).signature
            ),
        )

    forged = [resigned(keys[0], key_id), resigned(keys[1], key_id)]
    assert _chain_holds(forged, {})
    assert not _chain_holds(forged, {new_key_id: new_private})

    # --- Revoking ------------------------------------------------------------------------
    ok, message = revoke_member(request, project_id, owner_id, collaborator)
    assert not ok and "owner" in message
    ok, message = revoke_member(request, project_id, recovery_id, login)
    assert not ok and "replaced" in message
    assert revoke_member(request, project_id, editor_id, login) == (True, 2)
    taken = list_encryption_events(request, project_id, "revoke")[0]["event_detail"]
    assert (taken["member_id"], taken["member_name"]) == (editor_id, editor.name)
    ok, message = revoke_member(request, project_id, assistant_id, collaborator)
    assert not ok and "holds the project's key" in message

    # --- A new recovery kit, and the kit used ----------------------------------------
    new_recovery = _Person()
    new_recovery.name = member_name("recovery", project_id)
    ok, message = replace_recovery_member(
        request,
        project_id,
        new_recovery.public_key,
        [_grant(new_private, new_recovery.name, new_recovery.public_key)],
        login,
    )
    assert not ok and "every version" in message
    # A replacement deletes the old kit's grants: grants that open nothing,
    # from a session without the key, would leave no way back.
    ok, message = replace_recovery_member(
        request,
        project_id,
        new_recovery.public_key,
        [
            _grant(
                project_private,
                new_recovery.name,
                new_recovery.public_key,
                signer_private=stranger,
            ),
            _grant(new_private, new_recovery.name, new_recovery.public_key),
        ],
        login,
    )
    assert not ok and "not signed by its key" in message
    assert get_member(request, "recovery", project_id)["member_id"] == recovery_id
    ok, new_recovery_id = replace_recovery_member(
        request,
        project_id,
        new_recovery.public_key,
        [
            _grant(project_private, new_recovery.name, new_recovery.public_key),
            _grant(new_private, new_recovery.name, new_recovery.public_key),
        ],
        login,
    )
    assert ok, new_recovery_id
    assert get_member(request, "recovery", project_id)["member_id"] == new_recovery_id
    replaced = list_encryption_events(request, project_id, "recovery_replaced")[0]
    assert replaced["event_detail"]["member_name"] == new_recovery.name
    assert get_recovery_bundle(request, project_id, collaborator) is None
    kit = get_recovery_bundle(request, project_id, login)
    assert sorted(grant["key_id"] for grant in kit["project"]["grants"]) == sorted(
        [key_id, new_key_id]
    )
    ok, message = grant_with_recovery(
        request,
        project_id,
        [
            {
                "member_id": editor_id,
                "grant": _grant(
                    new_private, editor.name, editor.public_key, signer_private=stranger
                ),
            }
        ],
        login,
    )
    assert not ok and "not signed by its key" in message
    ok, count = grant_with_recovery(
        request,
        project_id,
        [
            {
                "member_id": editor_id,
                "grant": _grant(project_private, editor.name, editor.public_key),
            },
            {
                "member_id": editor_id,
                "grant": _grant(new_private, editor.name, editor.public_key),
            },
        ],
        login,
    )
    assert (ok, count) == (True, 2)
    used = list_encryption_events(request, project_id, "recovery_used")[0]
    assert used["event_detail"]["member_ids"] == [editor_id]
    assert used["event_detail"]["member_names"] == [editor.name]

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
    assert setup["event_detail"]["member_names"] == [owner.name, recovery.name]

    # --- A key set up before versions were signed ---------------------------------
    # Nobody can show they hold it, so nothing more is given of it and it is
    # not changed: encryption is set up again (the migration's note).
    session.query(EncryptionProjectKey).filter(
        EncryptionProjectKey.project_id == project_id
    ).update({"sign_public_key": None, "signed_by": None, "key_signature": None})
    session.commit()
    ok, message = add_grants(
        request,
        project_id,
        [
            {
                "member_id": editor_id,
                "grant": _grant(new_private, editor.name, editor.public_key),
            }
        ],
        login,
    )
    assert not ok and "before key versions were signed" in message
    third_private, third_public = _project_key()
    ok, message = rotate_project_key(
        request,
        project_id,
        third_public,
        [
            {
                "member_id": owner_id,
                "grant": _grant(third_private, owner.name, owner.public_key),
            }
        ],
        login,
        **_signed(third_private, new_private),
    )
    assert not ok and "before key versions were signed" in message
