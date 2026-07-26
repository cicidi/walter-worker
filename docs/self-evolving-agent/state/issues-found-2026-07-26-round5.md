# Issues Found — 2026-07-26 (Round 5)

> 🔍 甲方质检 (find-issues) — CLI Completeness + Documentation Audit

## CLI Gaps (3 found)

| ID | Issue | Evidence | Fix | Priority |
|----|-------|----------|-----|----------|
| CLI-1 | `coworker find-issues` CLI not implemented | `skills/find-issues/SKILL.md` references `coworker find-issues --project --phases` but no CLI command exists. Skill is invoke-only (must be called via Skill tool). | Add `@main.group() def find_issues()` with `--project` and `--phases` options | HIGH |
| CLI-2 | `coworker memory train` missing spec flags | Spec §12.4 says `coworker memory train --sessions all --target 10-skills 10-experiences` but our CLI only has `--limit` and `--skip-existing` | Add `--target-skills` and `--target-experiences` options | MEDIUM |
| CLI-3 | `coworker memory validate --compare-baseline` has flag always true | `--compare-baseline` defaults to `True` with `is_flag=True` — means you can't DISABLE it | Change to `default=False` or remove the flag (it's always on) | LOW |

## Documentation Gaps (2 found)

| ID | Issue | Evidence | Priority |
|----|-------|----------|----------|
| DOC-1 | Auto-worker SKILL.md references `src/coworker/autoworker/engine.py` and `src/coworker/autoworker/rules.py` in Sources section — stale after rewrite | `grep "Engine.*Rules" skills/auto-worker/SKILL.md` shows old structure reference | LOW |
| DOC-2 | Find-issues SKILL.md describes `coworker find-issues` CLI that doesn't exist | References `coworker find-issues --project ai-coworker --phases all` but no command group exists | LOW |

## Code Issues (1 found)

| ID | File:Line | Issue | Priority |
|----|-----------|-------|----------|
| C-11 | src/coworker/memory/metrics.py:16 | `METRICS_PATH = "~/.coworker/memory/metrics.json"` but file never created unless `record_session_metrics()` is called. `compute_evolution_score()` and `get_metrics_report()` both read from non-existent file silently (return empty data). | LOW |

## DeepSeek Analysis — Top 5 This Round

1. **[HIGH] CLI-Skill Gap** — 3 CLI commands referenced in skills/docs but not implemented. Most critical: `coworker find-issues` which is the 甲方质检员's primary interface.

2. **[MEDIUM] Training CLI Incomplete** — Spec §12.4 describes rich training CLI that doesn't match implementation.

3. **[LOW] Documentation Staleness** — Skills reference old code structure. Should be auto-generated from actual code.

4. **[LOW] Metrics File Lazy Creation** — Non-existent file returns empty data silently. Should at least warn.

5. **[LOW] Validation Flag Bug** — `--compare-baseline` always true, can't disable for quick validation tests.

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| HIGH | 1 | 1 (CLI-1: find-issues CLI) |
| MEDIUM | 1 | 1 (CLI-2: train flags) |
| LOW | 4 | 4 (all) |
| **Total (new)** | **6** | **6 auto-fixable** |
| **Grand Total** | **45** | |
