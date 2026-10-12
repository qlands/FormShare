"""Field encryption: the formats, and the server's record of who holds keys.

docs/formshare_field_encryption/ is the design record: README.md has the
formats and the split between FormShare core, the Encryption plugin and
RSTools; formshare.md is core's part. Read them before changing a shape here.

The rule this module keeps: **the server never opens anything.** It seals
answers with a project's public key, and it stores what a browser hands it --
public keys, member keys the browser has locked, grants the browser has
sealed -- checking that each has the shape the formats give it and that the
person asking may do what they ask. Nothing here can open an envelope, a
grant or a locked key, and nothing here should ever be able to.

The sealing is libsodium's sealed box, through PyNaCl: an ephemeral X25519
key and XSalsa20-Poly1305, the answer padded to 32-byte blocks first so that
a short answer does not give away its length. It is byte for byte what
RSTools' common/sealing.h does, and test_vectors.json holds envelopes RSTools
made that these functions must accept.

Which answers to seal is decided the way RSTools decides it: an answer's key
is its path below the submission's root -- groups and repeats included, as
``household/member/age`` -- which is the key the submission's JSON gives it
and the ``xmlcode`` the form's manifest gives the question. A question is
marked when its field in the manifest says ``fs_encrypted="true"``.
"""

import base64
import datetime
import hashlib
import json
import logging
import os
import re
import uuid

import nacl.bindings
from lxml import etree
from sqlalchemy import and_, or_, text

from formshare.models import (
    Collaborator,
    Collgroup,
    Collingroup,
    DictField,
    EncryptionEvent,
    EncryptionGrant,
    EncryptionMember,
    EncryptionProjectKey,
    EncryptionUnlock,
    Formacces,
    Formgrpacces,
    Project,
    User,
    Userproject,
)
from formshare.processes.logging.loggerclass import SecretLogger

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

__all__ = [
    "EncryptionFormatError",
    "b64u_encode",
    "b64u_decode",
    "key_id",
    "parse_public_key",
    "format_public_key",
    "parse_member_key",
    "parse_grant",
    "check_locked_key",
    "check_unlock_params",
    "is_envelope",
    "seal",
    "seal_submission",
    "seal_xml",
    "marked_xmlcodes",
    "marked_columns",
    "survey_marks",
    "field_is_encrypted",
    "field_labelled_encrypted",
    "invalid_encrypted_fields_heading",
    "describe_invalid_encrypted_fields",
    "encryption_change_message",
    "KEY_NEEDED",
    "key_needed_message",
    "encrypted_columns",
    "encrypted_column_message",
    "is_encrypted_refusal",
    "encrypted_edit_message",
    "manifest_marks",
    "get_active_project_key_with_engine",
    "submission_digest",
    "seal_json_text",
    "no_key_message",
    "get_user_role",
    "assistant_can_clean",
    "member_is_eligible",
    "get_member",
    "enroll_member",
    "retire_member",
    "add_unlock_method",
    "remove_unlock_method",
    "rename_unlock_method",
    "list_unlock_methods",
    "unlock_method_used",
    "get_unlock_bundle",
    "get_recovery_bundle",
    "get_active_project_key",
    "get_project_keys",
    "set_up_project_encryption",
    "rotate_project_key",
    "add_grants",
    "grant_with_recovery",
    "revoke_member",
    "revoke_ineligible_members",
    "access_changed",
    "member_access_changed",
    "grants_before_deletion",
    "record_deleted_grants",
    "list_project_access",
    "replace_recovery_member",
    "log_encryption_event",
    "list_encryption_events",
]

# A version 1 envelope is the sealed box of the answer padded to whole
# blocks: crypto_box_SEALBYTES (48: the ephemeral public key and the MAC)
# more than a multiple of 32, at least one block.
BLOCK = 32
SEALBYTES = nacl.bindings.crypto_box_SEALBYTES
KEY_BYTES = nacl.bindings.crypto_box_PUBLICKEYBYTES
# A grant is the project's 32-byte private key sealed to a member: no padding.
GRANT_BYTES = nacl.bindings.crypto_box_SECRETKEYBYTES + SEALBYTES
# A locked member key is crypto_secretbox_easy of the member's 32-byte
# private key: a 24-byte nonce beside it, a 16-byte MAC inside it.
NONCE_BYTES = nacl.bindings.crypto_secretbox_NONCEBYTES
LOCKED_KEY_BYTES = (
    nacl.bindings.crypto_box_SECRETKEYBYTES + nacl.bindings.crypto_secretbox_MACBYTES
)
# README 3.2: a passkey's PRF salt, and the least a passphrase is stretched.
PRF_SALT_BYTES = 32
PASSPHRASE_SALT_BYTES = 16
PASSPHRASE_OPSLIMIT = 3
PASSPHRASE_MEMLIMIT = 64 * 1024 * 1024
# A WebAuthn credential id is at most 1023 bytes.
CREDENTIAL_ID_BYTES = 1023

_B64U = re.compile(r"[A-Za-z0-9_-]*")
_KEY_ID = re.compile(r"[0-9a-f]{16}")


class EncryptionFormatError(ValueError):
    """Text that does not have the shape the formats give it. The message
    says what is wrong, in English, for the log and for the person who sent
    it -- in practice a plugin, since people do not type keys."""


# ---------------------------------------------------------------------------
# The formats (README 3), pure
# ---------------------------------------------------------------------------


def b64u_encode(data):
    """base64url without '=' padding (RFC 4648 section 5)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64u_decode(text):
    """The bytes of base64url without padding. Refuses anything else --
    another alphabet, padding, a length no encoding gives -- rather than
    skipping what it does not know, which is what Python's decoder does."""
    if not isinstance(text, str) or not _B64U.fullmatch(text) or len(text) % 4 == 1:
        raise EncryptionFormatError("it is not base64url without padding")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def key_id(public_key_bytes):
    """The first 8 bytes of SHA-256 of a public key, in lower-case hex."""
    return hashlib.sha256(public_key_bytes).hexdigest()[:16]


def _decoded(text, size, what):
    try:
        value = b64u_decode(text)
    except EncryptionFormatError:
        value = None
    if value is None or len(value) != size:
        raise EncryptionFormatError(
            "{} is not {} bytes of base64url".format(what, size)
        )
    return value


def parse_public_key(text):
    """(key id, the key's 32 bytes) of ``fsenc-pk:1:<key id>:<key>``.

    A key whose id is not the digest of its own bytes is refused: it was
    cut, mistyped or put together from two keys, and sealing to it would
    lose every answer. As RSTools' parsePublicKey does, the text is trimmed
    first."""
    parts = text.strip().split(":") if isinstance(text, str) else []
    if len(parts) != 4 or parts[0] != "fsenc-pk" or parts[1] != "1":
        raise EncryptionFormatError(
            "it is not a public key of the form fsenc-pk:1:<key id>:<key>"
        )
    key = _decoded(parts[3], KEY_BYTES, "its key")
    if key_id(key) != parts[2]:
        raise EncryptionFormatError(
            "its key id is not the key's own ({})".format(key_id(key))
        )
    return parts[2], key


def format_public_key(public_key_bytes):
    """``fsenc-pk:1:<key id>:<key>``, as every tool reads it."""
    return "fsenc-pk:1:{}:{}".format(
        key_id(public_key_bytes), b64u_encode(public_key_bytes)
    )


def parse_member_key(text):
    """The 32 bytes of a member's public key, ``fsenc-mk:1:<key>``. The
    recovery member's key has the same form."""
    parts = text.strip().split(":") if isinstance(text, str) else []
    if len(parts) != 3 or parts[0] != "fsenc-mk" or parts[1] != "1":
        raise EncryptionFormatError(
            "it is not a member key of the form fsenc-mk:1:<key>"
        )
    return _decoded(parts[2], KEY_BYTES, "its key")


def parse_grant(text):
    """The key id a grant gives, from ``fsenc-grant:1:<key id>:<sealed key>``.
    What it seals cannot be checked here -- only the grantee can open it --
    but its size can: a 32-byte private key in a sealed box."""
    parts = text.strip().split(":") if isinstance(text, str) else []
    if (
        len(parts) != 4
        or parts[0] != "fsenc-grant"
        or parts[1] != "1"
        or not _KEY_ID.fullmatch(parts[2])
    ):
        raise EncryptionFormatError(
            "it is not a grant of the form fsenc-grant:1:<key id>:<sealed key>"
        )
    _decoded(parts[3], GRANT_BYTES, "its sealed key")
    return parts[2]


