from __future__ import annotations
import json
from pathlib import Path

import pytest

from coworker.adapters import opencode
from coworker.models import (
    CoworkerConfig,
    InitiativeConfig,
    McpServer,
    OpenCodeOverrides,
    ProjectCatalog,
    ProjectEntry,
)


# ── Helper to build a minimal CoworkerConfig ──────────────────────────────────

def _make_config(**kwargs) -> CoworkerConfig:
    defaults = dict(version="1", scope="global", opencode=OpenCodeOverrides())
    defaults.update(kwargs)
    return CoworkerConfig(**defaults)


# ── sync() tests ──────────────────────────────────────────────────────────────


class TestSync:
    """Tests for opencode.sync()."""

    def test_no_existing_config_creates_new(self, tmp_path, monkeypatch):
        """When no config.json exists, sync creates one with MCP servers and permissions."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        config = _make_config(
            mcp=[
                McpServer(name="filesystem", command="npx", args=["-y", "@modelcontextprotocol/server-filesystem"]),
            ]
        )
        actions = opencode.sync(config)

        assert (tmp_path / "config.json").exists()
        written = json.loads((tmp_path / "config.json").read_text())
        assert "mcp" in written
        assert "filesystem" in written["mcp"]
        assert written["mcp"]["filesystem"]["type"] == "local"
        assert written["mcp"]["filesystem"]["enabled"] is True
        assert written["mcp"]["filesystem"]["command"] == ["npx", "-y", "@modelcontextprotocol/server-filesystem"]
        assert written["permission"]["bash"]["coworker *"] == "allow"
        assert any("config.json" in a for a in actions)

    def test_existing_config_mcp_is_replaced_not_merged(self, tmp_path, monkeypatch):
        """Coworker MCP servers replace (not merge with) any existing mcp key."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        # Pre-existing config with a user-defined MCP server
        existing = {
            "mcp": {
                "user-server": {
                    "type": "local",
                    "enabled": True,
                    "command": ["node", "user-server.js"],
                }
            }
        }
        (tmp_path / "config.json").write_text(json.dumps(existing))

        config = _make_config(
            mcp=[McpServer(name="coworker-server", command="coworker", args=["mcp"])],
        )
        opencode.sync(config)

        written = json.loads((tmp_path / "config.json").read_text())
        # Our server is written
        assert "coworker-server" in written["mcp"]
        assert written["mcp"]["coworker-server"]["command"] == ["coworker", "mcp"]
        # Existing user server is overwritten (full replace, not merge)
        assert "user-server" not in written["mcp"]

    def test_disabled_mcp_server_skipped(self, tmp_path, monkeypatch):
        """Disabled MCP servers are not written to config."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        config = _make_config(
            mcp=[
                McpServer(name="enabled-one", command="cmd1", enabled=True),
                McpServer(name="disabled-one", command="cmd2", enabled=False),
            ],
        )
        opencode.sync(config)

        written = json.loads((tmp_path / "config.json").read_text())
        assert "enabled-one" in written["mcp"]
        assert "disabled-one" not in written["mcp"]

    def test_empty_mcp_list_does_not_write_mcp_key(self, tmp_path, monkeypatch):
        """When config.mcp is empty, the 'mcp' key is not written."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        config = _make_config(mcp=[])
        opencode.sync(config)

        written = json.loads((tmp_path / "config.json").read_text())
        assert "mcp" not in written
        # Permissions are still injected
        assert written["permission"]["bash"]["coworker *"] == "allow"

    def test_all_servers_disabled_writes_empty_mcp(self, tmp_path, monkeypatch):
        """When all servers are disabled, mcp_servers dict is empty but mcp key is written."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        config = _make_config(
            mcp=[McpServer(name="off", command="cmd", enabled=False)],
        )
        opencode.sync(config)

        written = json.loads((tmp_path / "config.json").read_text())
        # mcp key is written but contains no servers (empty dict)
        assert "mcp" in written
        assert written["mcp"] == {}

    def test_project_dir_writes_to_project_opencode(self, tmp_path):
        """When project_dir is provided, config is written to <project_dir>/.opencode/config.json."""
        project_dir = tmp_path / "my-project"
        config = _make_config(
            mcp=[McpServer(name="local", command="ls")],
        )

        opencode.sync(config, project_dir=project_dir)

        expected_path = project_dir / ".opencode" / "config.json"
        assert expected_path.exists()
        written = json.loads(expected_path.read_text())
        assert "local" in written["mcp"]

    def test_permission_injection(self, tmp_path, monkeypatch):
        """The bash permission 'coworker *' is set to 'allow'."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        config = _make_config()
        opencode.sync(config)

        written = json.loads((tmp_path / "config.json").read_text())
        assert written["permission"]["bash"]["coworker *"] == "allow"

    def test_permission_injection_preserves_existing_perms(self, tmp_path, monkeypatch):
        """Existing permissions are preserved when injecting coworker bash permission."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        existing = {
            "permission": {
                "bash": {"git *": "allow", "npm *": "allow"}
            }
        }
        (tmp_path / "config.json").write_text(json.dumps(existing))

        config = _make_config()
        opencode.sync(config)

        written = json.loads((tmp_path / "config.json").read_text())
        assert written["permission"]["bash"]["git *"] == "allow"
        assert written["permission"]["bash"]["npm *"] == "allow"
        assert written["permission"]["bash"]["coworker *"] == "allow"

    def test_opencode_extra_applied(self, tmp_path, monkeypatch):
        """config.opencode.extra entries are merged into the config."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        config = _make_config(
            opencode=OpenCodeOverrides(extra={"theme": "dark", "editor": "vim"}),
        )
        opencode.sync(config)

        written = json.loads((tmp_path / "config.json").read_text())
        assert written["theme"] == "dark"
        assert written["editor"] == "vim"

    def test_opencode_extra_overwrites_existing_keys(self, tmp_path, monkeypatch):
        """config.opencode.extra values overwrite existing keys in the config."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        existing = {"theme": "light", "unchanged": "keep"}
        (tmp_path / "config.json").write_text(json.dumps(existing))

        config = _make_config(
            opencode=OpenCodeOverrides(extra={"theme": "dark"}),
        )
        opencode.sync(config)

        written = json.loads((tmp_path / "config.json").read_text())
        assert written["theme"] == "dark"
        assert written["unchanged"] == "keep"

    def test_mcp_server_with_env(self, tmp_path, monkeypatch):
        """MCP server entry includes 'env' when environment vars are configured."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        config = _make_config(
            mcp=[
                McpServer(
                    name="with-env",
                    command="python",
                    args=["server.py"],
                    env={"API_KEY": "secret", "DEBUG": "1"},
                ),
            ],
        )
        opencode.sync(config)

        written = json.loads((tmp_path / "config.json").read_text())
        server = written["mcp"]["with-env"]
        assert server["env"] == {"API_KEY": "secret", "DEBUG": "1"}

    def test_mcp_server_without_args(self, tmp_path, monkeypatch):
        """MCP server without args still works (uses empty args list)."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        config = _make_config(
            mcp=[McpServer(name="simple", command="myserver")],
        )
        opencode.sync(config)

        written = json.loads((tmp_path / "config.json").read_text())
        assert written["mcp"]["simple"]["command"] == ["myserver"]

    def test_sync_returns_actions_with_updated_message(self, tmp_path, monkeypatch):
        """sync() returns a list of actions including the 'updated' message."""
        monkeypatch.setattr(opencode, "OPENCODE_CONFIG", tmp_path / "config.json")

        config = _make_config()
        actions = opencode.sync(config)

        assert len(actions) >= 1
        assert any("updated" in a.lower() for a in actions)


# ── inject_static_context() tests ─────────────────────────────────────────────


class TestInjectStaticContext:
    """Tests for opencode.inject_static_context()."""

    def _mock_claude_helpers(self, monkeypatch, static_block="<!-- COWORKER:STATIC START -->\nblock\n<!-- COWORKER:STATIC END -->\n"):
        """Mock the claude helper functions used by inject_static_context."""
        monkeypatch.setattr(
            "coworker.adapters.claude._build_static_block",
            lambda catalog: static_block,
        )
        # Pass-through: return the content with block appended
        monkeypatch.setattr(
            "coworker.adapters.claude._replace_or_append_block",
            lambda content, start, end, block: content.rstrip() + "\n\n" + block + "\n",
        )
        monkeypatch.setattr(
            "coworker.adapters.claude.STATIC_START",
            "<!-- COWORKER:STATIC START -->",
        )
        monkeypatch.setattr(
            "coworker.adapters.claude.STATIC_END",
            "<!-- COWORKER:STATIC END -->",
        )

    def test_injects_into_empty_file(self, tmp_path, monkeypatch):
        """Static context is injected into a non-existent instructions.md."""
        self._mock_claude_helpers(monkeypatch)

        # Use a project_dir so instructions.md lands inside it
        instructions_dir = tmp_path / ".opencode"
        catalog = ProjectCatalog(projects=[ProjectEntry(name="test", local_path="/tmp/test")])

        actions = opencode.inject_static_context(catalog, project_dir=tmp_path)

        target = instructions_dir / "instructions.md"
        assert target.exists()
        content = target.read_text()
        assert "block" in content
        # Verb depends on whether the mock block contains STATIC_START marker
        assert any("injected" in a or "updated" in a for a in actions)

    def test_updates_existing_file(self, tmp_path, monkeypatch):
        """Static context replaces existing block in instructions.md."""
        self._mock_claude_helpers(monkeypatch)

        instructions_dir = tmp_path / ".opencode"
        instructions_dir.mkdir(parents=True)
        existing_content = "# Existing instructions\n"
        (instructions_dir / "instructions.md").write_text(existing_content)

        catalog = ProjectCatalog()

        actions = opencode.inject_static_context(catalog, project_dir=tmp_path)

        target = instructions_dir / "instructions.md"
        content = target.read_text()
        assert "# Existing instructions" in content
        assert "block" in content
        assert any("injected" in a or "updated" in a for a in actions)

    def test_empty_catalog_shows_no_projects(self, tmp_path, monkeypatch):
        """When catalog has no projects, the generated block contains a placeholder."""
        self._mock_claude_helpers(
            monkeypatch,
            static_block="<!-- COWORKER:STATIC START -->\n_(no projects configured)_\n<!-- COWORKER:STATIC END -->\n",
        )

        catalog = ProjectCatalog()

        actions = opencode.inject_static_context(catalog, project_dir=tmp_path)

        target = tmp_path / ".opencode" / "instructions.md"
        content = target.read_text()
        assert "no projects configured" in content
        assert len(actions) >= 1

    def test_without_project_dir_uses_cwd(self, tmp_path, monkeypatch):
        """When project_dir is None, instructions.md is written relative to cwd."""
        self._mock_claude_helpers(monkeypatch)

        # Redirect cwd to temp dir
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        catalog = ProjectCatalog()

        actions = opencode.inject_static_context(catalog)

        target = tmp_path / ".opencode" / "instructions.md"
        assert target.exists()
        assert any("injected" in a or "updated" in a for a in actions)


# ── inject_initiative() tests ─────────────────────────────────────────────────


class TestInjectInitiative:
    """Tests for opencode.inject_initiative() — delegation to claude adapter."""

    def test_delegates_to_claude_inject_initiative(self, monkeypatch):
        """inject_initiative delegates to claude.inject_initiative with the same args."""
        called_with = {}

        def fake_claude_inject(config, project_dir=None):
            called_with["config"] = config
            called_with["project_dir"] = project_dir
            return ["injected initiative test-initiative"]

        monkeypatch.setattr(
            "coworker.adapters.claude.inject_initiative",
            fake_claude_inject,
        )

        config = InitiativeConfig(name="test-initiative", description="A test")
        result = opencode.inject_initiative(config, project_dir=None)

        assert called_with["config"] is config
        assert called_with["project_dir"] is None
        assert result == ["injected initiative test-initiative"]

    def test_delegates_with_project_dir(self, monkeypatch, tmp_path):
        """inject_initiative passes project_dir through to claude.inject_initiative."""
        called_with = {}

        def fake_claude_inject(config, project_dir=None):
            called_with["config"] = config
            called_with["project_dir"] = project_dir
            return ["done"]

        monkeypatch.setattr(
            "coworker.adapters.claude.inject_initiative",
            fake_claude_inject,
        )

        config = InitiativeConfig(name="proj-init")
        result = opencode.inject_initiative(config, project_dir=tmp_path)

        assert called_with["project_dir"] == tmp_path
        assert result == ["done"]

    def test_returns_claude_inject_return_value(self, monkeypatch):
        """The return value from claude.inject_initiative is propagated directly."""
        expected = ["action-1", "action-2"]
        monkeypatch.setattr(
            "coworker.adapters.claude.inject_initiative",
            lambda config, project_dir=None: expected,
        )

        config = InitiativeConfig(name="test")
        result = opencode.inject_initiative(config)

        assert result == expected


# ── remove_initiative() tests ─────────────────────────────────────────────────


class TestRemoveInitiative:
    """Tests for opencode.remove_initiative() — delegation to claude adapter."""

    def test_delegates_to_claude_remove_initiative(self, monkeypatch):
        """remove_initiative delegates to claude.remove_initiative."""
        called_with = {}

        def fake_claude_remove(project_dir=None):
            called_with["project_dir"] = project_dir
            return ["removed initiative"]

        monkeypatch.setattr(
            "coworker.adapters.claude.remove_initiative",
            fake_claude_remove,
        )

        result = opencode.remove_initiative(project_dir=None)

        assert called_with["project_dir"] is None
        assert result == ["removed initiative"]

    def test_delegates_with_project_dir(self, monkeypatch, tmp_path):
        """remove_initiative passes project_dir through to claude.remove_initiative."""
        called_with = {}

        def fake_claude_remove(project_dir=None):
            called_with["project_dir"] = project_dir
            return ["cleared"]

        monkeypatch.setattr(
            "coworker.adapters.claude.remove_initiative",
            fake_claude_remove,
        )

        result = opencode.remove_initiative(project_dir=tmp_path)

        assert called_with["project_dir"] == tmp_path
        assert result == ["cleared"]

    def test_returns_claude_remove_return_value(self, monkeypatch):
        """The return value from claude.remove_initiative is propagated directly."""
        expected = ["removed initiative my-initiative"]
        monkeypatch.setattr(
            "coworker.adapters.claude.remove_initiative",
            lambda project_dir=None: expected,
        )

        result = opencode.remove_initiative()

        assert result == expected


# ── _resolve_instructions_md tests ────────────────────────────────────────────


class TestResolveInstructionsMd:
    """Tests for opencode._resolve_instructions_md()."""

    def test_with_project_dir(self, tmp_path):
        """Returns project_dir/.opencode/instructions.md when project_dir is given."""
        result = opencode._resolve_instructions_md(tmp_path)
        assert result == tmp_path / ".opencode" / "instructions.md"

    def test_without_project_dir(self, monkeypatch, tmp_path):
        """Returns cwd/.opencode/instructions.md when project_dir is None."""
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        result = opencode._resolve_instructions_md(None)
        assert result == tmp_path / ".opencode" / "instructions.md"
