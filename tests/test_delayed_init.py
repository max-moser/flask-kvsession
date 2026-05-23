# SPDX-FileCopyrightText: 2014 Marc Brinkmann.
# SPDX-FileCopyrightText: 2019 CERN.
# SPDX-License-Identifier: MIT

import pytest
from flask import Flask

from flask_kvsession import KVSessionExtension


@pytest.fixture
def vapp():
    return Flask("vapp")


def test_delayed_construction(vapp, store):
    ext = KVSessionExtension()

    with pytest.raises(ValueError):
        ext.init_app(vapp)

    ext.init_app(vapp, store)

    assert vapp.kvsession_store is store


def test_delayed_construction_with_default(vapp, store):
    ext = KVSessionExtension(store)
    ext.init_app(vapp)

    assert vapp.kvsession_store == store
