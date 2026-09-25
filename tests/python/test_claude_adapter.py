from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

import pytest

from coworker.adapters import claude
from coworker.models import (
    CoworkerConfig,
    Decision,
    GitHubRef,
    FeatureConfig,
    FeatureProjectRef,
    KnowledgePoolEntry,
    LinkRef,
    McpServer,
    Permissions,
    ProjectCatalog,
    ProjectEntry,
    ProjectRef,
    RedditRef,
    ReferenceDoc,
    Refs,
    Skill,
    SlackRef,
)


# ── _resolve_claude_md ────────────────────────────────────────────────────────


def test_resolve_claude_md_with_project_dir():
    path = claude._resolve_claude_md(Path("/tmp/myproject"))
    assert path == Path("/tmp/myproject/CLAUDE.md")


def test_resolve_claude_md_without_project_dir(monkeypatch):
    monkeypatch.setattr("os.getcwd", lambda: "/fake/cwd")
    path = claude._resolve_claude_md(None)
    assert path == Path("/fake/cwd/CLAUDE.md")


# ── _resolve_local_md ─────────────────────────────────────────────────────────


def test_resolve_local_md_with_project_dir():
    path = claude._resolve_local_md(Path("/tmp/myproject"))
    assert path == Path("/tmp/myproject/CLAUDE.local.md")


def test_resolve_local_md_without_project_dir(monkeypatch):
    monkeypatch.setattr("os.getcwd", lambda: "/fake/cwd")
    path = claude._resolve_local_md(None)
    assert path == Path("/fake/cwd/CLAUDE.local.md")


# ── _replace_or_append_block ──────────────────────────────────────────────────


def test_replace_or_append_full_block_replaces():
    start = "<!-- START -->"
    end = "<!-- END -->"
    content = "before\n<!-- START -->\nold block\n<!-- END -->\nafter"
    new_block = "<!-- START -->\nnew block\n<!-- END -->"
    result = claude._replace_or_append_block(content, start, end, new_block)
    assert "new block" in result
    assert "old block" not in result
    assert result.startswith("before")


def test_replace_or_append_truncated_block_appends_after_start():
    start = "<!-- START -->"
    end = "<!-- END -->"
    content = "before\n<!-- START -->\nsome content but no end"
    new_block = "<!-- START -->\nnew block\n<!-- END -->"
    result = claude._replace_or_append_block(content, start, end, new_block)
    assert "new block" in result
    # Should contain the part before START, plus the new block
    assert result.startswith("before\n")
    # Should not contain "some content but no end" — it's replaced
    assert "some content but no end" not in result.strip()


def test_replace_or_append_no_block_appends():
    start = "<!-- START -->"
    end = "<!-- END -->"
    content = "just some content"
    new_block = "<!-- START -->\nnew block\n<!-- END -->"
    result = claude._replace_or_append_block(content, start, end, new_block)
    assert result.startswith("just some content")
    assert "new block" in result


def test_replace_or_append_is_idempotent():
    """Replacing an existing block must not change the file.

    The pattern did not consume the newlines after END, so the block's own
    trailing newline stacked on them: each call added one blank line, and a
    CLAUDE.md grew by a byte every time `coworker project sync` ran.
    """
    start, end = "<!-- START -->", "<!-- END -->"
    new_block = "<!-- START -->\nnew block\n<!-- END -->\n"

    content = "before\n\n" + start + "\nold\n" + end + "\n\n"
    first = claude._replace_or_append_block(content, start, end, new_block)
    second = claude._replace_or_append_block(first, start, end, new_block)
    third = claude._replace_or_append_block(second, start, end, new_block)

    assert first == second == third, "repeated replacement must be stable"


def test_replace_or_append_collapses_accumulated_blank_lines():
    """Blank lines left by the old behaviour get cleaned up on the next run."""
    start, end = "<!-- START -->", "<!-- END -->"
    bloated = "before\n" + start + "\nold\n" + end + "\n" + "\n" * 5 + "after\n"

    result = claude._replace_or_append_block(
        bloated, start, end, "<!-- START -->\nnew\n<!-- END -->"
    )

    assert "after" in result, "content after the block must survive"
    assert "\n\n\n" not in result, "accumulated blank lines should collapse"


def test_replace_or_append_keeps_content_after_midfile_block():
    start, end = "<!-- START -->", "<!-- END -->"
    content = "top\n" + start + "\nold\n" + end + "\n\nKEEP ME\ntail\n"

    result = claude._replace_or_append_block(
        content, start, end, "<!-- START -->\nnew\n<!-- END -->"
    )

    assert "KEEP ME" in result and "tail" in result


