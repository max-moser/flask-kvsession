#!/usr/bin/env python
# coding=utf8
# SPDX-FileCopyrightText: 2011-2014 Marc Brinkmann.
# SPDX-FileCopyrightText: 2013 Mark Hildreth.
# SPDX-FileCopyrightText: 2013 Semion Sidorenko.
# SPDX-FileCopyrightText: 2015 John Gibson.
# SPDX-FileCopyrightText: 2019 CERN.
# SPDX-FileCopyrightText: 2026 Graz University of Technology.
# SPDX-License-Identifier: MIT

import json
import time
from datetime import timedelta

import pytest
from flask import Flask, session
from flask_kvsession import KVSession, KVSessionExtension, KVSessionInterface
from itsdangerous import Signer


class CustomSessionInterfaceWithPermanentAnonymousSession(KVSessionInterface):
    def save_session(self, app, session, response):
        return super(
            CustomSessionInterfaceWithPermanentAnonymousSession, self
        ).save_session(app, session, response, anonymous_session=True)


@pytest.fixture
def app_with_session_interface_factory(store):
    app = Flask(__name__)

    app.config["SESSION_INTERFACE_FACTORY"] = (
        CustomSessionInterfaceWithPermanentAnonymousSession
    )
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "devkey"
    app.kvsession = KVSessionExtension(store, app)

    @app.route("/store-in-session/<key>/<value>/")
    def store(key, value):
        session[key] = value
        return "stored %r at %r" % (value, key)

    yield app


def json_dec(bs):
    return json.loads(bs.decode("ascii"))


def split_cookie(app, rv):
    signer = Signer(app.secret_key)
    cookie_data = rv.headers["Set-Cookie"].split(";", 1)[0]

    for cookie in cookie_data.split("&"):
        name, value = cookie_data.split("=")

        if name == app.config["SESSION_COOKIE_NAME"]:
            unsigned_value = signer.unsign(value)
            sid, created = unsigned_value.split("_".encode())
            return sid.decode("ascii"), int(created, 16)


def test_app_request_no_extras(client):
    rv = client.get("/")
    assert "move along".encode() in rv.data


def test_no_session_usage_uses_no_storage(store, client):
    client.get("/")
    client.get("/")

    assert not store.keys()


def test_session_usage(store, client):
    client.get("/store-in-session/foo/bar/")

    assert store.keys()


def test_proper_cookie_received(store, app, client):
    rv = client.get("/store-in-session/bar/baz/")

    sid, created = split_cookie(app, rv)

    assert created != 0

    # check sid in store
    key = "%s_%x" % (sid, created)

    assert key in store


def test_session_restores_properly(client):
    client.get("/store-in-session/k1/value1/")
    client.get("/store-in-session/k2/value2/")

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)

    assert s["k1"] == "value1"
    assert s["k2"] == "value2"


def test_manipulation_caught(app, client):
    client.get("/store-in-session/k1/value1/")
    rv = client.get("/dump-session/")

    s = json_dec(rv.data)

    assert s["k1"] == "value1"

    # now manipulate the cookie
    cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"])
    v_orig = cookie.value

    # FIXME: this seems to break (i.e. not detect manipulation) if the
    #        last character of v_orig is changed. possibly padding?
    for i in range(len(v_orig) - 1):
        broken_value = v_orig[:i] + ("a" if v_orig[i] != "a" else "b") + v_orig[i + 1 :]
        cookie.value = broken_value
        assert broken_value != v_orig

        rv = client.get("/dump-session/")
        s = json_dec(rv.data)

        assert s == {}, "manipulation check failed: %s / %s / %d" % (
            v_orig,
            broken_value,
            i,
        )

    # sanity check: ensure original value still works
    cookie.value = v_orig
    rv = client.get("/dump-session/")
    s = json_dec(rv.data)

    assert s["k1"] == "value1"


def test_can_change_values(client):
    client.get("/store-in-session/k1/value1/")
    rv = client.get("/dump-session/")
    s = json_dec(rv.data)

    assert s["k1"] == "value1"

    client.get("/store-in-session/k1/value2/")
    rv = client.get("/dump-session/")
    s = json_dec(rv.data)

    assert s["k1"] == "value2"


def test_can_delete_values(client):
    client.get("/store-in-session/k1/value1/")
    client.get("/store-in-session/k2/value2/")

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)

    assert s["k1"] == "value1"
    assert s["k2"] == "value2"

    client.get("/delete-from-session/k1/")

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)

    assert "k1" not in s
    assert s["k2"] == "value2"


def test_can_destroy_sessions(client):
    client.get("/store-in-session/k1/value1/")
    client.get("/store-in-session/k2/value2/")

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)

    assert s["k1"] == "value1"
    assert s["k2"] == "value2"

    # destroy session
    rv = client.get("/destroy-session/")
    assert "session destroyed".encode() in rv.data

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)

    assert s == {}


def test_session_expires_without_backend_support(app, client):
    # set expiration to 1 second
    app.permanent_session_lifetime = timedelta(seconds=1)

    client.get("/store-in-session/k1/value1/")

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)
    assert s["k1"] == "value1"

    rv = client.get("/make-session-permanent/")

    # assert that the session has a non-zero timestamp
    sid, created = split_cookie(app, rv)

    assert created != 0

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)
    assert s["k1"] == "value1"

    # sleep two seconds
    time.sleep(2)

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)
    assert s == {}


