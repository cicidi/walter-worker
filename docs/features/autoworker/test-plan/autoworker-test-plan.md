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
| **TST-C** | PRD-C (partial) | The agent is started headless, in the given folder, with the time limit | `tests/python/test_autoworker_engine.py` `test_uses_the_headless_print_invocation` |
| **TST-D** | PRD-D (partial) | A missing `claude` command makes the agent start report failure, and its reason names the command | `tests/python/test_autoworker_engine.py` `test_missing_cli_does_not_report_success`, `test_the_reason_names_the_missing_cli` |
| **TST-E** | PRD-E | An unknown phase is an error, failing tests exit non-zero, a clean run exits zero, a different project reads its own documents, and an unknown project is reported as having no PRD files instead of another project being read | `tests/python/test_cli.py` `test_unknown_phases_are_an_error`, `test_failing_tests_exit_non_zero`, `test_a_clean_run_exits_zero`, `test_a_different_project_reads_its_own_docs`, `test_an_unknown_project_says_so_rather_than_reading_another` |
| **TST-F** | PRD-F | Critical wrong-history entries reach the agent before the first round | No test yet |

TST-C and TST-D are partial. TST-C checks only the command line, the working folder, and the time limit. It does not test that the specifications and the prior state reach the agent as context, or that the report is appended to the state file. TST-D checks only that `_spawn_agent`, the function that starts the agent, returns failure. It does not test that the failed round is recorded, or that a run whose rounds all failed exits non-zero. Those two PRD-D clauses are unmet today (QUES-A), and the context clause of PRD-C is met only partly (QUES-C).

Not covered today: the loop and the `run` command as a whole, an empty `--phases` value (QUES-J), the exit status of a fully failed run (QUES-A), and the `find-issues` timeout (QUES-B). `tests/python/test_autoworker_rules.py` and `test_autoworker_state.py` test code no command calls (QUES-F). The open questions are in the [design](../design/autoworker-design.md#open-questions).

## Test Execution Order

Run `test_autoworker_engine.py` first, then the `find-issues` classes in `test_cli.py`. The order does not matter for correctness; each test is independent.

## Expected Pass Threshold

Every case with a test must pass; the threshold is 100%. TST-A, TST-B, and TST-F have no test, and TST-C and TST-D are partial. So PRD-A, PRD-B, PRD-C, PRD-D, and PRD-F are not verified by automation. A 100% pass today does not mean PRD-D holds.

## Traceability

| Requirement | Test cases |
|---|---|
| PRD-A | TST-A (no test yet) |
| PRD-B | TST-B (no test yet) |
| PRD-C | TST-C (partial) |
| PRD-D | TST-D (partial) |
| PRD-E | TST-E |
| PRD-F | TST-F (no test yet) |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten with one case per requirement, mapped to pytest tests, untested behavior listed (ARD-A) |
| 0.3 | 2026-11-24 | Review fixes: TST-C and TST-D marked partial with their untested clauses named; PRD-C and PRD-D listed as not verified by automation; Traceability shows coverage status (ARD-E) |
