# Devil's Advocate Report — Memory Graph

**Date:** 2026-07-27
**Documents:** memory-graph-spec.md (§0-§11), memory-graph-test-plan.md
**Method:** 3-agent debate (CON / PRO / JUDGE), 1 round
**Status:** Complete — all Category B items fixed in spec

---

## Round Summary

| Role | Result |
|------|--------|
| CON | 12 findings — 4 HIGH, 5 MEDIUM, 3 LOW |
| PRO | All 12 accepted as factually correct |
| JUDGE | 5 Design Flaws (B), 4 Implementation Gaps (A), 3 Acknowledged Tradeoffs (C) |

## Fixed (Category B — 5 items)

| # | Issue | Fix Applied |
|---|-------|-------------|
| 5 | Concurrency: last-write-wins loses edges | Write-ahead queue: capture.py writes to `pending/<session_id>.json`, single-threaded merge worker serializes writes (§8.3) |
| 6 | No schema version field | Added `"schema_version": "1.0"` to graph.json root + migration function (§8.2) |
| 7 | Verification signals unenforceable | Replaced vague criteria with concrete `verify_finding()` API: test_pass, pr_merged, agent_confirmed (§3.3) |
| 8 | Baseline contradiction (§9.5 vs §10) | Clarified: data exists, v1 task is adding `graph_enabled` column + backfill, not new data collection (§9.5) |
| 9 | No session-node deduplication | Added `_dedup_and_merge()` with 0.7 similarity threshold, session_count tracking (§4.3) |

## Acknowledged (Category A — 4 items)

Expected for draft spec. Implementation follows spec approval.

| # | Issue |
|---|-------|
| 1 | Zero code (all §10 checkboxes) |
| 2 | `graph_queries` table DDL |
| 3 | Query API function stubs |
| 4 | LLM extraction validation |

## Deferred (Category C — 3 items)

Explicit v2 plan exists.

| # | Issue |
|---|-------|
| 10 | File rename orphaning |
| 11 | Graph-vs-vector conflict resolution |
| 12 | Confidence tier calibration |

## Top Risk

**Data loss from concurrent writes** (#5) — RESOLVED by write-ahead queue design.

## Outcome

All 5 Category B design flaws fixed in spec. Spec is ready for implementation.
12 test cases added for new items (W1-W3, D1-D3, V1-V4).
