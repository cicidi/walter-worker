from __future__ import annotations
import json
import os
import shutil
import re
import tempfile
from pathlib import Path
from ..models import CoworkerConfig, ProjectCatalog, InitiativeConfig
from .. import backup

CLAUDE_GLOBAL_DIR = Path.home() / ".claude"
CLAUDE_GLOBAL_SETTINGS = CLAUDE_GLOBAL_DIR / "settings.json"
CLAUDE_GLOBAL_SKILLS = CLAUDE_GLOBAL_DIR / "skills"
CLAUDE_GLOBAL_MCP = Path.home() / ".claude.json"

STATIC_START = "<!-- COWORKER:STATIC START -->"
STATIC_END = "<!-- COWORKER:STATIC END -->"
INITIATIVE_MARKER_RE = re.compile(
    r"<!-- INITIATIVE:.*? START -->.*?<!-- INITIATIVE:.*? END -->", re.DOTALL
)


def _resolve_claude_md(project_dir: Path | None) -> Path:
    if project_dir:
        return project_dir / "CLAUDE.md"
    return Path.cwd() / "CLAUDE.md"


def _resolve_local_md(project_dir: Path | None) -> Path:
    if project_dir:
        return project_dir / "CLAUDE.local.md"
    return Path.cwd() / "CLAUDE.local.md"


def _replace_or_append_block(
    content: str, start: str, end: str, new_block: str
) -> str:
    """Replace content between start..end markers with new_block.
    Handles truncated blocks (START present, END missing) by appending.
    Uses a single regex for the full range."""
    escaped_start = re.escape(start)
    escaped_end = re.escape(end)
    pattern = re.compile(
        escaped_start + r".*?" + escaped_end, re.DOTALL
    )
    if pattern.search(content):
        return pattern.sub(new_block, content)
    # No full match — could be truncated (START without END)
    if start in content:
        idx = content.index(start)
        return content[:idx] + new_block + "\n"
    return content.rstrip() + "\n\n" + new_block + "\n"


def _had_block(content: str, start: str) -> bool:
    return start in content


def _write_json_atomic(path: Path, data: object) -> None:
    """Write JSON to path atomically (tmp + rename) and keep a .bak."""
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


def _sync_mcp(config: CoworkerConfig, mcp_path: Path) -> list[str]:
    """Write MCP servers to mcp_path (union by server name)."""
    existing_mcp = {}
    if mcp_path.exists():
        try:
            existing_mcp = json.loads(mcp_path.read_text(encoding="utf-8")).get("mcpServers", {})
        except (json.JSONDecodeError, KeyError):
            pass

    ours = {}
    for server in config.mcp:
        if not server.enabled:
            continue
        entry: dict = {"command": server.command, "args": server.args}
        if server.env:
            entry["env"] = server.env
        ours[server.name] = entry

    merged = {**existing_mcp, **ours}  # our entries win on name collision
    mcp_doc = {"mcpServers": merged}
    _write_json_atomic(mcp_path, mcp_doc)
    added = [k for k in ours if k not in existing_mcp]
    updated = [k for k in ours if k in existing_mcp]
    actions = []
    if added:
        actions.append(f"MCP servers added: {', '.join(added)}")
    if updated:
        actions.append(f"MCP servers kept: {', '.join(updated)}")
    return actions


