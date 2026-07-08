from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from ..models import CoworkerConfig
from .. import backup

GEMINI_DIR = Path.home() / ".gemini"
GEMINI_SETTINGS = GEMINI_DIR / "settings.json"


def _write_json_atomic(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup.snapshot([path], "json-sync")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


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