# ── _had_block ────────────────────────────────────────────────────────────────


def test_had_block_present():
    assert claude._had_block("hello <!-- START --> world", "<!-- START -->") is True


def test_had_block_not_present():
    assert claude._had_block("hello world", "<!-- START -->") is False


# ── _write_json_atomic ────────────────────────────────────────────────────────


def test_write_json_atomic_creates_file(tmp_path):
    path = tmp_path / "settings.json"
    claude._write_json_atomic(path, {"key": "value"})
    assert path.exists()
    data = json.loads(path.read_text())
    assert data == {"key": "value"}


def test_write_json_atomic_overwrites_with_backup(tmp_path, monkeypatch):
    path = tmp_path / "existing.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"old": true}')

    # Mock backup.snapshot to avoid real backup side effects
    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    claude._write_json_atomic(path, {"new": "data"})
    data = json.loads(path.read_text())
    assert data == {"new": "data"}


def test_write_json_atomic_exception_safety(tmp_path, monkeypatch):
    """When json.dump fails, the temp file should be cleaned up."""
    path = tmp_path / "will_fail.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    # Make os.replace fail after temp file is created
    original_replace = os.replace

    def failing_replace(src, dst):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(os, "replace", failing_replace)

    with pytest.raises(RuntimeError, match="simulated failure"):
        claude._write_json_atomic(path, {"data": 42})

    # Path should NOT exist (was never replaced)
    assert not path.exists()


# ── _sync_mcp ─────────────────────────────────────────────────────────────────


def test_sync_mcp_new_file(tmp_path):
    mcp_path = tmp_path / ".mcp.json"
    config = CoworkerConfig(
        mcp=[
            McpServer(name="test-server", command="node", args=["server.js"]),
        ]
    )
    actions = claude._sync_mcp(config, mcp_path)
    assert any("added" in a for a in actions)
    data = json.loads(mcp_path.read_text())
    assert "test-server" in data["mcpServers"]


def test_sync_mcp_existing_file_union_merge(tmp_path):
    mcp_path = tmp_path / ".mcp.json"
    mcp_path.write_text(json.dumps({
        "mcpServers": {
            "existing-server": {"command": "python", "args": ["existing.py"]},
        }
    }))
    config = CoworkerConfig(
        mcp=[
            McpServer(name="new-server", command="node", args=["new.js"]),
        ]
    )
    actions = claude._sync_mcp(config, mcp_path)
    assert any("added" in a for a in actions)
    data = json.loads(mcp_path.read_text())
    assert "existing-server" in data["mcpServers"]
    assert "new-server" in data["mcpServers"]


def test_sync_mcp_overrides_existing_by_name(tmp_path):
    mcp_path = tmp_path / ".mcp.json"
    mcp_path.write_text(json.dumps({
        "mcpServers": {
            "my-server": {"command": "python", "args": ["old.py"]},
        }
    }))
    config = CoworkerConfig(
        mcp=[
            McpServer(name="my-server", command="node", args=["new.js"]),
        ]
    )
    actions = claude._sync_mcp(config, mcp_path)
    assert any("kept" in a for a in actions)
    data = json.loads(mcp_path.read_text())
    assert data["mcpServers"]["my-server"]["command"] == "node"


def test_sync_mcp_skips_disabled_server(tmp_path):
    mcp_path = tmp_path / ".mcp.json"
    config = CoworkerConfig(
        mcp=[
            McpServer(name="enabled-srv", command="python", args=["a.py"]),
            McpServer(name="disabled-srv", command="node", args=["b.js"], enabled=False),
        ]
    )
    claude._sync_mcp(config, mcp_path)
    data = json.loads(mcp_path.read_text())
    assert "enabled-srv" in data["mcpServers"]
    assert "disabled-srv" not in data["mcpServers"]


def test_sync_mcp_with_env_vars(tmp_path):
    mcp_path = tmp_path / ".mcp.json"
    config = CoworkerConfig(
        mcp=[
            McpServer(name="env-server", command="node", args=["app.js"], env={"NODE_ENV": "production"}),
        ]
    )
    claude._sync_mcp(config, mcp_path)
    data = json.loads(mcp_path.read_text())
    assert data["mcpServers"]["env-server"]["env"] == {"NODE_ENV": "production"}


def test_sync_mcp_no_env_vars_omitted(tmp_path):
    mcp_path = tmp_path / ".mcp.json"
    config = CoworkerConfig(
        mcp=[
            McpServer(name="noenv-server", command="python", args=["app.py"]),
        ]
    )
    claude._sync_mcp(config, mcp_path)
    data = json.loads(mcp_path.read_text())
    assert "env" not in data["mcpServers"]["noenv-server"]


