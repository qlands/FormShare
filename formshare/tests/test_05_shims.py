"""The classes that stand in for Pyramid, and the pure helpers around them.

FormShare 3 runs on FastAPI but its views still speak Pyramid: a request with
matchdict and route_url, a response with a status phrase, a session with
flash messages, a transaction manager with savepoints. The shims that give
them that live in formshare.middleware and formshare.config.dispatcher and
need no server to be exercised, so they are checked here, one call each.
"""

import json
import os
import uuid
from types import SimpleNamespace

import numpy
import pytest
import redis
from starlette.datastructures import FormData
from starlette.requests import Request as StarletteRequest
from starlette.responses import PlainTextResponse
from starlette.responses import Response as StarletteResponse

from formshare.config import dispatcher
from formshare.config.fastapi_config import FormShareConfig
from formshare.middleware import FormShareRequest, _MatchedRoute, _PostData
from formshare.middleware.httpexceptions import HTTPBadRequest, HTTPFound
from formshare.middleware.response import (
    FileResponse,
    MutableResponse,
    Response,
    _guess_content_type,
)
from formshare.middleware.session import FormShareSession, check_csrf_token
from formshare.middleware.tm import TransactionManager, _Savepoint
from formshare.models import User
from formshare.models import schema as model_schema
from formshare.processes.db import dictionary
from formshare.products import block, products
from formshare.views import users as users_view
from formshare.views.basic_views import BASE62_ALPHABET, base62_encode, new_user_id
from formshare.views.classes import remove_keys

# ------------------------------------------------------------------ responses


def test_a_response_takes_its_status_as_a_number_or_a_phrase():
    response = Response(
        body=b"x",
        status="404 Not Found",
        headerlist=[("Content-Type", "text/plain"), ("X-Custom", "1")],
        text="hello",
    )
    assert response.status == 404
    assert response.status_code == 404
    assert response.content_type == "text/plain"
    assert response.headers["X-Custom"] == "1"
    assert response.body == b"hello"
    assert response.text == "hello"

    response.status = 201
    assert response.status_code == 201
    response.status = "500 Internal Server Error"
    assert response.status == 500
    response.status_code = "302"
    assert response.status == 302

    response.text = b"raw"
    assert response.body == b"raw"
    response.body = b""
    assert response.text == ""

    response.content_disposition = 'attachment; filename="a.txt"'
    assert response.content_disposition == 'attachment; filename="a.txt"'
    response.content_disposition = None
    assert response.content_disposition is None
    assert "status=302" in repr(response)

    starlette = response.to_starlette()
    assert starlette.status_code == 302
    assert starlette.media_type.startswith("text/plain")


def test_a_file_response_names_its_type_and_its_caching(tmp_path):
    path = tmp_path / "a.csv"
    path.write_text("a,b")
    response = FileResponse(str(path), cache_max_age=60)
    assert response.content_type == "text/csv"
    response.status_code = 206
    assert response.status_code == 206
    response.content_disposition = "attachment"
    assert response.content_disposition == "attachment"
    response.content_disposition = None
    assert response.content_disposition is None
    assert response.to_starlette().headers["cache-control"] == "max-age=60"
    assert repr(response) == "<FileResponse path={!r}>".format(str(path))
    assert _guess_content_type("nothing.unknownextension") == "application/octet-stream"


def test_the_request_response_carries_its_changes_to_the_final_one():
    response = MutableResponse()
    response.status = "404 Not Found"
    assert response.status == 404
    response.status = 200
    response.status_code = 201
    assert response.status_code == 201
    response.content_disposition = "inline"
    assert response.content_disposition == "inline"
    response.content_disposition = None
    assert response.content_disposition is None
    response.headers["FS_error"] = "true"
    response.set_cookie("a", "1", path="/")

    final = response.apply_to_starlette(StarletteResponse(content=b""))
    assert final.status_code == 201
    assert final.headers["FS_error"] == "true"
    assert "a=1" in final.headers["set-cookie"]


# -------------------------------------------------------------------- session


def test_the_session_is_a_dict_with_flash_messages_and_a_csrf_token():
    session = FormShareSession({})
    session["a"] = 1
    assert session["a"] == 1
    assert "a" in session
    assert len(session) == 1
    assert list(iter(session)) == ["a"]
    assert session.get("b", 2) == 2
    assert session.setdefault("c", 3) == 3
    session.update({"d": 4}, e=5)
    assert set(session.keys()) == {"a", "c", "d", "e"}
    assert 4 in session.values()
    assert ("e", 5) in session.items()
    assert session.pop("e") == 5
    del session["d"]
    assert repr(session).startswith("FormShareSession(")

    session.flash("hi")
    session.flash("hi", allow_duplicate=False)
    session.flash("wrong", queue="error")
    assert session.peek_flash() == ["hi"]
    assert session.pop_flash() == ["hi"]
    assert session.pop_flash() == []
    assert session.pop_flash("error") == ["wrong"]

    token = session.get_csrf_token()
    assert session.get_csrf_token() == token
    assert session.new_csrf_token() != token
    session.invalidate()
    assert len(session) == 0
    session.clear()


