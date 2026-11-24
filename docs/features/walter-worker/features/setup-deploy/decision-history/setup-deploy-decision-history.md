---
feature: setup-deploy
type: decision-history
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Setup and Deploy — Decision History

Decisions about the install, update, and uninstall scripts. Newest first. Each decision has an entry in the Evidence Appendix with its reason and the options it rejected.

## Decision Log

| ID | Date | Decision |
|---|---|---|
| **ARD-E** | 2026-11-24 | Where the scripts do not meet a requirement, the PRD keeps the requirement, the design states what the code does today, and the conflict is a design Open Question with the owner deciding. The spec does not silently follow either side. |
| **ARD-D** | 2026-11-24 | The uncommitted 2026-11-04 drafts of this feature are rewritten whole in their first commit. Their IDs were never published, so they are renamed to letter IDs without an old-to-new table. From the first commit on, edits follow the normal size limit. |
| **ARD-C** | 2026-11-24 | A the-super-lab skill is deployed only as a skill. Only walter-worker's bundle skills are offered as Claude Code commands, and command copies an earlier release wrote are retired while identical to the source. |
| **ARD-B** | 2026-11-23 | Cursor receives skills as `~/.cursor/skills/<name>/` directory copies, and `personal-skills/` deploys alongside `skills/`. A destination that is the same file as its source is skipped. |
| **ARD-A** | 2026-09-25 | The install manifest claims each written path by name (schema version 2), and uninstall refuses a manifest without a schema version. |

## Evidence Appendix

### ARD-E

The 2026-11-24 review reproduced three behaviors that lose user data (QUES-C, QUES-D, QUES-E) and four smaller conflicts. The spec standard's conflict rule is to detect, report, and ask, never to pick the spec side or the code side silently. Rejected: rewriting the requirements to match the code, which would make data loss the specified behavior; and describing intended behavior as if it shipped, which is how the drafts went wrong. Evidence: `raw/review/2026-11-24-spec-review-setup-deploy-gaps.md` (local, not committed).

### ARD-D

The 2026-11-04 drafts were written by another agent and never committed. They used digit IDs such as `PRD-F1`, which the spec standard forbids, and they claimed behavior the scripts do not have: that the installer runs `pipx install` and that it writes managed regions into `CLAUDE.md`. Fixing them in edits of at most ten lines would have kept false sentences in place across many intermediate states. Rejected: editing the drafts in small steps, and discarding them and starting from nothing (their structure was usable). Evidence: the drafts in the shared checkout at `docs/features/walter-worker/features/setup-deploy/`; `setup/install.sh` at `a0f4ce0` contains no `pipx install` call and no marker block.

### ARD-C

Step 11b deploys every the-super-lab skill to `~/.claude/skills/<name>/`, but step 10 also offered the same skills as commands. A selected skill was therefore written twice and showed up twice in Claude Code's `/` menu; on the author's machine 17 of 19 commands duplicated a skill. Rejected: deleting every command whose name matches a skill, because a command the user edited would be lost; and leaving the duplicates, because they confuse which version runs. Evidence: walter-worker commit `893e17c`, PR #15.

### ARD-B

Current Cursor discovers Agent Skills under `~/.cursor/skills/<name>/SKILL.md`; the flat `~/.cursor/rules/<name>.md` files an earlier release wrote are rules, not skills, and were not loaded as skills. Some machines symlink a skill directory back into the-super-lab, which made `cp` fail with "same file" and aborted the install before hooks were written. Rejected: symlinking Cursor skills, because the manifest would then claim source files and uninstall could delete them out of the repository. Evidence: walter-worker commit `a3d08d7`, PR #14.

### ARD-A

The schema-1 manifest claimed every file found under `~/.claude`, `~/.opencode`, and `~/.coworker/analytics`, including plugin caches, session transcripts, other tools' skills, and the analytics database. Uninstall then deleted all of it. Rejected: keeping directory claims with an exclusion list, because any list misses the next tool's files. Evidence: walter-worker commit `016d875`. The refusal as shipped covers only the file list; hooks and owned directories are still removed, which the design tracks as QUES-E.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-24 | Created with ARD-A to ARD-D |
| 0.2 | 2026-11-24 | Added ARD-E |