def test_session_cleanup_works(store, app, client):
    # set expiration to 1 second
    app.permanent_session_lifetime = timedelta(seconds=1)

    client.get("/store-in-session/k1/value1/")
    client.get("/make-session-permanent/")

    # assume there is a valid session, even after cleanup
    assert list(store.keys())
    app.kvsession.cleanup_sessions(app)
    assert list(store.keys())

    time.sleep(2)

    app.kvsession.cleanup_sessions(app)
    assert not list(store.keys())


def test_can_regenerate_session(store, client):
    client.get("/store-in-session/k1/value1/")

    assert len(store.keys()) == 1
    key = store.keys()[0]

    # now regenerate
    client.get("/regenerate-session/")

    assert len(store.keys()) == 1
    new_key = store.keys()[0]

    assert new_key != key

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)
    assert s["k1"] == "value1"


def test_works_without_secret_key_if_session_not_used(app):
    app.config["SECRET_KEY"] = None

    client = app.test_client()
    client.get("/")


def test_correct_error_reporting_with_no_secret_key(app, client):
    app.config["SECRET_KEY"] = None

    with pytest.raises(RuntimeError):
        client.get("/store-in-session/k1/value1/")


def test_can_store_datetime(client):
    client.get("/store-datetime/")
    rv = client.get("/dump-datetime/")
    assert rv.data == "2011-08-10 15:46:00+00:00".encode()


def test_missing_session_causes_new_empty_session(store, client):
    client.get("/store-in-session/k1/value1/")

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)
    assert s["k1"] == "value1"
    store.delete(store.keys()[0])

    rv = client.get("/dump-session/")
    assert rv.data == "{}".encode()

    rv = client.get("/is-kvsession/")
    assert rv.data == "True".encode()


def test_manipulated_session_causes_new_empty_session(app, client):
    client.get("/store-in-session/k1/value1/")
    rv = client.get("/dump-session/")
    s = json_dec(rv.data)
    assert s["k1"] == "value1"

    cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"])
    cookie.value += "x"

    rv = client.get("/dump-session/")

    assert rv.data == "{}".encode()

    rv = client.get("/is-kvsession/")
    assert rv.data == "True".encode()


def test_expired_session_causes_new_empty_session(app, client):
    app.permanent_session_lifetime = timedelta(seconds=1)

    client.get("/store-in-session/k1/value1/")
    rv = client.get("/make-session-permanent/")

    # assert that the session has a non-zero timestamp
    sid, created = split_cookie(app, rv)

    assert created != 0

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)
    assert s["k1"] == "value1"

    # sleep two seconds
    time.sleep(2)

    # we should have a new session now
    rv = client.get("/is-new-session/")
    assert rv.data == "True".encode()

    rv = client.get("/dump-session/")
    s = json_dec(rv.data)
    assert s == {}


def test_expired_made_permanent_causes_no_exception(app, client):
    app.permanent_session_lifetime = timedelta(seconds=1)

    client.get("/store-in-session/k1/value1/")

    # sleep two seconds
    time.sleep(2)
    client.get("/make-session-permanent/")


def test_permanent_session_cookies_are_permanent(app, client):
    client.get("/store-in-session/k1/value1/")

    # session cookie
    assert client.get_cookie(app.config["SESSION_COOKIE_NAME"]).expires is None

    client.get("/make-session-permanent/")

    # now it needs to be permanent
    assert client.get_cookie(app.config["SESSION_COOKIE_NAME"]).expires is not None


def test_regenerate_before_session(client):
    client.get("/regenerate-session/")


def test_destroying_session_does_not_immediately_create_new(client, store):
    client.get("/store-in-session/k1/value1/")
    client.get("/make-session-permanent/")

    assert list(store.keys())

    client.get("/destroy-session/")

    # now the store should be empty
    assert not list(store.keys())


def test_destroying_session_immediately(client):
    client.get("/destroy-immediately/")


def test_new_session_not_modified(client):
    rv = client.get("/is-modified-session/")
    assert rv.data == "False".encode()


def test_existing_session_not_modified(client):
    client.get("/store-in-session/k1/value1/")
    rv = client.get("/is-modified-session/")
    assert rv.data == "False".encode()


def test_path_app_root(app, client):
    app.config["APPLICATION_ROOT"] = "/foo"

    client.get("/store-in-session/k1/value1/")
    cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"], path="/foo")
    assert cookie.path == "/foo"


def test_path_session_path(app, client):
    app.config["APPLICATION_ROOT"] = "/foo"
    app.config["SESSION_COOKIE_PATH"] = "/bar"

    client.get("/store-in-session/k1/value1/")
    cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"], path="/bar")
    assert cookie.path == "/bar"


def test_custon_session_interface(app_with_session_interface_factory):
    assert isinstance(
        app_with_session_interface_factory.session_interface,
        CustomSessionInterfaceWithPermanentAnonymousSession,
    )
