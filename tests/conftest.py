# SPDX-FileCopyrightText: 2014 Marc Brinkmann.
# SPDX-FileCopyrightText: 2015 John Gibson.
# SPDX-FileCopyrightText: 2019 CERN.
# SPDX-FileCopyrightText: 2026 Graz University of Technology.
# SPDX-License-Identifier: MIT

import json
from datetime import datetime, timezone

import pytest
from flask import Flask, session
from flask_kvsession import KVSession, KVSessionExtension
from simplekv.memory import DictStore


@pytest.fixture
def redis():
    try:
        from redis import StrictRedis
        from redis.exceptions import ConnectionError
    except ImportError:
        pytest.skip("redis library not installed")
    try:
        r = StrictRedis()
        r.ping()
    except ConnectionError:
        pytest.skip("could not connect to redis")
    r.flushall()
    yield r


@pytest.fixture
def redis_store(redis):
    from simplekv.memory.redisstore import RedisStore

    yield RedisStore(redis)


@pytest.fixture(params=["dict", "redis"])
def store(request):
    if request.param == "dict":
        yield DictStore()
    elif request.param == "redis":
        yield request.getfixturevalue("redis_store")


@pytest.fixture
def client(app):
    client = app.test_client()

    yield client


@pytest.fixture
def app(store):
    app = Flask(__name__)

    app.kvsession = KVSessionExtension(store, app)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "devkey"

    @app.route("/")
    def index():
        return "nothing to see here, move along"

    @app.route("/store-in-session/<key>/<value>/")
    def store(key, value):
        session[key] = value
        return "stored %r at %r" % (value, key)

    @app.route("/store-datetime/")
    def store_datetime():
        t = datetime(2011, 8, 10, 15, 46, 00, tzinfo=timezone.utc)
        session["datetime_key"] = t
        return "ok"

    @app.route("/delete-from-session/<key>/")
    def delete(key):
        del session[key]
        return "deleted %r" % key

    @app.route("/destroy-session/")
    def destroy():
        session.destroy()
        return "session destroyed"

    @app.route("/make-session-permanent/")
    def make_permanent():
        session.permanent = True
        return "made session permanent"

    @app.route("/dump-session/")
    def dump():
        return json.dumps(dict(session))

    @app.route("/dump-datetime/")
    def dump_datetime():
        return str(session["datetime_key"])

    @app.route("/regenerate-session/")
    def regenerate():
        session.regenerate()
        return "session regenerated"

    @app.route("/is-kvsession/")
    def is_kvsession():
        return str(isinstance(session._get_current_object(), KVSession))

    @app.route("/is-new-session/")
    def is_new_session():
        return str(session.new)

    @app.route("/is-modified-session/")
    def is_modified_session():
        return str(session.modified)

    @app.route("/destroy-immediately/")
    def destroy_immediately():
        # from issue
        # 1. Set a session.
        # works implicitly
        # 2. Update session with keys.
        session["foo"] = "bar"
        # 3. Destroy.
        session.destroy()
        # 4. Check if destroy worked.
        # ????
        # 5. PROFIT
        return "PROFIT"

    yield app
