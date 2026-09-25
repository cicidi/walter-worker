"""P5 tests: adapter sync respects user-owned entries (permissions union,
MCP union, hook dedup, atomic writes). All tests use a temp HOME."""
import json
import pytest
from coworker.models import CoworkerConfig, McpServer, Permissions, ClaudeOverrides, GeminiOverrides
from coworker.adapters import claude, gemini
from coworker import backup as bu


def _temp_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_DIR", home / ".claude")
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SETTINGS", home / ".claude" / "settings.json")
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SKILLS", home / ".claude" / "skills")
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_MCP", home / ".claude.json")
    monkeypatch.setattr(bu, "BACKUP_ROOT", home / ".coworker" / "backups")
    return home


def _fresh_config(**kw):
    defaults = dict(
        permissions=Permissions(), mcp=[], skills=[],
        claude=ClaudeOverrides(), gemini=GeminiOverrides(),
    )
    defaults.update(kw)
    return CoworkerConfig(**defaults)


def test_permissions_user_entries_survive(tmp_path, monkeypatch):
    home = _temp_home(tmp_path, monkeypatch)
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({
        "permissions": {"allow": ["Bash(kubectl *)"], "deny": ["Bash(rm *)"]}
    }))

    claude.sync(_fresh_config(permissions=Permissions(allow=["Bash(git *)"])))

    out = json.loads(settings.read_text())
    allow = out["permissions"]["allow"]
    assert "Bash(kubectl *)" in allow  # user's entry survived
    assert "Bash(git *)" in allow      # ours added
    assert "Bash(rm *)" in out["permissions"]["deny"]


def test_foreign_hook_survives_sync(tmp_path, monkeypatch):
    home = _temp_home(tmp_path, monkeypatch)
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({
        "hooks": {
            "Stop": [
                {"matcher": "", "hooks": [{"type": "command", "command": "/user/mine.sh"}]},
            ]
        }
    }))

    claude.sync(_fresh_config())

    out = json.loads(settings.read_text())
    commands = [h["command"] for g in out["hooks"]["Stop"]
                for h in g.get("hooks", [])]
    assert "/user/mine.sh" in commands
    assert "coworker state-update" in commands


def test_state_update_hook_deduped(tmp_path, monkeypatch):
    home = _temp_home(tmp_path, monkeypatch)
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}")

    c = _fresh_config()
    claude.sync(c)
    claude.sync(c)

    out = json.loads(settings.read_text())
    state_cmds = [h["command"] for g in out["hooks"]["Stop"]
                  for h in g.get("hooks", [])
                  if h.get("command") == "coworker state-update"]
    assert len(state_cmds) == 1


def test_mcp_written_to_claude_json_not_settings(tmp_path, monkeypatch):
    home = _temp_home(tmp_path, monkeypatch)
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text("{}")

    claude.sync(_fresh_config(mcp=[
        McpServer(name="mcp1", command="cmd1", args=[], enabled=True),
    ]))

    mcp_file = home / ".claude.json"
    assert mcp_file.exists()
    mcp = json.loads(mcp_file.read_text())
    assert mcp["mcpServers"]["mcp1"]["command"] == "cmd1"

    settings = json.loads((home / ".claude" / "settings.json").read_text())
    assert "mcpServers" not in settings


def test_gemini_mcp_union(tmp_path, monkeypatch):
    home = tmp_path / "home"; home.mkdir()
    gem_dir = home / ".gemini"; gem_dir.mkdir()
    settings = gem_dir / "settings.json"
    monkeypatch.setattr(gemini, "GEMINI_SETTINGS", settings)
    settings.write_text(json.dumps({
        "mcpServers": {"foreign": {"command": "f", "args": []}}
    }))

    gemini.sync(_fresh_config(mcp=[
        McpServer(name="coworker-srv", command="c", args=[], enabled=True),
    ]))

    out = json.loads(settings.read_text())
    assert "foreign" in out["mcpServers"]
    assert "coworker-srv" in out["mcpServers"]


# ── No-op writes must not churn or back up ───────────────────────────────────
# Sync runs on every install. It used to rewrite and re-back up settings.json
# unconditionally, which is why 1813 json-sync backups on this machine held
# only 44 distinct contents - one of them 645 times over.


def _backup_count(home):
    d = home / ".coworker" / "backups"
    return len(list(d.glob("*"))) if d.exists() else 0


def test_identical_write_is_a_noop(tmp_path, monkeypatch):
    home = _temp_home(tmp_path, monkeypatch)
    path = home / ".claude" / "settings.json"
    data = {"model": "opus", "permissions": {"allow": ["Bash(*)"]}}

    assert claude._write_json_atomic(path, data) is True, "first write must land"

    assert claude._write_json_atomic(path, data) is False, "identical rewrite is a no-op"
    assert claude._write_json_atomic(path, data) is False
    assert _backup_count(home) == 0, "a no-op must not create a backup"
    assert json.loads(path.read_text()) == data


def test_real_change_still_backs_up_the_previous_content(tmp_path, monkeypatch):
    home = _temp_home(tmp_path, monkeypatch)
    path = home / ".claude" / "settings.json"

    claude._write_json_atomic(path, {"v": 1})
    assert claude._write_json_atomic(path, {"v": 2}) is True

    assert _backup_count(home) == 1, "a real change must be backed up"
    snap = next((home / ".coworker" / "backups").glob("*"))
    saved = next(snap.rglob("settings.json"))
    assert json.loads(saved.read_text()) == {"v": 1}, "backup holds the pre-change content"
    assert json.loads(path.read_text()) == {"v": 2}


def test_repeated_sync_does_not_accumulate_backups(tmp_path, monkeypatch):
    """Three syncs over unchanged config produce one write, not three."""
    home = _temp_home(tmp_path, monkeypatch)
    cfg = _fresh_config(mcp=[McpServer(name="s", command="echo", args=[], enabled=True)])

    for _ in range(3):
        claude.sync(cfg)
    after_first = _backup_count(home)
    for _ in range(3):
        claude.sync(cfg)
    assert _backup_count(home) == after_first, (
        "re-syncing unchanged config must not create more backups"
    )