def check_locked_key(locked_key):
    """A member's private key as the browser locked it: ``{"nonce", "box"}``,
    both base64url. Returned as the JSON text the database keeps."""
    if isinstance(locked_key, str):
        try:
            locked_key = json.loads(locked_key)
        except ValueError:
            locked_key = None
    if not isinstance(locked_key, dict) or set(locked_key) != {"nonce", "box"}:
        raise EncryptionFormatError(
            'a locked key is {"nonce": <base64url>, "box": <base64url>}'
        )
    _decoded(locked_key["nonce"], NONCE_BYTES, "its nonce")
    _decoded(locked_key["box"], LOCKED_KEY_BYTES, "its box")
    return json.dumps(
        {"nonce": locked_key["nonce"], "box": locked_key["box"]}, sort_keys=True
    )


def check_unlock_params(unlock_method, params, credential_id=None):
    """What a browser needs to rebuild the key that unlocks a member key
    (README 3.2), checked against the least the design allows. Returns the
    parameters to keep, nothing else in them."""
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except ValueError:
            params = None
    if not isinstance(params, dict):
        raise EncryptionFormatError("the unlock parameters are not an object")
    if unlock_method == "passkey":
        if not isinstance(credential_id, str) or not credential_id:
            raise EncryptionFormatError("a passkey needs its credential id")
        try:
            credential = b64u_decode(credential_id)
        except EncryptionFormatError:
            credential = b""
        if not 0 < len(credential) <= CREDENTIAL_ID_BYTES:
            raise EncryptionFormatError(
                "the credential id is not base64url of at most {} bytes".format(
                    CREDENTIAL_ID_BYTES
                )
            )
        _decoded(params.get("prf_salt"), PRF_SALT_BYTES, "the PRF salt")
        return {"prf_salt": params["prf_salt"]}
    if unlock_method == "passphrase":
        _decoded(params.get("salt"), PASSPHRASE_SALT_BYTES, "the salt")
        if params.get("alg") != "argon2id13":
            raise EncryptionFormatError("a passphrase is stretched with argon2id13")
        opslimit = params.get("opslimit")
        memlimit = params.get("memlimit")
        if (
            not isinstance(opslimit, int)
            or isinstance(opslimit, bool)
            or opslimit < PASSPHRASE_OPSLIMIT
        ):
            raise EncryptionFormatError(
                "opslimit must be at least {}".format(PASSPHRASE_OPSLIMIT)
            )
        if (
            not isinstance(memlimit, int)
            or isinstance(memlimit, bool)
            or memlimit < PASSPHRASE_MEMLIMIT
        ):
            raise EncryptionFormatError(
                "memlimit must be at least {} bytes".format(PASSPHRASE_MEMLIMIT)
            )
        return {
            "salt": params["salt"],
            "opslimit": opslimit,
            "memlimit": memlimit,
            "alg": "argon2id13",
        }
    raise EncryptionFormatError("an unlock method is a passkey or a passphrase")


def is_envelope(value):
    """Whether a value is a version 1 envelope. Decoded, not only matched,
    as RSTools' isEnvelope does: text typed to look like one is an answer,
    and is sealed like any other."""
    if not isinstance(value, str) or not value.startswith("fsenc:1:"):
        return False
    parts = value.split(":")
    if len(parts) != 4 or not _KEY_ID.fullmatch(parts[2]):
        return False
    try:
        box = b64u_decode(parts[3])
    except EncryptionFormatError:
        return False
    sealed = len(box) - SEALBYTES
    return sealed >= BLOCK and sealed % BLOCK == 0


def _seal_with(answer, the_key_id, key):
    padded = nacl.bindings.sodium_pad(answer.encode("utf-8"), BLOCK)
    box = nacl.bindings.crypto_box_seal(padded, key)
    return "fsenc:1:{}:{}".format(the_key_id, b64u_encode(box))


def _needs_sealing(answer):
    """What RSTools leaves as it is: an empty answer (stored as NULL), and
    one that arrives sealed already -- an answer a follow-up copied from a
    case list, which sealing again would bury."""
    return answer.strip() != "" and not is_envelope(answer)


def seal(value, public_key_text):
    """The envelope of an answer, sealed as it was given: no rewriting of
    quotes or anything else, so that what the interface shows when it opens
    it is what was answered. An empty answer and an envelope come back as
    they are, as RSTools' xmltojson and jsontomysql leave them."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("an answer is sealed as text")
    if not _needs_sealing(value):
        return value
    the_key_id, key = parse_public_key(public_key_text)
    return _seal_with(value, the_key_id, key)


def _answer_text(value):
    """A value of a submission's JSON as the answer it is. A client may send
    a number; jsontomysql reads it as the text JSON wrote, and so it is
    sealed. null is an empty answer."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (bool, int, float)):
        return json.dumps(value)
    return None


def _seal_json(node, marked, the_key_id, key):
    sealed = 0
    if isinstance(node, list):
        for item in node:
            sealed += _seal_json(item, marked, the_key_id, key)
    elif isinstance(node, dict):
        for name, value in node.items():
            if isinstance(value, (dict, list)):
                sealed += _seal_json(value, marked, the_key_id, key)
            elif name in marked:
                answer = _answer_text(value)
                if answer is not None and _needs_sealing(answer):
                    node[name] = _seal_with(answer, the_key_id, key)
                    sealed += 1
    return sealed


def seal_submission(data, marked, public_key_text):
    """Seals, in place, every marked answer of a submission's JSON: the
    top-level keys and the objects inside repeat arrays, whose keys are full
    paths too. Returns how many answers it sealed. With nothing marked the
    data is not touched and the key is not needed."""
    if not marked:
        return 0
    the_key_id, key = parse_public_key(public_key_text)
    return _seal_json(data, set(marked), the_key_id, key)


def _qualified_name(element):
    """An element's name as written, prefix included: what Qt's tagName()
    gives xmltojson, which reads the submission without namespaces."""
    local = etree.QName(element).localname
    return "{}:{}".format(element.prefix, local) if element.prefix else local


def seal_xml(xml, marked, public_key_text):
    """A submission's XML with every marked answer sealed: (the XML, how
    many answers were sealed).

    This is what FormShare keeps instead of what it received, so the
    answers in clear are never written anywhere. It follows xmltojson's
    reading exactly (XMLtoJSON/main.cpp, processNodeBoost): an answer is an
    element with no child element; its key is the names of its ancestors
    below the root -- leaving out any named as the root is -- and its own,
    joined by '/'; its answer is all of its text, CDATA included and
    comments not. A sealed element holds its envelope and nothing else.

    When nothing is sealed the bytes come back as they arrived."""
    if not marked:
        return xml, 0
    marked = set(marked)
    the_key_id, key = parse_public_key(public_key_text)
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(xml, parser)
    main_tag = _qualified_name(root)
    sealed = 0
    for element in root.iter(etree.Element):
        if element is root:
            continue
        if next(element.iterchildren(etree.Element), None) is not None:
            continue
        names = [
            _qualified_name(ancestor)
            for ancestor in reversed(list(element.iterancestors(etree.Element)))
            if _qualified_name(ancestor) != main_tag
        ]
        if "/".join(names + [_qualified_name(element)]) not in marked:
            continue
        answer = (element.text or "") + "".join(child.tail or "" for child in element)
        if not _needs_sealing(answer):
            continue
        for child in list(element):
            element.remove(child)
        element.text = _seal_with(answer, the_key_id, key)
        sealed += 1
    if not sealed:
        return xml, 0
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8"), sealed


def marked_xmlcodes(manifest_path):
    """The xmlcode of every question a form's manifest marks, at any depth:
    the keys whose answers are sealed."""
    tree = etree.parse(manifest_path)
    return {
        field.get("xmlcode")
        for field in tree.iter("field")
        if field.get("fs_encrypted") == "true"
        and field.get("xmlcode") not in (None, "", "NONE")
    }


def marked_columns(create_xml_path):
    """(table, column) of every column a form's create.xml marks: the
    columns that hold envelopes and nothing else."""
    tree = etree.parse(create_xml_path)
    marked = set()
    for table in tree.iterfind(".//tables//table"):
        for field in table.findall("field"):
            if field.get("fs_encrypted") == "true":
                marked.add((table.get("name"), field.get("name")))
    return marked


# ---------------------------------------------------------------------------
# A form's marks through its life (formshare.md section 6)
# ---------------------------------------------------------------------------

# The elements of a survey that hold questions rather than being one.
_STRUCTURES = ("survey", "group", "repeat")


