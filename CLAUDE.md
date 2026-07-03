# ai-coworker — CLAUDE.md



<!-- PROTECTED:CRITICAL-RULES -->

## Local Override

CRITICAL: If `CLAUDE.local.md` exists in this project root, use Read tool to load it now before doing anything else.
- Claude Code: natively auto-loads this file
- OpenCode: must use Read tool explicitly

Contains personal working context — active initiative, task state, config paths, workflow preferences, available skills.

## Mandatory Guardrails

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

## Compaction & State Persistence

1. **Save on compaction / session end**: A hook runs `coworker state-update` on Stop. State file path is in `CLAUDE.local.md`.
2. **Manual milestone save**: Run `coworker state-update -s "what I finished"` after completing a milestone.
3. **After compaction**: CLAUDE.md is re-injected but prior conversation is gone. Re-read `docs/state/state-{task}.md` and CLAUDE.local.md. Re-run the Context Self-Assessment Checklist.
4. **Compact early**: Write state at 50-70% of context window — before model performance degrades.

## Context Management

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

## Workflow Selection

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

## Auto Memory

- Read this CLAUDE.md first (upfront rules), then check auto-memory for past learnings
- Conflict: upfront rules override auto-memory. Never let auto-memory write back into CLAUDE.md

<!-- END PROTECTED:CRITICAL-RULES -->



## Project Identity



Repo: git@github.com:cicidi/ai-coworker.git



## Project Relationships

_(none configured)_



## Knowledge Repo

- Specs: `docs/specs/`
- Discussions: `docs/discussion/`



## Team Links

_(none configured — add shared wikis, Slack channels, design docs)_
