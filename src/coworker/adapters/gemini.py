from __future__ import annotations
import json
from pathlib import Path
from ..models import CoworkerConfig
# Shared with the Claude adapter rather than duplicated: the two copies had
# already drifted, and a fix applied to one would silently miss the other.
from .claude import _write_json_atomic

GEMINI_DIR = Path.home() / ".gemini"
GEMINI_SETTINGS = GEMINI_DIR / "settings.json"


def sync(config: CoworkerConfig, project_dir: Path | None = None) -> list[str]:
    """Sync coworker config to Gemini CLI. Returns list of actions taken."""
    actions = []

    if project_dir:
        settings_path = project_dir / ".gemini" / "settings.json"
    else:
        settings_path = GEMINI_SETTINGS

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if settings_path.exists():
        with open(settings_path, encoding="utf-8") as f:
            existing = json.load(f)

    existing.update(config.gemini.extra)

    # MCP servers — union by name, never remove user's servers
    if config.mcp:
        user_mcp = existing.get("mcpServers", {})
        ours = {}
        for server in config.mcp:
            if not server.enabled:
                continue
            entry: dict = {"command": server.command, "args": server.args}
            if server.env:
                entry["env"] = server.env
            ours[server.name] = entry
        existing["mcpServers"] = {**user_mcp, **ours}

    _write_json_atomic(settings_path, existing)
    actions.append(f"updated {settings_path}")

    return actions