def test_sync_mcp_json_decode_error(tmp_path):
    mcp_path = tmp_path / ".mcp.json"
    mcp_path.write_text("not valid json {{{")
    config = CoworkerConfig(
        mcp=[
            McpServer(name="recovered-server", command="cmd", args=["--flag"]),
        ]
    )
    actions = claude._sync_mcp(config, mcp_path)
    assert any("added" in a for a in actions)
    data = json.loads(mcp_path.read_text())
    assert "recovered-server" in data["mcpServers"]


# ── sync ──────────────────────────────────────────────────────────────────────


def test_sync_global_scope(tmp_path, monkeypatch):
    """sync() without project_dir writes to global paths. Mock the global constants."""
    home = tmp_path / "home"
    home.mkdir()
    claude_dir = home / ".claude"
    claude_dir.mkdir()
    settings = claude_dir / "settings.json"
    mcp_file = home / ".claude.json"

    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_DIR", claude_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SETTINGS", settings)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SKILLS", claude_dir / "skills")
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_MCP", mcp_file)

    # Mock backup.snapshot
    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    config = CoworkerConfig(
        permissions=Permissions(allow=["Bash(pytest:*)"])
    )
    actions = claude.sync(config)
    assert any("updated" in a for a in actions)
    assert settings.exists()
    data = json.loads(settings.read_text())
    assert "pytest" in str(data["permissions"]["allow"])


def test_sync_project_scope(tmp_path, monkeypatch):
    """sync() with project_dir writes to project/.claude/settings.json etc."""
    project = tmp_path / "myproject"
    project.mkdir()

    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    config = CoworkerConfig(
        permissions=Permissions(allow=["Bash(npm:*)"])
    )
    actions = claude.sync(config, project_dir=project)

    assert any("updated" in a for a in actions)
    settings = project / ".claude" / "settings.json"
    assert settings.exists()
    data = json.loads(settings.read_text())
    assert "npm" in str(data["permissions"]["allow"])


def test_sync_permissions_union_merge(tmp_path, monkeypatch):
    """Existing permissions should be preserved, new ones merged."""
    project = tmp_path / "proj"
    project.mkdir()
    claude_dir = project / ".claude"
    claude_dir.mkdir(parents=True)
    settings = claude_dir / "settings.json"
    settings.write_text(json.dumps({
        "permissions": {
            "allow": ["Bash(git:*)"],
            "deny": ["Bash(rm:*)"],
        }
    }))

    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    config = CoworkerConfig(
        permissions=Permissions(allow=["Bash(npm:*)", "Read"], deny=["Bash(sudo:*)"])
    )
    claude.sync(config, project_dir=project)

    data = json.loads(settings.read_text())
    assert "Bash(git:*)" in data["permissions"]["allow"]
    assert "Bash(npm:*)" in data["permissions"]["allow"]
    assert "Read" in data["permissions"]["allow"]
    assert "Bash(rm:*)" in data["permissions"]["deny"]
    assert "Bash(sudo:*)" in data["permissions"]["deny"]


def test_sync_stale_mcp_from_settings_removed(tmp_path, monkeypatch):
    """sync() removes stale mcpServers from settings.json."""
    project = tmp_path / "proj"
    project.mkdir()
    claude_dir = project / ".claude"
    claude_dir.mkdir(parents=True)
    settings = claude_dir / "settings.json"
    settings.write_text(json.dumps({
        "mcpServers": {"old-server": {"command": "x", "args": []}},
        "effortLevel": "high",
        "skipDangerousModePermissionPrompt": True,
    }))

    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    config = CoworkerConfig()
    claude.sync(config, project_dir=project)

    data = json.loads(settings.read_text())
    assert "mcpServers" not in data
    # effortLevel and skipDangerousModePermissionPrompt used to be asserted here
    # too. Both are the user's own settings and are no longer removed — see
    # test_sync_preserves_user_settings_it_does_not_own.


def test_sync_stop_hook_added(tmp_path, monkeypatch):
    """sync() adds the state-update Stop hook if not present."""
    project = tmp_path / "proj"
    project.mkdir()
    claude_dir = project / ".claude"
    claude_dir.mkdir(parents=True)
    settings = claude_dir / "settings.json"
    settings.write_text("{}")

    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    config = CoworkerConfig()
    claude.sync(config, project_dir=project)

    data = json.loads(settings.read_text())
    stop_hooks = data["hooks"]["Stop"]
    assert any(
        h.get("command") == "coworker state-update"
        for entry in stop_hooks
        for h in (entry.get("hooks") or [])
    )