class _CsrfRequest(object):
    """What check_csrf_token reads of a request."""

    def __init__(self, post, headers, session):
        self.POST = post
        self.headers = headers
        self.session = session


def test_the_csrf_check_reads_the_form_or_the_header():
    session = FormShareSession({})
    token = session.get_csrf_token()
    assert check_csrf_token(_CsrfRequest({"csrf_token": token}, {}, session)) is True
    assert check_csrf_token(_CsrfRequest({}, {"X-CSRF-Token": token}, session)) is True
    assert check_csrf_token(_CsrfRequest({}, {}, session), raises=False) is False
    with pytest.raises(HTTPBadRequest):
        check_csrf_token(_CsrfRequest({"csrf_token": "wrong"}, {}, session))


# ---------------------------------------------------------------- transactions


class _Nested(object):
    def __init__(self, calls, fail=False):
        self.calls = calls
        self.fail = fail

    def rollback(self):
        self.calls.append("nested rollback")
        if self.fail:
            raise RuntimeError("no savepoint")

    def commit(self):
        self.calls.append("nested commit")
        if self.fail:
            raise RuntimeError("no savepoint")


class _Session(object):
    """A session that remembers what was asked of it, and can refuse."""

    def __init__(self, fail=False, nested_fail=False):
        self.calls = []
        self.fail = fail
        self.nested_fail = nested_fail

    def commit(self):
        self.calls.append("commit")
        if self.fail:
            raise RuntimeError("deadlock")

    def rollback(self):
        self.calls.append("rollback")

    def begin_nested(self):
        return _Nested(self.calls, self.nested_fail)


def test_the_transaction_manager_commits_rolls_back_and_nests():
    session = _Session()
    manager = TransactionManager(session)
    assert manager.get() is manager
    with manager:
        pass
    with pytest.raises(ValueError):
        with manager:
            raise ValueError("inside")
    assert session.calls == ["commit", "rollback"]

    savepoint = manager.savepoint()
    savepoint.rollback()
    savepoint.commit()
    assert session.calls[-2:] == ["nested rollback", "nested commit"]

    failing = _Session(fail=True)
    with pytest.raises(RuntimeError):
        TransactionManager(failing).commit()
    assert failing.calls == ["commit", "rollback"]

    broken = _Savepoint(_Session(nested_fail=True))
    broken.rollback()
    with pytest.raises(RuntimeError):
        broken.commit()


# ------------------------------------------------------------------ dispatcher


def test_the_dispatcher_maps_results_and_errors_to_responses():
    assert dispatcher._error_fallback_status(HTTPBadRequest()) == 400
    assert dispatcher._error_fallback_status(ValueError()) == 500
    assert dispatcher._status_body(404) == b"Not Found"

    response = dispatcher._result_to_fs_response({"a": 1}, "unknown", None, None)
    assert response.content_type == "application/json"
    assert json.loads(response.body) == {"a": 1}
    assert dispatcher._result_to_fs_response(None, None, None, None).status == 204
    assert dispatcher._result_to_fs_response("plain", None, None, None).body == b"plain"

    passthrough = PlainTextResponse("x", status_code=201)
    response = dispatcher._result_to_fs_response(passthrough, None, None, None)
    assert response._starlette_passthrough is passthrough
    assert response.status == 201

    response = dispatcher._result_to_fs_response(
        HTTPFound(location="/elsewhere"), None, None, None
    )
    assert response.status == 302


# -------------------------------------------------------------------- products


KNOWN_PRODUCTS = [
    "fs1import",
    "xmlimport",
    "repository",
    "xlsx_public_export",
    "xlsx_private_export",
    "media_export",
    "kml_export",
    "csv_public_export",
    "csv_private_export",
    "zip_csv_public_export",
    "zip_csv_private_export",
    "zip_json_public_export",
    "zip_json_private_export",
    "merge_form",
]


