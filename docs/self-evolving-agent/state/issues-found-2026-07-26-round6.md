# Issues Found — 2026-07-26 (Round 6)

> 🔍 甲方质检 (find-issues) — Data Quality Crisis Audit

## CRITICAL: Data Quality Gap (3 found)

After 18 auto-worker rounds and 35 commits, the underlying DATA is still poor:

| ID | Metric | Current | Target | Gap | Priority |
|----|--------|---------|--------|-----|----------|
| DQ-1 | Project Attribution | **28.3%** (161/568) | >80% | 407 sessions have NO project tag — blind to which project they belong to | **CRITICAL** |
| DQ-2 | Session Summaries | **9.3%** (53/568) | >50% | 515 sessions never summarized — knowledge pipeline almost unused | **CRITICAL** |
| DQ-3 | Initiative Tagging | **3.3%** (19/568) | >30% | 549 sessions have no initiative — can't trace work to goals | HIGH |

**Evidence:** `query_data_quality()` returns these numbers every 10 minutes. Auto-worker has been reporting them as "healthy" for 18 rounds without flagging the gap.

## Why Auto-Worker Missed This

The auto-worker health check reports numbers but doesn't have THRESHOLDS. It says "project coverage 28.3%" but doesn't know that's bad. This is a meta-issue:

| ID | Issue | Fix | Priority |
|----|-------|-----|----------|
| M-1 | No data quality thresholds in auto-worker | Add `--min-project-coverage 80` flag. Health check should turn RED when coverage < threshold | HIGH |
| M-2 | `coworker memory train` never scheduled | Training pipeline exists but is only run manually. Add to cron or auto-worker schedule | HIGH |
| M-3 | Session import doesn't auto-detect project | 407 sessions have `project=NULL`. The import pipeline (`analytics/import_data.py`) should infer project from `cwd` path | MEDIUM |

## Code Issues (1 found)

| ID | File | Issue | Priority |
|----|------|-------|----------|
| C-12 | `tests/python/test_cli.py` | 137 CLI tests exist but NONE test the auto-worker or find-issues commands | LOW |

## DeepSeek Analysis — Top 5

1. **[CRITICAL] Data Quality Is the Silent Killer** — The system is technically "healthy" (tests pass, APIs work) but the underlying data is so poor that analytics are unreliable. The Evolution Score shows 0% skill reuse not because skills aren't reused, but because project attribution is missing for 72% of sessions.

2. **[HIGH] Auto-Worker Is Blind to Data Quality** — Health checks report numbers without thresholds. "28.3% coverage" is objectively terrible but reported as neutral information.

3. **[HIGH] Training Pipeline Never Runs** — `coworker memory train` could backfill summaries and improve token coverage (currently 63.6%), but it's never scheduled.

4. **[MEDIUM] 11 Files Uncommitted for 20+ Hours** — These pre-existing changes have been sitting since before this session. Auto-worker never flagged them.

5. **[LOW] Project Auto-Detection Missing** — `coworker init` scans for language/framework but import_data.py doesn't infer project from cwd.

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| CRITICAL | 2 | 0 (need design + user action) |
| HIGH | 2 | 1 (M-1: thresholds in auto-worker) |
| MEDIUM | 1 | 1 (M-3: project auto-detect) |
| LOW | 1 | 0 |
| **Total (new)** | **6** | **2 auto-fixable** |
| **Grand Total** | **51** | |
