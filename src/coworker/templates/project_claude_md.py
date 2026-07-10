# src/coworker/templates/project_claude_md.py

PROJECT_CLAUDE_MD_SENTINEL = "<!-- PROTECTED:CRITICAL-RULES -->"

LOCAL_OVERRIDE = """## Local Override

CRITICAL: If `CLAUDE.local.md` exists in this project root, use Read tool to load it now before doing anything else.
- Claude Code: natively auto-loads this file
- OpenCode: must use Read tool explicitly

Contains personal working context — active initiative, task state, config paths, project info, workflow preferences.
"""

GUARDRAILS = """## Mandatory Guardrails

ALL team members must follow these. No exceptions.

### Git Safety
- Never push to main/master — all changes through PR
- Never force push; never delete remote branches without confirmation
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
- No commented-out code; no `TODO` without a linked GitHub issue
- Don't modify PROTECTED blocks
- Don't fabricate information — ask when uncertain
"""

COMPACTION = """## Compaction & State Persistence

- Save on compaction / session end: `coworker state-update {name} -s "summary"`
- After compaction: re-read `docs/state/state-*.md` and `CLAUDE.local.md`
- Compact early: write state at 50-70% context window before performance degrades
"""

CONTEXT_MGMT = """## Context Management

Before starting any non-trivial task:
1. Clarify goal — if unclear, ask user
2. Check `docs/specs/` for relevant PRD or design docs
3. Check `docs/discussion/` for prior discussions
4. Recall state — read prior state files and `CLAUDE.local.md`
5. Verify all referenced documents are actually read before proceeding
"""

WORKFLOW_HEURISTICS = """## Workflow Selection

For every new task, scan these characteristics and decide:

### Auto-execute
- Clear requirements, simple change, low risk → Just do it
- Bug fix with clear reproduction → debug → fix → verify
- Minor refactoring, tests pass → Edit, run tests, done

### Confirm first
- Unclear requirements, large scope → brainstorm → spec → implement
- Complex/high-risk code → TDD + loop engineering
- Large feature → brainstorming + TDD + loop

**Decision logic**: If requirements AND scope AND risk are all clear/small/low → auto.
**Reality check**: These are heuristics, not iron laws. Use judgment for trivial work.
"""

AUTO_MEMORY = """## Auto Memory

- Read CLAUDE.md upfront rules before auto-memory
- Upfront rules override auto-memory; never let auto-memory write back into CLAUDE.md
"""


def generate_project_claude_md(project_name: str = "", **kwargs) -> str:
    """Generate canonical Project CLAUDE.md — pure meta-controller."""
    title = f"# {project_name or 'Project'} — CLAUDE.md" if project_name else "# Project CLAUDE.md"

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
    ]
    return "\n\n".join(parts)
