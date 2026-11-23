"""A user's API token on the ODK routes, and the login that gives it
(2026-11-23).

- ODKView read a token only in the branch of a Basic header, which a token
  never reaches: the Digest parser failed on "Bearer ...", and every ODK
  route answered a token with a 500. A token is read as a token now, and a
  header that cannot be read is asked for again.
- A submission is an assistant's: the push views ask a token for an
  assistant's credentials before authorize, which reads Digest's fields.
- /api/1/security/login read only an encrypted secret. createsuperuser and
  the Users page stored them as given, and decode_data's "" for those, and a
  missing secret, were a 500. Such a secret is read, and stored encrypted
  once it matches.

No database: the views run on stand-ins, with the functions they call
replaced.
"""

import json
from types import SimpleNamespace

import pytest

import formshare.views.classes as classes
import formshare.views.odk as odk
from formshare.config.encdecdata import (
    encode_data,
    secret_matches,
    stored_as_given,
    stored_secret,
)
from formshare.models import Collaborator, User
from formshare.views.api.version_1.tokens import TokenView

KEY = "0123456789abcdef0123456789abcdef"
OTHER_KEY = "fedcba9876543210fedcba9876543210"
SECRET = "5f2b8c1d9e0a4b7c6d3e2f1a0b9c8d7e"


def _settings(key=KEY):
    return SimpleNamespace(
        settings={"aes.key": key, "auth.opaque": "OPAQUE", "auth.realm": "formshare"}
    )


def _encrypted(secret, key=KEY):
    return encode_data(SimpleNamespace(registry=_settings(key)), secret).decode()


class _Request:
    def __init__(self, headers=None, method="GET", testing="false"):
        self.headers = headers or {}
        self.method = method
        self.matchdict = {"userid": "owner", "projcode": "survey", "formid": "hh"}
        self.registry = _settings()
        self.translate = lambda text: text
        self.matched_route = None
        self._testing = testing

    def encget(self, name, default=None):
        if name == "FS_for_testing":
            return self._testing
        return default

    def route_url(self, *args, **kwargs):
        return "http://example.org/push"


class _Probe(classes.ODKView):
    def pre_process_view(self):
        return "processed"


@pytest.fixture
def odk_view(monkeypatch):
    access = {"value": 1}
    monkeypatch.setattr(classes, "get_project_id_from_name", lambda *a: "P1")
    monkeypatch.setattr(classes, "refuse_form_being_deleted", lambda *a: None)
    monkeypatch.setattr(
        classes,
        "get_user_with_token",
        lambda request, token: "api_user" if token == "good-token" else None,
    )
    monkeypatch.setattr(classes, "get_project_access_type", lambda *a: access["value"])
    monkeypatch.setattr(classes, "project_has_crowdsourcing", lambda *a: False)

    def make(authorization):
        return _Probe(_Request({"Authorization": authorization}))

    make.access = access
    return make


def _is_challenge(result):
    return getattr(result, "status_code", None) == 401 and result.headers.get(
        "WWW-Authenticate", ""
    ).startswith("Digest realm=")


def test_a_token_reaches_the_view_as_the_api_user(odk_view):
    view = odk_view("Bearer good-token")
    assert view() == "processed"
    assert view.api is True
    assert view.user == "api_user"


def test_a_token_of_someone_without_the_project_is_asked_again(odk_view):
    odk_view.access["value"] = 5
    view = odk_view("Bearer good-token")
    assert _is_challenge(view())
    assert view.api is False


@pytest.mark.parametrize("authorization", ["Bearer unknown", "Bearer", "bearer  "])
def test_an_unknown_or_empty_token_is_asked_again(odk_view, authorization):
    view = odk_view(authorization)
    assert _is_challenge(view())
    assert view.api is False


def test_digest_still_signs_in_an_assistant(odk_view):
    view = odk_view(
        'Digest username="ana", realm="formshare", nonce="n1", uri="/formList", '
        'qop=auth, nc=00000001, cnonce="c1", response="r1", opaque="OPAQUE"'
    )
    assert view() == "processed"
    assert view.api is False
    assert view.user == "ana"
    assert view.authHeader["qop"] == "auth"


@pytest.mark.parametrize(
    "authorization",
    ["Basic YW5hOnNlY3JldA==", "Something else", "Digest", "Digest no-equals-sign"],
)
def test_a_header_that_cannot_be_read_is_asked_again(odk_view, authorization):
    view = odk_view(authorization)
    assert _is_challenge(view())
    assert view.authHeader == {}


@pytest.fixture
def push(monkeypatch):
    monkeypatch.setattr(odk, "get_project_id_from_name", lambda *a: "P1")
    monkeypatch.setattr(odk, "project_has_crowdsourcing", lambda *a: False)

    def looked_up(*args):
        raise AssertionError("a token was taken for an assistant")

    monkeypatch.setattr(odk, "get_odk_assistant_uuid", looked_up)

    def make(view_class, method):
        view = view_class(_Request(method=method))
        view.api = True
        view.user = "api_user"
        return view

    return make


