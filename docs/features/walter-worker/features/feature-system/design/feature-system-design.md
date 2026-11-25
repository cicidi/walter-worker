---
feature: feature-system
type: design
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Feature System — Design

Requirements are in the [PRD](../prd/feature-system-prd.md). Decisions are in the [decision history](../decision-history/feature-system-decision-history.md). Behavior below was read from the code at commit `a0f4ce0`; where it does not meet a requirement, the gap is an Open Question.

## Problem Statement

Work that spans several repositories needs the same context in each: what the goal is, which projects are involved, what was decided, and where the documents are. Writing that by hand into every project's instruction file drifts, and a stale block from the last task misleads the AI in the next session.

## Solution

One record per feature lives in the user's home directory and is shared by all projects. Activation is per project: it writes the record as a delimited block into that project's `CLAUDE.local.md`, replacing any feature block already there. The block is the single source of truth for "which feature is active here"; there is no separate marker file.

## User Stories

The user stories are in the [PRD](../prd/feature-system-prd.md#user-stories).

## Implementation Decisions

Records are YAML files, one per feature, so a user can edit fields the commands do not expose. Unknown keys survive a load and save. Activation writes only `CLAUDE.local.md`, never the committed `CLAUDE.md`, because the active feature is a personal working state (ARD-B). The old "initiative" spelling is read in place and never migrated automatically (ARD-C).

## Design

### DSGN-A — Names

A feature name must match lowercase letters and digits joined by single hyphens, such as `spec-driven-development`. The check runs on every load, save, and existence test, so no command can read or write a file outside the features directory through the name. This implements PRD-A. Today `create`, `edit`, `show`, `activate`, and `remove` stop on a bad name with an uncaught Python error and a traceback, which exits with status 1, while `start` prints the error cleanly but exits 0 (QUES-A).

### DSGN-B — The record

A feature is stored at `~/.coworker/features/<name>.yaml`. Its fields are the name, a description, a goal, an approach, a testing note, recommended skills, a status (`active` until archived), the creation date, the projects in scope (each with a name, a role, and branches), links (each with a title, a URL, and an optional description that the block shows), decisions (date, decision, rationale, decided by), reference documents, artifacts, and remaining work. A project's role is free text that defaults to `peer`. By convention it is `upstream`, `downstream`, or `peer`, but no command checks it, and any other text is stored and shown as given (QUES-H). The goal, approach, testing note, recommended skills, link descriptions, artifacts, and remaining work have no command-line setter; they are edited in the YAML file. This implements PRD-B.

### DSGN-C — Commands

| Command | Behavior |
|---|---|
| `create NAME [-d] [-p DIR]` | Writes the record and creates `docs/features/<name>/` in the project with the folders `prd`, `spec`, `impl-plan`, `test-plan`, `decision-history`, and `how-to`. An existing name prints a message and exits 0. Implements PRD-C. |
| `start NAME [-d] [-p DIR] [--role] [-b BRANCHES]` | The role defaults to `peer` and the branches to `main`. Creates the record if needed, which also scaffolds `docs/features/<name>/` in the project exactly as `create` does; an existing record is reused with a notice. It then adds the project to the scope if missing, saves, and activates. Implements PRD-D. |
| `activate NAME [-p DIR]` / `deactivate [-p DIR]` | See DSGN-D. |
| `edit NAME [-p DIR] [...]` | Changes the description, adds a project (`name:role:branches`), a link (`Title\|URL`), a decision (`date\|decision\|rationale\|by`, the format its `--help` documents; QUES-D says how it is stored today), or a reference document (`Title\|path`), or archives. It accepts `-p DIR` but ignores it, because the record is shared by all projects. Implements PRD-F. |
| `list [-p DIR] [-v]` / `show NAME [-p DIR]` | `list` prints every feature with its status and marks the one active in the project. A record file that cannot be read appears as a row whose description is `[error: ...]`, and the command still succeeds. `show` prints the record as YAML; it accepts `-p DIR` but ignores it. Neither changes a record or a project file. Both create the empty folder `~/.coworker/features/` when neither it nor the old `initiatives/` folder exists, even when the name is invalid (QUES-I). Implements PRD-G. |
| `remove NAME [-p DIR] [--force]` | See DSGN-E. |

A missing feature in `edit`, `show`, `activate`, or `remove` is an error with exit status 1.

### DSGN-D — Activation

Activating loads the record and fails with exit status 1 if it does not exist. It then removes every feature block from the project's `CLAUDE.local.md`, creating that file from the template if it is missing, and writes the new block. The block starts with `<!-- FEATURE:<name> START -->`, ends with `<!-- FEATURE:<name> END -->`, and contains the heading `## Active Feature: <name>`, the description, and sections for the goal, approach, testing, recommended skills, projects in scope (a table), key decisions, reference documents, and links, each only when present. The block goes just before a `<!-- FEATURE_PLACEHOLDER -->` marker when there is one, and at the end of the file otherwise.

Deactivating removes the block named by the first feature marker in the file and exits 0 whether or not there was one. When the project has no `CLAUDE.local.md`, it prints that there is nothing to remove and exits 0. The active feature of a project is read from the first `FEATURE` start marker in its `CLAUDE.local.md`. Only the given project is changed; the other projects in the feature's scope are not touched. These rules implement PRD-E, except for the gaps below.

Text outside the markers is not kept byte for byte today, so PRD-E does not fully hold. When the file has the `<!-- FEATURE_PLACEHOLDER -->` marker, which the default template has, activation writes the block followed by a blank line, but removing a block takes away only the line break after its end marker. Each activation therefore leaves one more blank line before the block, and deactivation leaves one more after it (QUES-G). Deactivation, and activation in a file without the placeholder, also trim trailing whitespace at the end of the file.

Two hand-edited marker cases are not handled (QUES-K). A start marker without its end marker is never removed, so activation adds a second block while the active-feature lookup still reports the old name. Deactivation finds a marker only when it is written with single spaces, while the active-feature lookup accepts any whitespace, so a marker can read as active yet not be removable by `deactivate`.

### DSGN-E — Removal

`remove` asks for confirmation unless `--force` is given; answering no prints "Cancelled." and exits 0. After confirmation it works in four steps, and a failure in one step stops the steps after it:

1. It deactivates the feature in the current project if it is active there.
2. It deletes the record. On a machine with only the old `initiatives/` folder this step fails today, after step 1 has already run (QUES-C).
3. It removes the feature's block from the `CLAUDE.local.md` of every other project in the project catalog (the list kept by `coworker project`) that has the block. Before changing each file it copies it into a backup folder `~/.coworker/backups/<timestamp>-feature-remove/` and prints that folder's name. The timestamp is to the second, so files backed up in the same second share a folder, and a sweep that crosses a second boundary leaves several folders.
4. It prints the documentation folders it kept.

This implements PRD-H and PRD-J. Activation and deactivation in the current project take no backup; PRD-J asks for one only in other projects.

### DSGN-F — The old "initiative" name

When `~/.coworker/features/` does not exist and `~/.coworker/initiatives/` does, every read and write uses the old folder. Old `INITIATIVE` markers are recognized when blocks are removed or replaced, and an old `INITIATIVE_PLACEHOLDER` is rewritten to the new spelling on the next activation. `coworker initiative` is a hidden command group that mirrors all eight subcommands and prints a deprecation notice on standard error. Two gaps break PRD-I today: a project whose only block uses the old marker shows no active feature (QUES-B), and `remove` fails half-way on a machine that has only the old folder (QUES-C). Any access to a record, including `list` and `show`, creates `~/.coworker/features/` when neither folder exists. If the old folder is restored after that, the new empty folder still wins and the old records are no longer seen (QUES-I).

### Sub-problem ownership (子问题归属)

| 子问题 | 归属 | 依据 |
|---|---|---|
| Whether activation should reach every project in scope, not only the current one; the code changes one project, and no decision records why | 人决定 | UNKNOWN |
| Whether to ship an automatic migration from the old folder | 人决定 | ARD-C; `config.py` mentions a migrate command that does not exist |
| Which command errors are intended to exit 0 | AI 查完人决定 | QUES-A |

## Testing Decisions

Behavior is covered by pytest at the command level and at the block-injection level. The cases are in the [test plan](../test-plan/feature-system-test-plan.md), which also lists the behaviors no test covers yet.

## Out of Scope

The project catalog, `coworker status`, and `coworker state-update` are specified in the [core CLI design](../../core-cli/design/core-cli-design.md).

## Further Notes

`create` scaffolds a `spec/` folder, while the spec standard this repository now follows names that document type `design/`. The scaffold is tracked as QUES-E.

## Alternatives Considered

A global "active feature" marker file was rejected: two projects could not have different features active, and the marker could disagree with the instruction file the AI actually reads. Writing the block into the committed `CLAUDE.md` was rejected because it would commit one person's working state for the whole team (ARD-B).

## Drawbacks

Because the block is the only record of activation, any tool that rewrites `CLAUDE.local.md` without understanding the markers can silently deactivate a feature. Fields without a command-line setter push users to edit YAML by hand.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| A stale block misleads the AI after a task switch | Activation removes every feature block before writing the new one (DSGN-D) |
| A name reaches outside the features directory | The name rule is checked on every file access (DSGN-A) |
| `remove` damages another project's notes | That project's file is backed up first (DSGN-E); restoring by label may bring back only some projects (QUES-J) |
| An `edit` with several options applies only some | Not mitigated today (QUES-D) |
| Blank lines pile up in `CLAUDE.local.md` with each activation | Not mitigated today (QUES-G) |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | A bad name already makes `create`, `edit`, `show`, `activate`, and `remove` exit 1, but with an uncaught Python traceback in place of a clear message; `start` prints a clear message but exits 0. Should every command print the message and exit 1, as PRD-A requires? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-B** | A project whose only block uses the old `INITIATIVE` marker shows no active feature in `list` and `status`, and `remove` does not deactivate it. Should the active-feature lookup accept both spellings? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-C** | On a machine with only `~/.coworker/initiatives/`, `remove` fails half-way, because it deletes the record from the new folder. The current project's block is already removed, the record survives in `initiatives/`, the other projects' blocks are not swept, and the command exits 1. The feature is still listed but is deactivated in this project only. Fix the path, or ship a migration? | Found in the code at `a0f4ce0`; no test covers it. | cicidi | no |
| **QUES-D** | `edit --add-decision` splits its value only at the first `\|`, so the rationale and decided-by parts stay glued into the decision text with their `\|` separators, the decided-by field is always empty, and the block shows `(by )` for every decision added this way. `edit --add-project` with a project already in scope returns before saving, discarding other options given in the same command. Fix both so PRD-F holds? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-E** | `create` scaffolds `spec/`; the spec standard uses `design/`. Change the scaffold? | Open. | cicidi | no |
| **QUES-F** | `start` always records the project under its folder name, because its catalog lookup reads a field that does not exist and the error is swallowed. Should it use the catalog name? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-G** | Each activation in a file with the placeholder marker adds one blank line outside the block, and deactivation adds one more (DSGN-D), so PRD-E fails. Should removal also consume the blank line after the block, as the adapter already does for its static block? | Found in the code at `a0f4ce0`; no test checks that the file is unchanged after activating and deactivating. | cicidi | no |
| **QUES-H** | A project's role is free text; `start` and `edit` store any value. Should the commands accept only `upstream`, `downstream`, and `peer`? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-I** | `list` and `show` create the empty folder `~/.coworker/features/` when no record folder exists, even for an invalid name, and that folder then wins over a later-restored `initiatives/` folder. Should reads stop creating the folder? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-J** | `remove` backs up each swept project in a per-second folder, and `coworker restore feature-remove` restores only the newest folder with that label, so a sweep that crosses a second boundary is restored only in part. Only the newest 20 folders per label are kept. Should the sweep back up all files in one folder? | Found in the code at `a0f4ce0`; until then, restore each printed backup folder by its full name. | cicidi | no |
| **QUES-K** | A start marker without its end marker is never removed, and `deactivate` misses a marker written with extra spaces (DSGN-D). Should both cases be handled? | Found in the code at `a0f4ce0`. | cicidi | no |

## Reversibility

Activation is undone by `deactivate`, or by activating another feature. A removed record cannot be recovered by the command; the documentation folders are kept, and other projects' instruction files can be restored with `coworker restore <folder>`, once for each backup folder name the command printed. `coworker restore feature-remove` restores only the newest such folder (QUES-J). The current project's `CLAUDE.local.md` is not backed up by activation, so an unwanted rewrite there is recovered from the user's own history only.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft as `initiative-system` (never committed) |
| 0.2 | 2026-11-24 | Renamed and rewritten from the code at `a0f4ce0`; the false migration claim removed; gaps recorded as QUES-A to QUES-F (ARD-A) |
| 0.3 | 2026-11-24 | Review fixes: DSGN-D no longer claims outside text is kept; QUES-A, QUES-C, QUES-D corrected; role is free text; missing command behavior added; removal steps spelled out; QUES-G to QUES-K added (ARD-D, ARD-E) |
