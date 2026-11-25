---
feature: walter-worker
type: test-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# walter-worker — Test Plan

This parent test plan says how to run every area's tests and maps the parent requirements to the sub-feature test plans that verify them. The older test plan is kept as a part until it is folded in: [ai-coworker test plan](ai-coworker-test-plan.md).

## Test Cases

| ID | Covers | Case | Where |
|---|---|---|---|
| **TST-A** | PRD-A | Install, update, and uninstall behave as specified | [setup-deploy test plan](../features/setup-deploy/test-plan/setup-deploy-test-plan.md) |
| **TST-B** | PRD-B | Configuration commands and sync behave as specified | [core-cli test plan](../features/core-cli/test-plan/core-cli-test-plan.md) |
| **TST-C** | PRD-C | Feature commands and activation behave as specified | [feature-system test plan](../features/feature-system/test-plan/feature-system-test-plan.md) |
| **TST-D** | PRD-D | Session capture, import, and the dashboard behave as specified | [analytics-listener test plan](../features/analytics-listener/test-plan/analytics-listener-test-plan.md), [analytics-dashboard test plan](../features/analytics-dashboard/test-plan/analytics-dashboard-test-plan.md) |
| **TST-E** | PRD-E | Memory capture, merge, curation, and snapshots behave as specified | [memory-platform test plan](../../memory-platform/test-plan/memory-platform-test-plan.md) |
| **TST-F** | PRD-F | The review loop and `find-issues` behave as specified | [autoworker test plan](../../autoworker/test-plan/autoworker-test-plan.md) |
| **TST-G** | PRD-G | No hook stops a session through its own failure | The hook cases in the analytics-listener and memory-platform test plans |
| **TST-H** | PRD-H | No session content leaves the machine except where documented | No automated test; checked by review of each design's privacy section |

## Test Execution Order

Run `bats tests/setup/` first, because the installer sets up the files the other areas use. Then `python3 -m pytest tests/`, which covers every Python area. The order inside pytest does not matter. The test `tests/python/test_skill_factory_integration.py::TestSuperLabSource::test_walter_worker_skills_have_skill_md` fails at `a0f4ce0` for a reason outside this repository (a the-super-lab folder without `SKILL.md`).

## Expected Pass Threshold

Every bats and pytest case must pass, except the one outside failure named above; the threshold is 100% of the rest. A sub-feature requirement without a test is listed in that sub-feature's test plan as not verified.

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
| 0.1 | 2026-11-24 | Written as the parent entry linking every sub-feature test plan; the legacy test plan linked as a part |