def survey_marks(survey_file):
    """The names of the questions a form's survey JSON marks fs_encrypted,
    read as jxformtomysql reads the mark (JXFormToMysql/main.cpp): a key that
    is fs_encrypted in any case -- pyxform keeps a header as it was written
    -- whose text is yes or true, in any case. What a repository build reads
    before it runs anything (create_repository)."""
    with open(survey_file, encoding="utf-8") as a_file:
        survey = json.load(a_file)
    marked = []

    def walk(element):
        if not isinstance(element, dict):
            return
        if element.get("type") not in _STRUCTURES:
            for key, value in element.items():
                if (
                    " ".join(str(key).split()).lower() == "fs_encrypted"
                    and isinstance(value, str)
                    and value.strip().lower() in ("yes", "true")
                ):
                    marked.append(element.get("name", ""))
                    break
        for child in element.get("children") or []:
            walk(child)

    walk(survey)
    return marked


def field_is_encrypted(field):
    """1 when a field of create.xml holds envelopes and nothing else: RSTools
    writes fs_encrypted="true" on it. The dictionary's field_encrypted comes
    from this and from nothing else; the plugin opens what it marks."""
    return 1 if field.get("fs_encrypted") == "true" else 0


def field_labelled_encrypted(field):
    """formshare_encrypted, the XLSForm column that labelled a field
    "encrypted" while its answers were stored in clear. Retired (formshare.md
    6.5): it marks the field sensitive, which is what it was, and never makes
    a column encrypted -- turning it into fs_encrypted would have every
    update of such a form refused by mergeversions (ENC)."""
    return field.get("formshare_encrypted", "no") in ("yes", "1")


def _reason(reason, translate):
    _ = translate
    reasons = {
        "key": _("it is the form's key"),
        "select": _("it is a select: its answer must match an option"),
        "filter": _("a choice filter reads it"),
        "geo": _("it is a location"),
        "media": _("it is a file (photo, audio, video), which cannot be encrypted yet"),
    }
    return reasons.get(reason, reason)


def invalid_encrypted_fields_heading(translate):
    _ = translate
    return _(
        "The ODK you just submitted marks as encrypted (fs_encrypted) questions "
        "that cannot be encrypted:"
    )


def describe_invalid_encrypted_fields(root, translate):
    """The lines of jxformtomysql's XMLInvalidEncryptedFields (exit 39), one
    per question a mark cannot work on, with its reason in words."""
    _ = translate
    report = (
        root
        if root.tag == "XMLInvalidEncryptedFields"
        else root.find(".//XMLInvalidEncryptedFields")
    )
    if report is None:
        return []
    lines = []
    for a_field in report.findall("invalidField"):
        name = a_field.get("name", "")
        table = a_field.get("table", "")
        reason = _reason(a_field.get("reason", ""), _)
        if table in ("", "maintable"):
            lines.append(
                _('The question "{}" cannot be encrypted: {}.').format(name, reason)
            )
        else:
            lines.append(
                _(
                    'The question "{}" of the table "{}" cannot be encrypted: {}.'
                ).format(name, table, reason)
            )
    return lines


def encryption_change_message(translate, table, field, marked_in_repository):
    """What mergeversions' ENC means: a version marks a column the
    repository holds in clear, or unmarks one it holds sealed. Its report
    gives the two field definitions, which do not say which; the
    repository's create.xml does."""
    _ = translate
    if marked_in_repository:
        return _(
            'The question "{}" of the table "{}" is encrypted in the repository '
            "and not in the new version. Its answers would have to be decrypted, "
            "which a form update cannot do: mark it fs_encrypted again before "
            "merging."
        ).format(field, table)
    return _(
        'The question "{}" of the table "{}" is not encrypted in the repository '
        "and is in the new version. Its answers would have to be encrypted, "
        "which a form update cannot do: remove fs_encrypted from it, or ask it "
        "as a new question, before merging."
    ).format(field, table)


# create_repository's own code, outside RSTools' range: a form that encrypts
# answers, in a project with no key to seal them with (formshare.md 6.6).
KEY_NEEDED = 1001


def key_needed_message(translate, questions):
    _ = translate
    return _(
        "This form encrypts the answers to {}, and encryption is not set up for "
        "the project yet. Its repository can be created, or this version "
        "merged, once the project has a key."
    ).format(", ".join(questions))


def encrypted_columns(request, project_id, form_id, table_name):
    """The columns of a repository's table that hold envelopes, as its
    dictionary says (field_encrypted, from create.xml's fs_encrypted)."""
    return {
        row[0]
        for row in request.dbsession.query(DictField.field_name)
        .filter(DictField.project_id == project_id)
        .filter(DictField.form_id == form_id)
        .filter(DictField.table_name == table_name)
        .filter(DictField.field_encrypted == 1)
        .all()
    }


def encrypted_column_message(translate, column, use):
    """Why a column that holds envelopes cannot be put to a use that reads
    it: a list's label, key or filter, an action's condition or target
    (formshare.md 6.7). use says what was asked of it."""
    _ = translate
    return _(
        'The column "{}" is encrypted, so it cannot be {}: only FormShare\'s '
        "interface can read it."
    ).format(column, use)


# ---------------------------------------------------------------------------
# Writes (formshare.md section 7)
# ---------------------------------------------------------------------------

# What MySQL answers when a value breaks a CHECK constraint (README 6).
CHECK_CONSTRAINT_VIOLATED = 3819


def is_encrypted_refusal(error):
    """Whether a database error is MySQL refusing a value in a column that
    holds envelopes: 3819, a CHECK constraint violated, on one of RSTools'
    fsenc_ constraints -- which are the only CHECK constraints a repository
    has. Whoever wrote it -- the cleaning grid, the API, an action -- wrote
    an answer in clear where only an envelope may go."""
    original = getattr(error, "orig", error)
    errno = getattr(original, "errno", None)
    if errno is None and getattr(original, "args", None):
        errno = original.args[0] if isinstance(original.args[0], int) else None
    return errno == CHECK_CONSTRAINT_VIOLATED and "fsenc_" in str(error)


def encrypted_edit_message(translate, for_api=False):
    """What a person, or an API client, is told when the database refused an
    answer in clear in an encrypted column."""
    _ = translate
    if for_api:
        return _(
            "This answer is encrypted: send it sealed with the project's "
            "public key, or null to clear it."
        )
    return _("This answer is encrypted: unlock it to edit.")


# ---------------------------------------------------------------------------
# The submission pipeline (formshare.md section 5)
# ---------------------------------------------------------------------------


def manifest_marks(odk_dir, form_directory):
    """The xmlcodes a form marks fs_encrypted, read from the manifest beside
    its create.xml: the upload check writes it there for a form in testing,
    and the repository build writes it again. Empty when the form marks
    nothing, or has no manifest (a form older than the marks)."""
    manifest = os.path.join(
        odk_dir, "forms", form_directory, "repository", "manifest.xml"
    )
    if not os.path.exists(manifest):
        return set()
    return marked_xmlcodes(manifest)


def get_active_project_key_with_engine(engine, project_id):
    """get_active_project_key for code with an engine and no request: the
    Celery tasks that load submissions."""
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT public_key FROM encryption_project_key WHERE "
                "project_id = :project AND key_status = 'active'"
            ),
            {"project": project_id},
        ).first()
    return row[0] if row is not None else None


# What an envelope counts as in a submission's digest.
ENVELOPE_PLACEHOLDER = "fsenc"


def submission_digest(data):
    """The md5 by which a resend of a submission with sealed answers is
    recognised (formshare.md 5.6). Sealing is random, so two sends of the
    same answers never hash alike as written: this hashes the JSON with
    every envelope replaced by one placeholder, the keys in order. It needs
    no answer in clear, and stores none -- a hash of the answers would let
    anyone with the database guess a short one. Two submissions that differ
    only in what they seal hash alike; a form's key, which no mark can take,
    tells two cases apart, and a device's instanceID two sends."""

    def blank(node):
        if isinstance(node, dict):
            return {key: blank(value) for key, value in node.items()}
        if isinstance(node, list):
            return [blank(value) for value in node]
        if is_envelope(node):
            return ENVELOPE_PLACEHOLDER
        return node

    canonical = json.dumps(blank(data), sort_keys=True, ensure_ascii=False)
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()


def seal_json_text(raw, marked, public_key_text):
    """A submission's JSON, as received, with its marked answers sealed:
    (the JSON to keep, as bytes, and how many answers were sealed). When
    nothing needed sealing the bytes come back as they arrived, so a form
    that marks nothing -- or a client that sealed for itself -- keeps the
    file it sent."""
    data = json.loads(raw)
    sealed = seal_submission(data, marked, public_key_text)
    if not sealed:
        return raw, 0
    return json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8"), sealed


def no_key_message(translate):
    """What a device is told when it submits to a form that encrypts answers
    in a project with no key to seal them with: nothing is kept, so that no
    answer is ever written in clear (formshare.md 5)."""
    _ = translate
    return _(
        "This form encrypts some of its answers and encryption is not set up "
        "for its project yet, so the submission was not accepted. Keep it on "
        "the device and send it again once the project has a key."
    )