def test_sync_stop_hook_not_duplicated(tmp_path, monkeypatch):
    """sync() should not add a second state-update hook if one exists."""
    project = tmp_path / "proj"
    project.mkdir()
    claude_dir = project / ".claude"
    claude_dir.mkdir(parents=True)
    settings = claude_dir / "settings.json"
    settings.write_text(json.dumps({
        "hooks": {
            "Stop": [{
                "matcher": "",
                "hooks": [{"type": "command", "command": "coworker state-update"}],
            }],
        }
    }))

    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    config = CoworkerConfig()
    claude.sync(config, project_dir=project)

    data = json.loads(settings.read_text())
    stop_hooks = data["hooks"]["Stop"]
    count = sum(
        1 for entry in stop_hooks
        for h in (entry.get("hooks") or [])
        if h.get("command") == "coworker state-update"
    )
    assert count == 1


def test_sync_install_skill_dir(tmp_path, monkeypatch):
    """sync() copies skill directory to skills dir."""
    home = tmp_path / "home"
    home.mkdir()
    claude_dir = home / ".claude"
    claude_dir.mkdir()
    settings = claude_dir / "settings.json"
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()
    mcp_file = home / ".claude.json"

    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_DIR", claude_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SETTINGS", settings)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SKILLS", skills_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_MCP", mcp_file)
    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    # Create a temp skill directory with files
    skill_src = tmp_path / "my_skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text("# My Skill")

    config = CoworkerConfig(
        skills=[Skill(name="my-skill", path=str(skill_src))]
    )
    actions = claude.sync(config)
    assert any("installed skill" in a for a in actions)
    dest = skills_dir / "my-skill" / "SKILL.md"
    assert dest.exists()
    assert dest.read_text() == "# My Skill"


def test_sync_install_skill_file(tmp_path, monkeypatch):
    """sync() copies a single skill file to skills dir."""
    home = tmp_path / "home"
    home.mkdir()
    claude_dir = home / ".claude"
    claude_dir.mkdir()
    settings = claude_dir / "settings.json"
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()
    mcp_file = home / ".claude.json"

    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_DIR", claude_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SETTINGS", settings)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SKILLS", skills_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_MCP", mcp_file)
    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    skill_file = tmp_path / "standalone.md"
    skill_file.write_text("# Standalone Skill")

    config = CoworkerConfig(
        skills=[Skill(name="standalone-skill", path=str(skill_file))]
    )
    actions = claude.sync(config)
    assert any("installed skill" in a for a in actions)
    dest = skills_dir / "standalone-skill" / "standalone.md"
    assert dest.exists()
    assert dest.read_text() == "# Standalone Skill"


def test_sync_skill_not_found_warns(tmp_path, monkeypatch):
    """sync() warns when a configured skill path doesn't exist."""
    home = tmp_path / "home"
    home.mkdir()
    claude_dir = home / ".claude"
    claude_dir.mkdir()
    settings = claude_dir / "settings.json"
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()
    mcp_file = home / ".claude.json"

    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_DIR", claude_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SETTINGS", settings)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SKILLS", skills_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_MCP", mcp_file)
    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    config = CoworkerConfig(
        skills=[Skill(name="ghost", path="/nonexistent/skill/path")]
    )
    actions = claude.sync(config)
    assert any("not found" in a for a in actions)


def test_sync_disabled_skill_skipped(tmp_path, monkeypatch):
    """sync() skips skills with enabled=False."""
    home = tmp_path / "home"
    home.mkdir()
    claude_dir = home / ".claude"
    claude_dir.mkdir()
    settings = claude_dir / "settings.json"
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()
    mcp_file = home / ".claude.json"

    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_DIR", claude_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SETTINGS", settings)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SKILLS", skills_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_MCP", mcp_file)
    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    # Create a valid skill dir but mark it disabled
    skill_src = tmp_path / "disabled_skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text("# Disabled")

    config = CoworkerConfig(
        skills=[Skill(name="disabled-skill", path=str(skill_src), enabled=False)]
    )
    actions = claude.sync(config)
    # No "installed skill" message for disabled skills
    assert not any("installed skill" in a for a in actions)


def test_sync_project_dir_affects_skill_base_path(tmp_path, monkeypatch):
    """When project_dir is given, relative skill paths resolve against project_dir."""
    project = tmp_path / "myproj"
    project.mkdir()
    claude_sub = project / ".claude"
    claude_sub.mkdir()
    settings = claude_sub / "settings.json"
    skills_dir = claude_sub / "skills"
    skills_dir.mkdir()

    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    # Create the skill relative to project_dir
    rel_skill = project / "skills" / "my-skill"
    rel_skill.mkdir(parents=True)
    (rel_skill / "SKILL.md").write_text("# Rel Skill")

    config = CoworkerConfig(
        skills=[Skill(name="my-skill", path="skills/my-skill")]
    )
    actions = claude.sync(config, project_dir=project)
    assert any("installed skill" in a for a in actions)
    dest = skills_dir / "my-skill" / "SKILL.md"
    assert dest.exists()


