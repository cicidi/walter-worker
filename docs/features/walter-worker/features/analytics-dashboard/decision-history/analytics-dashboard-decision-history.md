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
| **ARD-E** | 2026-11-24 | The review-fix pass for this backfill is applied as edits larger than the 10-line/200-character limit, authorized by the owner's 2026-11-24 instruction to decide the approach ("你自己看着弄"). |
| **ARD-D** | 2026-11-24 | Where the code does not meet a requirement, the PRD keeps the requirement, the design states what the code does today, and the gap is a design Open Question for the owner to decide. |
| **ARD-A** | 2026-11-24 | The uncommitted 2026-11-04 drafts are rewritten whole in their first commit. Their IDs were never published, so no old-to-new table is kept. |
| **ARD-C** | 2026-09-25 | Every write request must carry the header `X-Coworker-Dashboard: 1`; requests without it are refused with 403. |
| **ARD-F** | 2026-09-25 | The server binds to `127.0.0.1` by default, offers a `--host` option to bind elsewhere, and prints a warning when bound to a host other than `127.0.0.1` or `::1`. Before this decision the server bound to every interface (`0.0.0.0`) while announcing itself as localhost. This restates ARD-B with the correct date and commit. |
| ~~**ARD-B**~~ | ~~2026-07-26~~ | ~~The server binds to `127.0.0.1` by default and warns when told to bind elsewhere.~~ Superseded by [ARD-F](#ard-f). |

## Evidence Appendix

### ARD-E

The 2026-11-24 review of this spec (`raw/review/2026-11-24-spec-review-analytics-dashboard-gaps.md`) found fifteen findings rated 3 or higher. Applying them under the 10-line/200-character edit limit would take many dozens of small edits across five documents. The owner told the AI to decide the approach ("你自己看着弄"). Rejected: splitting the pass into edits under the limit, which would leave the documents inconsistent between edits. Evidence: the owner's instruction of 2026-11-24; the review report above.

### ARD-D

The 2026-11-24 fact pass found five gaps between the requirements and the code (QUES-A to QUES-E). The spec standard's conflict rule is to report and ask, never to pick a side silently. Rejected: lowering the requirements to match the code. Evidence: the design's Open Questions, each citing the code at `a0f4ce0`.

### ARD-A

The drafts named Flask instead of FastAPI, called the dashboard read-only although it has five write endpoints, and described a trace waterfall, session replay, diff view, and heatmap that do not exist. Rejected: correcting them in many small edits. Evidence: the drafts in the shared checkout at `docs/features/walter-worker/features/analytics-dashboard/`; `src/coworker/dashboard/app.py` at `a0f4ce0`.

### ARD-C

The write endpoints approve and reject skills, rewrite `~/CLAUDE.local.md`, and reset the circuit breaker. A plain cross-site form post needs no browser permission check, so any page the user visited could reach them on localhost. A custom header forces that check, which this server does not answer. Rejected: a login, which the loopback-only default does not otherwise need. Evidence: walter-worker commit `3834ee8`; the docstring of `require_dashboard_header` at `a0f4ce0`.

### ARD-F

ARD-B gave the wrong date and commit. Commit `af4cb48` (2026-07-26) only moved a hard-coded `127.0.0.1` while splitting `cli.py` into modules; it added no option and no warning. Commit `b9f9e85` (2026-09-25), titled "the dashboard listened on every interface and said it was localhost", added the `--host` option with the `127.0.0.1` default and the warning, after a period in which the server bound to `0.0.0.0`. The reason is unchanged from ARD-B: the database holds full prompts and tool inputs, and binding to every interface exposes them to the local network. Rejected: binding to all interfaces by default for convenience on remote machines. Evidence: walter-worker commit `b9f9e85`; `git log -S'0.0.0.0' -- src/coworker/cli_analytics.py`; `tests/python/test_cli.py` `test_the_default_host_is_loopback`; the review at `raw/review/2026-11-24-spec-review-analytics-dashboard-gaps.md` (W1).

### ARD-B

Superseded by ARD-F, which corrects the date and the commit. The database holds full prompts and tool inputs. Binding to every interface would expose them to the local network. Rejected: binding to all interfaces by default for convenience on remote machines. Evidence: walter-worker commit `af4cb48`; `tests/python/test_cli.py` `test_the_default_host_is_loopback`.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-24 | Created with ARD-A to ARD-D |
| 0.2 | 2026-11-24 | Review fixes: added ARD-E (edit-size authorization) and ARD-F, which supersedes ARD-B with the correct date and commit `b9f9e85` |