# ---------------------------------------------------------------------------
# Who may do what (formshare.md section 4)
# ---------------------------------------------------------------------------

OWNER, ADMIN, EDITOR = 1, 2, 3
# The people who enroll. The recovery kit is a member too, made only with
# the project's encryption (set up, a new kit).
PEOPLE = ("user", "assistant")
EVENT_TYPES = (
    "setup",
    "enroll",
    "unlock_method_added",
    "unlock_method_removed",
    "unlock",
    "grant",
    "revoke",
    "rotate",
    "recovery_used",
    "recovery_replaced",
    "key_alarm",
    "decrypted",
)
ACTOR_TYPES = ("user", "assistant", "system")
# What happens in a browser, where the server cannot see, and the plugin
# records through log_encryption_event. Every other event is written by the
# function that does what it records, and by nothing else.
BROWSER_EVENTS = ("key_alarm", "decrypted")


def get_user_role(request, project_id, user_id):
    """A user's access to a project -- 1 owner, 2 admin, 3 editor, 4 member
    -- once accepted; None when they have none."""
    row = (
        request.dbsession.query(Userproject.access_type)
        .filter(Userproject.project_id == project_id)
        .filter(Userproject.user_id == user_id)
        .filter(Userproject.project_accepted == 1)
        .first()
    )
    return row[0] if row is not None else None


def _assistants_who_clean(request, project_id):
    """The coll_uuid of every assistant who may clean or supervise a form of
    the project, directly or through an active group."""
    direct = (
        request.dbsession.query(Formacces.coll_uuid)
        .filter(Formacces.form_project == project_id)
        .filter(or_(Formacces.coll_can_clean == 1, Formacces.coll_is_supervisor == 1))
    )
    grouped = (
        request.dbsession.query(Collingroup.coll_uuid)
        .join(
            Formgrpacces,
            and_(
                Formgrpacces.project_id == Collingroup.project_id,
                Formgrpacces.group_id == Collingroup.group_id,
            ),
        )
        .join(
            Collgroup,
            and_(
                Collgroup.project_id == Collingroup.project_id,
                Collgroup.group_id == Collingroup.group_id,
            ),
        )
        .filter(Formgrpacces.form_project == project_id)
        .filter(Collgroup.group_active == 1)
        .filter(
            or_(
                Formgrpacces.group_can_clean == 1,
                Formgrpacces.group_is_supervisor == 1,
            )
        )
    )
    found = {row[0] for row in direct.all()} | {row[0] for row in grouped.all()}
    if not found:
        return set()
    active = (
        request.dbsession.query(Collaborator.coll_uuid)
        .filter(Collaborator.coll_uuid.in_(found))
        .filter(Collaborator.coll_active == 1)
        .all()
    )
    return {row[0] for row in active}


def assistant_can_clean(request, project_id, coll_uuid):
    """Whether an active assistant may clean or supervise a form of the
    project: the assistants who may be given its key."""
    return coll_uuid in _assistants_who_clean(request, project_id)


def member_is_eligible(request, project_id, member):
    """Whether a member may hold the project's key: a user who is its owner,
    an admin or an editor; an assistant who may clean or supervise one of
    its forms; its own recovery kit. Partners may not, in phase 1."""
    if member is None or member.revoked_date is not None:
        return False
    if member.member_type == "user":
        role = get_user_role(request, project_id, member.user_id)
        return role is not None and role <= EDITOR
    if member.member_type == "assistant":
        return assistant_can_clean(request, project_id, member.coll_uuid)
    if member.member_type == "recovery":
        return member.project_id == project_id
    return False


# ---------------------------------------------------------------------------
# The record (section 2.5)
# ---------------------------------------------------------------------------


def _event(request, project_id, actor_type, actor_id, event_type, detail=None):
    """Adds an event to the transaction under way."""
    agent = getattr(request, "user_agent", None) or None
    request.dbsession.add(
        EncryptionEvent(
            event_id=str(uuid.uuid4()),
            project_id=project_id,
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event_type,
            event_detail=(
                json.dumps(detail, sort_keys=True) if detail is not None else None
            ),
            event_date=datetime.datetime.now(),
            ip=getattr(request, "client_addr", None),
            user_agent=agent[:512] if agent else None,
        )
    )


def log_encryption_event(
    request, project_id, actor_type, actor_id, event_type, detail=None
):
    """Records what happened in a browser, where the server cannot see: a
    key that did not match the one the server holds (key_alarm), answers
    opened on a page (decrypted). Only those, and only from someone who
    holds the project's key: the record of a grant or a revocation is
    written by the function that made it, and cannot be made up here.
    actor_id is the person logged in. Returns (True, "") or (False, message)."""
    _ = request.translate
    if event_type not in BROWSER_EVENTS or actor_type not in PEOPLE:
        return False, _("This is not an event a browser records")
    member = _active_member(request, actor_type, actor_id)
    if member is None or not _grants_of(request, project_id, member.member_id):
        return False, _("Only someone who holds the project's key records its events")
    try:
        _event(request, project_id, actor_type, actor_id, event_type, detail)
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while recording the encryption event {} of project {}".format(
                str(e), event_type, project_id
            )
        )
        return False, _("The event could not be recorded")


def _event_dict(event):
    return {
        "event_id": event.event_id,
        "project_id": event.project_id,
        "actor_type": event.actor_type,
        "actor_id": event.actor_id,
        "event_type": event.event_type,
        "event_detail": json.loads(event.event_detail) if event.event_detail else None,
        "event_date": event.event_date,
        "ip": event.ip,
        "user_agent": event.user_agent,
    }


def list_encryption_events(request, project_id, event_type=None, start=0, length=100):
    """A project's events, the newest first."""
    query = request.dbsession.query(EncryptionEvent).filter(
        EncryptionEvent.project_id == project_id
    )
    if event_type is not None:
        query = query.filter(EncryptionEvent.event_type == event_type)
    events = (
        query.order_by(EncryptionEvent.event_date.desc(), EncryptionEvent.event_id)
        .offset(start)
        .limit(length)
        .all()
    )
    return [_event_dict(event) for event in events]


# ---------------------------------------------------------------------------
# Members and unlocking (sections 2.2, 2.3)
# ---------------------------------------------------------------------------

_MEMBER_OF = {
    "user": EncryptionMember.user_id,
    "assistant": EncryptionMember.coll_uuid,
    "recovery": EncryptionMember.project_id,
}


def _active_member(request, member_type, identity):
    """The active member of a user (identity: user_id), an assistant
    (coll_uuid) or a project's recovery kit (project_id)."""
    if member_type not in _MEMBER_OF:
        return None
    return (
        request.dbsession.query(EncryptionMember)
        .filter(EncryptionMember.member_type == member_type)
        .filter(_MEMBER_OF[member_type] == identity)
        .filter(EncryptionMember.revoked_date.is_(None))
        .first()
    )


def _member_by_id(request, member_id):
    return (
        request.dbsession.query(EncryptionMember)
        .filter(EncryptionMember.member_id == member_id)
        .first()
    )


def _identity(member):
    """(actor type, actor id) of a person's member."""
    if member.member_type == "user":
        return "user", member.user_id
    return "assistant", member.coll_uuid


def _member_dict(member):
    return {
        "member_id": member.member_id,
        "member_type": member.member_type,
        "user_id": member.user_id,
        "coll_uuid": member.coll_uuid,
        "project_id": member.project_id,
        "public_key": member.public_key,
        "created_date": member.created_date,
        "revoked_date": member.revoked_date,
    }


def get_member(request, member_type, identity):
    """The active member of a user (identity: user_id), an assistant
    (coll_uuid) or a project's recovery kit (project_id), as a dict; None
    when there is none."""
    member = _active_member(request, member_type, identity)
    return _member_dict(member) if member is not None else None


def _lock(request, model, column, value):
    """Locks a row until the transaction ends, so that two requests that
    would each find nothing in the way cannot both act."""
    return (
        request.dbsession.query(model).filter(column == value).with_for_update().first()
    )


def _lock_owner_of(request, member_type, identity):
    if member_type == "user":
        return _lock(request, User, User.user_id, identity)
    if member_type == "assistant":
        return _lock(request, Collaborator, Collaborator.coll_uuid, identity)
    return _lock(request, Project, Project.project_id, identity)


