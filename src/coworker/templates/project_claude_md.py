# src/coworker/templates/project_claude_md.py

PROJECT_CLAUDE_MD_SENTINEL = "<!-- PROTECTED:CRITICAL-RULES -->"

LOCAL_OVERRIDE = """## Local Override

CRITICAL: If `CLAUDE.local.md` exists, read it before doing anything else.
- Claude Code auto-loads this file; OpenCode must use Read tool explicitly.
"""

GUARDRAILS = """## Mandatory Guardrails

### Git
- Never push to main/master — all changes through PR
- Never force push; never delete remote branches without confirmation
- Branch: `{type}/{issue-id}-{short-description}`
- Commit: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`)

### Code
- Never hardcode secrets or tokens — use env vars; never commit `.env` files
- Never log passwords, tokens, or PII
- Never bypass auth checks — always validate permissions
- Use parameterized queries — never interpolate user input into SQL/shell/HTML
- Code must pass lint and format checks before commit
- No commented-out code; no `TODO` without a linked GitHub issue
- Don't modify PROTECTED blocks; don't fabricate information — ask when uncertain
"""

COMPACTION = """## Compaction & State Persistence

- Save task progress to `docs/state/` before compaction; compact early (50-70% context)
- After compaction: re-read `docs/state/` and `CLAUDE.local.md`
"""

CONTEXT_MGMT = """## Context Management

1. Clarify goal — if unclear, ask user
2. Check `docs/<initiative>/` for PRD/design docs and prior discussions
3. Recall state — read prior state files and `CLAUDE.local.md`
4. Verify all referenced documents are actually read before proceeding
"""

WORKFLOW_HEURISTICS = """## Workflow Selection

- Simple, clear, low-risk → just do it
- Bug fix with reproduction → debug → fix → verify
- Minor refactoring → edit, run tests, done
- Unclear requirements / large scope → brainstorm → spec → implement
- Complex or high-risk → TDD + loop engineering
- Large feature → brainstorming + TDD + loop

**Reality check**: These are heuristics, not iron laws. Use judgment for trivial work.
"""

AUTO_MEMORY = """## Auto Memory

- Upfront rules override auto-memory; never let auto-memory write back into CLAUDE.md

## Development Loop

- After every code change: run lint + tests before marking task complete
- Commit in logical chunks with conventional commit messages
"""


def generate_project_claude_md(project_name: str = "", **kwargs) -> str:
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
