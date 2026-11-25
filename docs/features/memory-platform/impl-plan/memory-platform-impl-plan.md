---
feature: memory-platform
type: impl-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Memory Platform — Implementation Plan

This plan was written after the code shipped. Each task records a unit of work that exists at commit `634adf1`, what it depends on, what it blocks, and the test that proves it. Behavior is defined in the [design](../design/memory-platform-design.md).

## Global Constraints

No memory step may stop a session: capture without a key returns quietly, and the curator on the hook path always exits 0. Capture and then merge run once per session, detached from a SessionEnd hook (design DSGN-A, ARD-H). Graph writes are atomic. Skill promotion needs human approval.

## Acceptance Criteria

The feature is not done while the blocking open questions are open. They are QUES-A (a bad dump blocks later merges), QUES-B (concurrent merges lose updates), and QUES-J (folded nodes leave broken edges). Beyond that, it is done when the tasks below are done, their Verify lines pass, and every other open question is fixed or explicitly accepted by the owner.

## Execution order

IMPL-A and IMPL-B come first, because capture, merge, and queries build on the stores. IMPL-F depends on IMPL-A and comes next, because capture stages skills through its circuit breaker. IMPL-C depends on IMPL-A, IMPL-B, and IMPL-F. IMPL-D depends on IMPL-A and IMPL-B. IMPL-E depends on IMPL-A. IMPL-H depends on IMPL-B. IMPL-G depends on IMPL-A for its model client and reads the [analytics listener](../../walter-worker/features/analytics-listener/impl-plan/analytics-listener-impl-plan.md)'s database.

## IMPL-A — Vector store and model client

mem0 over local Qdrant with local embeddings, and the DeepSeek-then-Gemini language-model client (ARD-B). Depends on: nothing. Blocks: IMPL-C, IMPL-D, IMPL-E, IMPL-F, and IMPL-G.

Verify: these tests, which need no key, pass: `tests/python/test_mem0_client.py` `test_missing_api_key_raises_config_error` (it needs mem0 installed), and `tests/python/test_llm.py` `TestLLMClientInit`, `TestLLMClientFallback`, and `TestLLMClientBuildProviderList`. The other tests in both files call DeepSeek and are skipped without `DEEPSEEK_API_KEY`.

## IMPL-B — Graph core

The graph schema, atomic storage, node folding, edge weights, and decay (DSGN-B, DSGN-C). Depends on: nothing. Blocks: IMPL-C, IMPL-D, and IMPL-H.

Verify: `tests/memory/test_graph_core.py` passes, including `TestPassiveDecay`, `TestNodeDedup`, `TestAtomicWrite`, and `TestSchemaVersion`.

## IMPL-C — Capture and merge

The capture hook and the `close` merge (DSGN-A, DSGN-B). Depends on: IMPL-A, IMPL-B, and IMPL-F. Blocks: nothing.

Verify: `tests/python/test_capture.py` `TestSkillThresholdIsConfigurable`, `TestMemoriesAreTaggedWithTheRealProject`, and `TestSessionEndHasRoomForItsOwnResponse` pass; `TestProcessTurnReal` calls DeepSeek and is skipped without a key. `tests/python/test_cli.py` `test_unconfigured_mem0_skips_quietly`, `test_empty_stdin_is_an_error_not_a_silent_pass`, and `test_a_named_session_processes_only_that_dump` pass. `tests/hooks/on-session-end.bats` "runs capture with the payload, then close" and "returns before the summary finishes" pass.

## IMPL-D — Queries

`memory query` and `memory search` (DSGN-C). Depends on: IMPL-B and, for the vector side, IMPL-A. Blocks: nothing.

Verify: `tests/memory/test_query_quality.py` `test_budget_zero_returns_nothing` and `TestMinScoreFiltering` pass, with mem0 replaced. `test_min_score_filters_quality` is not part of this line: it is in `tests/memory/test_memory_integration.py`, is marked `integration`, uses the real mem0 store, and is skipped when mem0 is not configured.

## IMPL-E — Curator

The weekly curator and its steps (DSGN-D). Depends on: IMPL-A. Blocks: nothing.

Verify: `tests/python/test_curator.py` passes, including `TestDueCheck` and `test_an_imported_old_session_is_pruned`, and `tests/python/test_cli.py` `test_curate_stays_quiet_on_the_hook_path` passes.

## IMPL-F — Snapshot, staging limit, and wrong-history

`memory refresh`, the circuit breaker, and the wrong-history commands (DSGN-E, DSGN-F, DSGN-I). Depends on: IMPL-A. Blocks: IMPL-C, because capture stages skills through the circuit breaker.

Verify: `tests/python/test_inject.py` `test_different_project_markers`, `tests/python/test_safety.py` `test_trips_after_limit` and `test_corrupt_state_file`, and `tests/python/test_wrong_history.py` pass.

## IMPL-G — Knowledge commands

`knowledge summarize` and `knowledge analyze` (DSGN-G). Depends on: IMPL-A for the model client and on the analytics database. Blocks: nothing.

Verify: `tests/python/test_knowledge.py` `test_summarize_session_writes_the_summary` and `test_get_all_sessions_since_rejects_nonsense` pass.

## IMPL-H — Graph from Graphify

`memory init` and `memory sync`, which build or extend the graph from Graphify's output (DSGN-I, PRD-I). Depends on: IMPL-B. Blocks: nothing.

Verify: TST-I passes. That is `tests/python/test_cli.py` `test_refuses_to_overwrite_a_populated_graph`, and `tests/memory/test_graph_core.py` `TestGraphifySync` and `TestGraphifyEdgeCases`.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten as a record of shipped work with Verify lines; added Acceptance Criteria (ARD-A) |
| 0.3 | 2026-11-24 | Review fixes: dependency edges corrected, IMPL-H added for init and sync, Verify lines name only tests that run without a key, QUES-I and QUES-J added to the done bar (ARD-D, ARD-F) |
| 0.4 | 2026-11-24 | PR #22 merged: capture runs from SessionEnd (ARD-H); QUES-I left the done bar; IMPL-C cites the hook tests; Depends on and Blocks labels; commit `634adf1` |