def _unlock_row(member_id, unlock):
    """An unlock method from what a browser sends -- {unlock_method,
    unlock_label, credential_id, unlock_params, locked_key} -- checked.
    Raises EncryptionFormatError."""
    if not isinstance(unlock, dict):
        raise EncryptionFormatError("an unlock method is an object")
    method = unlock.get("unlock_method")
    credential_id = unlock.get("credential_id")
    params = check_unlock_params(method, unlock.get("unlock_params"), credential_id)
    label = unlock.get("unlock_label") or method.capitalize()
    if not isinstance(label, str) or len(label.strip()) > 120:
        raise EncryptionFormatError("a label is text of at most 120 characters")
    return EncryptionUnlock(
        unlock_id=str(uuid.uuid4()),
        member_id=member_id,
        unlock_method=method,
        unlock_label=label.strip(),
        credential_id=credential_id if method == "passkey" else None,
        unlock_params=json.dumps(params, sort_keys=True),
        locked_key=check_locked_key(unlock.get("locked_key")),
        created_date=datetime.datetime.now(),
    )


def enroll_member(request, member_type, identity, public_key, first_unlock):
    """Records a person's member key, made in their browser, with the first
    method that unlocks it (README 3.2). identity is the user_id of a user
    or the coll_uuid of an assistant: the person logged in, never one a
    browser names. Refused when they have a member key already.

    Returns (True, member_id) or (False, message)."""
    _ = request.translate
    if member_type not in PEOPLE:
        return False, _("Only a user or an assistant can enroll")
    member_id = str(uuid.uuid4())
    try:
        parse_member_key(public_key)
        unlock = _unlock_row(member_id, first_unlock)
    except EncryptionFormatError as e:
        return False, _("The encryption key is not valid:") + " " + str(e)
    try:
        if _lock_owner_of(request, member_type, identity) is None:
            request.dbsession.rollback()
            return False, _("There is no such user or assistant")
        if _active_member(request, member_type, identity) is not None:
            request.dbsession.rollback()
            return False, _("This person has an encryption key already")
        request.dbsession.add(
            EncryptionMember(
                member_id=member_id,
                member_type=member_type,
                user_id=identity if member_type == "user" else None,
                coll_uuid=identity if member_type == "assistant" else None,
                public_key=public_key.strip(),
                created_date=datetime.datetime.now(),
            )
        )
        request.dbsession.flush()
        request.dbsession.add(unlock)
        _event(
            request,
            None,
            member_type,
            identity,
            "enroll",
            {"member_id": member_id, "unlock_method": unlock.unlock_method},
        )
        request.dbsession.commit()
        return True, member_id
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while enrolling the {} {}".format(str(e), member_type, identity)
        )
        return False, _("The encryption key could not be saved")


def retire_member(request, member_type, identity):
    """Starts a person again when they can no longer unlock their key -- a
    forgotten passphrase, lost passkeys. Their member is revoked, kept for
    the record, and its grants on every project deleted: what was sealed to
    it cannot be opened by anyone, so it is worth nothing. They enroll anew
    and are given the keys again by someone who holds them.

    Returns (True, how many projects they lost) or (False, message)."""
    _ = request.translate
    try:
        _lock_owner_of(request, member_type, identity)
        member = _active_member(request, member_type, identity)
        if member is None or member_type not in PEOPLE:
            request.dbsession.rollback()
            return False, _("This person has no encryption key")
        projects = sorted(
            {
                row[0]
                for row in request.dbsession.query(EncryptionGrant.project_id)
                .filter(EncryptionGrant.member_id == member.member_id)
                .all()
            }
        )
        for project_id in projects:
            _revoke_grants(
                request, project_id, member, member_type, identity, "key replaced"
            )
        member.revoked_date = datetime.datetime.now()
        request.dbsession.commit()
        return True, len(projects)
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while retiring the key of the {} {}".format(
                str(e), member_type, identity
            )
        )
        return False, _("The encryption key could not be retired")


def _person(request, member_id):
    """A person's active member, by id."""
    member = _member_by_id(request, member_id)
    if member is None or member.revoked_date is not None:
        return None
    if member.member_type not in PEOPLE:
        return None
    return member


def add_unlock_method(request, member_id, unlock):
    """One more locked copy of a member's key: a second passkey, a
    passphrase. The browser locks it; the member must have unlocked first.
    Returns (True, unlock_id) or (False, message)."""
    _ = request.translate
    member = _person(request, member_id)
    if member is None:
        return False, _("There is no such encryption key")
    try:
        row = _unlock_row(member_id, unlock)
    except EncryptionFormatError as e:
        return False, _("The unlock method is not valid:") + " " + str(e)
    try:
        request.dbsession.add(row)
        actor_type, actor_id = _identity(member)
        _event(
            request,
            None,
            actor_type,
            actor_id,
            "unlock_method_added",
            {"member_id": member_id, "unlock_method": row.unlock_method},
        )
        request.dbsession.commit()
        return True, row.unlock_id
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while adding an unlock method to {}".format(str(e), member_id)
        )
        return False, _("The unlock method could not be saved")


def remove_unlock_method(request, member_id, unlock_id):
    """Removes a way to unlock a member's key. The last one is never
    removed: without it the key, and every grant to it, would be lost.
    Returns (True, "") or (False, message)."""
    _ = request.translate
    try:
        member = _lock(request, EncryptionMember, EncryptionMember.member_id, member_id)
        if member is None or member.revoked_date is not None:
            request.dbsession.rollback()
            return False, _("There is no such encryption key")
        methods = (
            request.dbsession.query(EncryptionUnlock)
            .filter(EncryptionUnlock.member_id == member_id)
            .all()
        )
        target = [a_method for a_method in methods if a_method.unlock_id == unlock_id]
        if not target:
            request.dbsession.rollback()
            return False, _("There is no such unlock method")
        if len(methods) == 1:
            request.dbsession.rollback()
            return False, _("A key must keep at least one way to unlock it")
        request.dbsession.delete(target[0])
        actor_type, actor_id = _identity(member)
        _event(
            request,
            None,
            actor_type,
            actor_id,
            "unlock_method_removed",
            {"member_id": member_id, "unlock_method": target[0].unlock_method},
        )
        request.dbsession.commit()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while removing the unlock method {}".format(str(e), unlock_id)
        )
        return False, _("The unlock method could not be removed")


def rename_unlock_method(request, member_id, unlock_id, label):
    _ = request.translate
    if not isinstance(label, str) or not label.strip() or len(label.strip()) > 120:
        return False, _("A label is text of at most 120 characters")
    try:
        changed = (
            request.dbsession.query(EncryptionUnlock)
            .filter(EncryptionUnlock.member_id == member_id)
            .filter(EncryptionUnlock.unlock_id == unlock_id)
            .update({"unlock_label": label.strip()})
        )
        request.dbsession.commit()
        if not changed:
            return False, _("There is no such unlock method")
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while renaming the unlock method {}".format(str(e), unlock_id)
        )
        return False, _("The unlock method could not be renamed")


def list_unlock_methods(request, member_id):
    """A member's unlock methods, to manage them; without the locked keys,
    which only an unlock needs (get_unlock_bundle)."""
    methods = (
        request.dbsession.query(EncryptionUnlock)
        .filter(EncryptionUnlock.member_id == member_id)
        .order_by(EncryptionUnlock.created_date)
        .all()
    )
    return [
        {
            "unlock_id": a_method.unlock_id,
            "unlock_method": a_method.unlock_method,
            "unlock_label": a_method.unlock_label,
            "credential_id": a_method.credential_id,
            "created_date": a_method.created_date,
            "last_used_date": a_method.last_used_date,
        }
        for a_method in methods
    ]


def unlock_method_used(request, member_id, unlock_id):
    """Notes when a method last unlocked the key, so that a person can see
    which ones they still use."""
    try:
        request.dbsession.query(EncryptionUnlock).filter(
            EncryptionUnlock.member_id == member_id
        ).filter(EncryptionUnlock.unlock_id == unlock_id).update(
            {"last_used_date": datetime.datetime.now()}
        )
        request.dbsession.commit()
        return True
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while noting the use of {}".format(str(e), unlock_id))
        return False


def _key_dict(key):
    return {
        "key_id": key.key_id,
        "public_key": key.public_key,
        "key_status": key.key_status,
        "created_by": key.created_by,
        "created_date": key.created_date,
        "retired_date": key.retired_date,
    }


def _project_keys(request, project_id):
    return (
        request.dbsession.query(EncryptionProjectKey)
        .filter(EncryptionProjectKey.project_id == project_id)
        .order_by(EncryptionProjectKey.created_date, EncryptionProjectKey.key_id)
        .all()
    )


def _grants_of(request, project_id, member_id):
    return (
        request.dbsession.query(EncryptionGrant)
        .filter(EncryptionGrant.project_id == project_id)
        .filter(EncryptionGrant.member_id == member_id)
        .order_by(EncryptionGrant.key_id)
        .all()
    )


