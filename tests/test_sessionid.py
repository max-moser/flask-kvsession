# SPDX-FileCopyrightText: 2014 Marc Brinkmann.
# SPDX-FileCopyrightText: 2019 CERN.
# SPDX-FileCopyrightText: 2026 Graz University of Technology.
# SPDX-License-Identifier: MIT

import time
from datetime import datetime, timezone

from flask_kvsession import SessionID


def test_serialize():
    t = int(time.time())
    dt = datetime.fromtimestamp(t, tz=timezone.utc)
    sid = SessionID(1234, dt)

    assert "%x_%x" % (1234, t) == sid.serialize()


def test_automatic_created_date():
    start = datetime.now(tz=timezone.utc)
    sid = SessionID(0)
    end = datetime.now(tz=timezone.utc)

    assert start <= sid.created <= end


def test_serialize_unserialize():
    dt = datetime(2011, 7, 9, 13, 14, 15, tzinfo=timezone.utc)
    id = 59034

    sid = SessionID(id, dt)
    data = sid.serialize()

    SessionID(123)

    restored_sid = sid.unserialize(data)

    assert sid.id == restored_sid.id
    assert sid.created == restored_sid.created
