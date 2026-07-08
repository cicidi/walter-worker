from __future__ import annotations
import json
import shutil
import re
from pathlib import Path
from ..models import CoworkerConfig, ProjectCatalog, InitiativeConfig

CLAUDE_GLOBAL_DIR = Path.home() / ".claude"
CLAUDE_GLOBAL_SETTINGS = CLAUDE_GLOBAL_DIR / "settings.json"
CLAUDE_GLOBAL_SKILLS = CLAUDE_GLOBAL_DIR / "skills"

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
    if start in content:
        before = content[: content.index(start)]
        after = content[content.index(end) + len(end):]
        return before + new_block + after
    return content.rstrip() + "\n\n" + new_block + "\n"


def sync(config: CoworkerConfig, project_dir: Path | None = None) -> list[str]:
    """Sync coworker config to Claude Code. Returns list of actions taken."""
    actions = []

    if project_dir:
        settings_path = project_dir / ".claude" / "settings.json"
        skills_dir = project_dir / ".claude" / "skills"
    else:
        settings_path = CLAUDE_GLOBAL_SETTINGS
        skills_dir = CLAUDE_GLOBAL_SKILLS

    # --- settings.json ---
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if settings_path.exists():
        with open(settings_path) as f:
            existing = json.load(f)

    # apply claude overrides
    overrides = config.claude.model_dump(exclude={"extra"})
    overrides.update(config.claude.extra)
    existing.update(overrides)

    # apply permissions
    if config.permissions.allow:
        existing["permissions"] = existing.get("permissions", {})
        existing["permissions"]["allow"] = config.permissions.allow
    if config.permissions.deny:
        existing.setdefault("permissions", {})["deny"] = config.permissions.deny

    # apply MCP servers
    if config.mcp:
        mcp_servers = {}
        for server in config.mcp:
            if not server.enabled:
                continue
            entry: dict = {"command": server.command, "args": server.args}
            if server.env:
                entry["env"] = server.env
            mcp_servers[server.name] = entry
        existing["mcpServers"] = mcp_servers

    # apply state-update hook (runs coworker state-update on Stop).
    # Each entry must be {"matcher": str, "hooks": [{"type","command"}, ...]}.
    existing.setdefault("hooks", {})
    stop_hooks = existing["hooks"].get("Stop", [])

    def _is_state_update(h):
        return isinstance(h, dict) and h.get("command") == "coworker state-update"

    # Drop legacy malformed entries (command at group level) and detect any
    # correctly-nested state-update hook so we don't duplicate it.
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

    with open(settings_path, "w") as f:
        json.dump(existing, f, indent=2)
    actions.append(f"updated {settings_path}")

    # --- skills ---
    skills_dir.mkdir(parents=True, exist_ok=True)
    for skill in config.skills:
        if not skill.enabled:
            continue
        skill_path = Path(skill.path)
        if not skill_path.is_absolute():
            # resolve relative to coworker global dir or project dir
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
    content = _replace_or_append_block(content, STATIC_START, STATIC_END, block)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)

    verb = "updated" if STATIC_START in content else "injected"
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
    lines.append("Expected project documentation layout:")
    lines.append("- `docs/` — Project documentation root")
    lines.append("- `docs/architecture/` — Architecture decisions and overview")
    lines.append("- `docs/spec/` — Feature specifications and technical design")
    lines.append("- `docs/planning/` — Task breakdowns and implementation plans")
    lines.append("")
    lines.append("## Coworker Skills")
    lines.append("")
    lines.append("Prefer coworker skills for repeatable workflows. Check available skills before")
    lines.append("writing ad-hoc instructions. Skills are auto-loaded from `personal/skills/` and")
    lines.append("`.cursor/rules/` directories. If a task has a matching coworker skill, use it.")
    lines.append("")
    lines.append("Key skill categories:")
    lines.append("- `coworker-dev-*` — Development workflow stages (understand, decompose, execute, verify, pr)")
    lines.append("- `coworker-do-*` — Quality gates (guardrails, code-review, code-conventions, unit-tests)")
    lines.append("- `coworker-debug-*` — Debugging and issue investigation")
    lines.append("")
    lines.append("For tasks without a matching skill, follow the 5-stage pipeline defined above.")
    lines.append("When a pattern repeats, suggest creating a new coworker skill via `create-skill`.")
    lines.append("")
    lines.append("## Additional Behavioral Guidelines")
    lines.append("")
    lines.append("_Source: [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) —")
    lines.append("merged with attribution._")
    lines.append("")
    lines.append("### 1. Think Before Coding")
    lines.append("")
    lines.append("Dont assume. Dont hide confusion. Surface tradeoffs.")
    lines.append("")
    lines.append("- State your assumptions explicitly. If uncertain, ask.")
    lines.append("- If multiple interpretations exist, present them — dont pick silently.")
    lines.append("- If a simpler approach exists, say so. Push back when warranted.")
    lines.append("- If something is unclear, stop. Name whats confusing. Ask.")
    lines.append("")
    lines.append("### 2. Simplicity First")
    lines.append("")
    lines.append("Minimum code that solves the problem. Nothing speculative.")
    lines.append("")
    lines.append("- No features beyond what was asked.")
    lines.append("- No abstractions for single-use code.")
    lines.append("- No flexibility or configurability that wasnt requested.")
    lines.append("- No error handling for impossible scenarios.")
    lines.append("- If you write 200 lines and it could be 50, rewrite it.")
    lines.append("")
    lines.append("Ask yourself: Would a senior engineer say this is overcomplicated? If yes, simplify.")
    lines.append("")
    lines.append("### 3. Surgical Changes")
    lines.append("")
    lines.append("Touch only what you must. Clean up only your own mess.")
    lines.append("")
    lines.append("- Dont improve adjacent code, comments, or formatting.")
    lines.append("- Dont refactor things that arent broken.")
    lines.append("- Match existing style, even if youd do it differently.")
    lines.append("- If you notice unrelated dead code, mention it — dont delete it.")
    lines.append("")
    lines.append("When your changes create orphans, remove only what YOUR changes made unused.")
    lines.append("The test: Every changed line should trace directly to the users request.")
    lines.append("")
    lines.append("### 4. Goal-Driven Execution")
    lines.append("")
    lines.append("Define success criteria. Loop until verified.")
    lines.append("")
    lines.append("Transform tasks into verifiable goals:")
    lines.append('- "Add validation" → "Write tests for invalid inputs, then make them pass"')
    lines.append('- "Fix the bug" → "Write a test that reproduces it, then make it pass"')
    lines.append('- "Refactor X" → "Ensure tests pass before and after"')
    lines.append("")
    lines.append("For multi-step tasks, state a brief plan with verifiable checkpoints.")
    lines.append("Strong success criteria let you loop independently.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("These guidelines are working if: fewer unnecessary diffs, fewer rewrites")
    lines.append("from overcomplication, and clarifying questions come before implementation")
    lines.append("rather than after mistakes.")
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
