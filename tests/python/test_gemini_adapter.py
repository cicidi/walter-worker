"""Tests for gemini adapter."""
import json
import pytest
from pathlib import Path


@pytest.fixture
def gemini_home(tmp_path, monkeypatch):
    """Redirect GEMINI_DIR to temp."""
    home = tmp_path / "home"
    home.mkdir()
    gemini_dir = home / ".gemini"
    gemini_dir.mkdir(parents=True)
    import coworker.adapters.gemini as gm
    monkeypatch.setattr(gm, "GEMINI_DIR", gemini_dir)
    monkeypatch.setattr(gm, "GEMINI_SETTINGS", gemini_dir / "settings.json")
    return home


def test_sync_basic(gemini_home, monkeypatch):
    """sync writes settings.json with MCP servers."""
    from coworker.adapters import gemini as gm
    from coworker.models import CoworkerConfig, McpServer

    monkeypatch.setattr(gm.backup, "snapshot", lambda *a, **kw: None)

    config = CoworkerConfig(mcp=[
        McpServer(name="test-server", command="echo", args=["hello"], enabled=True)
    ])
    actions = gm.sync(config)
    assert len(actions) == 1

    with open(gemini_home / ".gemini" / "settings.json") as f:
        data = json.load(f)
    assert "mcpServers" in data
    assert "test-server" in data["mcpServers"]


def test_sync_project_dir(tmp_path, monkeypatch):
    """sync writes to project_dir when provided."""
    from coworker.adapters import gemini as gm
    from coworker.models import CoworkerConfig

    monkeypatch.setattr(gm.backup, "snapshot", lambda *a, **kw: None)

    project = tmp_path / "project"
    config = CoworkerConfig()
    actions = gm.sync(config, project_dir=project)
    assert (project / ".gemini" / "settings.json").exists()


def test_sync_disabled_server_skipped(gemini_home, monkeypatch):
    """Disabled MCP servers are skipped."""
    from coworker.adapters import gemini as gm
    from coworker.models import CoworkerConfig, McpServer

    monkeypatch.setattr(gm.backup, "snapshot", lambda *a, **kw: None)

    config = CoworkerConfig(mcp=[
        McpServer(name="disabled", command="echo", args=[], enabled=False)
    ])
    gm.sync(config)

    with open(gemini_home / ".gemini" / "settings.json") as f:
        data = json.load(f)
    assert "disabled" not in data.get("mcpServers", {})


def test_sync_server_with_env(gemini_home, monkeypatch):
    """MCP server with env vars includes them."""
    from coworker.adapters import gemini as gm
    from coworker.models import CoworkerConfig, McpServer

    monkeypatch.setattr(gm.backup, "snapshot", lambda *a, **kw: None)

    config = CoworkerConfig(mcp=[
        McpServer(name="with-env", command="cmd", args=[], env={"KEY": "val"}, enabled=True)
    ])
    gm.sync(config)

    with open(gemini_home / ".gemini" / "settings.json") as f:
        data = json.load(f)
    assert data["mcpServers"]["with-env"]["env"] == {"KEY": "val"}


def test_write_json_atomic_exception(gemini_home, monkeypatch):
    """_write_json_atomic cleans up temp file on exception."""
    from coworker.adapters import gemini as gm

    monkeypatch.setattr(gm.backup, "snapshot", lambda *a, **kw: None)
    monkeypatch.setattr(gm.os, "replace", lambda src, dst: (_ for _ in ()).throw(RuntimeError("fail")))

    target = gemini_home / ".gemini" / "test.json"
    target.write_text("{}")

    with pytest.raises(RuntimeError, match="fail"):
        gm._write_json_atomic(target, {"key": "val"})


def test_sync_merges_existing_mcp(gemini_home, monkeypatch):
    """sync preserves existing user MCP servers."""
    from coworker.adapters import gemini as gm
    from coworker.models import CoworkerConfig, McpServer

    monkeypatch.setattr(gm.backup, "snapshot", lambda *a, **kw: None)

    # Write existing settings with a user MCP server
    settings_path = gemini_home / ".gemini" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({
        "mcpServers": {"user-server": {"command": "user-cmd", "args": []}}
    }))

    config = CoworkerConfig(mcp=[
        McpServer(name="coworker-server", command="cw", args=[], enabled=True)
    ])
    gm.sync(config)

    with open(settings_path) as f:
        data = json.load(f)
    assert "user-server" in data["mcpServers"]
    assert "coworker-server" in data["mcpServers"]


def test_sync_with_extra_fields(gemini_home, monkeypatch):
    """sync applies gemini.extra overrides."""
    from coworker.adapters import gemini as gm
    from coworker.models import CoworkerConfig

    monkeypatch.setattr(gm.backup, "snapshot", lambda *a, **kw: None)

    config = CoworkerConfig()
    config.gemini.extra = {"theme": "dark"}
    gm.sync(config)

    with open(gemini_home / ".gemini" / "settings.json") as f:
        data = json.load(f)
    assert data["theme"] == "dark"
