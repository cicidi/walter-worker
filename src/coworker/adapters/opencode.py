from __future__ import annotations
import json
from pathlib import Path
from ..models import CoworkerConfig, ProjectCatalog, FeatureConfig
# Shared with the Claude adapter rather than duplicated, as gemini.py already
# does for _write_json_atomic: the managed-entry bookkeeping has to mean the
# same thing wherever it is read.
from .claude import _load_managed_mcp, _save_managed_mcp

OPENCODE_DIR = Path.home() / ".config" / "opencode"
OPENCODE_CONFIG = OPENCODE_DIR / "config.json"


def _resolve_instructions_md(project_dir: Path | None) -> Path:
    if project_dir:
        return project_dir / ".opencode" / "instructions.md"
    return Path.cwd() / ".opencode" / "instructions.md"


def sync(config: CoworkerConfig, project_dir: Path | None = None) -> list[str]:
    """Sync coworker config to OpenCode. Returns list of actions taken."""
    actions = []

    if project_dir:
        config_path = project_dir / ".opencode" / "config.json"
    else:
        config_path = OPENCODE_CONFIG

    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if config_path.exists():
        with open(config_path) as f:
            existing = json.load(f)

    # apply opencode-specific overrides
    existing.update(config.opencode.extra)

    # apply MCP servers
    if config.mcp:
        mcp_servers = {}
        for server in config.mcp:
            if not server.enabled:
                continue
            command = [server.command] + (server.args or [])
            entry: dict = {"type": "local", "enabled": True, "command": command}
            if server.env:
                entry["env"] = server.env
            mcp_servers[server.name] = entry

        # Merge, don't replace. Assigning the map outright deleted every server
        # the user had added to their own OpenCode config, on every sync — the
        # same silent loss of the user's configuration that the Claude settings
        # path was fixed for. Only entries we wrote, and that still hold
        # exactly what we wrote, are ours to retire.
        user_mcp = existing.get("mcp", {})
        if not isinstance(user_mcp, dict):
            user_mcp = {}
        managed = _load_managed_mcp(config_path)
        for name, written in managed.items():
            if name not in mcp_servers and user_mcp.get(name) == written:
                user_mcp.pop(name)

        existing["mcp"] = {**user_mcp, **mcp_servers}
        _save_managed_mcp(config_path, mcp_servers)

    with open(config_path, "w") as f:
        json.dump(existing, f, indent=2)
    actions.append(f"updated {config_path}")

    # Add state-update permission
    existing.setdefault("permission", {})
    bash_perms = existing["permission"].get("bash", {})
    if isinstance(bash_perms, dict):
        bash_perms["coworker *"] = "allow"
        existing["permission"]["bash"] = bash_perms
        with open(config_path, "w") as f:
            json.dump(existing, f, indent=2)

    return actions


# ── Context injection ───────────────────────────────────────────────────────


def inject_static_context(
    catalog: ProjectCatalog, project_dir: Path | None = None
) -> list[str]:
    from .claude import (
        _build_static_block,
        _replace_or_append_block,
        STATIC_START,
        STATIC_END,
    )
    actions = []
    block = _build_static_block(catalog)
    target = _resolve_instructions_md(project_dir)

    content = target.read_text() if target.exists() else ""
    content = _replace_or_append_block(content, STATIC_START, STATIC_END, block)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)

    verb = "updated" if STATIC_START in content else "injected"
    actions.append(f"{verb} static context in {target.name}")
    return actions


def inject_feature(
    config: FeatureConfig, project_dir: Path | None = None
) -> list[str]:
    from .claude import inject_feature as claude_inject
    return claude_inject(config, project_dir=project_dir)


def remove_feature(project_dir: Path | None = None) -> list[str]:
    from .claude import remove_feature as claude_remove
    return claude_remove(project_dir=project_dir)
