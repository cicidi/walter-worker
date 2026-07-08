# src/coworker/templates/project_claude_md.py

# Sentinel string the init command uses to detect an existing coworker-generated
# CLAUDE.md. Must match what the template actually emits (single source of truth;
# if this heading ever changes, update this constant).
PROJECT_CLAUDE_MD_SENTINEL = "## Project Identity"

LOCAL_OVERRIDE = """## Local Override

CRITICAL: If `CLAUDE.local.md` exists in this project root, use Read tool to load it now before doing anything else.
- Claude Code: natively auto-loads this file
- OpenCode: must use Read tool explicitly

Contains personal working context — active initiative, task state, config paths, workflow preferences, available skills.
"""

GUARDRAILS = """## Mandatory Guardrails

ALL team members must follow these. No exceptions.

### Git Safety
- Never push to main/master — all changes through PR
- Never force push. Never delete remote branches without confirmation
- Never merge PRs without human approval
- Branch: `{type}/{issue-id}-{short-description}`
- Commit: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`)

### Code Safety
- Never hardcode secrets or tokens — use env vars
- Never commit `.env` files or credentials
- Never log passwords, tokens, or PII
- Never bypass auth checks — always validate permissions
- Always use parameterized queries — never interpolate user input into SQL/shell/HTML

### Code Quality
- Code must pass lint and format checks before commit
- No commented-out code in PRs
- No `TODO` without a linked GitHub issue
- Don't modify PROTECTED blocks (`<!-- PROTECTED -->` to `<!-- END PROTECTED -->`)
- Don't fabricate information — ask when uncertain
"""

AUTO_MEMORY = """## Auto Memory

- Read this CLAUDE.md first (upfront rules), then check auto-memory for past learnings
- Conflict: upfront rules override auto-memory. Never let auto-memory write back into CLAUDE.md
"""

COMPACTION = """## Compaction & State Persistence

1. **Save on compaction / session end**: Run `coworker state-update {descriptive-name} -s "one-line summary"` before stopping. Use a descriptive task name (e.g. `fix-state-paths`, `add-oauth-flow`). If no name is given, a timestamp is auto-generated to ensure uniqueness.
2. **Manual milestone save**: Run `coworker state-update {task-name} -s "what I finished"` after completing a milestone.
3. **After compaction**: CLAUDE.md is re-injected but prior conversation is gone. Re-read the most recent `docs/state/state-*.md` and `CLAUDE.local.md`. Re-run the Context Self-Assessment Checklist.
4. **Compact early**: Write state at 50-70% of context window — before model performance degrades.
"""

CONTEXT_MGMT = """## Context Management

MANDATORY: Before starting any non-trivial task, run this checklist:

1. **Goal clarity** — Is the goal clear? If not, ask user. Current task details are in `CLAUDE.local.md`.
2. **Find spec** — Does `docs/specs/` contain PRD or design docs for this task? Read them before coding.
3. **Check discussions** — Were there prior discussions? Check `docs/discussion/` and Team Links below.
4. **Recall state** — Was this task started before? Check state file path in `CLAUDE.local.md`, then read it.
5. **Verify reads** — Are ALL referenced documents actually read? Do not proceed until confirmed.

### Information Flow
| What | Where | Notes |
|------|-------|-------|
| Project identity, repo, relationships | This file | Slow-changing, shared by all |
| Design docs, specs, discussion logs | `docs/specs/`, `docs/discussion/` | Shared, committed |
| Team wikis, Slack, external links | Team Links section below | Shared references |
| Task goal, testing approach | `CLAUDE.local.md` | Changes per task, personal |
| Current workflow, skills in use | `CLAUDE.local.md` | Changes per session |
| Initiative context, reference docs | `CLAUDE.local.md` | Injected by coworker |
| Work-in-progress, temp artifacts | `CLAUDE.local.md` or `docs/state/` | Discardable after completion |
"""

WORKFLOW_HEURISTICS = """## Workflow Selection

For every new task, scan these characteristics and decide:

### Auto-execute (no prompt needed)
- Clear requirements, simple change, low risk → Just do it
- Bug fix with clear reproduction steps → bug-hunt, fix, verify
- Minor refactoring, tests pass → Edit, run tests, done

### Suggest workflow, then confirm
- Unclear requirements, large scope → brainstorming → spec → implement
- Clear requirements, complex/high-risk code → TDD + loop engineering
- Large feature, lots of discussion needed → brainstorming + TDD + loop
- Documentation work → doc conventions skill

**Decision logic**: If requirements AND scope AND risk are all clear/small/low → auto. Otherwise → suggest + confirm.

**Reality check**: These are heuristics, not iron laws. For reversible ops (reading files, `ls`, `grep`, `git status`) just proceed. Don't overthink trivial work.
"""

SKILL_REFS = """## Available Skills

Invoke a skill when its description matches the task. Do not invoke blindly — only when relevant.
- `brainstorming`: creative/design work, feature exploration, spec writing
- `TDD` / `auto-tdd`: test-first development, red-green-refactor
- `bug-hunt`: systematic debugging, hypothesis → test → confirm
- `commit`: conventional commits, git conventions
- `self-heal`: log corrections, self-analyze: find patterns
- `doc-*`: documentation create, merge, protect
"""


def generate_project_claude_md(
    project_name: str = "",
    language: str = "",
    framework: str = "",
    package_manager: str = "",
    build_cmd: str = "",
    lint_cmd: str = "",
    test_cmd: str = "",
    ides: str = "claude, opencode",
    repo: str = "",
    branch: str = "main",
    relationships: str = "",
    doc_map: str = "",
    team_links: str = "",
) -> str:
    """Generate canonical Project CLAUDE.md."""
    title = f"# {project_name or 'Project'} — CLAUDE.md" if project_name else "# Project CLAUDE.md"

    identity_lines = []
    if repo:
        identity_lines.append(f"Repo: {repo}")
    identity = "\n".join(identity_lines) if identity_lines else ""

    rel_section = (
        "## Project Relationships\n\n"
        + (relationships or "_(none configured)_")
    )

    knowledge = (
        "## Knowledge Repo\n\n"
        + (doc_map or "_(run `coworker init` to scan docs/ structure)_")
    )

    team_section = (
        "## Team Links\n\n"
        + (team_links or "_(none configured — add shared wikis, Slack channels, design docs)_")
    )

    parts = [
        title,
        "",
        "<!-- PROTECTED:CRITICAL-RULES -->",
        LOCAL_OVERRIDE.strip(),
        GUARDRAILS.strip(),
        COMPACTION.strip(),
        CONTEXT_MGMT.strip(),
        WORKFLOW_HEURISTICS.strip(),
        AUTO_MEMORY.strip(),
        "<!-- END PROTECTED:CRITICAL-RULES -->",
        "",
        "## Project Identity",
        "",
        identity.strip() if identity else "_Repo URL auto-discovered by AI._",
        "",
        rel_section.strip(),
        "",
        knowledge.strip(),
        "",
        team_section.strip(),
    ]
    return "\n\n".join(parts)
