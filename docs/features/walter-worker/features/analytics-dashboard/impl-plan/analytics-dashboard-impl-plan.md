---
feature: analytics-dashboard
type: impl-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Dashboard — Implementation Plan

This plan was written after the code shipped. Each task records a unit of work that exists at commit `a0f4ce0`, what it depends on, what it blocks, and the test that proves it. Behavior is defined in the [design](../design/analytics-dashboard-design.md).

## Global Constraints

Bind to the loopback address unless told otherwise. Every write endpoint requires the dashboard header. No read endpoint may return a server error on an empty or new database.

## Acceptance Criteria

The feature is done when the tasks below are done, their Verify lines pass, and the open questions in the design are each fixed or explicitly accepted by the owner. None of them is blocking.

## Execution order

IMPL-A first, because the server needs the database the [analytics listener](../../analytics-listener/impl-plan/analytics-listener-impl-plan.md) defines (its IMPL-C and IMPL-D). IMPL-B and IMPL-C depend on IMPL-A and can proceed in parallel. IMPL-D depends on IMPL-B.

## IMPL-A — Server and launch

The FastAPI application, the launch command with port, host, and database options, and the loopback default with its warning (DSGN-A). Depends on the analytics listener's database. Blocks IMPL-B, IMPL-C, and IMPL-D.

Verify: `tests/python/test_cli.py` `test_the_default_host_is_loopback` and `test_an_explicit_host_is_honoured_and_warned_about` pass.

## IMPL-B — Read interface

The read endpoints and the WebSocket (DSGN-C). Depends on IMPL-A. Blocks IMPL-D.

Verify: `tests/python/test_dashboard.py` `test_no_get_route_returns_5xx`, `test_returns_200_with_null_session_for_missing_id`, and `test_websocket_returns_overview_on_refresh` pass.

## IMPL-C — Write interface

The write endpoints behind the dashboard header (DSGN-D). Depends on IMPL-A. Blocks nothing.

Verify: `tests/python/test_dashboard.py` `test_a_bare_post_is_refused` and `test_the_dashboards_own_js_sends_the_header` pass.

## IMPL-D — Front end

The static page with its three groups, filters, refresh, and error panels (DSGN-B). Depends on IMPL-B. Blocks nothing.

Verify: `tests/analytics/test_e2e_setup.py` `test_dashboard_api` passes. The front end itself has no browser test.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten as a record of shipped work with Verify lines; added Acceptance Criteria (ARD-A) |
