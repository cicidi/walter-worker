---
feature: analytics-listener
type: impl-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Listener — Implementation Plan

This plan was written after the code shipped. Each task records a unit of work that exists at commit `634adf1`, what it depends on, what it blocks, and the test that proves it. Behavior is defined in the [design](../design/analytics-listener-design.md).

## Global Constraints

A hook must not stop or noticeably slow a session; its writes ignore failure. Nothing leaves the machine. The database schema is created and migrated on every connection, so readers never handle a missing database.

## Acceptance Criteria

The feature is not done while any blocking open question is open: QUES-A (secret redaction), QUES-I (hook tool results never reach the database), QUES-P (`import` stores messages twice), and QUES-K (pruning hook data that was never imported). Beyond that, it is done when the tasks below are done, their Verify lines pass, and every other open question is fixed or explicitly accepted by the owner.

## Execution order

IMPL-A, IMPL-C, and IMPL-E depend on nothing and can proceed in parallel; IMPL-A goes first among the hook work, because every hook writes through it. IMPL-D comes next, because it depends on IMPL-A and IMPL-C: it reads what the hooks wrote into the schema IMPL-C defines. IMPL-C does not use the hook files, so it does not wait for IMPL-A. IMPL-B comes last: it depends on IMPL-A, and its stop hook runs the importer from IMPL-D.

## IMPL-A — Session files

Create the session directory and `session.yaml`, keep the sequence counter under a lock, quarantine records without a session id, and append JSON lines that ignore write failures (DSGN-A, DSGN-B). Depends on: nothing. Blocks: IMPL-B and IMPL-D.

Verify: `tests/analytics/test_hooks.py` `test_session_yaml_is_valid_when_cwd_contains_a_quote`, `test_prompt_content_is_json_escaped`, and `test_parallel_tool_calls_get_valid_unique_seqs` pass.

## IMPL-B — Event hooks

The prompt, before-tool, after-tool, and stop hooks with their payload parsing; the stop hook also imports the transcript (DSGN-A). Depends on: IMPL-A and IMPL-D. Blocks: nothing.

Verify: `tests/analytics/test_hooks.py` `test_user_prompt_is_recorded` and `test_each_hook_starts_at_most_one_interpreter` pass, and `tests/hooks/on-stop.bats` passes. The interpreter test only counts the text `python3 -c` in each `on-*.sh` file, so it counts neither the interpreter `common.sh` starts nor `record.py` (DSGN-B).

## IMPL-C — Database and migrations

The schema, the path override, and the migrations including the `initiative` to `feature` rename (DSGN-C). Depends on: nothing. Blocks: IMPL-D.

Verify: `tests/python/test_db_migration.py` `test_rename_migrates_column_and_preserves_rows`, `test_rename_migration_is_idempotent`, and `test_fresh_database_has_token_columns` pass.

## IMPL-D — Importers

Hook-directory import, Claude Code transcript import, OpenCode metadata import, and the `once` and `daemon` loops (DSGN-C). Depends on: IMPL-A and IMPL-C. Blocks: IMPL-B and the [analytics dashboard](../../analytics-dashboard/impl-plan/analytics-dashboard-impl-plan.md), which reads the database.

Verify: `tests/python/test_import_data.py` `test_import_session_basic` and `test_import_session_pre_and_post_merge` pass, and `tests/python/test_auto_import.py` `test_import_claude_jsonl_basic`, `test_import_claude_jsonl_reimport_appends_without_double_counting`, `test_run_once_hooks_skips_dot_and_underscore_dirs`, and `test_run_daemon_one_iteration` pass.

## IMPL-E — Correction detector

Score prompts and write draft traces (DSGN-D). Depends on: nothing. Blocks: nothing.

Verify: no passing positive test exists yet; `tests/python/test_correction_detector.py::test_correction_detected` is marked expected-to-fail, and all four tests in that file run a hook path that does not exist, so the negative tests pass without running the detector (QUES-G).

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten as a record of shipped work with Verify lines; added Acceptance Criteria (ARD-A) |
| 0.3 | 2026-11-24 | Review fixes: one dependency for IMPL-C, IMPL-A's Blocks list corrected, IMPL-E added to the order, blocking questions QUES-I to QUES-K added to Acceptance Criteria, test limits stated (ARD-E) |
| 0.4 | 2026-11-24 | PRs #22 and #23: counter lock, stop-hook import (IMPL-B now depends on IMPL-D), new tests; QUES-J left the done bar; QUES-P added; commit `634adf1`; Depends on and Blocks labels |
