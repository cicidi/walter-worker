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
