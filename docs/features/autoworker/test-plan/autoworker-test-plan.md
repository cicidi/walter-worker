---
feature: autoworker
type: test-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Auto-worker — Test Plan

Each case names the requirement from the [PRD](../prd/autoworker-prd.md) it covers and the pytest test that implements it at commit `a0f4ce0`. Agent starts are tested with the subprocess replaced, so no real Claude Code session runs.

## Test Cases

| ID | Covers | Case | Pytest test |
|---|---|---|---|
| **TST-A** | PRD-A | `run` without `--loop` does nothing | No test yet |
| **TST-B** | PRD-B | The loop stops on its time budget and round cap | No test yet |
| **TST-C** | PRD-C | Each round starts the agent headless and appends its report | `tests/python/test_autoworker_engine.py` `test_uses_the_headless_print_invocation`; the appending has no test |
| **TST-D** | PRD-D | A missing `claude` command is a failed round, and its reason names the command | `tests/python/test_autoworker_engine.py` `test_missing_cli_does_not_report_success`, `test_the_reason_names_the_missing_cli` |
| **TST-E** | PRD-E | An unknown phase is an error, failing tests exit non-zero, a clean run exits zero, and a different project reads its own documents | `tests/python/test_cli.py` `test_unknown_phases_are_an_error`, `test_failing_tests_exit_non_zero`, `test_a_clean_run_exits_zero`, `test_a_different_project_reads_its_own_docs` |
| **TST-F** | PRD-F | Critical wrong-history entries reach the agent before the first round | No test yet |

Not covered today: the loop and the `run` command as a whole, the exit status of a fully failed run (QUES-A), and the `find-issues` timeout (QUES-B). `tests/python/test_autoworker_rules.py` and `test_autoworker_state.py` test code no command calls (QUES-F). The open questions are in the [design](../design/autoworker-design.md#open-questions).

## Test Execution Order

Run `test_autoworker_engine.py` first, then the `find-issues` classes in `test_cli.py`. The order does not matter for correctness; each test is independent.

## Expected Pass Threshold

Every case with a test must pass; the threshold is 100%. TST-A, TST-B, and TST-F have no test, so PRD-A, PRD-B, and PRD-F are not verified by automation.

## Traceability

| Requirement | Test cases |
|---|---|
| PRD-A | TST-A |
| PRD-B | TST-B |
| PRD-C | TST-C |
| PRD-D | TST-D |
| PRD-E | TST-E |
| PRD-F | TST-F |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten with one case per requirement, mapped to pytest tests, untested behavior listed (ARD-A) |
