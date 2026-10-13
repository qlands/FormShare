"""Losing access takes the key (formshare.md section 9).

Whoever may no longer hold a project's key loses it the moment the change
that took their right is made, and the record says so:

- a collaborator made a plain member, or removed from the project;
- an assistant whose right to clean is taken, on a form or through a group,
  or whose group is deactivated, or who is deactivated;
- an assistant deleted, and a project deleted: their grants go with them
  through ON DELETE CASCADE, and the record is written once they have gone.

The step calls the very functions the pages call (processes/db), so that the
rule holds for every page and for the API that reach them.
"""

import os
import shutil
import uuid
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from formshare.processes.db.assistant import delete_assistant, modify_assistant
from formshare.processes.db.assistant_group import modify_group
from formshare.processes.db.collaborator import (
    add_collaborator_to_project,
    remove_collaborator_from_project,
    set_collaborator_role,
)
from formshare.processes.db.encryption import (
    member_name,
    add_grants,
    enroll_member,
    get_member,
    list_encryption_events,
    list_project_access,
    set_up_project_encryption,
)
from formshare.processes.db.form import (
    update_assistant_privileges,
    update_group_privileges,
)
from formshare.processes.db.project import delete_project
from .encryption_forms import (
    MARKED_FORM,
    _assistant,
    _give,
    _new_project,
    _project_id,
    _query,
    _upload,
    _workbook,
)
from .encryption_keys import _Person, _Request, _grant, _project_key, _signed

CODE = "enc_access"
DOOMED = "enc_access_gone"


class _User:
    def __init__(self, login):
        self.login = login


def t_e_s_t_encryption_access(test_object):
    login = test_object.randonLogin
    testapp = test_object.testapp
    config = test_object.server_config
    work = os.path.join(test_object.working_dir, "encryption_access")
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    session = sessionmaker(bind=engine)()
    try:
        _run(test_object, login, testapp, config, work, engine, session)
    finally:
        session.close()
        engine.dispose()


def _member(request, member_type, identity):
    """The member's id and public key, enrolling it when it has none."""
    existing = get_member(request, member_type, identity)
    if existing is not None:
        return existing["member_id"], existing["public_key"]
    person = _Person()
    ok, member_id = enroll_member(
        request, member_type, identity, person.public_key, person.unlock()
    )
    assert ok, member_id
    return member_id, person.public_key


def _set_up(request, project_id, login):
    owner_id, owner_public = _member(request, "user", login)
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
    return project_private


