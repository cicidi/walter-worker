---
name: auto-worker
description: Run an autonomous QA validation loop that checks 8 rules (mem0 health, API keys, skills directory, pending queue, memory store size, dead skills, usage-audit, requirement-audit) and auto-fixes issues where possible. Use when the user wants continuous autonomous validation or asks to "run auto-worker".
---

# Auto-Worker

Autonomous QA validation loop that continuously checks the health of the self-evolving agent platform and flags or auto-fixes issues.

## Quick Start

```
coworker run --loop --max-hours 2 --project ai-coworker
```

Or within a Claude Code session:

```
/auto-worker
```

## 8 Validation Rules

| # | Rule | What it checks | Auto-Fix? |
|---|------|---------------|-----------|
| 1 | `validate_against_raw_data` | Skill `usage.json` claimed calls vs `analytics.db` actual calls | No (flags mismatch) |
| 2 | `detect_dead_skills` | Skills with zero actual calls in analytics.db | No (reports dead) |
| 3 | `audit_requirement` | PRD item vs code grep + test results | No (reports gap) |
| 4 | `check_mem0_operational` | mem0 importable and configured | No |
| 5 | `check_api_keys` | DEEPSEEK_API_KEY set in environment | No |
| 6 | `check_skills_directory` | `~/.coworker/skills/` exists and has entries | No |
| 7 | `check_pending_queue` | Pending review queue size (<20 is healthy) | Yes (flags for review) |
| 8 | `check_memory_store_size` | Active mem0 entries (<500 is healthy) | No (flags for curation) |

## State File

Each run writes to `docs/self-evolving-agent/state/auto-worker-YYYY-MM-DD-state.md`:
- **Checked** table — each rule with verdict (DONE_RIGHT / DONE_WRONG / NOT_DONE)
- **Open Questions** table — issues that need human attention

The loop exits when no new findings are discovered in a round (convergence).

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `COWORKER_SKILL_THRESHOLD` | `10` | Min tool calls for skill creation trigger |

## CLI Reference

```
coworker run --loop                         # Start continuous auto-worker
coworker run --loop --max-hours 4           # Run for up to 4 hours
coworker run --loop --project skill-factory # Target a different project
```

## Related

- `coworker memory search` — Search cross-session memory
- `coworker memory refresh` — Refresh CLAUDE.local.md snapshot
- `coworker memory train` — Batch-train mem0 from past sessions
- `coworker analytics dashboard` — Web dashboard with Evolution page

## Anti-Patterns

- Don't run auto-worker while another instance is writing to the same state file
- Don't expect auto-fix for all rules — most are detection-only, requiring human review
- Don't run indefinitely without a max-hours limit (default 12h)

## Sources

- Spec: `docs/self-evolving-agent/spec/self-evolving-agent-spec.md` §7 (Evolution Metrics)
- Impl plan: `docs/self-evolving-agent/impl-plan/self-evolving-agent-impl-plan.md` Wave 6
- Code: `src/coworker/autoworker/` (state.py, rules.py, engine.py)
