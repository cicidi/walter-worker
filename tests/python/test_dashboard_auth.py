"""Dashboard password (HTTP Basic Auth) and the refuse-to-expose guard.

The dashboard serves session prompts, file paths and memories, and has
endpoints that change state. With COWORKER_DASHBOARD_PASSWORD set, every
HTTP and WebSocket request must carry the credentials. Listening beyond
loopback without a password is refused outright.
"""

from __future__ import annotations

import base64
import sys
import types

import pytest
from click.testing import CliRunner
from coworker.cli import main
from coworker.dashboard.app import app
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def _basic(user: str, password: str) -> dict:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("COWORKER_DASHBOARD_PASSWORD", raising=False)
    monkeypatch.delenv("COWORKER_DASHBOARD_USER", raising=False)
    from coworker.dashboard import app as app_module
    app_module._auth_failures.clear()  # wrong-password counts must not leak between tests
    return TestClient(app)


def test_no_password_configured_means_no_prompt(client):
    assert client.get("/").status_code == 200


def test_password_set_rejects_anonymous_with_a_login_prompt(client, monkeypatch):
    monkeypatch.setenv("COWORKER_DASHBOARD_PASSWORD", "s3cret")
    r = client.get("/")
    assert r.status_code == 401
    assert r.headers["www-authenticate"].startswith("Basic ")
    assert client.get("/api/file-summary").status_code == 401


def test_wrong_password_and_wrong_user_are_rejected(client, monkeypatch):
    monkeypatch.setenv("COWORKER_DASHBOARD_PASSWORD", "s3cret")
    assert client.get("/", headers=_basic("coworker", "nope")).status_code == 401
    assert client.get("/", headers=_basic("admin", "s3cret")).status_code == 401
    assert client.get("/", headers={"Authorization": "Basic !!!"}).status_code == 401


def test_right_credentials_pass(client, monkeypatch):
    monkeypatch.setenv("COWORKER_DASHBOARD_PASSWORD", "s3cret")
    assert client.get("/", headers=_basic("coworker", "s3cret")).status_code == 200
    monkeypatch.setenv("COWORKER_DASHBOARD_USER", "walter")
    assert client.get("/", headers=_basic("walter", "s3cret")).status_code == 200


def test_websocket_needs_credentials_too(client, monkeypatch):
    monkeypatch.setenv("COWORKER_DASHBOARD_PASSWORD", "s3cret")
    # Rejected during the handshake; connecting at all fails "DID NOT RAISE".
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws"):
            pass


@pytest.fixture
def fake_uvicorn(monkeypatch):
    ran = {}
    mod = types.ModuleType("uvicorn")
    mod.run = lambda app, **kw: ran.update(kw)
    monkeypatch.setitem(sys.modules, "uvicorn", mod)
    return ran


def test_refuses_to_listen_publicly_without_a_password(fake_uvicorn, monkeypatch):
    monkeypatch.delenv("COWORKER_DASHBOARD_PASSWORD", raising=False)
    r = CliRunner().invoke(main, ["analytics", "dashboard", "--host", "0.0.0.0"])
    assert r.exit_code != 0
    assert "COWORKER_DASHBOARD_PASSWORD" in r.output
    assert fake_uvicorn == {}


def test_listens_publicly_with_a_password(fake_uvicorn, monkeypatch):
    monkeypatch.setenv("COWORKER_DASHBOARD_PASSWORD", "s3cret")
    r = CliRunner().invoke(main, ["analytics", "dashboard", "--host", "0.0.0.0"])
    assert r.exit_code == 0
    assert fake_uvicorn["host"] == "0.0.0.0"


# ── Repeated wrong passwords are locked out ──────────────────────────────────

@pytest.fixture
def clock(monkeypatch):
    """A clock the test moves by hand, and a clean failure record."""
    from coworker.dashboard import app as app_module
    now = {"t": 1000.0}
    monkeypatch.setattr(app_module, "_now", lambda: now["t"])
    app_module._auth_failures.clear()
    yield now
    app_module._auth_failures.clear()


def test_too_many_wrong_passwords_lock_the_address_out(client, monkeypatch, clock):
    from coworker.dashboard import app as app_module
    monkeypatch.setenv("COWORKER_DASHBOARD_PASSWORD", "s3cret")
    for _ in range(app_module.AUTH_FAIL_LIMIT):
        assert client.get("/", headers=_basic("coworker", "guess")).status_code == 401

    locked = client.get("/", headers=_basic("coworker", "guess"))
    assert locked.status_code == 429
    assert int(locked.headers["retry-after"]) > 0
    # The right password does not get through either until the lockout ends,
    # so a guesser cannot tell when it has hit the right one.
    assert client.get("/", headers=_basic("coworker", "s3cret")).status_code == 429


def test_the_lockout_ends_after_the_window(client, monkeypatch, clock):
    from coworker.dashboard import app as app_module
    monkeypatch.setenv("COWORKER_DASHBOARD_PASSWORD", "s3cret")
    for _ in range(app_module.AUTH_FAIL_LIMIT):
        client.get("/", headers=_basic("coworker", "guess"))
    assert client.get("/", headers=_basic("coworker", "s3cret")).status_code == 429

    clock["t"] += app_module.AUTH_FAIL_WINDOW + 1

    assert client.get("/", headers=_basic("coworker", "s3cret")).status_code == 200


def test_requests_without_credentials_do_not_count_as_guesses(client, monkeypatch, clock):
    """A browser's first request never carries credentials; it must not lock anyone out."""
    from coworker.dashboard import app as app_module
    monkeypatch.setenv("COWORKER_DASHBOARD_PASSWORD", "s3cret")
    for _ in range(app_module.AUTH_FAIL_LIMIT * 3):
        assert client.get("/").status_code == 401
    assert client.get("/", headers=_basic("coworker", "s3cret")).status_code == 200


def test_a_few_typos_do_not_lock_out(client, monkeypatch, clock):
    monkeypatch.setenv("COWORKER_DASHBOARD_PASSWORD", "s3cret")
    for _ in range(3):
        client.get("/", headers=_basic("coworker", "typo"))
    assert client.get("/", headers=_basic("coworker", "s3cret")).status_code == 200