def test_sync_mcp_integration(tmp_path, monkeypatch):
    """sync() calls _sync_mcp and picks up its actions."""
    home = tmp_path / "home"
    home.mkdir()
    claude_dir = home / ".claude"
    claude_dir.mkdir()
    settings = claude_dir / "settings.json"
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()
    mcp_file = home / ".claude.json"

    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_DIR", claude_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SETTINGS", settings)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SKILLS", skills_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_MCP", mcp_file)
    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    config = CoworkerConfig(
        mcp=[McpServer(name="mcp1", command="cmd1", args=["--flag"])]
    )
    actions = claude.sync(config)
    assert any("MCP servers added" in a for a in actions)


# ── inject_static_context ─────────────────────────────────────────────────────


def test_inject_static_context_existing_file(tmp_path, monkeypatch):
    """inject_static_context updates an existing CLAUDE.md that already has a static block."""
    project = tmp_path / "proj"
    project.mkdir()
    claude_md = project / "CLAUDE.md"
    claude_md.write_text(
        "# My Project\n\n"
        + claude.STATIC_START + "\nold static\n" + claude.STATIC_END + "\n"
        "Some content.\n"
    )

    monkeypatch.setattr(claude, "_resolve_claude_md", lambda pd: claude_md)

    catalog = ProjectCatalog()
    actions = claude.inject_static_context(catalog, project_dir=project)
    assert any("updated" in a for a in actions)
    content = claude_md.read_text()
    assert claude.STATIC_START in content
    assert claude.STATIC_END in content
    assert "# My Project" in content
    assert "old static" not in content  # replaced


def test_inject_static_context_new_file(tmp_path, monkeypatch):
    """inject_static_context creates CLAUDE.md if it doesn't exist."""
    project = tmp_path / "proj"
    project.mkdir()
    claude_md = project / "CLAUDE.md"

    monkeypatch.setattr(claude, "_resolve_claude_md", lambda pd: claude_md)

    catalog = ProjectCatalog()
    actions = claude.inject_static_context(catalog, project_dir=project)
    assert any("injected" in a for a in actions)
    assert claude_md.exists()
    content = claude_md.read_text()
    assert claude.STATIC_START in content


# ── inject_feature ─────────────────────────────────────────────────────────


def test_inject_feature_existing_local_md(tmp_path, monkeypatch):
    """inject_feature injects into an existing CLAUDE.local.md."""
    project = tmp_path / "proj"
    project.mkdir()
    local_md = project / "CLAUDE.local.md"
    local_md.write_text("# Local context\n\n<!-- FEATURE_PLACEHOLDER -->\n")

    monkeypatch.setattr(claude, "_resolve_local_md", lambda pd: local_md)

    config = FeatureConfig(name="my-feature", description="Test feature")
    actions = claude.inject_feature(config, project_dir=project)
    assert any("injected" in a for a in actions)
    content = local_md.read_text()
    assert "my-feature" in content
    assert "FEATURE:my-feature START" in content
    assert "FEATURE:my-feature END" in content


def test_inject_feature_no_local_md_generates_template(tmp_path, monkeypatch):
    """inject_feature generates a template when CLAUDE.local.md doesn't exist."""
    project = tmp_path / "proj"
    project.mkdir()
    local_md = project / "CLAUDE.local.md"

    monkeypatch.setattr(claude, "_resolve_local_md", lambda pd: local_md)

    config = FeatureConfig(name="new-feature")
    actions = claude.inject_feature(config, project_dir=project)
    assert any("injected" in a for a in actions)
    assert local_md.exists()
    content = local_md.read_text()
    assert "new-feature" in content


def test_inject_feature_replaces_previous_feature(tmp_path, monkeypatch):
    """inject_feature replaces any existing feature blocks."""
    project = tmp_path / "proj"
    project.mkdir()
    local_md = project / "CLAUDE.local.md"
    local_md.write_text(
        "<!-- FEATURE:old START -->\n"
        "old content\n"
        "<!-- FEATURE:old END -->\n"
        "\n"
        "<!-- FEATURE_PLACEHOLDER -->\n"
    )

    monkeypatch.setattr(claude, "_resolve_local_md", lambda pd: local_md)

    config = FeatureConfig(name="new-feature", description="Fresh start")
    actions = claude.inject_feature(config, project_dir=project)
    content = local_md.read_text()
    assert "new-feature" in content
    assert "old" not in content  # old feature fully removed


