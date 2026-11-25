---
feature: analytics-listener
type: test-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Listener — Test Plan

Each case names the requirement from the [PRD](../prd/analytics-listener-prd.md) it covers and the test that implements it at commit `634adf1`. Hook tests run the scripts with sample payloads against a temporary home directory; importer tests use temporary databases.

## Test Cases

| ID | Covers | Case | Test |
|---|---|---|---|
| **TST-A** | PRD-A | A submitted prompt is recorded, and content and working folders with quotes stay valid JSON and YAML | `tests/analytics/test_hooks.py` `test_user_prompt_is_recorded`, `test_prompt_content_is_json_escaped`, `test_session_yaml_is_valid_when_cwd_contains_a_quote` |
| **TST-B** | PRD-B | Each `on-*.sh` file contains the text `python3 -c` at most once, and the stop hook stays quiet with no message files. The text count ignores the interpreters started by `common.sh` and `record.py`, and no test checks that a hook exits successfully when it cannot write | `tests/analytics/test_hooks.py` `test_each_hook_starts_at_most_one_interpreter`; `tests/hooks/on-stop.bats` "stays quiet when the session has no message files" |
| **TST-C** | PRD-C | `once` does not import directories whose names start with `_`. No test covers the hook-side quarantine or checks that `import` skips `_unattributed`, which it does not (QUES-L) | `tests/python/test_auto_import.py` `test_run_once_hooks_skips_dot_and_underscore_dirs` |
| **TST-D** | PRD-D | Hook sessions, Claude Code transcripts, and OpenCode metadata are imported, before and after tool records are paired, and creating the schema twice works; a transcript re-import adds no duplicates. No test re-runs a hook-directory import | `tests/python/test_import_data.py` `test_import_session_basic`, `test_import_session_pre_and_post_merge`; `tests/python/test_auto_import.py` `test_import_claude_jsonl_basic`, `test_import_opencode_skips_existing`, `test_import_claude_jsonl_reimport_appends_without_double_counting`, `test_cli_import_session_reads_hook_payload`; `tests/analytics/test_e2e_setup.py` `test_db_idempotent` |
| **TST-E** | PRD-E | A fresh database has the full schema, and migrations are repeatable | `tests/python/test_db_migration.py` `test_fresh_database_has_token_columns`, `test_rename_migration_is_idempotent` |
| **TST-F** | PRD-F | A correction writes a draft trace | `tests/python/test_correction_detector.py::test_correction_detected`, marked expected-to-fail; the test file also runs a hook path that does not exist (QUES-G) |
| **TST-G** | PRD-G | Secrets are not stored in plain text | No test; not implemented (QUES-A) |
| **TST-H** | PRD-H | A directory whose session id is in the database and that is older than 30 days is pruned; a recent one and one the database never saw are kept. No test checks that the directory itself was imported (QUES-K) | `tests/python/test_curator.py` `test_an_imported_old_session_is_pruned`, `test_an_imported_recent_session_is_kept`, `test_a_session_the_database_never_saw_is_kept` |
| **TST-I** | PRD-D | A transcript whose typed prompt is a plain string stores that prompt | `tests/python/test_auto_import.py` `test_import_claude_jsonl_stores_typed_prompt_string`, `test_import_claude_jsonl_typed_prompt_without_prompt_source` |
| **TST-J** | PRD-A | A newline in a payload field and parallel tool calls give valid lines with unique numbers; no test sends a non-JSON payload or a null duration | `tests/analytics/test_hooks.py` `test_tool_id_with_newline_keeps_fields_in_place`, `test_parallel_tool_calls_get_valid_unique_seqs` |

The following behavior is not covered by any test today:

- The redaction that PRD-G asks for (QUES-A).
- The correction detector firing, because its tests run a file that does not exist (QUES-G).
- Re-running a hook-directory import (QUES-E).
- Hook records from a payload that is not JSON, or with a null duration (QUES-J).
- The hook-side quarantine, and `import` of `_unattributed` (QUES-L).
- A hook whose write fails (QUES-B).

The open questions are in the [design](../design/analytics-listener-design.md#open-questions).

## Test Execution Order

Run `test_db_migration.py` first, then the hook tests, then the importer tests, then `test_curator.py`, then `test_e2e_setup.py`, which runs the whole pipeline.

## Expected Pass Threshold

Every case with a passing test must pass; the threshold is 100%. TST-F and TST-G have no passing test, so PRD-F and PRD-G are not verified by automation. TST-J covers two of its cases, so PRD-A is verified only in part.

## Traceability

| Requirement | Test cases |
|---|---|
| PRD-A | TST-A, TST-J |
| PRD-B | TST-B |
| PRD-C | TST-C |
| PRD-D | TST-D, TST-I |
| PRD-E | TST-E |
| PRD-F | TST-F |
| PRD-G | TST-G |
| PRD-H | TST-H |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten with one case per requirement, mapped to tests, untested behavior listed (ARD-A) |
| 0.3 | 2026-11-24 | Review fixes: TST-B, TST-C, and TST-D state what their tests check; TST-H cites the curator tests; TST-I and TST-J added for QUES-I and QUES-J (ARD-E) |
| 0.4 | 2026-11-24 | Tests from walter-worker PRs #22 and #23 cited in TST-D, TST-I, and TST-J; commit `634adf1` |
