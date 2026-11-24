---
feature: analytics-dashboard
type: design
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Dashboard — Design

Requirements are in the [PRD](../prd/analytics-dashboard-prd.md). Decisions are in the [decision history](../decision-history/analytics-dashboard-decision-history.md). Behavior below was read from the code at commit `a0f4ce0`; where it does not meet a requirement, the gap is an Open Question.

## Problem Statement

The analytics database holds months of sessions, but SQL is not how a developer wants to look at last week. Some state also needs a person's decision, such as whether a proposed skill should be promoted, and that decision is easier to make looking at the evidence.

## Solution

A small FastAPI server (FastAPI is a Python web framework; uvicorn is the server that runs it) serves a static single-page front end and a JSON interface over the local analytics database and stores. The front end is plain HTML, JavaScript, and CSS. Write actions sit behind a header that only the page's own script sends.

## User Stories

The user stories are in the [PRD](../prd/analytics-dashboard-prd.md#user-stories).

## Implementation Decisions

The default bind is `127.0.0.1` because the data includes full prompts (ARD-B). There is no login. A cross-site write is blocked by requiring the header `X-Coworker-Dashboard: 1` on every write request, which a page on another site cannot send without the browser asking this server first (ARD-C).

## Design

### DSGN-A — Starting the server

`coworker analytics dashboard [--port 8080] [--host 127.0.0.1] [--db PATH]` starts uvicorn. `--db` sets `COWORKER_ANALYTICS_DB` for the run and restores the old value afterwards. A host other than a loopback address prints a warning. This implements PRD-A.

### DSGN-B — Pages

The front end has three groups. Activity holds Summary (refreshed every 15 seconds), Sessions (with filters on session id, AI tool, project, and feature, applied in the browser), and Files. Insights holds Usage, Cost, Quality, and Knowledge. System holds Health, Errors, Evolution, and Graph, which embeds the memory graph page. A failed request shows an error panel with a retry button. This implements PRD-B and PRD-F.

### DSGN-C — Read interface

All read endpoints are `GET` under `/api/`. The main ones are listed here; the full list is the route table in `src/coworker/dashboard/app.py` at `a0f4ce0`.

| Endpoint | Returns |
|---|---|
| `/api/overview` | Totals, active sessions, ten recent sessions, the ten most used tools, and fourteen days of daily counts |
| `/api/sessions?limit=50` | Sessions with their statistics |
| `/api/sessions/{id}` | One session's messages, tool calls, file operations, summary, and statistics |
| `/api/sessions/{id}/timeline` | Messages, tool calls, and file operations merged in time order |
| `/api/tools` | Calls, average duration, and longest duration per tool |
| `/api/files`, `/api/top-files`, `/api/file-stats`, `/api/file-detail` | File activity |
| `/api/skills`, `/api/skill-detail`, `/api/skill-timeline` | Skill usage |
| `/api/knowledge`, `/api/features`, `/api/projects` | Knowledge cards, features, projects |
| `/api/cost-analytics`, `/api/models`, `/api/model-usage`, `/api/efficiency` | Cost and model figures |
| `/api/errors`, `/api/session-errors`, `/api/data-quality`, `/api/memory-stats` | Health and errors |
| `/api/graph`, `/api/evolution/...` | The memory graph and the skill evolution views |

A WebSocket at `/ws` replies with the overview each time the page sends it a message. The database is created with its schema on first access, so an empty or new database gives empty results, not errors, and an unknown session id returns an empty record with status 200. A malformed number in a query parameter gets the framework's automatic 422 response; a negative limit is passed to the database unchecked. These rules implement PRD-C. Two skill endpoints return wrong results (QUES-B).

### DSGN-D — Write interface

| Endpoint | Effect |
|---|---|
| `POST /api/evolution/approve/{id}`, `POST /api/evolution/reject/{id}` | Approves or rejects a proposed skill; 404 when unknown |
| `POST /api/evolution/skills/{name}/status?status=active\|pending\|inactive` | Rewrites that skill's usage record; 400 for a bad status, 404 for an unknown skill |
| `POST /api/memory/refresh-snapshot` | Rewrites the memory snapshot in `~/CLAUDE.local.md`; 500 on failure |
| `POST /api/memory/reset-circuit` | Resets the memory circuit breaker |

Every write request without the header `X-Coworker-Dashboard: 1` is refused with 403. This implements PRD-D.

### DSGN-E — Figures without data

Token and cost columns exist in the database, but no importer fills them at `a0f4ce0`, so cost figures show no data. Session duration is filled only for sessions imported from hook directories. Whether the page shows these gaps as missing or as zero is UNKNOWN, so PRD-E is not verified (QUES-C).

### Sub-problem ownership (子问题归属)

| 子问题 | 归属 | 依据 |
|---|---|---|
| Whether the dashboard should ever be reachable from another machine, and with what login | 人决定 | QUES-A |
| Where cost and token figures should come from | AI 查完人决定 | QUES-C; the analytics listener's QUES-H |

## Testing Decisions

The server is tested in process with FastAPI's test client against a temporary database, including a sweep of every read endpoint. The cases are in the [test plan](../test-plan/analytics-dashboard-test-plan.md).

## Out of Scope

Session recording and import, and the memory graph's own logic, are specified elsewhere, as listed in the [PRD](../prd/analytics-dashboard-prd.md#out-of-scope).

## Further Notes

The `dashboard` skill in walter-worker's `skills/` folder documents an `import --files` option and `start`, `stop`, and `--daemon` forms that the command does not have (QUES-E). Query functions are duplicated across two modules, one of which carries an unreachable copy.

## Alternatives Considered

A server-rendered page per view was rejected in favor of one static page over a JSON interface, which keeps the server small and lets the same interface serve tests. Requiring a login was rejected for a loopback-only default (ARD-B).

## Drawbacks

The interface has more than forty endpoints, several overlapping. The page reads everything through the server, so nothing works when the server is stopped.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Prompts become visible to others on the network | Loopback by default and a warning otherwise (DSGN-A); no login exists (QUES-A) |
| Another website triggers a write | The required header (DSGN-D) |
| A figure misleads | Not mitigated where data is missing (QUES-C) |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | There is no login. Bound to a non-loopback host, anyone who can reach the port reads full prompts. Refuse non-loopback binds, or add a token? | Found in the code at `a0f4ce0`; a warning is printed. | cicidi | no |
| **QUES-B** | `/api/skill-detail` filters on a tool name that matches nothing for real skills, and both skill-detail and skill-timeline ignore `days`. Fix the queries? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-C** | Token and cost figures are never filled, and duration only for hook-imported sessions. Show them as missing, and fill them from the importer? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-D** | Negative `limit` values reach the database unchecked. Validate them? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-E** | The `dashboard` skill documents options the command does not have. Update the skill? | Found in `skills/dashboard/SKILL.md` at `a0f4ce0`. | cicidi | no |

## Reversibility

Stopping the server ends all access. The write actions change skill status, pending items, the memory snapshot, and the circuit breaker; a skill status can be set back from the page, and the other effects are reversed by their own commands in the memory platform.

## Terms

| Term | Meaning |
|---|---|
| Loopback address | `127.0.0.1`, reachable only from the same machine |
| Endpoint | One URL path and method the server answers |
| 403, 404, 422, 500 | HTTP status codes: refused, not found, invalid input, server error |
| WebSocket | A connection that stays open so the server can answer repeated requests quickly |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0` with the 13 required sections; gaps recorded as QUES-A to QUES-E (ARD-A, ARD-D) |
