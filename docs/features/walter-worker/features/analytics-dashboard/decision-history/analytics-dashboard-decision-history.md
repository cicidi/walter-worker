---
feature: analytics-dashboard
type: decision-history
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Dashboard — Decision History

Decisions about the dashboard. Newest first. Each decision has an entry in the Evidence Appendix with its reason and the options it rejected.

## Decision Log

| ID | Date | Decision |
|---|---|---|
| **ARD-D** | 2026-11-24 | Where the code does not meet a requirement, the PRD keeps the requirement, the design states what the code does today, and the gap is a design Open Question for the owner to decide. |
| **ARD-A** | 2026-11-24 | The uncommitted 2026-11-04 drafts are rewritten whole in their first commit. Their IDs were never published, so no old-to-new table is kept. |
| **ARD-C** | 2026-09-25 | Every write request must carry the header `X-Coworker-Dashboard: 1`; requests without it are refused with 403. |
| **ARD-B** | 2026-07-26 | The server binds to `127.0.0.1` by default and warns when told to bind elsewhere. |

## Evidence Appendix

### ARD-D

The 2026-11-24 fact pass found five gaps between the requirements and the code (QUES-A to QUES-E). The spec standard's conflict rule is to report and ask, never to pick a side silently. Rejected: lowering the requirements to match the code. Evidence: the design's Open Questions, each citing the code at `a0f4ce0`.

### ARD-A

The drafts named Flask instead of FastAPI, called the dashboard read-only although it has five write endpoints, and described a trace waterfall, session replay, diff view, and heatmap that do not exist. Rejected: correcting them in many small edits. Evidence: the drafts in the shared checkout at `docs/features/walter-worker/features/analytics-dashboard/`; `src/coworker/dashboard/app.py` at `a0f4ce0`.

### ARD-C

The write endpoints approve and reject skills, rewrite `~/CLAUDE.local.md`, and reset the circuit breaker. A plain cross-site form post needs no browser permission check, so any page the user visited could reach them on localhost. A custom header forces that check, which this server does not answer. Rejected: a login, which the loopback-only default does not otherwise need. Evidence: walter-worker commit `3834ee8`; the docstring of `require_dashboard_header` at `a0f4ce0`.

### ARD-B

The database holds full prompts and tool inputs. Binding to every interface would expose them to the local network. Rejected: binding to all interfaces by default for convenience on remote machines. Evidence: walter-worker commit `af4cb48`; `tests/python/test_cli.py` `test_the_default_host_is_loopback`.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-24 | Created with ARD-A to ARD-D |
