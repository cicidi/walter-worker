---
feature: core-cli
type: decision-history
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Core CLI — Decision History

Decisions about the configuration commands. Newest first. Each decision has an entry in the Evidence Appendix with its reason and the options it rejected.

## Decision Log

| ID | Date | Decision |
|---|---|---|
| **ARD-F** | 2026-11-24 | The review-fix pass for this backfill is applied as edits larger than the 10-line/200-character limit, authorized by the owner's 2026-11-24 instruction to decide the approach ("你自己看着弄"). |
| **ARD-D** | 2026-11-24 | Where the code does not meet a requirement, the PRD keeps the requirement, the design states what the code does today, and the gap is a design Open Question for the owner to decide. |
| **ARD-A** | 2026-11-24 | The uncommitted 2026-11-04 drafts are rewritten whole in their first commit. Their IDs were never published, so no old-to-new table is kept. |
| **ARD-E** | 2026-09-25 | `restore` exposes the backups that mutating commands take, by path, folder name, or label. |
| **ARD-B** | 2026-09-25 | `sync` records each MCP server it writes in `~/.coworker/mcp-managed.json` and removes a server only when that record shows it wrote it and the entry is unchanged. Settings writes are atomic and skipped when nothing changes. |
| **ARD-C** | 2026-07-07 | Every command that overwrites a user-visible file first copies it under `~/.coworker/backups/<timestamp>-<label>/`, keeping at most twenty copies per label. |

## Evidence Appendix

### ARD-F

The spec standard limits each AI edit under `docs/` to 10 lines and 200 characters unless a human authorizes a larger change and the authorization is recorded as an ARD. The 2026-11-24 review found false sentences and missing behavior across the design, implementation plan, and test plan, and the owner told the agent to decide the approach. Rejected: applying the pass as a long series of edits within the limit. Evidence: the review report [`raw/review/2026-11-24-spec-review-core-cli-gaps.md`](../raw/review/2026-11-24-spec-review-core-cli-gaps.md) (local, not committed).

### ARD-D

The 2026-11-24 fact pass found eleven gaps between the requirements and the code (QUES-A to QUES-K), one of which crashes `upgrade`. The spec standard's conflict rule is to report and ask, never to pick a side silently. Rejected: lowering the requirements to match the code. Evidence: the design's Open Questions, each citing the code at `a0f4ce0`.

### ARD-A

The drafts claimed a Cursor adapter and secret references through environment variables, neither of which exists, and used digit IDs such as `PRD-F1`. Rejected: correcting them in many small edits, which would have kept false sentences in place across intermediate states. Evidence: the drafts in the shared checkout at `docs/features/walter-worker/features/core-cli/`; the adapters at `a0f4ce0`.

### ARD-E

Install, upgrade, sync, and the feature commands printed where their backup went, but no command could act on it; the restore function existed and nothing called it. Rejected: asking users to copy files back by hand from the mirrored paths. Evidence: walter-worker commit `7fff3b7`.

### ARD-B

Syncing MCP configuration used to replace the user's servers, and could never retire a server walter-worker itself had written, because it could not tell its own entries from the user's. JSON has no comments, so ownership cannot be marked inside the file. Rejected: markers inside JSON keys, which would leak into each tool's configuration. Evidence: walter-worker commits `33e5e4c` (managed record) and `68d4109` (permissions union, MCP location, atomic writes).

### ARD-C

Several commands rewrote files the user also edits: the global `CLAUDE.md`, project instruction files, and tool settings. Without a copy, a bad merge or sync was not recoverable. Rejected: relying on the user's version control, because most of these files live outside any repository. Evidence: walter-worker commit `8d670d1`.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-24 | Created with ARD-A to ARD-E |
| 0.2 | 2026-11-24 | Review fixes: added ARD-F, which authorizes the review-fix pass as larger edits |
