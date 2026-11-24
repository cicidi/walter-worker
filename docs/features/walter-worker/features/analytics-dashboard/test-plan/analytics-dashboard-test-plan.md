---
feature: analytics-dashboard
type: test-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Dashboard — Test Plan

Each case names the requirement from the [PRD](../prd/analytics-dashboard-prd.md) it covers and the pytest test that implements it at commit `a0f4ce0`. The server is tested in process with FastAPI's test client against a shared in-memory SQLite database that the fixtures fill with sample rows.

## Test Cases

| ID | Covers | Case | Pytest test |
|---|---|---|---|
| **TST-A** | PRD-A | The default host is loopback, an explicit host is honoured with a warning, and `--db` points the run at another database and restores the old setting afterwards | `tests/python/test_cli.py` `test_the_default_host_is_loopback`, `test_an_explicit_host_is_honoured_and_warned_about`, `test_analytics_dashboard_with_db`, `test_analytics_dashboard_restores_previous_db` |
| **TST-B** | PRD-B | The page's data endpoints answer through the full pipeline | `tests/analytics/test_e2e_setup.py` `test_dashboard_api` |
| **TST-C** | PRD-C | Against the seeded test database, no read endpoint without a path parameter returns a server error, and an unknown session returns an empty record with 200. The empty or new database case has no test. | `tests/python/test_dashboard.py` `test_no_get_route_returns_5xx`, `test_returns_200_with_null_session_for_missing_id` |
| **TST-D** | PRD-D | A write request without the header is refused, and the page's own script sends it | `tests/python/test_dashboard.py` `test_a_bare_post_is_refused`, `test_the_dashboards_own_js_sends_the_header` |
| **TST-E** | PRD-E | A figure with no data behind it is shown as missing | No test yet (QUES-C) |
| **TST-F** | PRD-F | The Summary polls `/api/overview` every 15 seconds while it is open | No test yet. The page refreshes by HTTP polling, not through the WebSocket, so the WebSocket test does not cover this requirement. |
| **TST-G** | PRD-G | One session's detail and its merged timeline are returned in time order | `tests/python/test_dashboard.py` `test_returns_200_with_full_detail`, `test_returns_200_with_interleaved_timeline`, `test_returns_interleaved_timeline`, `test_ordered_by_ts_and_seq` |

Not covered today: the front end in a real browser, the 15-second polling (TST-F), read endpoints on an empty database, endpoints with path parameters in the sweep, the skill query bugs (QUES-B), negative limits (QUES-D), and the missing `Host` and `Origin` checks (QUES-G, QUES-H). The open questions are in the [design](../design/analytics-dashboard-design.md#open-questions).

## Test Execution Order

Run `test_dashboard.py` first, then the launch tests in `test_cli.py`, then `test_e2e_setup.py`, which depends on the whole analytics pipeline.

## Expected Pass Threshold

Every case with a test must pass; the threshold is 100%. TST-E and TST-F have no test, so PRD-E and PRD-F are not verified. PRD-E is also known to be violated (QUES-C).

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

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten with one case per requirement, mapped to pytest tests, untested behavior listed (ARD-A) |
| 0.3 | 2026-11-24 | Review fixes: TST-C states what its test proves; TST-F marked untested because the page polls instead of using the WebSocket; TST-A covers `--db`; TST-G added for PRD-G (ARD-E) |