def _project_part(request, project_id, member_id):
    """A project's key versions and a member's grants on it: what a browser
    opens, and what it checks the grants against (README 3.3)."""
    return {
        "project_id": project_id,
        "keys": [_key_dict(key) for key in _project_keys(request, project_id)],
        "grants": [
            {"key_id": grant.key_id, "grant": grant.grant_value}
            for grant in _grants_of(request, project_id, member_id)
        ],
    }


def get_unlock_bundle(request, member_type, identity, project_id=None):
    """What a browser needs to unlock a person's key and, given a project,
    to open their grants there: the member's public key; every unlock method
    with its locked key; the project's key versions and the person's grants.
    identity is the person logged in -- a locked key is worth guessing at,
    so it is never given for anyone else. Records an unlock on the project.

    None when the person has no member key."""
    if member_type not in PEOPLE:
        return None
    member = _active_member(request, member_type, identity)
    if member is None:
        return None
    methods = (
        request.dbsession.query(EncryptionUnlock)
        .filter(EncryptionUnlock.member_id == member.member_id)
        .order_by(EncryptionUnlock.created_date)
        .all()
    )
    bundle = {
        "member": _member_dict(member),
        "unlock_methods": [
            {
                "unlock_id": a_method.unlock_id,
                "unlock_method": a_method.unlock_method,
                "unlock_label": a_method.unlock_label,
                "credential_id": a_method.credential_id,
                "unlock_params": json.loads(a_method.unlock_params),
                "locked_key": json.loads(a_method.locked_key),
            }
            for a_method in methods
        ],
    }
    if project_id is not None:
        bundle["project"] = _project_part(request, project_id, member.member_id)
        try:
            _event(
                request,
                project_id,
                member_type,
                identity,
                "unlock",
                {"member_id": member.member_id},
            )
            request.dbsession.commit()
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while recording an unlock of project {}".format(
                    str(e), project_id
                )
            )
    return bundle


def get_recovery_bundle(request, project_id, user_id):
    """For the owner and the holders of the recovery kit: the kit's member
    key, its grants and the project's key versions. The kit itself never
    reaches the server; the browser derives the member's private key from it
    (README 3.4). None for anyone but the owner, or when there is no kit."""
    if get_user_role(request, project_id, user_id) != OWNER:
        return None
    member = _active_member(request, "recovery", project_id)
    if member is None:
        return None
    return {
        "member": _member_dict(member),
        "project": _project_part(request, project_id, member.member_id),
    }


# ---------------------------------------------------------------------------
# A project's keys (section 2.1)
# ---------------------------------------------------------------------------


def get_active_project_key(request, project_id):
    """The public key answers to the project's marked questions are sealed
    with, as every tool takes it; None when the project has none."""
    row = (
        request.dbsession.query(EncryptionProjectKey.public_key)
        .filter(EncryptionProjectKey.project_id == project_id)
        .filter(EncryptionProjectKey.key_status == "active")
        .first()
    )
    return row[0] if row is not None else None


def get_project_keys(request, project_id):
    """Every version of the project's key, the oldest first."""
    return [_key_dict(key) for key in _project_keys(request, project_id)]


def _grant_list(grants):
    """[(member_id, grant, key id)] from what a browser sends: a list of
    {member_id, grant}. Raises EncryptionFormatError."""
    if not isinstance(grants, list) or not grants:
        raise EncryptionFormatError("the grants are a list of {member_id, grant}")
    given = []
    for item in grants:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("member_id"), str)
            or not isinstance(item.get("grant"), str)
        ):
            raise EncryptionFormatError("a grant is {member_id, grant}")
        given.append(
            (item["member_id"], item["grant"].strip(), parse_grant(item["grant"]))
        )
    if len({(a_member, a_key) for a_member, _, a_key in given}) != len(given):
        raise EncryptionFormatError("a member is given the same key twice")
    return given


def _put_grant(request, project_id, the_key_id, member_id, grant, granted_by, now):
    """Adds a grant, or replaces the one there: a browser made it again."""
    existing = request.dbsession.query(EncryptionGrant).get(
        (project_id, the_key_id, member_id)
    )
    if existing is None:
        request.dbsession.add(
            EncryptionGrant(
                project_id=project_id,
                key_id=the_key_id,
                member_id=member_id,
                grant_value=grant,
                granted_by=granted_by,
                granted_date=now,
            )
        )
    else:
        existing.grant_value = grant
        existing.granted_by = granted_by
        existing.granted_date = now


def set_up_project_encryption(
    request,
    project_id,
    public_key,
    owner_member_id,
    owner_grant,
    recovery_public_key,
    recovery_grant,
    user_id,
):
    """Encryption for a project, set up in its owner's browser (README 5):
    the project's first key, granted to the owner and to the recovery kit,
    whose member is made here. All of it or nothing.

    Returns (True, the key id) or (False, message)."""
    _ = request.translate
    if get_user_role(request, project_id, user_id) != OWNER:
        return False, _("Only the owner of the project can set up encryption")
    try:
        new_key_id, new_key = parse_public_key(public_key)
        parse_member_key(recovery_public_key)
        for a_grant in (owner_grant, recovery_grant):
            if parse_grant(a_grant) != new_key_id:
                raise EncryptionFormatError("a grant is not of the new key")
    except EncryptionFormatError as e:
        return False, _("The encryption set up is not valid:") + " " + str(e)
    try:
        project = _lock(request, Project, Project.project_id, project_id)
        if project is None:
            request.dbsession.rollback()
            return False, _("There is no such project")
        if _project_keys(request, project_id):
            request.dbsession.rollback()
            return False, _("Encryption is set up for this project already")
        owner = _active_member(request, "user", user_id)
        if owner is None or owner.member_id != owner_member_id:
            request.dbsession.rollback()
            return False, _("The owner must have an encryption key first")
        now = datetime.datetime.now()
        recovery_id = str(uuid.uuid4())
        request.dbsession.add(
            EncryptionProjectKey(
                project_id=project_id,
                key_id=new_key_id,
                public_key=format_public_key(new_key),
                key_status="active",
                created_by=user_id,
                created_date=now,
            )
        )
        request.dbsession.add(
            EncryptionMember(
                member_id=recovery_id,
                member_type="recovery",
                project_id=project_id,
                public_key=recovery_public_key.strip(),
                created_date=now,
            )
        )
        request.dbsession.flush()
        for member_id, a_grant in (
            (owner.member_id, owner_grant),
            (recovery_id, recovery_grant),
        ):
            _put_grant(
                request,
                project_id,
                new_key_id,
                member_id,
                a_grant.strip(),
                owner.member_id,
                now,
            )
        project.project_encrypted = 1
        _event(
            request,
            project_id,
            "user",
            user_id,
            "setup",
            {"key_id": new_key_id, "recovery_member_id": recovery_id},
        )
        request.dbsession.commit()
        return True, new_key_id
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while setting up encryption for project {}".format(
                str(e), project_id
            )
        )
        return False, _("Encryption could not be set up")


def _holders(request, project_id, the_key_id):
    """The members holding a grant on a key version."""
    return (
        request.dbsession.query(EncryptionMember)
        .join(EncryptionGrant, EncryptionGrant.member_id == EncryptionMember.member_id)
        .filter(EncryptionGrant.project_id == project_id)
        .filter(EncryptionGrant.key_id == the_key_id)
        .all()
    )


def _grantees_may_hold(request, project_id, given, recovery_allowed):
    """Whether every member a list of grants names exists, is active and may
    hold the project's key."""
    for member_id, _grant, _key in given:
        member = _member_by_id(request, member_id)
        if member is None or not member_is_eligible(request, project_id, member):
            return False
        if member.member_type == "recovery" and not recovery_allowed:
            return False
    return True


