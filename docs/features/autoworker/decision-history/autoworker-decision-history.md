---
feature: autoworker
type: decision-history
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Auto-worker — Decision History

Decisions about the auto-worker. Newest first. Each decision has an entry in the Evidence Appendix with its reason and the options it rejected.

## Decision Log

| ID | Date | Decision |
|---|---|---|
| **ARD-D** | 2026-11-24 | Where the code does not meet a requirement, the PRD keeps the requirement, the design states what the code does today, and the gap is a design Open Question for the owner to decide. |
| **ARD-A** | 2026-11-24 | The uncommitted 2026-11-04 drafts are rewritten whole in their first commit. Their IDs were never published, so no old-to-new table is kept. |
| **ARD-C** | 2026-09-25 | A missing `claude` command makes the round fail; there is no fallback that pretends to run without tools. |
| **ARD-B** | 2026-09-25 | Each round runs the agent as `claude -p <prompt> --output-format json`, with a per-round time limit. |

## Evidence Appendix

### ARD-D

The 2026-11-24 fact pass found six gaps (QUES-A to QUES-F), one of which lets a fully failed run exit 0. The spec standard's conflict rule is to report and ask, never to pick a side silently. Rejected: lowering the requirements to match the code. Evidence: the design's Open Questions, each citing the code at `a0f4ce0`.

### ARD-A

The drafts described a `coworker autoworker` command, an `AutoWorkerEngine` class, gap detection and classification in code, and state under the project's `docs/state/`; none of these exists. Rejected: correcting them in many small edits. Evidence: the drafts in the shared checkout at `docs/features/autoworker/`; `src/coworker/autoworker/engine.py` at `a0f4ce0`.

### ARD-C

Before this decision, the agent start could not work, and the fallback reported success anyway, so an unattended loop produced nothing while looking healthy. Rejected: a tool-less API fallback, because an audit that cannot read files or run tests has nothing real to report. Evidence: walter-worker commit `d6d6a8b`; `tests/python/test_autoworker_engine.py` `test_missing_cli_does_not_report_success`.

### ARD-B

A headless session gives the agent the same tools as an interactive one and returns a structured result the supervisor can parse. The time limit bounds a hung session. Rejected: an interactive session, which cannot run unattended. Evidence: walter-worker commit `d6d6a8b`; `test_uses_the_headless_print_invocation`.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-24 | Created with ARD-A to ARD-D |