@pytest.mark.parametrize(
    "view_class, method",
    [
        (odk.ODKPushData, "POST"),
        (odk.ODKPushJSONData, "POST"),
        (odk.ODKSubmission, "POST"),
        (odk.ODKSubmission, "HEAD"),
    ],
)
def test_a_token_cannot_send_a_submission(push, view_class, method):
    assert _is_challenge(push(view_class, method).process_view())


def test_an_assistant_is_not_refused_as_a_token():
    view = _Probe(_Request())
    assert view.refuse_a_token() is None


def test_a_secret_is_read_encrypted_or_as_given():
    request = SimpleNamespace(registry=_settings())
    encrypted = _encrypted(SECRET)
    assert encrypted.startswith("gAAAAA")
    assert stored_secret(request, encrypted) == SECRET
    assert stored_secret(request, encrypted.encode()) == SECRET
    assert stored_secret(request, SECRET) == SECRET
    assert stored_as_given(SECRET) and not stored_as_given(encrypted)
    assert not stored_as_given(None) and not stored_as_given("")
    for nothing in (None, "", b""):
        assert stored_secret(request, nothing) is None
    # Encrypted with another key: no secret, and no exception
    assert stored_secret(request, _encrypted(SECRET, OTHER_KEY)) is None


def test_a_secret_matches_only_itself():
    request = SimpleNamespace(registry=_settings())
    for stored in (SECRET, _encrypted(SECRET)):
        assert secret_matches(request, stored, SECRET)
        assert not secret_matches(request, stored, SECRET[:-1] + "0")
        assert not secret_matches(request, stored, None)
        assert not secret_matches(request, stored, "")
    assert not secret_matches(request, None, SECRET)
    assert not secret_matches(request, _encrypted(SECRET, OTHER_KEY), SECRET)


class _Query:
    def __init__(self, session, model):
        self.session = session
        self.model = model

    def filter(self, *args):
        return self

    def first(self):
        return self.session.rows.get(self.model)

    def update(self, values):
        self.session.updates.append((self.model, values))
        return 1


class _Session:
    def __init__(self, user=None, assistant=None):
        self.rows = {User: user, Collaborator: assistant}
        self.updates = []

    def query(self, model):
        return _Query(self, model)

    def commit(self):
        pass

    def rollback(self):
        pass


def _login(session, secret):
    request = SimpleNamespace(
        method="POST",
        POST={},
        body=json.dumps({"X-API-Key": "the-key", "X-API-Secret": secret}).encode(),
        dbsession=session,
        registry=_settings(),
        translate=lambda text: text,
    )
    response = TokenView(request)()
    return response.status_code, json.loads(response.body)


def _user(secret):
    return SimpleNamespace(user_apisecret=secret)


def _assistant(secret):
    return SimpleNamespace(coll_apisecret=secret)


def test_a_secret_stored_as_given_logs_in_and_is_stored_encrypted():
    session = _Session(user=_user(SECRET))
    status, answer = _login(session, SECRET)
    assert status == 200 and answer["result"]["token"]
    ((model, values),) = session.updates
    assert model is User
    stored = values["user_apisecret"]
    stored = stored.decode() if isinstance(stored, bytes) else stored
    assert stored.startswith("gAAAAA")
    assert stored_secret(SimpleNamespace(registry=_settings()), stored) == SECRET


def test_an_encrypted_secret_logs_in_and_is_left_as_it_is():
    session = _Session(user=_user(_encrypted(SECRET)))
    status, answer = _login(session, SECRET)
    assert status == 200 and answer["result"]["token"]
    ((model, values),) = session.updates
    assert "user_apisecret" not in values


def test_a_wrong_secret_is_refused():
    for stored in (SECRET, _encrypted(SECRET)):
        session = _Session(user=_user(stored))
        status, answer = _login(session, "not-the-secret")
        assert status == 401 and answer["error"] == "Such API key does not exist."
        assert session.updates == []


@pytest.mark.parametrize("stored", [None, "", "OTHER"])
def test_a_user_without_a_secret_to_read_is_told_so(stored):
    if stored == "OTHER":
        stored = _encrypted(SECRET, OTHER_KEY)
    status, answer = _login(_Session(user=_user(stored)), SECRET)
    assert status == 401
    assert answer["error"].startswith("Your account does not have an API secret")


@pytest.mark.parametrize("stored", [None, "", "OTHER"])
def test_an_assistant_without_a_secret_to_read_is_refused(stored):
    if stored == "OTHER":
        stored = _encrypted(SECRET, OTHER_KEY)
    status, answer = _login(_Session(assistant=_assistant(stored)), SECRET)
    assert status == 401 and answer["error"] == "Such API key does not exist."


def test_an_assistant_logs_in_with_an_encrypted_secret():
    session = _Session(assistant=_assistant(_encrypted(SECRET)))
    status, answer = _login(session, SECRET)
    assert status == 200 and answer["result"]["token"]
    ((model, values),) = session.updates
    assert (
        model is Collaborator and values["coll_apitoken"] == answer["result"]["token"]
    )