def rotate_project_key(request, project_id, public_key, grants, user_id):
    """A new version of the project's key, made in the owner's browser and
    granted there to everyone who holds the current one, the recovery kit
    included, so that nobody who may read the project loses it. The current
    version is retired and stays, to open what was sealed to it.

    Returns (True, the new key id) or (False, message)."""
    _ = request.translate
    if get_user_role(request, project_id, user_id) != OWNER:
        return False, _("Only the owner of the project can change its key")
    try:
        new_key_id, new_key = parse_public_key(public_key)
        given = _grant_list(grants)
    except EncryptionFormatError as e:
        return False, _("The new key is not valid:") + " " + str(e)
    if any(a_key != new_key_id for _member, _grant, a_key in given):
        return False, _("Every grant must be of the new key")
    try:
        if _lock(request, Project, Project.project_id, project_id) is None:
            request.dbsession.rollback()
            return False, _("There is no such project")
        keys = _project_keys(request, project_id)
        current = [key for key in keys if key.key_status == "active"]
        if not current:
            request.dbsession.rollback()
            return False, _("Encryption is not set up for this project")
        current = current[0]
        if any(key.key_id == new_key_id for key in keys):
            request.dbsession.rollback()
            return False, _("The project has used this key before")
        owner = _active_member(request, "user", user_id)
        if owner is None:
            request.dbsession.rollback()
            return False, _("The owner must have an encryption key first")
        if not _grantees_may_hold(request, project_id, given, True):
            request.dbsession.rollback()
            return False, _("A grant is for someone who may not hold the key")
        required = {
            member.member_id
            for member in _holders(request, project_id, current.key_id)
            if member_is_eligible(request, project_id, member)
        }
        if not required <= {a_member for a_member, _grant, _key in given}:
            request.dbsession.rollback()
            return False, _(
                "The new key must be given to everyone who holds the current "
                "one, the recovery kit included"
            )
        now = datetime.datetime.now()
        current.key_status = "retired"
        current.retired_date = now
        # The functional index allows one active version: the current one
        # has to stop being active before the new one is.
        request.dbsession.flush()
        request.dbsession.add(
            EncryptionProjectKey(
                project_id=project_id,
                key_id=new_key_id,
                public_key=format_public_key(new_key),
                key_status="active",
                created_by=user_id,
                created_date=now,
            )
        )
        request.dbsession.flush()
        for member_id, a_grant, _key in given:
            _put_grant(
                request,
                project_id,
                new_key_id,
                member_id,
                a_grant,
                owner.member_id,
                now,
            )
        _event(
            request,
            project_id,
            "user",
            user_id,
            "rotate",
            {"from": current.key_id, "to": new_key_id, "members": len(given)},
        )
        request.dbsession.commit()
        return True, new_key_id
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while changing the key of project {}".format(str(e), project_id)
        )
        return False, _("The project's key could not be changed")


# ---------------------------------------------------------------------------
# Granting and revoking (section 2.4)
# ---------------------------------------------------------------------------


def add_grants(request, project_id, grants, granted_by):
    """Grants made in the browser of someone who holds the project's key,
    for colleagues who may read the project. The server cannot check what a
    grant seals; it checks the right to have made it: the granter is the
    owner or an admin and holds each version given, and each grantee is
    enrolled and may hold the key. granted_by is the user logged in.

    Returns (True, how many grants) or (False, message)."""
    _ = request.translate
    role = get_user_role(request, project_id, granted_by)
    if role is None or role > ADMIN:
        return False, _("Only the owner or an admin of the project can give its key")
    try:
        given = _grant_list(grants)
    except EncryptionFormatError as e:
        return False, _("The grants are not valid:") + " " + str(e)
    try:
        granter = _active_member(request, "user", granted_by)
        held = (
            {
                grant.key_id
                for grant in _grants_of(request, project_id, granter.member_id)
            }
            if granter is not None
            else set()
        )
        keys = {key.key_id for key in _project_keys(request, project_id)}
        refusal = None
        if any(a_key not in keys for _member, _grant, a_key in given):
            refusal = _("A grant is for a key the project does not have")
        elif any(a_key not in held for _member, _grant, a_key in given):
            refusal = _("You can only give a key you hold")
        elif not _grantees_may_hold(request, project_id, given, False):
            refusal = _("A grant is for someone who may not hold the key")
        if refusal is not None:
            request.dbsession.rollback()
            return False, refusal
        now = datetime.datetime.now()
        for member_id, a_grant, a_key in given:
            _put_grant(
                request, project_id, a_key, member_id, a_grant, granter.member_id, now
            )
        for member_id in sorted({a_member for a_member, _grant, _key in given}):
            _event(
                request,
                project_id,
                "user",
                granted_by,
                "grant",
                {
                    "member_id": member_id,
                    "key_ids": sorted(
                        a_key
                        for a_member, _grant, a_key in given
                        if a_member == member_id
                    ),
                },
            )
        request.dbsession.commit()
        return True, len(given)
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while giving the key of project {}".format(str(e), project_id)
        )
        return False, _("The key could not be given")


def grant_with_recovery(request, project_id, grants, user_id):
    """The recovery kit used (README 3.4): the owner and the kit's holders
    open its grants in a browser and give the project's key to a member the
    owner chooses. Returns (True, how many grants) or (False, message)."""
    _ = request.translate
    if get_user_role(request, project_id, user_id) != OWNER:
        return False, _("Only the owner of the project can use its recovery kit")
    try:
        given = _grant_list(grants)
    except EncryptionFormatError as e:
        return False, _("The grants are not valid:") + " " + str(e)
    try:
        recovery = _active_member(request, "recovery", project_id)
        held = (
            {
                grant.key_id
                for grant in _grants_of(request, project_id, recovery.member_id)
            }
            if recovery is not None
            else set()
        )
        refusal = None
        if recovery is None:
            refusal = _("Encryption is not set up for this project")
        elif any(a_key not in held for _member, _grant, a_key in given):
            refusal = _("A grant is for a key the recovery kit does not hold")
        elif not _grantees_may_hold(request, project_id, given, False):
            refusal = _("A grant is for someone who may not hold the key")
        if refusal is not None:
            request.dbsession.rollback()
            return False, refusal
        now = datetime.datetime.now()
        for member_id, a_grant, a_key in given:
            _put_grant(
                request, project_id, a_key, member_id, a_grant, recovery.member_id, now
            )
        _event(
            request,
            project_id,
            "user",
            user_id,
            "recovery_used",
            {
                "member_ids": sorted({a_member for a_member, _grant, _key in given}),
                "key_ids": sorted({a_key for _member, _grant, a_key in given}),
            },
        )
        request.dbsession.commit()
        return True, len(given)
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while using the recovery kit of project {}".format(
                str(e), project_id
            )
        )
        return False, _("The key could not be given")


def _revoke_grants(request, project_id, member, actor_type, actor_id, reason):
    """Deletes a member's grants on a project, in the transaction under way,
    and records it. Returns how many there were."""
    grants = _grants_of(request, project_id, member.member_id)
    if not grants:
        return 0
    for grant in grants:
        request.dbsession.delete(grant)
    _event(
        request,
        project_id,
        actor_type,
        actor_id,
        "revoke",
        {
            "member_id": member.member_id,
            "key_ids": [grant.key_id for grant in grants],
            "reason": reason,
        },
    )
    return len(grants)


def revoke_member(request, project_id, member_id, revoked_by):
    """Takes every version of the project's key from a member: their grants
    on the project are deleted. Someone who may have kept a key is stopped
    only by a rotation as well, which the plugin offers. The recovery kit is
    replaced, not revoked; an admin cannot take the key from the owner.
    revoked_by is the user logged in, who must hold the key themselves.

    Returns (True, how many grants) or (False, message)."""
    _ = request.translate
    role = get_user_role(request, project_id, revoked_by)
    if role is None or role > ADMIN:
        return False, _("Only the owner or an admin of the project can take its key")
    revoker = _active_member(request, "user", revoked_by)
    if revoker is None or not _grants_of(request, project_id, revoker.member_id):
        return False, _("Only someone who holds the project's key can take it")
    target = _member_by_id(request, member_id)
    if target is None:
        return False, _("There is no such encryption key")
    if target.member_type == "recovery":
        return False, _("The recovery kit is replaced, not revoked")
    if (
        role != OWNER
        and target.member_type == "user"
        and get_user_role(request, project_id, target.user_id) == OWNER
    ):
        return False, _("An admin cannot take the key from the owner")
    try:
        count = _revoke_grants(
            request, project_id, target, "user", revoked_by, "revoked"
        )
        request.dbsession.commit()
        return True, count
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while taking the key of project {} from {}".format(
                str(e), project_id, member_id
            )
        )
        return False, _("The key could not be taken")


def revoke_ineligible_members(request, project_id, actor_type="system", actor_id=None):
    """Takes the project's key from every member who may no longer hold it
    (section 9): a collaborator removed or made a plain member, an assistant
    removed or left without the right to clean. Called after any change to
    who may do what in a project. Returns how many members lost it."""
    members = (
        request.dbsession.query(EncryptionMember)
        .join(EncryptionGrant, EncryptionGrant.member_id == EncryptionMember.member_id)
        .filter(EncryptionGrant.project_id == project_id)
        .distinct()
        .all()
    )
    lost = 0
    try:
        for member in members:
            if member.member_type == "recovery":
                continue
            if not member_is_eligible(request, project_id, member):
                _revoke_grants(
                    request, project_id, member, actor_type, actor_id, "not eligible"
                )
                lost += 1
        if lost:
            request.dbsession.commit()
        return lost
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while taking the key of project {} from those who lost "
            "access".format(str(e), project_id)
        )
        return 0