def sync(config: CoworkerConfig, project_dir: Path | None = None) -> list[str]:
    """Sync coworker config to Claude Code. Returns list of actions taken."""
    actions = []

    if project_dir:
        settings_path = project_dir / ".claude" / "settings.json"
        skills_dir = project_dir / ".claude" / "skills"
        mcp_path = project_dir / ".mcp.json"
    else:
        settings_path = CLAUDE_GLOBAL_SETTINGS
        skills_dir = CLAUDE_GLOBAL_SKILLS
        mcp_path = CLAUDE_GLOBAL_MCP

    # --- settings.json ---
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if settings_path.exists():
        with open(settings_path, encoding="utf-8") as f:
            existing = json.load(f)

    # Permissions: union-merge — never remove user's entries
    if config.permissions.allow:
        existing.setdefault("permissions", {})
        user_allow = set(existing["permissions"].get("allow", []))
        existing["permissions"]["allow"] = sorted(user_allow | set(config.permissions.allow))
    if config.permissions.deny:
        existing.setdefault("permissions", {})
        user_deny = set(existing["permissions"].get("deny", []))
        existing["permissions"]["deny"] = sorted(user_deny | set(config.permissions.deny))

    # MCP servers → ~/.claude.json or .mcp.json (Claude Code reads MCP from
    # these files, NOT from settings.json).  Remove stale mcpServers from
    # settings.json if present.
    if config.mcp:
        mcp_actions = _sync_mcp(config, mcp_path)
        actions.extend(mcp_actions)
    existing.pop("mcpServers", None)
    existing.pop("effortLevel", None)
    existing.pop("skipDangerousModePermissionPrompt", None)

    # State-update hook (correctly-shaped — already fixed in prior WIP)
    existing.setdefault("hooks", {})
    stop_hooks = existing["hooks"].get("Stop", [])

    def _is_state_update(h):
        return isinstance(h, dict) and h.get("command") == "coworker state-update"

    stop_hooks = [g for g in stop_hooks if not (_is_state_update(g) and "hooks" not in g)]
    has_state_update = any(
        _is_state_update(h)
        for g in stop_hooks if isinstance(g, dict)
        for h in (g.get("hooks") or [])
    )
    if not has_state_update:
        stop_hooks.append({
            "matcher": "",
            "hooks": [{"type": "command", "command": "coworker state-update"}],
        })
    existing["hooks"]["Stop"] = stop_hooks

    _write_json_atomic(settings_path, existing)
    actions.append(f"updated {settings_path}")

    # --- skills ---
    skills_dir.mkdir(parents=True, exist_ok=True)
    for skill in config.skills:
        if not skill.enabled:
            continue
        skill_path = Path(skill.path)
        if not skill_path.is_absolute():
            base = project_dir or (Path.home() / ".coworker")
            skill_path = base / skill.path
        if not skill_path.exists():
            actions.append(f"  [warn] skill path not found: {skill_path}")
            continue
        dest = skills_dir / skill.name
        dest.mkdir(parents=True, exist_ok=True)
        if skill_path.is_dir():
            for f in skill_path.iterdir():
                shutil.copy2(f, dest / f.name)
        else:
            shutil.copy2(skill_path, dest / skill_path.name)
        actions.append(f"  installed skill '{skill.name}' → {dest}")

    return actions


# ── Context injection ───────────────────────────────────────────────────────


def inject_static_context(
    catalog: ProjectCatalog, project_dir: Path | None = None
) -> list[str]:
    actions = []
    block = _build_static_block(catalog)
    target = _resolve_claude_md(project_dir)

    content = target.read_text() if target.exists() else ""
    had_block = _had_block(content, STATIC_START)
    content = _replace_or_append_block(content, STATIC_START, STATIC_END, block)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    verb = "updated" if had_block else "injected"
    actions.append(f"{verb} static context in {target.name}")
    return actions


def inject_initiative(
    config: InitiativeConfig, project_dir: Path | None = None
) -> list[str]:
    actions = []
    block = _build_initiative_block(config)
    target = _resolve_local_md(project_dir)

    if target.exists():
        content = target.read_text()
    else:
        from ..templates.local_claude_md import generate_local_claude_md
        content = generate_local_claude_md()

    from ..templates.local_claude_md import inject_initiative_into_local_md
    updated = inject_initiative_into_local_md(content, block)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(updated)
    actions.append(f"injected initiative '{config.name}' into {target.name}")
    return actions


def remove_initiative(project_dir: Path | None = None) -> list[str]:
    actions = []
    target = _resolve_local_md(project_dir)
    if not target.exists():
        actions.append("no CLAUDE.local.md found, nothing to remove")
        return actions

    content = target.read_text()
    name = None
    match = re.search(r"<!-- INITIATIVE:(\S+) START -->", content)
    if match:
        name = match.group(1)
    if name:
        from ..templates.local_claude_md import remove_initiative_from_local_md
        updated = remove_initiative_from_local_md(content, name)
        if updated != content:
            target.write_text(updated)
            actions.append(f"removed initiative '{name}' from {target.name}")
        else:
            actions.append(f"no initiative in {target.name}")
    else:
        actions.append(f"no initiative in {target.name}")
    return actions


def _remove_all_initiative_blocks(content: str) -> str:
    result = INITIATIVE_MARKER_RE.sub("", content)
    # collapse multiple blank lines left by removed blocks
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.rstrip() + "\n"