def test_the_product_registry_and_its_descriptions(tmp_path):
    code = "pytest_" + uuid.uuid4().hex[:6]
    assert products.get_product(code) is None
    product = products.create_product(code, hidden=True, icon="fas fa-vial")
    added, product = products.add_metadata_to_product(product, "k", "v")
    assert added
    assert product["metadata"]["k"] == "v"
    added, _ = products.add_metadata_to_product({"code": code}, "k", "v")
    assert not added

    products.add_product(product)
    assert products.product_found(code)
    with pytest.raises(Exception):
        products.add_product(product)
    assert products.get_product(code)["hidden"] is True

    request = SimpleNamespace(
        translate=lambda text: text,
        registry=SimpleNamespace(settings={"repository.path": str(tmp_path)}),
    )
    directory = products.get_product_directory(request, "prj", "frm", code)
    assert os.path.isdir(directory)
    assert products.get_product_directory(request, "prj", "frm", "no_such") is None
    broken = SimpleNamespace(translate=lambda text: text, registry=SimpleNamespace())
    assert products.get_product_directory(broken, "prj", "frm", code) is None

    for known in KNOWN_PRODUCTS:
        assert products.get_product_description(request, known) != "Without description"
    assert products.get_product_description(request, "no_such") == "Without description"

    products.remove_product(code)
    assert not products.product_found(code)


def test_the_export_lock_is_per_form_and_platform_wide():
    # A database of its own, so the worker's exports are never in the way
    client = redis.StrictRedis(host="localhost", port=6379, db=15)
    assert block.get_redis_client({}) is not None
    schema = "pytest_" + uuid.uuid4().hex[:6]
    with block.export_lock("one", client, schema):
        with pytest.raises(block.LockAcquisitionError):
            with block.export_lock("two", client, schema, form_timeout=0):
                pass

    held = [
        block.export_lock("slot{}".format(slot), client, "{}_{}".format(schema, slot))
        for slot in range(block.MAX_CONCURRENT_EXPORTS)
    ]
    for a_lock in held:
        a_lock.__enter__()
    try:
        with pytest.raises(block.LockAcquisitionError):
            with block.export_lock("late", client, schema + "_late"):
                pass
    finally:
        for a_lock in held:
            a_lock.__exit__(None, None, None)
    client.close()


# ---------------------------------------------------------------------- schema


def test_the_schema_maps_extras_in_and_out():
    model_schema.initialize_schema()
    model_schema.add_modules_to_schema([User.__module__])
    table = User.__table__.name
    extra = "pytest_extra_" + uuid.uuid4().hex[:6]
    model_schema.add_column_to_schema(table, extra, "an extra column")
    with pytest.raises(Exception):
        model_schema.add_column_to_schema(table, "user_id", "already there")
    assert model_schema.get_storage_type("dictfield", "anything") == "extras"

    mapped = model_schema.map_to_schema(User, {"user_id": "a", extra: 1, "nope": 2})
    assert mapped == {"user_id": "a", "extras": json.dumps({extra: 1})}
    with pytest.raises(Exception):
        model_schema.map_to_schema(User, {"nope": 1})

    row = User(user_id="a", extras=json.dumps({"k": "v"}))
    assert model_schema.map_from_schema(row)["k"] == "v"
    assert model_schema.map_from_schema([row])[0]["k"] == "v"

    # A joined row: a model with extras next to plain columns and raw extras
    Row = type(
        "Row",
        (),
        {
            "_asdict": lambda self: {
                "User": row,
                "extras": json.dumps({"x": 1}),
                "plain": 2,
            }
        },
    )
    for mapped in [
        model_schema.map_from_schema(Row()),
        model_schema.map_from_schema([Row()])[0],
    ]:
        assert mapped["k"] == "v"
        assert mapped["x"] == 1
        assert mapped["plain"] == 2


# ----------------------------------------------------------------- small helpers


def test_the_api_result_is_stripped_of_secrets():
    data = {
        "user_password": "x",
        "keep": [{"user_apikey": "k", "ok": 1}, "user_password"],
    }
    assert remove_keys(data, ["user_password", "user_apikey"]) == {"keep": [{"ok": 1}]}


def test_the_dml_helper_logs_what_it_cannot_do():
    from formshare.processes.db.sql import execute_dml_sql

    memory = SimpleNamespace(
        registry=SimpleNamespace(settings={"sqlalchemy.url": "sqlite://"})
    )
    execute_dml_sql(memory, "CREATE TABLE a_table (a INTEGER)")
    execute_dml_sql(memory, "THIS IS NOT SQL")
    no_driver = SimpleNamespace(
        registry=SimpleNamespace(settings={"sqlalchemy.url": "nosuchdriver://x"})
    )
    execute_dml_sql(no_driver, "SELECT 1")
    no_server = SimpleNamespace(
        registry=SimpleNamespace(
            settings={
                "sqlalchemy.url": "mysql+mysqlconnector://nobody:x@127.0.0.1:9/none"
            }
        )
    )
    execute_dml_sql(no_server, "SELECT 1")


