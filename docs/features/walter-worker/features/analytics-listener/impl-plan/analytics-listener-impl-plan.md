---
feature: analytics-listener
type: impl-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Listener — Implementation Plan

This plan was written after the code shipped. Each task records a unit of work that exists at commit `a0f4ce0`, what it depends on, what it blocks, and the test that proves it. Behavior is defined in the [design](../design/analytics-listener-design.md).

## Global Constraints

A hook must not stop or noticeably slow a session; its writes ignore failure. Nothing leaves the machine. The database schema is created and migrated on every connection, so readers never handle a missing database.

## Acceptance Criteria

The feature is not done while the blocking open question QUES-A (secret redaction) is open. Beyond that, it is done when the tasks below are done, their Verify lines pass, and every other open question is fixed or explicitly accepted by the owner.

## Execution order

IMPL-A first, because every hook writes through it. IMPL-B and IMPL-C depend on IMPL-A and can proceed in parallel. IMPL-D depends on IMPL-A and IMPL-C, because it reads what the hooks wrote into the schema IMPL-C defines.

## IMPL-A — Session files

Create the session directory and `session.yaml`, keep the sequence counter, quarantine records without a session id, and append JSON lines that ignore write failures (DSGN-A, DSGN-B). Depends on nothing. Blocks IMPL-B, IMPL-C, and IMPL-D.

Verify: `tests/analytics/test_hooks.py` `test_session_yaml_is_valid_when_cwd_contains_a_quote` and `test_prompt_content_is_json_escaped` pass.

## IMPL-B — Event hooks

The prompt, before-tool, after-tool, and stop hooks with their payload parsing (DSGN-A). Depends on IMPL-A. Blocks nothing.

Verify: `tests/analytics/test_hooks.py` `test_user_prompt_is_recorded` and `test_each_hook_starts_at_most_one_interpreter` pass, and `tests/hooks/on-stop.bats` passes.

## IMPL-C — Database and migrations

The schema, the path override, and the migrations including the `initiative` to `feature` rename (DSGN-C). Depends on nothing. Blocks IMPL-D.

Verify: `tests/python/test_db_migration.py` `test_rename_migrates_column_and_preserves_rows`, `test_rename_migration_is_idempotent`, and `test_fresh_database_has_token_columns` pass.

## IMPL-D — Importers

Hook-directory import, Claude Code transcript import, OpenCode metadata import, and the `once` and `daemon` loops (DSGN-C). Depends on IMPL-A and IMPL-C. Blocks the [analytics dashboard](../../analytics-dashboard/impl-plan/analytics-dashboard-impl-plan.md), which reads the database.

Verify: `tests/python/test_import_data.py` `test_import_session_basic` and `test_import_session_pre_and_post_merge` pass, and `tests/python/test_auto_import.py` `test_import_claude_jsonl_basic`, `test_run_once_hooks_skips_dot_and_underscore_dirs`, and `test_run_daemon_one_iteration` pass.

## IMPL-E — Correction detector

Score prompts and write draft traces (DSGN-D). Depends on nothing. Blocks nothing.

Verify: no passing positive test exists yet; `tests/python/test_correction_detector.py::test_correction_detected` is marked expected-to-fail (QUES-G).

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten as a record of shipped work with Verify lines; added Acceptance Criteria (ARD-A) |