# ── remove_feature ─────────────────────────────────────────────────────────


def test_remove_feature_no_file(tmp_path, monkeypatch):
    """remove_feature reports nothing to remove when file doesn't exist."""
    project = tmp_path / "proj"
    project.mkdir()
    local_md = project / "CLAUDE.local.md"

    monkeypatch.setattr(claude, "_resolve_local_md", lambda pd: local_md)

    actions = claude.remove_feature(project_dir=project)
    assert any("nothing to remove" in a for a in actions)


def test_remove_feature_with_feature(tmp_path, monkeypatch):
    """remove_feature removes an existing feature block."""
    project = tmp_path / "proj"
    project.mkdir()
    local_md = project / "CLAUDE.local.md"
    local_md.write_text(
        "# Local context\n\n"
        "<!-- FEATURE:test-init START -->\n"
        "## Active Feature: test-init\n\n"
        "Some content.\n"
        "<!-- FEATURE:test-init END -->\n"
        "\n"
        "<!-- FEATURE_PLACEHOLDER -->\n"
    )

    monkeypatch.setattr(claude, "_resolve_local_md", lambda pd: local_md)

    actions = claude.remove_feature(project_dir=project)
    assert any("removed" in a for a in actions)
    content = local_md.read_text()
    assert "test-init" not in content


def test_remove_feature_no_feature_in_file(tmp_path, monkeypatch):
    """remove_feature reports no feature when none exists in the file."""
    project = tmp_path / "proj"
    project.mkdir()
    local_md = project / "CLAUDE.local.md"
    local_md.write_text("# Just some local context\nNo features here.\n")

    monkeypatch.setattr(claude, "_resolve_local_md", lambda pd: local_md)

    actions = claude.remove_feature(project_dir=project)
    assert any("no feature" in a for a in actions)


# ── _remove_all_feature_blocks ─────────────────────────────────────────────


def test_remove_all_feature_blocks_single():
    content = (
        "before\n"
        "<!-- FEATURE:foo START -->\n"
        "block content\n"
        "<!-- FEATURE:foo END -->\n"
        "after\n"
    )
    result = claude._remove_all_feature_blocks(content)
    assert "FEATURE" not in result
    assert "before" in result
    assert "after" in result


def test_remove_all_feature_blocks_multiple():
    content = (
        "top\n"
        "<!-- FEATURE:a START -->\nblock a\n<!-- FEATURE:a END -->\n"
        "middle\n"
        "<!-- FEATURE:b START -->\nblock b\n<!-- FEATURE:b END -->\n"
        "bottom\n"
    )
    result = claude._remove_all_feature_blocks(content)
    assert "FEATURE" not in result
    assert "top" in result
    assert "middle" in result
    assert "bottom" in result


def test_remove_all_feature_blocks_collapses_blank_lines():
    content = (
        "line1\n\n\n\n"
        "<!-- FEATURE:foo START -->\nblock\n<!-- FEATURE:foo END -->\n"
        "\n\n\n\n"
        "line2\n"
    )
    result = claude._remove_all_feature_blocks(content)
    # Multiple blank lines collapsed into at most 2 consecutive
    assert "\n\n\n" not in result
    assert "line1" in result
    assert "line2" in result


# ── _build_static_block ───────────────────────────────────────────────────────


def test_build_static_block_empty_catalog():
    catalog = ProjectCatalog()
    block = claude._build_static_block(catalog)
    assert claude.STATIC_START in block
    assert claude.STATIC_END in block
    assert "_(no projects configured)_" in block
    assert "## Project Catalog" in block
    assert "## Coworker Skills" in block


def test_build_static_block_with_projects():
    catalog = ProjectCatalog(projects=[
        ProjectEntry(
            name="my-project",
            local_path="/home/user/my-project",
            upstream=[ProjectRef(name="lib-a")],
            downstream=[ProjectRef(name="app-x")],
        )
    ])
    block = claude._build_static_block(catalog)
    assert "my-project" in block
    assert "/home/user/my-project" in block
    assert "lib-a" in block
    assert "app-x" in block


def test_build_static_block_with_knowledge_pools():
    catalog = ProjectCatalog(projects=[
        ProjectEntry(
            name="kp-project",
            local_path="/tmp/kp",
            knowledge_pool=[
                KnowledgePoolEntry(type="docs", url="https://example.com"),
                KnowledgePoolEntry(type="code", path="/local/path"),
            ],
        )
    ])
    block = claude._build_static_block(catalog)
    assert "### Knowledge Pools" in block
    assert "https://example.com" in block
    assert "/local/path" in block


