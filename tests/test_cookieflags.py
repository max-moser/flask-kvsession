def test_secure_false(app, client):
    app.config["SESSION_COOKIE_SECURE"] = False

    client.get("/store-in-session/k1/value1/")
    cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"])
    assert not cookie.secure


def test_secure_true(app, client):
    app.config["SESSION_COOKIE_SECURE"] = True

    client.get("/store-in-session/k1/value1/")
    cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"])

    assert cookie.secure


def test_httponly_false(app, client):
    app.config["SESSION_COOKIE_HTTPONLY"] = False

    client.get("/store-in-session/k1/value1/")
    cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"])
    assert not cookie.http_only


def test_httponly_true(app, client):
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    client.get("/store-in-session/k1/value1/")
    cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"])
    assert cookie.http_only


def test_default_samesite(app, client):
    client.get("/store-in-session/k1/value1/")
    cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"])
    assert cookie.same_site is None


def test_samesite_with_value(app, client):
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    client.get("/store-in-session/k1/value1/")
    cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"])

    assert cookie.same_site == "Lax"
