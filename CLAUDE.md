# ai-coworker — CLAUDE.md



<!-- PROTECTED:CRITICAL-RULES -->

## Local Override

CRITICAL: If `CLAUDE.local.md` exists, read it before doing anything else.
- Claude Code auto-loads this file; OpenCode must use Read tool explicitly.

## Golden Rule: Think → Ask → Act

**CRITICAL: Never start working immediately. Always follow this sequence:**

1. **Think** — Analyze the problem. Consider alternatives. Identify what you don't know.
2. **Ask** — Ask at least 1-2 clarifying questions before writing any code or making changes.
3. **Act** — Only proceed when the user confirms or provides the missing information.

This applies to every single prompt, even seemingly trivial ones. The user prefers a brief clarification over incorrect or wasted work.

## Mandatory Guardrails

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

## Compaction & State Persistence

- Save task progress to `docs/state/` before compaction; compact early (50-70% context)
- After compaction: re-read `docs/state/` and `CLAUDE.local.md`

## Context Management

1. Clarify goal — if unclear, ask user
2. Check `docs/<initiative>/` for PRD/design docs and prior discussions
3. Recall state — read prior state files and `CLAUDE.local.md`
4. Verify all referenced documents are actually read before proceeding

## Workflow Selection

- Simple, clear, low-risk → just do it
- Bug fix with reproduction → debug → fix → verify
- Minor refactoring → edit, run tests, done
- Unclear requirements / large scope → brainstorm → spec → implement
- Complex or high-risk → TDD + loop engineering
- Large feature → brainstorming + TDD + loop

**Reality check**: These are heuristics, not iron laws. Use judgment for trivial work.

## Auto Memory

- Upfront rules override auto-memory; never let auto-memory write back into CLAUDE.md

## Documentation

- **MUST use `write-doc` skill** before writing or modifying any file in `docs/`
- Every doc modification appends a Change Log entry at end of file
- Change Log format: `| YYYY-MM-DD | Brief description |`
- This rule applies to: creating, moving, editing, renaming any doc file

## Development Loop

- After every code change: run lint + tests before marking task complete
- Commit in logical chunks with conventional commit messages

<!-- END PROTECTED:CRITICAL-RULES -->