def test_build_static_block_with_refs():
    catalog = ProjectCatalog(projects=[
        ProjectEntry(
            name="ref-project",
            local_path="/tmp/ref",
            refs=Refs(
                github=[GitHubRef(owner="alice", repo="repo1")],
                slack=[SlackRef(channel="general", id="C123")],
                reddit=[RedditRef(subreddit="python")],
            ),
        )
    ])
    block = claude._build_static_block(catalog)
    assert "### Refs" in block
    assert "alice/repo1" in block
    assert "general" in block
    assert "python" in block


# ── _build_feature_block ───────────────────────────────────────────────────


def test_build_feature_block_minimal():
    config = FeatureConfig(name="minimal")
    block = claude._build_feature_block(config)
    assert "FEATURE:minimal START" in block
    assert "FEATURE:minimal END" in block
    assert "## Active Feature: minimal" in block
    # Optional sections should not appear
    assert "### Goal" not in block
    assert "### Approach" not in block
    assert "### Testing" not in block
    assert "### Recommended Skills" not in block
    assert "### Projects in scope" not in block
    assert "### Key Decisions" not in block
    assert "### Reference Docs" not in block
    assert "### Links" not in block


def test_build_feature_block_full_config():
    config = FeatureConfig(
        name="full-feature",
        description="A comprehensive test.",
        goal="Achieve greatness.",
        approach="TDD all the way.",
        testing="pytest with 95% coverage.",
        recommended_skills=["skill-a", "skill-b"],
        status="active",
        created="2025-01-15",
        projects=[
            FeatureProjectRef(name="proj1", role="primary", branches=["main", "dev"]),
            FeatureProjectRef(name="proj2", role="peer"),
        ],
        decisions=[
            Decision(date="2025-01-10", decision="Use Python", rationale="Best fit", by="team"),
        ],
        reference_docs=[
            ReferenceDoc(path="docs/ref.md", title="Reference One"),
        ],
        links=[
            LinkRef(url="https://example.com", title="Example", description="A useful link"),
        ],
    )
    block = claude._build_feature_block(config)
    assert "FEATURE:full-feature START" in block
    assert "FEATURE:full-feature END" in block
    assert "A comprehensive test." in block
    assert "Achieve greatness." in block
    assert "TDD all the way." in block
    assert "pytest with 95% coverage." in block
    assert "skill-a" in block
    assert "skill-b" in block
    assert "proj1" in block
    assert "proj2" in block
    assert "primary" in block
    assert "peer" in block
    assert "main, dev" in block
    assert "Use Python" in block
    assert "Best fit" in block
    assert "by team" in block
    assert "Reference One" in block
    assert "Example" in block
    assert "https://example.com" in block
    assert "A useful link" in block


def test_build_feature_block_with_goal_and_approach():
    config = FeatureConfig(name="ga", goal="Do something.", approach="Step by step.")
    block = claude._build_feature_block(config)
    assert "### Goal" in block
    assert "Do something." in block
    assert "### Approach" in block
    assert "Step by step." in block


def test_build_feature_block_with_testing():
    config = FeatureConfig(name="t", testing="pytest -v")
    block = claude._build_feature_block(config)
    assert "### Testing" in block
    assert "pytest -v" in block


def test_build_feature_block_with_recommended_skills():
    config = FeatureConfig(name="rs", recommended_skills=["code-review", "commit"])
    block = claude._build_feature_block(config)
    assert "### Recommended Skills" in block
    assert "code-review" in block
    assert "commit" in block


def test_build_feature_block_with_decisions_no_rationale():
    config = FeatureConfig(
        name="dec",
        decisions=[Decision(date="2025-06-01", decision="Switch DB", by="lead")],
    )
    block = claude._build_feature_block(config)
    assert "### Key Decisions" in block
    assert "2025-06-01" in block
    assert "Switch DB" in block
    assert "by lead" in block


def test_build_feature_block_with_links_no_description():
    config = FeatureConfig(
        name="lnk",
        links=[LinkRef(url="https://a.com", title="Site A")],
    )
    block = claude._build_feature_block(config)
    assert "### Links" in block
    assert "[Site A](https://a.com)" in block


def test_build_feature_block_with_projects_no_branches():
    config = FeatureConfig(
        name="np",
        projects=[FeatureProjectRef(name="p", role="downstream")],
    )
    block = claude._build_feature_block(config)
    assert "### Projects in scope" in block
    assert "| p | downstream | - |" in block


