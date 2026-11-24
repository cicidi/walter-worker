---
feature: feature-system
type: decision-history
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Feature System — Decision History

Decisions about `coworker feature`. Newest first. Each decision has an entry in the Evidence Appendix with its reason and the options it rejected.

## Decision Log

| ID | Date | Decision |
|---|---|---|
| **ARD-D** | 2026-11-24 | Where the code does not meet a requirement, the PRD keeps the requirement, the design states what the code does today, and the gap is a design Open Question for the owner to decide. |
| **ARD-A** | 2026-11-24 | The uncommitted 2026-11-04 `initiative-system` drafts are renamed to `feature-system` and rewritten whole in their first commit. Their IDs were never published, so no old-to-new table is kept. |
| **ARD-C** | 2026-09-24 | The "initiative" concept is renamed "feature". The old folder, markers, and command group keep working in place; nothing is migrated automatically. |
| **ARD-B** | 2026-09-24 | Activation writes only the project's `CLAUDE.local.md`, and the block there is the only record of which feature is active. |

## Evidence Appendix

### ARD-D

The 2026-11-24 fact pass found six places where the code falls short of the requirements (QUES-A to QUES-D and QUES-F) and one standard mismatch (QUES-E). The spec standard's conflict rule is to report and ask, never to pick the spec side or the code side silently. Rejected: lowering the requirements to match the code. Evidence: the design's Open Questions, each citing the code at `a0f4ce0`.

### ARD-A

The drafts claimed a migration command that does not exist, used digit IDs such as `PRD-F1`, and carried the old name that the code had already dropped. Rejected: keeping the old directory name, because every command, marker, and folder in the code now says "feature". Evidence: the drafts in the shared checkout at `docs/features/walter-worker/features/initiative-system/`; `coworker feature --help` at `a0f4ce0`.

### ARD-C

The rename touched the commands, the storage folder, the markers, and the documentation tree. Machines installed earlier hold records under `~/.coworker/initiatives/` and blocks with `INITIATIVE` markers. Reading them in place keeps those machines working without a one-time step the user could miss. Rejected: a forced migration on first run, which would rewrite user files without asking. Evidence: walter-worker commits `4a62aeb` and `4ef6e43`, merged in PR #12 (`ee8c321`).

### ARD-B

The active feature is personal working state: two people on one repository may work on different features. `CLAUDE.local.md` is uncommitted and read by Claude Code at the start of each session, so it is where that state belongs. A separate marker file was rejected because it could disagree with the instruction file the AI actually reads. Evidence: walter-worker commit `4a62aeb`; the `FeatureManager` docstring at `a0f4ce0` ("No global .active marker — single source of truth").

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-24 | Created with ARD-A to ARD-D |
