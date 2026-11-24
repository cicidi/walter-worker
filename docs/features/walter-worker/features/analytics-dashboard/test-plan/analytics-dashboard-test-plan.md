---
feature: analytics-dashboard
type: test-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Dashboard — Test Plan

Each case names the requirement from the [PRD](../prd/analytics-dashboard-prd.md) it covers and the pytest test that implements it at commit `a0f4ce0`. The server is tested in process with FastAPI's test client against a temporary database.

## Test Cases

| ID | Covers | Case | Pytest test |
|---|---|---|---|
| **TST-A** | PRD-A | The default host is loopback, and an explicit host is honoured with a warning | `tests/python/test_cli.py` `test_the_default_host_is_loopback`, `test_an_explicit_host_is_honoured_and_warned_about` |
| **TST-B** | PRD-B | The page's data endpoints answer through the full pipeline | `tests/analytics/test_e2e_setup.py` `test_dashboard_api` |
| **TST-C** | PRD-C | No read endpoint returns a server error, and an unknown session returns an empty record with 200 | `tests/python/test_dashboard.py` `test_no_get_route_returns_5xx`, `test_returns_200_with_null_session_for_missing_id` |
| **TST-D** | PRD-D | A write request without the header is refused, and the page's own script sends it | `tests/python/test_dashboard.py` `test_a_bare_post_is_refused`, `test_the_dashboards_own_js_sends_the_header` |
| **TST-E** | PRD-E | A figure with no data behind it is shown as missing | No test yet (QUES-C) |
| **TST-F** | PRD-F | The WebSocket returns the overview on each refresh | `tests/python/test_dashboard.py` `test_websocket_returns_overview_on_refresh` |

Not covered today: the front end in a real browser, the skill query bugs (QUES-B), and negative limits (QUES-D). The open questions are in the [design](../design/analytics-dashboard-design.md#open-questions).

## Test Execution Order

Run `test_dashboard.py` first, then the launch tests in `test_cli.py`, then `test_e2e_setup.py`, which depends on the whole analytics pipeline.

## Expected Pass Threshold

Every case with a test must pass; the threshold is 100%. TST-E has no test, so PRD-E is not verified.

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
