---
name: auto-worker
description: Use when running autonomous QA — spawn a Claude agent that scans the codebase with real tools (Grep, Bash, Read, Glob), finds bugs, checks spec compliance, audits dashboard, and fixes issues. NOT a deterministic script — this is an AI agent doing real investigation.
---

# Auto-Worker

> **This is a Claude agent skill, NOT a Python script.**

When invoked, the agent:
1. Uses real tools (Grep, Bash, Read, Glob) to scan the codebase
2. Investigates issues — reads files, runs commands, checks outputs
3. Makes decisions based on what it finds
4. Fixes bugs or reports them with evidence
5. Writes findings to state file

## Two Modes

### Mode 1: Agent Investigation (primary)
Trigger: `/auto-worker` or cron at :03 and :33 each hour
Duration: ~2-5 minutes per run
Actions:
- `git diff` recent commits → identify risky changes
- `grep -rn "TODO\|FIXME" src/` → find unfinished work
- Compare `docs/.../spec/` sections against `src/` → find spec gaps
- Query dashboard APIs → verify data is returning
- Check uncommitted files → flag forgotten work
- Read modified files → identify potential bugs
- Run targeted tests on changed code

### Mode 2: Health Check (complementary)
Trigger: cron every 10 minutes (:07, :17, :27, etc.)
Duration: ~60 seconds
Actions: Run unit tests, check imports, verify dashboard APIs, check circuit breaker, verify frontend integrity

## Agent Investigation Checklist

When invoked as an agent, work through these steps:

1. **Recent changes** — `git diff --stat HEAD~3..HEAD`, read any suspicious diffs
2. **TODOs** — `grep -rn "TODO\|FIXME\|HACK" src/coworker/ --include="*.py"`
3. **Spec gaps** — compare spec sections against implemented modules, flag missing
4. **Dashboard data** — query all API endpoints, verify non-empty responses
5. **Uncommitted work** — `git status --short`, flag anything that looks forgotten
6. **Dashboard frontend** — verify JS has init call, CSS has expand classes, line counts healthy
7. **Wrong-history check** — read entries, verify prevention rules are being followed
8. **Circuit breaker** — check safety gates status

## Output

Write findings to `docs/self-evolving-agent/state/auto-worker-YYYY-MM-DD-state.md`:
```markdown
## Agent Scan — <timestamp>
- Finding 1
- Finding 2
```

## Anti-Patterns

- **DO NOT** just run a Python script and call it done
- **DO NOT** skip the agent investigation step — use tools to explore
- **DO NOT** claim "all good" without actually reading code
- **DO** read real files, run real commands, find real issues
- **DO** fix critical bugs immediately when found

## CLI Reference

```
coworker run --loop --max-hours 12   # Continuous agent loop (Claude SDK)
coworker memory refresh              # Refresh CLAUDE.local.md snapshots
coworker memory train                # Batch-train mem0 from past sessions
```

## Related Skills

- `/wrong-history` — Record mistakes so they never repeat
- `/bug-hunt` — Root cause investigation
- `/contrarian-review` — Adversarial spec/code review

## Sources

- Spec: `docs/self-evolving-agent/spec/self-evolving-agent-spec.md` §12
- Engine: `src/coworker/autoworker/engine.py` (AutoWorkerAgent — Claude SDK spawner)
- Rules: `src/coworker/autoworker/rules.py` (8 rules, used by agent for guidance)
