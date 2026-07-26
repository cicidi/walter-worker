# Issues Found — 2026-07-27 (Day 2)

> 🔍 甲方质检 (find-issues) — Long-Running System Audit

## Process Gaps (2 found)

| ID | Issue | Evidence | Priority |
|----|-------|----------|----------|
| P-3 | Auto-worker never auto-creates wrong-history entries | 52 rounds, 27 bugs fixed, 0 wrong-history entries auto-created. P-1 from Round 11 remains unfixed. When auto-worker fixes a bug, it should call `coworker memory wrong_history` inject with the lesson. | HIGH |
| P-4 | Training pipeline ran but data quality didn't improve | 3 sessions processed, 1 lesson extracted. 515 sessions still await summarization. Need to run on ALL sessions not just 3. | HIGH |

## Services Health (1 found)

| ID | Service | Status |
|----|---------|--------|
| SVC-1 | Dashboard API | ✅ 568 sessions, 12,110 tools |
| SVC-2 | Auto-worker daemon | ✅ Running |
| SVC-3 | Cron jobs | ✅ 2 jobs active |

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| HIGH | 2 | 1 (P-3: wrong-history auto-creation) |
| **Total (new)** | **2** | **1 auto-fixable** |
| **Grand Total** | **90** | |
