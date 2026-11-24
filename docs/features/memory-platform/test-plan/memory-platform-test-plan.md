---
feature: memory-platform
type: test-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Memory Platform — Test Plan

Each case names the requirement from the [PRD](../prd/memory-platform-prd.md) it covers and the test that implements it at commit `a0f4ce0`. The language model and mem0 are replaced in tests, so no test calls an outside provider.

## Test Cases

| ID | Covers | Case | Test |
|---|---|---|---|
| **TST-A** | PRD-A | Capture without a configured key stays quiet, empty input is an error, the skill threshold is configurable, and memories carry the real project | `tests/python/test_cli.py` `test_unconfigured_mem0_skips_quietly`, `test_empty_stdin_is_an_error_not_a_silent_pass`; `tests/python/test_capture.py` `TestSkillThresholdIsConfigurable`, `TestMemoriesAreTaggedWithTheRealProject` |
| **TST-B** | PRD-B | Nodes are folded, edges are weighted, writes are atomic, and a named session merges only its own dump | `tests/memory/test_graph_core.py` `TestNodeDedup`, `TestEdgeEnrichment`, `TestAtomicWrite`; `tests/python/test_cli.py` `test_a_named_session_processes_only_that_dump` |
| **TST-C** | PRD-C | Queries respect the budget and the minimum score, and vector search works without a graph | `tests/memory/test_query_quality.py` `test_budget_zero_returns_nothing`, `test_min_score_filters_quality`; `tests/python/test_cli.py` `TestQueryVectorDoesNotNeedAGraph` |
| **TST-D** | PRD-D | The due check works, decay runs, imported old sessions are pruned, and the hook path stays quiet | `tests/python/test_curator.py` `TestDueCheck`, `TestDecayActuallyRuns`, `test_an_imported_old_session_is_pruned`; `tests/python/test_cli.py` `test_curate_stays_quiet_on_the_hook_path` |
| **TST-E** | PRD-E | Blocks for different projects keep separate markers | `tests/python/test_inject.py` `test_different_project_markers` |
| **TST-F** | PRD-F | Staging trips after the limit, a damaged counter is handled, and training respects the limit | `tests/python/test_safety.py` `test_trips_after_limit`, `test_corrupt_state_file`; `tests/python/test_train.py` `test_training_respects_the_circuit_breaker` |
| **TST-G** | PRD-G | A summary is written, and a nonsense `--since` is rejected | `tests/python/test_knowledge.py` `test_summarize_session_writes_the_summary`, `test_get_all_sessions_since_rejects_nonsense` |
| **TST-H** | PRD-H | Keys are read from `~/.coworker/.env`, and a memory can be deleted | No test; not implemented (QUES-D) |
| **TST-I** | PRD-I | `init` refuses to overwrite a populated graph | `tests/python/test_cli.py` `test_refuses_to_overwrite_a_populated_graph` |
| **TST-J** | PRD-J | Wrong-history entries keep their continuation lines | `tests/python/test_wrong_history.py` `test_the_continuation_is_kept` |

Not covered today: a dump with invalid values (QUES-A), concurrent merges (QUES-B), a damaged `graph.json` (QUES-C), and `memory refresh` run from another folder (QUES-F). The open questions are in the [design](../design/memory-platform-design.md#open-questions).

## Test Execution Order

Run `tests/memory/test_graph_core.py` and `tests/python/test_mem0_client.py` first, because the stores underlie everything else. Then capture, curator, injection, safety, and knowledge tests, then the memory classes in `test_cli.py`.

## Expected Pass Threshold

Every case with a test must pass; the threshold is 100%. TST-H has no test, so PRD-H is not verified.

## Traceability

| Requirement | Test cases |
|---|---|
| PRD-A | TST-A |
| PRD-B | TST-B |
| PRD-C | TST-C |
| PRD-D | TST-D |
| PRD-E | TST-E |
| PRD-F | TST-F |
| PRD-G | TST-G |
| PRD-H | TST-H |
| PRD-I | TST-I |
| PRD-J | TST-J |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten with one case per requirement, mapped to tests, untested behavior listed (ARD-A) |
