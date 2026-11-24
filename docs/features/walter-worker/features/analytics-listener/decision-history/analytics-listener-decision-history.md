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
| **ARD-E** | 2026-11-24 | The review-fix pass for this backfill is applied as edits larger than the 10-line/200-character limit, authorized by the owner's 2026-11-24 instruction to decide the approach ("你自己看着弄"). |
| **ARD-D** | 2026-11-24 | Where the code does not meet a requirement, the PRD keeps the requirement, the design states what the code does today, and the gap is a design Open Question for the owner to decide. |
| **ARD-A** | 2026-11-24 | The uncommitted 2026-11-04 drafts are rewritten whole in their first commit. Their IDs were never published, so no old-to-new table is kept. |
| **ARD-C** | 2026-06-23 | Claude Code's own transcripts are imported and preferred over hook records for message text. |
| **ARD-B** | 2026-06-12 | Hooks append JSON lines to per-session files; a separate import step loads them into one SQLite database. |

## Evidence Appendix

### ARD-E

The 2026-11-24 gaps review found 14 findings rated 3 or higher across all five documents, several of which needed whole paragraphs rewritten (DSGN-B, DSGN-C, DSGN-E) and seven new open questions (QUES-I to QUES-O). The spec standard limits an AI edit to 10 lines and 200 characters unless a human authorizes more and the authorization is recorded as an ARD. The owner was asked how to apply the fixes and answered "你自己看着弄" (decide it yourself). Rejected: splitting the pass into dozens of small edits, which would leave the documents contradicting themselves between edits. Evidence: `../raw/review/2026-11-24-spec-review-analytics-listener-gaps.md`; the owner's instruction of 2026-11-24.

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
| 0.2 | 2026-11-24 | Added ARD-E (review-fix pass authorized above the edit-size limit) |
