# SPDX-FileCopyrightText: 2014 Marc Brinkmann.
# SPDX-FileCopyrightText: 2019 CERN.
# SPDX-License-Identifier: MIT

from datetime import timedelta

import pytest

from flask_kvsession import KVSession, KVSessionExtension

TEST_TTL = 300


@pytest.fixture
def app_with_redis_store(app, redis_store):
    app.kvsession = KVSessionExtension(redis_store, app)
    yield app


def test_redis_expiration_permanent_session(
    redis, redis_store, app_with_redis_store, client
):
    app_with_redis_store.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        seconds=TEST_TTL
    )

    client.get("/store-in-session/k1/v1/")
    client.get("/make-session-permanent/")

    sid = redis_store.keys()[0]
    ttl = redis.ttl(sid)

    # 5 seconds tolerance should be plenty
    assert TEST_TTL - ttl <= 5


def test_redis_expiration_ephemeral_session(
    redis, redis_store, app_with_redis_store, client
):
    app_with_redis_store.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        seconds=TEST_TTL
    )

    client.get("/store-in-session/k1/v1/")

    sid = redis_store.keys()[0]
    ttl = redis.ttl(sid)

    assert TEST_TTL - ttl <= 5
