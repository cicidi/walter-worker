---
feature: memory-platform
type: impl-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Memory Platform — Implementation Plan

This plan was written after the code shipped. Each task records a unit of work that exists at commit `a0f4ce0`, what it depends on, what it blocks, and the test that proves it. Behavior is defined in the [design](../design/memory-platform-design.md).

## Global Constraints

No memory step may stop a session: capture without a key returns quietly, and the curator on the hook path always exits 0. Graph writes are atomic. Skill promotion needs human approval.

## Acceptance Criteria

The feature is not done while the blocking open questions QUES-A and QUES-B are open. Beyond that, it is done when the tasks below are done, their Verify lines pass, and every other open question is fixed or explicitly accepted by the owner.

## Execution order

IMPL-A and IMPL-B first, because capture, merge, and queries build on the stores. IMPL-C depends on both. IMPL-D depends on IMPL-B. IMPL-E and IMPL-F depend on IMPL-A. IMPL-G depends on nothing in this feature but reads the [analytics listener](../../walter-worker/features/analytics-listener/impl-plan/analytics-listener-impl-plan.md)'s database.

## IMPL-A — Vector store and model client

mem0 over local Qdrant with local embeddings, and the DeepSeek-then-Gemini language-model client (ARD-B). Depends on nothing. Blocks IMPL-C, IMPL-E, and IMPL-F.

Verify: `tests/python/test_mem0_client.py` `test_missing_api_key_raises_config_error` and the `tests/python/test_llm.py` suite pass.

## IMPL-B — Graph core

The graph schema, atomic storage, node folding, edge weights, and decay (DSGN-B, DSGN-C). Depends on nothing. Blocks IMPL-C and IMPL-D.

Verify: `tests/memory/test_graph_core.py` passes, including `TestPassiveDecay`, `TestNodeDedup`, `TestAtomicWrite`, and `TestSchemaVersion`.

## IMPL-C — Capture and merge

The capture hook and the `close` merge (DSGN-A, DSGN-B). Depends on IMPL-A and IMPL-B. Blocks nothing.

Verify: `tests/python/test_capture.py` passes, and `tests/python/test_cli.py` `test_unconfigured_mem0_skips_quietly`, `test_empty_stdin_is_an_error_not_a_silent_pass`, and `test_a_named_session_processes_only_that_dump` pass.

## IMPL-D — Queries

`memory query` and `memory search` (DSGN-C). Depends on IMPL-B and, for the vector side, IMPL-A. Blocks nothing.

Verify: `tests/memory/test_query_quality.py` `test_budget_zero_returns_nothing` and `test_min_score_filters_quality` pass.

## IMPL-E — Curator

The weekly curator and its steps (DSGN-D). Depends on IMPL-A. Blocks nothing.

Verify: `tests/python/test_curator.py` passes, including `TestDueCheck` and `test_an_imported_old_session_is_pruned`, and `tests/python/test_cli.py` `test_curate_stays_quiet_on_the_hook_path` passes.

## IMPL-F — Snapshot, staging limit, and wrong-history

`memory refresh`, the circuit breaker, and the wrong-history commands (DSGN-E, DSGN-F, DSGN-I). Depends on IMPL-A. Blocks nothing.

Verify: `tests/python/test_inject.py` `test_different_project_markers`, `tests/python/test_safety.py` `test_trips_after_limit` and `test_corrupt_state_file`, and `tests/python/test_wrong_history.py` pass.

## IMPL-G — Knowledge commands

`knowledge summarize` and `knowledge analyze` (DSGN-G). Depends on the analytics database. Blocks nothing.

Verify: `tests/python/test_knowledge.py` `test_summarize_session_writes_the_summary` and `test_get_all_sessions_since_rejects_nonsense` pass.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten as a record of shipped work with Verify lines; added Acceptance Criteria (ARD-A) |