# ---------------------------------------------------------------------------
# Losing access (section 9)
# ---------------------------------------------------------------------------


def _actor(request):
    """Who changed who may do what, for the record: the user logged in, or the
    system when no one is."""
    login = getattr(getattr(request, "user", None), "login", None)
    if login:
        return "user", login
    return "system", None


def access_changed(request, project_id):
    """Called after anything that may take someone's right to hold the
    project's key: a collaborator removed or made a plain member, an
    assistant's rights on a form or through a group taken away, a group
    deactivated or deleted. Takes the key from whoever lost the right, and
    records it. Never raises: the change it follows stands either way, and a
    failure here is logged. Returns how many members lost it."""
    try:
        actor_type, actor_id = _actor(request)
        return revoke_ineligible_members(request, project_id, actor_type, actor_id)
    except Exception as e:
        log.error(
            "Error {} while taking the key of project {} from those who lost "
            "access".format(str(e), project_id)
        )
        return 0


def member_access_changed(request, member_type, identity):
    """The same after a change to a person rather than to a project -- an
    assistant deactivated: every project where they hold a key."""
    try:
        projects = sorted(
            {
                row[0]
                for row in request.dbsession.query(EncryptionGrant.project_id)
                .join(
                    EncryptionMember,
                    EncryptionMember.member_id == EncryptionGrant.member_id,
                )
                .filter(EncryptionMember.member_type == member_type)
                .filter(_MEMBER_OF[member_type] == identity)
                .all()
            }
        )
    except Exception as e:
        log.error(
            "Error {} while finding the projects of the {} {}".format(
                str(e), member_type, identity
            )
        )
        return 0
    return sum(access_changed(request, project_id) for project_id in projects)


def grants_before_deletion(request, member_type=None, identity=None, project_id=None):
    """What a deletion is about to take with it through ON DELETE CASCADE --
    a person's grants, or a project's -- as {(project_id, member_id): [key
    ids]}. Read before the deletion and recorded after it succeeds
    (record_deleted_grants): taking the grants first would leave a project
    nobody can read if the deletion then failed."""
    query = request.dbsession.query(
        EncryptionGrant.project_id, EncryptionGrant.member_id, EncryptionGrant.key_id
    )
    if project_id is not None:
        query = query.filter(EncryptionGrant.project_id == project_id)
    if member_type is not None:
        query = (
            query.join(
                EncryptionMember,
                EncryptionMember.member_id == EncryptionGrant.member_id,
            )
            .filter(EncryptionMember.member_type == member_type)
            .filter(_MEMBER_OF[member_type] == identity)
        )
    held = {}
    try:
        for a_project, a_member, a_key in query.all():
            held.setdefault((a_project, a_member), []).append(a_key)
    except Exception as e:
        log.error("Error {} while reading the grants a deletion takes".format(str(e)))
    return held


def record_deleted_grants(request, held, reason):
    """Writes the revoke events a deletion owes: its grants went with what
    they belonged to, and the record outlives them."""
    if not held:
        return
    try:
        actor_type, actor_id = _actor(request)
        for (project_id, member_id), key_ids in sorted(held.items()):
            _event(
                request,
                project_id,
                actor_type,
                actor_id,
                "revoke",
                {"member_id": member_id, "key_ids": sorted(key_ids), "reason": reason},
            )
        request.dbsession.commit()
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while recording the grants a deletion took".format(str(e)))


def list_project_access(request, project_id):
    """Who may read the project and who can: the users and assistants who may
    hold its key, enrolled or not, with the versions each holds; anyone with a
    grant who may no longer hold one; and the recovery kit. Each member comes
    with its public key, which a granting browser seals to."""
    held = {}
    for grant in (
        request.dbsession.query(EncryptionGrant)
        .filter(EncryptionGrant.project_id == project_id)
        .all()
    ):
        held.setdefault(grant.member_id, []).append(grant.key_id)

    def entry(member, **extra):
        found = dict(extra)
        found["member"] = _member_dict(member) if member is not None else None
        found["key_ids"] = (
            sorted(held.get(member.member_id, [])) if member is not None else []
        )
        return found

    people = []
    listed = set()
    users = (
        request.dbsession.query(Userproject.access_type, User.user_id, User.user_name)
        .join(User, User.user_id == Userproject.user_id)
        .filter(Userproject.project_id == project_id)
        .filter(Userproject.project_accepted == 1)
        .filter(Userproject.access_type <= EDITOR)
        .order_by(Userproject.access_type, User.user_name)
        .all()
    )
    for access_type, user_id, user_name in users:
        member = _active_member(request, "user", user_id)
        people.append(
            entry(
                member,
                member_type="user",
                user_id=user_id,
                name=user_name,
                role=access_type,
                eligible=True,
            )
        )
        if member is not None:
            listed.add(member.member_id)
    coll_uuids = _assistants_who_clean(request, project_id)
    if coll_uuids:
        assistants = (
            request.dbsession.query(
                Collaborator.coll_uuid, Collaborator.coll_id, Collaborator.coll_name
            )
            .filter(Collaborator.coll_uuid.in_(coll_uuids))
            .order_by(Collaborator.coll_name)
            .all()
        )
        for coll_uuid, coll_id, coll_name in assistants:
            member = _active_member(request, "assistant", coll_uuid)
            people.append(
                entry(
                    member,
                    member_type="assistant",
                    coll_uuid=coll_uuid,
                    coll_id=coll_id,
                    name=coll_name,
                    eligible=True,
                )
            )
            if member is not None:
                listed.add(member.member_id)
    recovery = None
    for member_id in sorted(held):
        if member_id in listed:
            continue
        member = _member_by_id(request, member_id)
        if member is None:
            continue
        if member.member_type == "recovery":
            if member.revoked_date is None:
                recovery = entry(member)
            continue
        people.append(
            entry(
                member,
                member_type=member.member_type,
                user_id=member.user_id,
                coll_uuid=member.coll_uuid,
                eligible=False,
            )
        )
    return {
        "keys": [_key_dict(key) for key in _project_keys(request, project_id)],
        "people": people,
        "recovery": recovery,
    }


def replace_recovery_member(request, project_id, recovery_public_key, grants, user_id):
    """A new recovery kit (README 3.4). Its member, granted every version of
    the project's key in the owner's browser, takes the place of the old
    one, which is revoked and kept for the record. grants are the grant
    texts, one for each version.

    Returns (True, the new member id) or (False, message)."""
    _ = request.translate
    if get_user_role(request, project_id, user_id) != OWNER:
        return False, _("Only the owner of the project can replace its recovery kit")
    try:
        parse_member_key(recovery_public_key)
        if not isinstance(grants, list):
            raise EncryptionFormatError("the grants are a list")
        given = {}
        for a_grant in grants:
            a_key = parse_grant(a_grant)
            if a_key in given:
                raise EncryptionFormatError("a key is given twice")
            given[a_key] = a_grant.strip()
    except EncryptionFormatError as e:
        return False, _("The recovery kit is not valid:") + " " + str(e)
    try:
        if _lock(request, Project, Project.project_id, project_id) is None:
            request.dbsession.rollback()
            return False, _("There is no such project")
        old = _active_member(request, "recovery", project_id)
        if old is None:
            request.dbsession.rollback()
            return False, _("Encryption is not set up for this project")
        keys = {key.key_id for key in _project_keys(request, project_id)}
        if set(given) != keys:
            request.dbsession.rollback()
            return False, _("The new kit must be given every version of the key")
        owner = _active_member(request, "user", user_id)
        if owner is None:
            request.dbsession.rollback()
            return False, _("The owner must have an encryption key first")
        now = datetime.datetime.now()
        for grant in _grants_of(request, project_id, old.member_id):
            request.dbsession.delete(grant)
        old.revoked_date = now
        request.dbsession.flush()
        new_id = str(uuid.uuid4())
        request.dbsession.add(
            EncryptionMember(
                member_id=new_id,
                member_type="recovery",
                project_id=project_id,
                public_key=recovery_public_key.strip(),
                created_date=now,
            )
        )
        request.dbsession.flush()
        for a_key, a_grant in given.items():
            _put_grant(
                request, project_id, a_key, new_id, a_grant, owner.member_id, now
            )
        _event(
            request,
            project_id,
            "user",
            user_id,
            "recovery_replaced",
            {"from": old.member_id, "to": new_id},
        )
        request.dbsession.commit()
        return True, new_id
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while replacing the recovery kit of project {}".format(
                str(e), project_id
            )
        )
        return False, _("The recovery kit could not be replaced")
