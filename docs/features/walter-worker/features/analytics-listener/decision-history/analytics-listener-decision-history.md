---
feature: analytics-listener
type: decision-history
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Listener — Decision History

Decisions about session capture and import. Newest first. Each decision has an entry in the Evidence Appendix with its reason and the options it rejected.

## Decision Log

| ID | Date | Decision |
|---|---|---|
| **ARD-D** | 2026-11-24 | Where the code does not meet a requirement, the PRD keeps the requirement, the design states what the code does today, and the gap is a design Open Question for the owner to decide. |
| **ARD-A** | 2026-11-24 | The uncommitted 2026-11-04 drafts are rewritten whole in their first commit. Their IDs were never published, so no old-to-new table is kept. |
| **ARD-C** | 2026-06-23 | Claude Code's own transcripts are imported and preferred over hook records for message text. |
| **ARD-B** | 2026-06-12 | Hooks append JSON lines to per-session files; a separate import step loads them into one SQLite database. |

## Evidence Appendix

### ARD-D

The 2026-11-24 fact pass found eight gaps (QUES-A to QUES-H), one of which stores secrets in plain text. The spec standard's conflict rule is to report and ask, never to pick a side silently. Rejected: lowering the requirements to match the code. Evidence: the design's Open Questions, each citing the code at `a0f4ce0`.

### ARD-A

The drafts described an OpenCode plugin that writes the same session files, and an `index.jsonl` that feeds dashboard queries; neither is true, and the drafts used digit IDs. Rejected: correcting them in many small edits that would keep false sentences in place. Evidence: the drafts in the shared checkout at `docs/features/walter-worker/features/analytics-listener/`; `src/coworker/analytics/` at `a0f4ce0`.

### ARD-C

Hooks see the user's prompts and the tool calls, but never the assistant's replies, which are what session summaries need. Transcripts carry the full conversation. Rejected: transcripts as the only source, because they carry no tool durations. Evidence: walter-worker commit `0b57ec3`.

### ARD-B

A hook runs on every prompt and tool call, so it must start fast, need no installed package, and never leave shared state damaged when interrupted. Appending a line to a file meets all three; writing to SQLite from each hook would not. Rejected: writing to the database directly from hooks. Evidence: walter-worker commit `2d6924d`.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-24 | Created with ARD-A to ARD-D |