def _build_static_block(catalog: ProjectCatalog) -> str:
    lines = [STATIC_START, "## Project Catalog", ""]
    if not catalog.projects:
        lines.append("_(no projects configured)_")
    else:
        lines.append("| Project | Path | Upstream | Downstream |")
        lines.append("|---------|------|----------|------------|")
        for p in catalog.projects:
            up = ", ".join(u.name for u in p.upstream) or "-"
            down = ", ".join(d.name for d in p.downstream) or "-"
            lines.append(f"| {p.name} | {p.local_path} | {up} | {down} |")

        lines.append("")
        lines.append("### Knowledge Pools")
        for p in catalog.projects:
            if p.knowledge_pool:
                entries = []
                for kp in p.knowledge_pool:
                    if kp.url:
                        entries.append(f"{kp.type} ({kp.url})")
                    elif kp.path:
                        entries.append(f"{kp.type} ({kp.path})")
                if entries:
                    lines.append(f"- {p.name}: {', '.join(entries)}")

        lines.append("")
        lines.append("### Refs")
        for p in catalog.projects:
            ref_parts = []
            if p.refs.slack:
                ref_parts.append(
                    f"Slack: {', '.join(s.channel for s in p.refs.slack)}"
                )
            if p.refs.github:
                ref_parts.append(
                    f"GitHub: {', '.join(f'{g.owner}/{g.repo}' for g in p.refs.github)}"
                )
            if p.refs.reddit:
                ref_parts.append(
                    f"Reddit: {', '.join(r.subreddit for r in p.refs.reddit)}"
                )
            if ref_parts:
                lines.append(f"- {p.name}: {'; '.join(ref_parts)}")

    lines.append("")
    lines.append("## Docs Directory Structure")
    lines.append("")
    from ..constants import DOCS_DISCIPLINES
    disciplines = ", ".join(DOCS_DISCIPLINES)
    lines.append(f"Docs organized by topic: `docs/<initiative>/{{{disciplines}}}/`")
    lines.append("")
    lines.append("Each initiative creates its own docs folder with prd/plan/spec subdirectories.")
    lines.append("")
    lines.append("## Coworker Skills")
    lines.append("")
    lines.append("Coworker skills are installed to IDE skill directories. Check available")
    lines.append("skills before writing ad-hoc instructions. Use `coworker skill list` to")
    lines.append("see installed skills.")
    lines.append("")
    lines.append("Skills must have a matching trigger phrase to be invoked.")
    lines.append("")
    lines.append(STATIC_END)
    return "\n".join(lines) + "\n"


def _build_initiative_block(config: InitiativeConfig) -> str:
    start = f"<!-- INITIATIVE:{config.name} START -->"
    end = f"<!-- INITIATIVE:{config.name} END -->"
    lines = [start, f"## Active Initiative: {config.name}", ""]
    if config.description:
        lines.append(f"> {config.description}")
        lines.append("")

    if config.goal:
        lines.append("### Goal")
        lines.append(config.goal)
        lines.append("")

    if config.approach:
        lines.append("### Approach")
        lines.append(config.approach)
        lines.append("")

    if config.testing:
        lines.append("### Testing")
        lines.append(config.testing)
        lines.append("")

    if config.recommended_skills:
        lines.append("### Recommended Skills")
        lines.append("_User-reviewed skills for this initiative. Invoke when relevant._")
        lines.append("")
        for skill in config.recommended_skills:
            lines.append(f"- `{skill}`")
        lines.append("")

    if config.projects:
        lines.append("### Projects in scope")
        lines.append("| Project | Role | Branches |")
        lines.append("|---------|------|----------|")
        for p in config.projects:
            branches = ", ".join(p.branches) if p.branches else "-"
            lines.append(f"| {p.name} | {p.role} | {branches} |")
        lines.append("")

    if config.decisions:
        lines.append("### Key Decisions")
        for d in config.decisions:
            lines.append(f"- {d.date}: {d.decision} (by {d.by})")
            if d.rationale:
                lines.append(f"  - {d.rationale}")
        lines.append("")

    if config.reference_docs:
        lines.append("### Reference Docs")
        for rd in config.reference_docs:
            lines.append(f"- `{rd.path}` — {rd.title}")
        lines.append("")

    if config.links:
        lines.append("### Links")
        for link in config.links:
            lines.append(f"- [{link.title}]({link.url})")
            if link.description:
                lines.append(f"  - {link.description}")
        lines.append("")

    lines.append(end)
    return "\n".join(lines) + "\n"