def test_build_feature_block_with_reference_docs():
    config = FeatureConfig(
        name="refs",
        reference_docs=[ReferenceDoc(path="~/docs/a.md", title="Doc A")],
    )
    block = claude._build_feature_block(config)
    assert "### Reference Docs" in block
    assert "~/docs/a.md" in block
    assert "Doc A" in block


def test_build_feature_block_with_empty_string_fields_not_rendered():
    config = FeatureConfig(
        name="empty-fields",
        description="",
        goal="",
        approach="",
        testing="",
    )
    block = claude._build_feature_block(config)
    assert "### Goal" not in block
    assert "### Approach" not in block
    assert "### Testing" not in block
    # description is falsy when empty, so it won't be rendered
    assert "> " not in block


def test_sync_preserves_user_settings_it_does_not_own(tmp_path, monkeypatch):
    """sync() must not strip settings the user set.

    It popped skipDangerousModePermissionPrompt from ~/.claude/settings.json on
    every run, so a user's own configuration disappeared without notice — and
    unlike the CLAUDE.md claims elsewhere ("your own content is never touched"),
    nothing said so.
    """
    home = tmp_path / "home"
    claude_dir = home / ".claude"
    claude_dir.mkdir(parents=True)
    settings = claude_dir / "settings.json"
    settings.write_text(json.dumps({
        "skipDangerousModePermissionPrompt": True,
        "effortLevel": "high",
        "theme": "dark",
    }))

    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_DIR", claude_dir)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SETTINGS", settings)
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_SKILLS", claude_dir / "skills")
    monkeypatch.setattr(claude, "CLAUDE_GLOBAL_MCP", home / ".claude.json")
    monkeypatch.setattr(claude.backup, "snapshot", lambda files, tag: None)

    claude.sync(CoworkerConfig())

    data = json.loads(settings.read_text())
    assert data.get("skipDangerousModePermissionPrompt") is True, (
        "sync() removed a setting the user had set"
    )
    assert data.get("effortLevel") == "high", (
        "sync() removed a setting the user had set"
    )
    assert data.get("theme") == "dark"


class TestManagedMcpPruning:
    """_sync_mcp was union-only, so a retired server lived in ~/.claude.json for ever.

    The refusal to delete is right — those entries may be the user's own — but
    it was unconditional, so there was no way to retire one of ours either.
    The fix is to remember what we wrote, exactly as we wrote it, and prune
    only that.
    """

    def _config(self, *names):
        from coworker.models import CoworkerConfig, McpServer

        return CoworkerConfig(
            name="t",
            mcp=[McpServer(name=n, command="npx", args=["-y", n], enabled=True)
                 for n in names],
        )

    def test_a_server_we_wrote_and_no_longer_produce_is_removed(
        self, tmp_path, monkeypatch
    ):
        from coworker.adapters.claude import _sync_mcp

        monkeypatch.setenv("HOME", str(tmp_path))
        mcp = tmp_path / ".claude.json"

        _sync_mcp(self._config("keeper", "retired"), mcp)
        _sync_mcp(self._config("keeper"), mcp)

        doc = json.loads(mcp.read_text())
        assert "keeper" in doc["mcpServers"]
        assert "retired" not in doc["mcpServers"], "our own retired server must go"

    def test_a_server_the_user_added_is_never_removed(self, tmp_path, monkeypatch):
        from coworker.adapters.claude import _sync_mcp

        monkeypatch.setenv("HOME", str(tmp_path))
        mcp = tmp_path / ".claude.json"
        mcp.write_text(json.dumps({"mcpServers": {
            "theirs": {"command": "their-own", "args": []},
        }}))

        _sync_mcp(self._config("ours"), mcp)
        _sync_mcp(self._config("ours"), mcp)

        doc = json.loads(mcp.read_text())
        assert "theirs" in doc["mcpServers"], "a server we never wrote is not ours"

    def test_a_server_the_user_edited_is_left_alone(self, tmp_path, monkeypatch):
        """Once it stops being what we wrote, it is theirs."""
        from coworker.adapters.claude import _sync_mcp

        monkeypatch.setenv("HOME", str(tmp_path))
        mcp = tmp_path / ".claude.json"

        _sync_mcp(self._config("shared"), mcp)

        doc = json.loads(mcp.read_text())
        doc["mcpServers"]["shared"] = {"command": "user-changed-it", "args": []}
        mcp.write_text(json.dumps(doc))

        _sync_mcp(self._config("other"), mcp)

        doc = json.loads(mcp.read_text())
        assert "shared" in doc["mcpServers"], "a user-edited entry must survive"
        assert "other" in doc["mcpServers"]
