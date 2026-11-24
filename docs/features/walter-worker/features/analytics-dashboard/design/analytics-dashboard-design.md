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

The analytics database holds months of sessions, but SQL is not how a developer wants to look at last week. Some state also needs a person's decision, such as whether a proposed skill should be promoted, and that decision is easier to make while looking at the evidence.

## Solution

A small FastAPI server (FastAPI is a Python web framework; uvicorn is the server that runs it) serves a static single-page front end and a JSON interface over the local analytics database and stores. The front end is plain HTML, JavaScript, and CSS. Write actions sit behind a header that only the page's own script sends. Today the page itself can reach only one write action, changing a skill's status (DSGN-D).

## User Stories

The user stories are in the [PRD](../prd/analytics-dashboard-prd.md#user-stories).

## Implementation Decisions

The default bind is `127.0.0.1` because the data includes full prompts (ARD-F). There is no login. A cross-site write is blocked by requiring the header `X-Coworker-Dashboard: 1` on every write request, which a page on another site cannot send without the browser asking this server first (ARD-C). The header protects only against a page whose origin differs from the dashboard's. It does not protect against DNS rebinding, an attack in which a foreign site makes the browser treat that site as the dashboard's own origin; the server checks neither the `Host` header nor the WebSocket `Origin` header (QUES-G, QUES-H).

## Design

### DSGN-A — Starting the server

`coworker analytics dashboard [--port 8080] [--host 127.0.0.1] [--db PATH]` starts uvicorn. `--db` sets the environment variable `COWORKER_ANALYTICS_DB`, which names the database file, for the run and restores the old value afterwards. Without `--db` the server uses that variable if it is set, else `~/.coworker/analytics/analytics.db`. Any host other than the literal `127.0.0.1` or `::1` prints a warning, so `--host localhost` also warns (`cli_analytics.py` at `a0f4ce0`). This implements PRD-A.

### DSGN-B — Pages

The front end has three groups. Activity holds Summary, Sessions (with filters on session id, AI tool, project, and feature, applied in the browser), and Files. Insights holds Usage, Cost, Quality, and Knowledge. System holds Health, Errors, Evolution, and Graph, which embeds the memory graph page. Most pages show an error panel with a retry button when a request fails; the Graph page shows an error without a retry button. This implements PRD-B.

The Summary refreshes by polling: while Summary is open, the page requests `/api/overview` over HTTP every 15 seconds and skips the request while the browser tab is hidden (`dashboard.js:618-619` at `a0f4ce0`). The page never opens the WebSocket at `/ws`. This implements PRD-F.

Clicking a session row opens that session, which loads `/api/sessions/{id}` and `/api/sessions/{id}/timeline` (`viewSession` in `dashboard.js`, DSGN-C). This implements PRD-G.

The page can reach only one write action: on a skill's Evolution page, buttons change the skill's status (`dashboard.js:659`). The script also defines functions that approve and reject a proposed skill, but no control calls them (`dashboard.js:660-661`). A Memory Control page with "Refresh Snapshot" and "Reset Circuit" buttons exists in the script, but no menu entry or link leads to it (`dashboard.js:590,670`). Its "Refresh Snapshot" button posts to `/api/memory/refresh`, which does not exist and answers 405; the real endpoint is `/api/memory/refresh-snapshot` (QUES-F).

### DSGN-C — Read interface

All read endpoints are `GET` under `/api/`. The main ones are listed here. The full documented interface is the OpenAPI description that FastAPI serves at `/openapi.json`; FastAPI also serves it as browsable pages at `/docs` and `/redoc`. These three paths are public to anyone who can reach the port, like every other endpoint.

| Endpoint | Returns |
|---|---|
| `/api/overview` | Totals, active sessions, ten recent sessions, the ten most used tools, and daily session counts for the 14 most recent days that have any sessions (days without sessions are left out, so the window can span months; `queries.py:139-142` at `a0f4ce0`, QUES-I) |
| `/api/sessions?limit=50` | Sessions with their statistics |
| `/api/sessions/{id}` | One session's messages, tool calls, file operations, summary, and statistics |
| `/api/sessions/{id}/timeline` | Messages, tool calls, and file operations merged in time order |
| `/api/tools`, `/api/tool-detail` | Calls, average duration, and longest duration per tool; `/api/tool-detail` also gives each tool's type, server name, and session count |
| `/api/files`, `/api/top-files`, `/api/file-stats`, `/api/file-detail` | File activity |
| `/api/skills`, `/api/skill-detail`, `/api/skill-timeline`, `/api/skill-session-ids`, `/api/skill-mentions` | Skill usage |
| `/api/knowledge`, `/api/knowledge/{id}/sessions`, `/api/features`, `/api/projects`, `/api/hotspots`, `/api/daily-sessions` | Knowledge cards, features, projects, the most frequently modified files, and daily session counts |
| `/api/cost-analytics`, `/api/models`, `/api/model-usage`, `/api/efficiency` | Cost and model figures |
| `/api/errors`, `/api/session-errors`, `/api/data-quality`, `/api/memory-stats` | Health and errors |
| `/api/graph`, `/api/evolution/overview`, `/api/evolution/skills`, `/api/evolution/skills/{name}`, `/api/evolution/experiences`, `/api/evolution/experiences/{id}`, `/api/evolution/pending` | The memory graph and the skill evolution views |

A WebSocket at `/ws` replies with the overview each time a client sends it a message. The page does not use it. The server accepts a WebSocket connection from any origin, and browsers apply no same-origin rule to WebSockets, so any website the user visits can read the overview, including the ten most recent sessions with their project, working folder, branch, feature, and model (`app.py:378-387` at `a0f4ce0`, QUES-H).

The database is created with its schema on first access, so an empty or new database gives empty results, not errors, and an unknown session id returns an empty record with status 200. An unknown skill on `/api/evolution/skills/{name}` returns 404. `/api/evolution/experiences/{id}` returns 404 for any failure, including a failure to start the memory store, not only for an unknown id (`app.py:229-237`). A malformed number in a query parameter gets the framework's automatic 422 response. A negative limit is passed to the database unchecked, and in SQLite `LIMIT -1` means no limit, so every row is returned (QUES-D). These rules implement PRD-C. The two session endpoints, `/api/sessions/{id}` and `/api/sessions/{id}/timeline`, implement PRD-G. Two skill endpoints return wrong results (QUES-B).

### DSGN-D — Write interface

| Endpoint | Effect |
|---|---|
| `POST /api/evolution/approve/{id}` | Approves a proposed skill and promotes it to the active skills; 404 when unknown; also 404, with the item marked rejected, when the item fails the safety check (QUES-J) |
| `POST /api/evolution/reject/{id}` | Rejects a proposed skill; 404 when unknown |
| `POST /api/evolution/skills/{name}/status?status=active\|pending\|inactive` | Rewrites that skill's usage record; 400 for a bad status, 404 for an unknown skill, 500 when the record cannot be read or written |
| `POST /api/memory/refresh-snapshot` | Rewrites the memory snapshot in `~/CLAUDE.local.md`; 500 on failure |
| `POST /api/memory/reset-circuit` | Resets the memory circuit breaker |

Every write request without the header `X-Coworker-Dashboard: 1` is refused with 403. This implements PRD-D, except that the page can reach only the skill status action (DSGN-B, QUES-F) and the header does not stop a DNS rebinding attack (QUES-G).

### DSGN-E — Figures without data

Token and cost columns exist in the database, but no importer fills them at `a0f4ce0`. Session duration is filled only for sessions imported from hook directories. The page shows these missing figures as zero, not as missing: the columns default to 0 (`db.py:86-92`), the queries wrap sums in `COALESCE(..., 0)` (`queries_analytics.py` `query_cost_analytics` and `query_models`, `queries.py` `query_projects`), and the Health page then shows "Total Cost $0.0000" and "Total Tokens 0" (`dashboard.js:600-601`). PRD-E is therefore not met (QUES-C). The `cost` column is an integer column, so a fractional dollar amount would be cut to a whole number once an importer fills it (QUES-C).

### Sub-problem ownership (子问题归属)

| 子问题 | 归属 | 依据 |
|---|---|---|
| Whether the dashboard should ever be reachable from another machine, and with what login | 人决定 | QUES-A |
| Where cost and token figures should come from | AI 查完人决定 | QUES-C; the analytics listener's QUES-H |
| How to keep other websites from reading session data (Host and Origin checks) | AI 查完人决定 | QUES-G, QUES-H |
| Whether the page should offer approve, reject, snapshot, and circuit actions | 人决定 | QUES-F |

## Testing Decisions

The server is tested in process with FastAPI's test client against a shared in-memory SQLite database that the test fixtures fill with sample rows. A sweep calls every read endpoint whose path has no parameter. The graph, evolution, and memory endpoints read files under the real home folder (`~/.coworker`), which the tests do not redirect. No test runs the endpoints against an empty database. The cases are in the [test plan](../test-plan/analytics-dashboard-test-plan.md).

## Out of Scope

Session recording and import, and the memory graph's own logic, are specified elsewhere, as listed in the [PRD](../prd/analytics-dashboard-prd.md#out-of-scope).

## Further Notes

The `dashboard` skill in walter-worker's `skills/` folder documents an `import --files` option and `start`, `stop`, and `--daemon` forms that the command does not have (QUES-E).

## Alternatives Considered

A server-rendered page per view was rejected in favor of one static page over a JSON interface, which keeps the server small and lets the same interface serve tests. Requiring a login was rejected for a loopback-only default (ARD-F).

## Drawbacks

The interface has more than forty endpoints, several overlapping. The page reads everything through the server, so nothing works when the server is stopped.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Prompts become visible to others on the network | Loopback by default and a warning otherwise (DSGN-A); no login exists (QUES-A) |
| Another website triggers a write | The required header (DSGN-D), which works only while the other site's origin differs from the dashboard's |
| DNS rebinding: a foreign site makes the browser treat it as the dashboard's origin, then reads every endpoint, full prompts included, and sends the header on writes | Not mitigated; the server does not check the `Host` header (QUES-G) |
| Another website reads the overview through the WebSocket | Not mitigated; the server does not check the `Origin` header (QUES-H) |
| A figure misleads | Not mitigated where data is missing (QUES-C) |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | There is no login. Bound to a non-loopback host, anyone who can reach the port reads full prompts. Refuse non-loopback binds, or add a token? | Found in the code at `a0f4ce0`; a warning is printed. | cicidi | no |
| **QUES-B** | `/api/skill-detail?name=...` requires the tool to be `Skill` and equal to the name at once, so with a name it matches nothing. `/api/skill-timeline` filters on the tool equal to the skill name, so it returns nothing for real skills. Both ignore `days`. The page calls skill-detail. Fix the queries? | Found in `queries.py:382-410` at `a0f4ce0` and by the 2026-11-24 review (W6). | cicidi | no |
| **QUES-C** | Token and cost figures are never filled, and duration only for hook-imported sessions, yet the page shows them as zero, which violates PRD-E. The `cost` column is an integer, so fractional dollars would be cut. Show missing figures as missing, store cost as a decimal number, and fill both from the importer? | Found in the code at `a0f4ce0` and by the 2026-11-24 review (I3). | cicidi | no |
| **QUES-D** | Negative `limit` values reach the database unchecked, and `LIMIT -1` returns every row. Validate them? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-E** | The `dashboard` skill documents options the command does not have. Update the skill? | Found in `skills/dashboard/SKILL.md` at `a0f4ce0`. | cicidi | no |
| **QUES-F** | The page cannot approve or reject a proposed skill, refresh the memory snapshot, or reset the circuit breaker, although PRD-D and the user stories expect it. The approve and reject functions have no control, the Memory Control page has no way in, and its refresh button posts to a wrong URL (405). Wire these into the page, or drop them from the requirements? | Found in `dashboard.js` at `a0f4ce0` and by the 2026-11-24 review (C1). | cicidi | no |
| **QUES-G** | The server checks no `Host` header, so a DNS rebinding attack lets a foreign page read every endpoint, confidential prompts included, and send the write header. Add a host allow-list, for example Starlette's `TrustedHostMiddleware` limited to `localhost` and `127.0.0.1`? | Found in `app.py` at `a0f4ce0`; a request with `Host: evil.example:8080` gets 200 on reads and writes (2026-11-24 review, I1). | cicidi | yes |
| **QUES-H** | The WebSocket at `/ws` accepts any `Origin`, so any website can read the overview with recent session details. Check `Origin`, or remove `/ws`, which the page does not use? | Found in `app.py:378-387` at `a0f4ce0`; a connection with `Origin: http://evil.example` received the overview (2026-11-24 review, I2). | cicidi | yes |
| **QUES-I** | The activity chart shows the 14 most recent days that have sessions, not the last 14 calendar days. Are calendar days intended? | Found in `queries.py:139-142` at `a0f4ce0`. | cicidi | no |
| **QUES-J** | Approve answers 404 "not found" when the item exists but fails the safety check, and it marks the item rejected. Return a distinct error that says the check failed? | Found in `memory/pending.py` and `app.py` at `a0f4ce0`. | cicidi | no |

## Reversibility

Stopping the server ends all access. The write actions change skill status, pending items, the memory snapshot, and the circuit breaker. A skill status can be set back from the page. In the [memory platform](../../../../memory-platform/prd/memory-platform-prd.md), the snapshot block in `~/CLAUDE.local.md` can be rewritten with `coworker memory refresh` or removed by hand, and a pending skill can be marked rejected with `coworker skill reject`. Whether a promoted skill can be taken back by a command is UNKNOWN. A circuit-breaker reset cannot be undone; the counter simply starts again from zero.

## Terms

| Term | Meaning |
|---|---|
| Loopback address | `127.0.0.1`, reachable only from the same machine |
| Endpoint | One URL path and method the server answers |
| 403, 404, 422, 500 | HTTP status codes: refused, not found, invalid input, server error |
| WebSocket | A connection that stays open so the server can answer repeated requests quickly |
| DNS rebinding | An attack in which a foreign website changes what its domain name points to, so the browser sends that site's requests to the dashboard and treats the answers as same-origin |
| Circuit breaker | A counter in `~/.coworker/safety/circuit_state.json` that allows at most three skill proposals per 24-hour window; resetting it sets the count to zero |
| Memory snapshot | The block of the current project's memories that the memory platform writes between markers in `~/CLAUDE.local.md`, so the next session starts with them |
| Memory loop | The memory platform's process that, at the end of each session, extracts lessons and candidate skills and stages the skills in `~/.coworker/pending/skills/` for approval |
| Knowledge cards | Entries in the analytics database's `knowledge` table that `coworker knowledge` derives from recorded sessions |
| Hook directories | The per-session folders under `~/.coworker/analytics/sessions/` that the analytics listener's hook scripts write while a session runs |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0` with the 13 required sections; gaps recorded as QUES-A to QUES-E (ARD-A, ARD-D) |
| 0.3 | 2026-11-24 | Review fixes: the page's reachable writes, polling refresh, the 14-day rule, zero for missing figures, public `/docs`, `/redoc`, and `/openapi.json`, and write error cases corrected; PRD-G anchored; terms defined; memory platform linked; QUES-F to QUES-J added, QUES-G and QUES-H blocking (ARD-E, ARD-F) |