def test_a_new_user_id_is_base62():
    assert base62_encode(0) == BASE62_ALPHABET[0]
    assert base62_encode(61) == BASE62_ALPHABET[61]
    assert base62_encode(62) == BASE62_ALPHABET[1] + BASE62_ALPHABET[0]
    assert len(new_user_id()) == 16
    assert new_user_id(4).isalnum()
    assert users_view.base62_encode(62) == "10"
    assert len(users_view.new_user_id()) == 16


def test_the_lookup_value_helpers():
    a_field = {"field_type": "decimal", "field_size": 10, "field_decsize": 3}
    assert dictionary.sql_column_type(a_field) == "decimal(10,3)"
    assert dictionary.bindable_value({"a": 1}) == ""
    assert dictionary.bindable_value([1]) == ""
    assert dictionary.bindable_value(numpy.int64(5)) == 5
    assert dictionary.xml_attribute(None) == ""
    assert dictionary.xml_attribute("a") == "a"
    assert dictionary.xml_attribute(5) == "5"


# --------------------------------------------------------------------- request


def test_the_post_data_wrapper_keeps_repeated_keys():
    post = _PostData(FormData([("a", "1"), ("a", "2"), ("b", "3")]))
    assert post.keys() == ["a", "b"]
    assert post.getall("a") == ["1", "2"]
    assert post.dict_of_lists() == {"a": ["1", "2"], "b": ["3"]}
    assert list(post.items()) == [("a", "1"), ("a", "2"), ("b", "3")]
    assert post["b"] == "3"
    assert "b" in post
    assert post
    assert post.get("z") is None
    assert list(iter(post)) == ["a", "b"]

    plain = _PostData({"a": "1"})
    assert plain.getall("a") == ["1"]
    assert plain.getall("z") == []
    assert plain.dict_of_lists() == {"a": ["1"]}
    assert plain.keys() == ["a"]
    assert not _PostData({})


def _starlette_request(path="/", headers=None, client=None):
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "root_path": "",
        "query_string": b"",
        "headers": [
            (name.lower().encode(), value.encode())
            for name, value in (headers or {}).items()
        ],
        "server": ("localhost", 80),
        "scheme": "http",
        "client": client,
    }
    return StarletteRequest(scope)


def _formshare_request(starlette_request, settings=None):
    return FormShareRequest(
        starlette_request=starlette_request,
        db_session=None,
        settings=settings or {},
        session_data={},
        policies=[],
        helpers=None,
        locale_name="en",
        form_data=_PostData({}),
        json_body_data={"j": 1},
        body_bytes=b"raw",
    )


def test_the_request_shim_answers_like_a_pyramid_request():
    request = _formshare_request(
        _starlette_request(
            "/some/path",
            {"referer": "http://a/b", "host": "localhost"},
            ("10.0.0.1", 1234),
        ),
        {"k": "v"},
    )
    assert request.host_url == "http://localhost"
    assert request.path_url == "http://localhost/some/path"
    assert request.path == "/some/path"
    assert request.referer == "http://a/b"
    assert request.referrer == "http://a/b"
    assert request.client_addr == "10.0.0.1"
    assert request.remote_addr == "10.0.0.1"
    assert request.json_body == {"j": 1}
    assert request.body == b"raw"
    assert request.registry.settings == {"k": "v"}
    assert request.route_path("nowhere", _query={"a": "1"}, _anchor="top") == (
        "/nowhere?a=1#top"
    )
    assert request.get_secondary_session() == {}
    assert request.session_multi["secondary_session"] == {}
    assert repr(request).startswith("<FormShareRequest GET")
    assert not request.matched_route
    assert not _MatchedRoute(request._request)
    assert isinstance(request.tm, TransactionManager)

    anonymous = _formshare_request(_starlette_request())
    assert anonymous.client_addr is None


def test_the_config_shim_records_what_the_app_factory_needs():
    config = FormShareConfig({"a": 1})
    assert config.get_settings() == {"a": 1}
    assert "'a'" in repr(config.registry)
    config.add_jinja2_search_path(None)
    config.add_jinja2_search_path("second")
    config.add_jinja2_search_path("first", prepend=True)
    config.add_jinja2_search_path("second")
    assert config.template_paths == ["first", "second"]
    config.add_static_view("static", "/one")
    config.add_static_view("static", "/two")
    assert len(config.static_views) == 1
    config.include(".no_such_module")
    config.include("formshare.middleware.settings")
    config.add_request_method()
    config.set_session_factory()
    config.set_csrf_storage_policy()
    config.add_subscriber()
    config.set_default_csrf_options()
    assert config.make_wsgi_app() is None
    assert config.get_jinja2_environment() is None
