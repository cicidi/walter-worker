---
feature: autoworker
type: impl-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Auto-worker — Implementation Plan

This plan was written after the code shipped. Each task records a unit of work that exists at commit `a0f4ce0`, what it depends on, what it blocks, and the test that proves it. Behavior is defined in the [design](../design/autoworker-design.md).

## Global Constraints

A loop must stop on its time budget and its round cap. A missing or failing agent is never reported as success (ARD-C). The Python code itself does not create commits, branches, or issues.

## Acceptance Criteria

The feature is not done while the blocking open question QUES-A is open. Beyond that, it is done when the tasks below are done, their Verify lines pass, and every other open question is fixed or explicitly accepted by the owner.

## Execution order

IMPL-A first, because the loop starts the agent through it. IMPL-B depends on IMPL-A. IMPL-C depends on nothing and can proceed in parallel.

## IMPL-A — Agent start

Start a headless `claude` session with a time limit and report a missing command as a failure (DSGN-B, ARD-B, ARD-C). Depends on nothing. Blocks IMPL-B.

Verify: `tests/python/test_autoworker_engine.py` `test_uses_the_headless_print_invocation`, `test_missing_cli_does_not_report_success`, and `test_the_reason_names_the_missing_cli` pass.

## IMPL-B — Loop and state file

The `run` command, the wrong-history injection, the rounds, the stop conditions, and the state file (DSGN-A to DSGN-C). Depends on IMPL-A. Blocks nothing.

Verify: no test covers the loop or the `run` command yet.

## IMPL-C — `find-issues`

The phases, the report, and the exit statuses (DSGN-D). Depends on nothing. Blocks nothing.

Verify: `tests/python/test_cli.py` `test_unknown_phases_are_an_error`, `test_failing_tests_exit_non_zero`, `test_a_clean_run_exits_zero`, and `test_a_different_project_reads_its_own_docs` pass.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten as a record of shipped work with Verify lines; added Acceptance Criteria (ARD-A) |
