---
feature: core-cli
type: design
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Core CLI — Design

Requirements are in the [PRD](../prd/core-cli-prd.md). Decisions are in the [decision history](../decision-history/core-cli-decision-history.md). Behavior below was read from the code at commit `a0f4ce0`; where it does not meet a requirement, the gap is an Open Question.

## Problem Statement

Each AI coding tool keeps its own settings file in its own format: Claude Code in `settings.json` and `~/.claude.json`, Gemini CLI in `~/.gemini/settings.json`, OpenCode in `~/.config/opencode/config.json`. Keeping MCP servers and permissions consistent across them by hand drifts, and a tool that rewrites another tool's file can silently delete the user's own entries.

## Solution

One YAML configuration, global plus an optional project layer, is the source. `coworker sync` translates it into each tool's format through one adapter per tool. Each adapter merges into the existing file rather than replacing it, and remembers which entries it wrote, so it can later remove its own retired entries without touching the user's.

## User Stories

The user stories are in the [PRD](../prd/core-cli-prd.md#user-stories).

## Implementation Decisions

Settings writes are atomic (written to a temporary file, then renamed) and are skipped when the content would not change, so a repeated sync creates no new backup (ARD-B). Every command that overwrites a user-visible file first copies it under `~/.coworker/backups/` (ARD-C). There is no Cursor adapter.

## Design

### DSGN-A — `init`

Without a flag, `init` asks whether to initialize globally; answering no means project mode. `init --global` creates `~/.coworker/` and `~/.coworker/skills/` and writes `coworker.yaml` from the template only when it is missing. It detects nothing. This implements PRD-A.

`init --project` scans the current folder: the project name is the folder name, the repository comes from `git remote get-url origin`, the language and frameworks from `package.json`, `pyproject.toml`, `go.mod`, or `Cargo.toml` (first match wins), the AI tools from `~/.claude`, `~/.config/opencode`, `~/.gemini`, and `<project>/.cursor`, plus topic folders under `docs/` and links from the project catalog. It prints the result and asks for confirmation; declining writes nothing. It then writes `.coworker/coworker.yaml`, copies each `skills/*/SKILL.md` that has a name into `.claude/commands/` and `.opencode/instructions/` (skipping files already there), writes `CLAUDE.md` (see below), creates `docs/`, and writes `CLAUDE.local.md`. This implements PRD-B, with one gap: an existing `.coworker/coworker.yaml` is overwritten with no backup (QUES-B).

`CLAUDE.md` is written from the template when missing. When it exists and contains the `<!-- PROTECTED:CRITICAL-RULES -->` marker it is left alone; otherwise it is backed up with the label `init` and overwritten. When `CLAUDE.local.md` exists, only its `## Project Info` section is rewritten, with a backup if the content changed; when it is missing it is created, and `CLAUDE.local.md` and `docs/state/` are added to `.gitignore` if absent.

### DSGN-B — Configuration

The global file is `~/.coworker/coworker.yaml`; the project file is the nearest `.coworker/coworker.yaml` found by walking up from the current folder. Top-level fields are `version`, `scope`, `mcp` (servers, each with a name, command, arguments, environment, and an enabled flag), `skills` (name, path, description, enabled), `permissions` (allow and deny lists), and per-tool sections `claude`, `gemini`, and `opencode`. Unknown top-level keys are dropped.

The merge takes the global file as the base. A project MCP server is added, replacing a global server of the same name. A project skill is added only when its name is new, so the global skill wins a clash. Non-empty project allow and deny lists replace the global ones. The per-tool sections come from the global file only. This implements PRD-C, except that an invalid file ends the command with a Python traceback and exit status 1 (QUES-C).

### DSGN-C — `sync`

`sync [--tool claude|gemini|opencode|all] [--project]` runs the selected adapters, `all` by default, against the global targets or, with `--project`, the current folder's targets. The configuration used is always the merged one. Each adapter reports its actions; a failing adapter prints an error and the others still run. The command ends with "Done." or "Finished with errors" and exits 0 in both cases. `--global` is accepted and has no effect (QUES-F).

| Adapter | Files (global / `--project`) | What it writes |
|---|---|---|
| Claude Code | `~/.claude/settings.json`, `~/.claude.json`, `~/.claude/skills/` / the same under `<project>/.claude/` and `<project>/.mcp.json` | Permissions merged as a sorted union with the user's; MCP servers into `~/.claude.json` or `.mcp.json` (removed from `settings.json` if present); the Stop hook `coworker state-update` if absent; each enabled skill copied into `skills/<name>/` |
| Gemini CLI | `~/.gemini/settings.json` / `<project>/.gemini/settings.json` | The `gemini` section's keys, and MCP servers |
| OpenCode | `~/.config/opencode/config.json` / `<project>/.opencode/config.json` | The `opencode` section's keys, MCP servers in OpenCode's local-server shape, and a permission allowing `coworker *` in bash |

For every adapter, MCP servers the user wrote are kept, and a configured server replaces a same-named one. A server is removed only when walter-worker's record at `~/.coworker/mcp-managed.json` shows it wrote that server, the server is no longer configured, and the file still holds exactly what was written. With an empty `mcp` list nothing is pruned. Claude Code and Gemini writes are atomic and backed up under the label `json-sync` when the content changes. The OpenCode adapter writes in place with no backup (QUES-E). Skills removed from the configuration are never deleted from the tool, and a skill folder with subfolders is not copied correctly (QUES-J). These rules implement PRD-D; no adapter makes a network call, which implements PRD-E.

### DSGN-D — `status`

`status` prints a table of the global and project configuration files, with their paths and the number of MCP servers and skills in each. When a feature is active in the project (see the [feature system](../../feature-system/design/feature-system-design.md)), it also prints the feature's details, the files under `docs/features/<name>/`, the number of commits mentioning the feature since it was created, session and summary counts from the analytics database, recent topics, and the remaining work. It writes nothing. This implements PRD-F.

### DSGN-E — `project`

The catalog is `~/.coworker/project.yaml`; a missing file counts as empty. Each entry has a name, a local path, a repository, a team, an environment, upstream and downstream project names, knowledge pools, and references to GitHub, Slack, and Reddit. `add NAME` defaults the path to the current folder and fails on a duplicate name; `edit NAME` changes the path or repository and adds upstream, downstream, or knowledge-pool entries; `list`, `show`, and `remove` work by name. An unknown name in `show`, `edit`, or `remove` is an error with exit status 1. `project sync` writes the catalog, knowledge pools, references, and documentation layout into the current project's `CLAUDE.md` between `<!-- COWORKER:STATIC START -->` and `<!-- COWORKER:STATIC END -->`, replacing an earlier block or appending one, with no backup (QUES-K). This implements PRD-G.

### DSGN-F — `skill`

`skill list` prints the skills in the merged configuration. `skill new NAME` scaffolds `~/.coworker/skills/<name>/SKILL.md`, or `<project>/.coworker/skills/<name>/SKILL.md` with `--project`, and refuses to overwrite an existing file. Proposed skills wait in `~/.coworker/pending/skills/` as JSON; `skill pending` lists them, newest first. `skill approve ID` runs a safety check (a name of at least three characters, no shell metacharacters, no dangerous commands in the description, a source session) and, on success, promotes the skill to `~/.coworker/skills/<id>/` and to the Claude Code and OpenCode command folders when absent. A failed check marks the item rejected. `skill reject ID` marks it rejected. This implements PRD-H, except that a failed safety check is reported as "Not found" (QUES-D).

### DSGN-G — `upgrade`

`upgrade [--dry-run] [-y] [--force]` compares `~/.claude/CLAUDE.md`, section by section, with the current template. A section inside a protected span or containing a feature marker, a section identical to the template, a section the user only appended to, and a section the template does not have are all kept. A section where the user added lines and the template added none is a conflict; a section where both changed is overwritten; a template section with a new heading is appended. The command prints the plan, including up to five lines each conflict would lose. `--force` turns conflicts into overwrites. `--dry-run` stops after the plan. Without a terminal and without `-y` it refuses; otherwise it asks for confirmation. It then backs up the file under the label `upgrade`, merges, and verifies that every protected span is unchanged; a violation rolls back and exits 1. This implements PRD-I, except that a conflict combined with any overwrite or addition crashes the merge after the backup and before writing (QUES-A).

### DSGN-H — `restore`

Backups are folders named `<YYYYMMDD-HHMMSS>-<label>` under `~/.coworker/backups/`, each holding copies at their original absolute paths. At most twenty folders are kept per label; the `pristine` folder is never pruned. `restore BACKUP` accepts a path, a folder name, or a label, and a label picks the newest folder whose name ends with it. It lists up to ten files, asks for confirmation unless `-y` is given, and copies every file back. It does not back up the current files first and does not delete files absent from the backup. An unknown backup is an error with exit status 1. This implements PRD-J; the label match can pick a longer label (QUES-I).

### DSGN-I — `state-update`

`state-update [TASK] [-s SUMMARY]` walks up from the current folder to the first folder containing `.coworker/` or `CLAUDE.local.md`, and exits silently with status 0 if none is found. It writes `<root>/docs/state/state-<TASK>.md`, where TASK defaults to today's date. A new file gets a heading, a start time, a status line, and a `## Progress` section; an existing file gets a timestamped update with the summary. This implements PRD-K; the summary is ignored when the file is first created (QUES-H).

### Sub-problem ownership (子问题归属)

| 子问题 | 归属 | 依据 |
|---|---|---|
| Whether secrets in MCP environments should be expanded from the environment or `~/.coworker/.env` | 人决定 | QUES-G |
| Whether `sync` should delete skills removed from the configuration | 人决定 | QUES-J |
| Whether an adapter for Cursor is wanted | 人决定 | UNKNOWN; the 2026-11-04 draft claimed one, and none exists |

## Testing Decisions

Commands are tested through Click's test runner against a temporary home directory; adapters and the merge are tested directly. The cases are in the [test plan](../test-plan/core-cli-test-plan.md).

## Out of Scope

The feature commands, analytics, memory, the auto-worker, and the installer have their own specifications.

## Further Notes

`sync` exits 0 even when an adapter fails, on purpose: an install or hook that runs it must not stop because one tool's file is malformed. The failure is the last line printed.

## Alternatives Considered

Writing each tool's file from scratch was rejected because it deletes the user's own servers and permissions. Tracking ownership with markers inside JSON was rejected because JSON has no comments; a separate record of written entries is used instead (ARD-B).

## Drawbacks

The project layer cannot override per-tool settings or a global skill of the same name. Skills are copied, so an edited skill reaches a tool only on the next sync.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Sync deletes a user's MCP server | Only servers recorded as written, and still unchanged, are removed (DSGN-C) |
| Upgrade loses user lines | Conflicts are shown and kept unless `--force`; protected spans are verified after the merge (DSGN-G) |
| An overwrite cannot be undone | Backups before overwriting, and `restore` (DSGN-H); gaps in QUES-B, QUES-E, QUES-K |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | `upgrade` crashes when one section is a conflict and another is an overwrite or an addition, and `--force` was not given; the backup is taken and nothing is written. Fix the merge to keep conflicts? | Reproduced in an in-memory run on 2026-11-24; no test covers the mix. | cicidi | yes |
| **QUES-B** | `init --project` overwrites an existing `.coworker/coworker.yaml` with no backup. Back it up, or refuse? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-C** | An invalid `coworker.yaml` ends any command with a traceback. Print a one-line error naming the file? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-D** | `skill approve` reports a failed safety check as "Not found" and exits 0. Report the real reason? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-E** | The OpenCode adapter writes its file in place, twice, with no backup. Make it atomic and backed up like the others? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-F** | `sync --global` has no effect. Remove the flag, or make it skip the project layer? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-G** | MCP environment values are copied literally, so a secret written in `coworker.yaml` lands in every tool's file. Expand references instead? | Not implemented; the 2026-11-04 draft claimed it was. | cicidi | no |
| **QUES-H** | `state-update -s` is ignored when the state file is first created. Write the summary then too? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-I** | A `restore` label also matches longer labels ending in it, so `sync` can pick a `json-sync` backup. Match the label exactly? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-J** | `sync` never removes a skill dropped from the configuration, and does not copy a skill's subfolders. Fix both? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-K** | `project sync` rewrites `CLAUDE.md` with no backup. Back it up? | Found in the code at `a0f4ce0`. | cicidi | no |

## Reversibility

Files backed up before a change can be restored with `coworker restore <label>`: `init` for `init`, `json-sync` for Claude Code and Gemini settings, `upgrade` for the global `CLAUDE.md`. Writes without a backup (QUES-B, QUES-E, QUES-K) are not reversible by the tool. A sync can also be undone by removing the server from `coworker.yaml` and syncing again, which prunes it.

## Terms

| Term | Meaning |
|---|---|
| Adapter | The part of `sync` that translates the configuration into one tool's settings format |
| MCP server | An external tool server an AI tool connects to through the Model Context Protocol |
| Protected span | Text between `<!-- PROTECTED -->` and `<!-- END PROTECTED -->` (or the START/END spelling) that `upgrade` must never change |
| Backup label | The word at the end of a backup folder's name, naming the command that took it |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0` with the 13 required sections; gaps recorded as QUES-A to QUES-K (ARD-A, ARD-D) |
