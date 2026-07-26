# Issues Found — 2026-07-26 (Round 7)

> 🔍 甲方质检 (find-issues) — Code Quality + Operational Gaps

## Code Health (3 found)

| ID | File | Issue | Fix | Priority |
|----|------|-------|-----|----------|
| CH-1 | `src/coworker/cli.py` | **1,317 lines** — exceeds global CLAUDE.md rule "File ≤ 1000 lines". 37% growth from our changes. | Split into sub-modules: `cli_memory.py`, `cli_autoworker.py`, `cli_dashboard.py` | HIGH |
| CH-2 | `src/coworker/dashboard/queries.py` | **845 lines** — growing fast (was ~200). Mixing analytics + evolution + cost queries in one file. | Split into `queries_analytics.py`, `queries_evolution.py` | MEDIUM |
| CH-3 | `src/coworker/autoworker/engine.py` | 392 lines, two different engines (AutoWorkerAgent + run_autoworker_loop). Duplicate entry points cause confusion. | Consolidate to one clear entry point | LOW |

## Operational (2 found)

| ID | Issue | Evidence | Fix | Priority |
|----|-------|----------|-----|----------|
| OPS-1 | Auto-worker daemon died silently | `ps aux` showed no auto_worker_runner process at R21. Restarted. No alert was triggered. | Add daemon health check to cron — if daemon dead, restart it and log | HIGH |
| OPS-2 | Dashboard never tested with real traffic | 37 endpoints all return data, but no load test or concurrent-access test exists | Add `coworker dashboard --benchmark` with `wrk` or `hey` | LOW |

## PRD Audit (1 found)

| ID | Section | Issue | Priority |
|----|---------|-------|----------|
| PRD-1 | §4 State Engine | PRD describes "state transition diagram" and "checkpoint/resume" for state files. Our implementation writes state files but has no formal state machine or resume capability. | MEDIUM |

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| HIGH | 2 | 1 (OPS-1 daemon restart) |
| MEDIUM | 2 | 0 (refactoring) |
| LOW | 2 | 0 |
| **Total (new)** | **6** | **1 auto-fixable** |
| **Grand Total** | **57** | |
