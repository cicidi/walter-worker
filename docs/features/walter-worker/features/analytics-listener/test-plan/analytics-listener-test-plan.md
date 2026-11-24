---
feature: analytics-listener
type: test-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Listener — Test Plan

Each case names the requirement from the [PRD](../prd/analytics-listener-prd.md) it covers and the test that implements it at commit `a0f4ce0`. Hook tests run the scripts with sample payloads against a temporary home directory; importer tests use temporary databases.

## Test Cases

| ID | Covers | Case | Test |
|---|---|---|---|
| **TST-A** | PRD-A | A submitted prompt is recorded, and content and working folders with quotes stay valid JSON and YAML | `tests/analytics/test_hooks.py` `test_user_prompt_is_recorded`, `test_prompt_content_is_json_escaped`, `test_session_yaml_is_valid_when_cwd_contains_a_quote` |
| **TST-B** | PRD-B | Each hook starts at most one interpreter, and the stop hook stays quiet with no message files | `tests/analytics/test_hooks.py` `test_each_hook_starts_at_most_one_interpreter`; `tests/hooks/on-stop.bats` "stays quiet when the session has no message files" |
| **TST-C** | PRD-C | Records without a session id are kept apart and not imported as a session | `tests/python/test_auto_import.py` `test_run_once_hooks_skips_dot_and_underscore_dirs` |
| **TST-D** | PRD-D | Hook sessions, Claude Code transcripts, and OpenCode metadata are imported, before and after tool records are paired, and a re-run gives the same database | `tests/python/test_import_data.py` `test_import_session_basic`, `test_import_session_pre_and_post_merge`; `tests/python/test_auto_import.py` `test_import_claude_jsonl_basic`, `test_import_opencode_skips_existing`; `tests/analytics/test_e2e_setup.py` `test_db_idempotent` |
| **TST-E** | PRD-E | A fresh database has the full schema, and migrations are repeatable | `tests/python/test_db_migration.py` `test_fresh_database_has_token_columns`, `test_rename_migration_is_idempotent` |
| **TST-F** | PRD-F | A correction writes a draft trace | `tests/python/test_correction_detector.py::test_correction_detected`, marked expected-to-fail (QUES-G) |
| **TST-G** | PRD-G | Secrets are not stored in plain text | No test; not implemented (QUES-A) |
| **TST-H** | PRD-H | Imported directories older than 30 days are pruned and the database is kept | No test at this feature's level; the pruning lives in the memory curator |

Not covered today: the redaction PRD-G asks for, the correction detector firing, the re-run repeatability of skill call counts (QUES-E), and behavior when a write fails in `on-stop.sh` (QUES-B). The open questions are in the [design](../design/analytics-listener-design.md#open-questions).

## Test Execution Order

Run `test_db_migration.py` first, then the hook tests, then the importer tests, then `test_e2e_setup.py`, which runs the whole pipeline.

## Expected Pass Threshold

Every case with a passing test must pass; the threshold is 100%. TST-F, TST-G, and TST-H have no passing test, so PRD-F, PRD-G, and PRD-H are not verified by automation.

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

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten with one case per requirement, mapped to tests, untested behavior listed (ARD-A) |