def _run(test_object, login, testapp, config, work, engine, session):
    collaborator = test_object.collaboratorLogin
    request = _Request(session)
    request.user = _User(login)
    request.registry = SimpleNamespace(settings=config)

    _new_project(testapp, login, CODE)
    project_id = _project_id(engine, login, CODE)
    project_private = _set_up(request, project_id, login)
    _upload(
        testapp,
        login,
        CODE,
        _workbook(os.path.join(work, "enc_access.xlsx"), "enc_access", MARKED_FORM),
    )
    cleaner = _assistant(testapp, login, CODE)
    _give(testapp, login, CODE, "enc_access", project_id, cleaner)
    grouped = _assistant(testapp, login, CODE)
    group_id = uuid.uuid4().hex[:12]
    with engine.begin() as connection:
        connection.execute(
            "INSERT INTO collgroup (project_id, group_id, group_desc, group_active) "
            "VALUES (%(p)s, %(g)s, %(d)s, 1)",
            {"p": project_id, "g": group_id, "d": "cleaners " + group_id},
        )
        connection.execute(
            "INSERT INTO collingroup (project_id, group_id, enum_project, coll_id, "
            "coll_uuid) VALUES (%(p)s, %(g)s, %(p)s, %(c)s, %(u)s)",
            {"p": project_id, "g": group_id, "c": grouped[0], "u": grouped[1]},
        )
        connection.execute(
            "INSERT INTO formgrpaccess (project_id, group_id, form_project, form_id, "
            "group_can_submit, group_can_clean) VALUES (%(p)s, %(g)s, %(p)s, "
            "'enc_access', 1, 1)",
            {"p": project_id, "g": group_id},
        )
    assert add_collaborator_to_project(request, project_id, collaborator, 3)[0]

    members = {
        "editor": _member(request, "user", collaborator),
        "cleaner": _member(request, "assistant", cleaner[1]),
        "grouped": _member(request, "assistant", grouped[1]),
    }
    # Who each is, as a grant's signature names them (formshare.md 15.1).
    member_names = {
        "editor": member_name("user", collaborator),
        "cleaner": member_name("assistant", cleaner[1]),
        "grouped": member_name("assistant", grouped[1]),
    }

    def grant(*names):
        ok, count = add_grants(
            request,
            project_id,
            [
                {
                    "member_id": members[name][0],
                    "grant": _grant(
                        project_private, member_names[name], members[name][1]
                    ),
                }
                for name in names
            ],
            login,
        )
        assert ok, count

    def holds(name):
        session.rollback()
        return bool(
            _query(
                engine,
                "SELECT COUNT(*) FROM encryption_grant WHERE project_id = %(p)s "
                "AND member_id = %(m)s",
                p=project_id,
                m=members[name][0],
            )[0][0]
        )

    def last_revoke():
        session.rollback()
        return list_encryption_events(request, project_id, "revoke")[0]

    grant("editor", "cleaner", "grouped")
    assert holds("editor") and holds("cleaner") and holds("grouped")

    # --- A collaborator made a plain member, then removed --------------------
    assert set_collaborator_role(request, project_id, collaborator, 4)[0]
    assert not holds("editor") and holds("cleaner") and holds("grouped")
    revoked = last_revoke()
    assert (revoked["actor_type"], revoked["actor_id"]) == ("user", login)
    assert revoked["event_detail"]["member_id"] == members["editor"][0]
    assert revoked["event_detail"]["member_name"] == member_names["editor"]
    assert revoked["event_detail"]["reason"] == "not eligible"
    # An editor again may be given it again.
    assert set_collaborator_role(request, project_id, collaborator, 3)[0]
    grant("editor")
    assert remove_collaborator_from_project(request, project_id, collaborator)[0]
    assert not holds("editor")

    # --- An assistant whose right to clean is taken on the form --------------
    assert update_assistant_privileges(
        request,
        project_id,
        "enc_access",
        cleaner[1],
        {"coll_can_submit": 1, "coll_can_clean": 0},
    )[0]
    assert not holds("cleaner") and holds("grouped")

    # --- Through a group: its right on the form, then the group itself -------
    assert update_group_privileges(request, project_id, "enc_access", group_id, 1, 0)[0]
    assert not holds("grouped")
    assert update_group_privileges(request, project_id, "enc_access", group_id, 1, 1)[0]
    grant("grouped")
    assert modify_group(
        request,
        project_id,
        group_id,
        {"group_desc": "cleaners " + group_id, "group_active": 0},
    )[0]
    assert not holds("grouped")

    # --- An assistant deactivated, then deleted ----------------------------------
    assert update_assistant_privileges(
        request,
        project_id,
        "enc_access",
        cleaner[1],
        {"coll_can_submit": 1, "coll_can_clean": 1},
    )[0]
    grant("cleaner")
    assert modify_assistant(request, cleaner[1], {"coll_active": 0})[0]
    assert not holds("cleaner")
    assert modify_assistant(request, cleaner[1], {"coll_active": 1})[0]
    grant("cleaner")
    assert delete_assistant(request, cleaner[1])[0]
    assert not holds("cleaner")
    revoked = last_revoke()
    assert revoked["event_detail"]["member_id"] == members["cleaner"][0]
    assert revoked["event_detail"]["reason"] == "assistant deleted"
    # Named, though the member row went with the assistant (formshare.md 16.1).
    assert revoked["event_detail"]["member_name"] == member_names["cleaner"]
    session.rollback()
    assert get_member(request, "assistant", cleaner[1]) is None

    # --- A project deleted: its keys and grants go, the record stays ----------
    _new_project(testapp, login, DOOMED)
    doomed = _project_id(engine, login, DOOMED)
    session.rollback()  # a new transaction, to see the project just made
    _set_up(request, doomed, login)
    holders = len(list_project_access(request, doomed)["people"]) + 1  # the kit
    assert delete_project(request, login, doomed)[0]
    session.rollback()
    gone = list_encryption_events(request, doomed, "revoke")
    assert len(gone) == holders, gone
    assert {event["event_detail"]["reason"] for event in gone} == {"project deleted"}
    assert all(event["event_detail"]["member_name"] for event in gone)
    assert member_name("recovery", doomed) in {
        event["event_detail"]["member_name"] for event in gone
    }
    assert (
        _query(
            engine,
            "SELECT COUNT(*) FROM encryption_project_key WHERE project_id = %(p)s",
            p=doomed,
        )[0][0]
        == 0
    )
