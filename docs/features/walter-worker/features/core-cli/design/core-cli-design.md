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

Settings writes are atomic (written to a temporary file, then renamed) and are skipped when the content would not change, so a repeated sync creates no new backup (ARD-B). Decision ARD-C says that every command that overwrites a user-visible file first copies it under `~/.coworker/backups/`. The code at `a0f4ce0` does this for most writes but not all of them. These writes take no backup: an existing project `coworker.yaml` overwritten by `init --project` (QUES-B), the OpenCode settings file (QUES-E), the project `CLAUDE.md` rewritten by `project sync` (QUES-K, QUES-S), the project catalog `~/.coworker/project.yaml` (QUES-T), and the `.gitignore` lines that `init` appends. There is no Cursor adapter.

## Design

### DSGN-A — `init`

Without a flag, `init` asks whether to initialize globally; answering no means project mode. `init --global` creates `~/.coworker/` and `~/.coworker/skills/` and writes `coworker.yaml` from the template only when it is missing. It detects nothing. This implements PRD-A.

`init --project` scans the current folder: the project name is the folder name, the repository comes from `git remote get-url origin`, the language and frameworks from `package.json`, `pyproject.toml`, `go.mod`, or `Cargo.toml` (first match wins), the AI tools from `~/.claude`, `~/.config/opencode`, `~/.gemini`, and `<project>/.cursor`, plus topic folders under `docs/` and links from the project catalog. It prints the result and asks for confirmation; declining writes nothing. It then writes `.coworker/coworker.yaml`, copies each `skills/*/SKILL.md` that has a name into `.claude/commands/` and `.opencode/instructions/` (skipping files already there), writes `CLAUDE.md` (see below), creates `docs/`, and writes `CLAUDE.local.md`. This implements PRD-B, with one gap: an existing `.coworker/coworker.yaml` is overwritten with no backup (QUES-B). When `init --project` runs in the home folder itself, that file is the global file `~/.coworker/coworker.yaml`, so the global configuration is replaced by the project template with no backup.

`CLAUDE.md` is written from the template when missing. When it exists and contains the `<!-- PROTECTED:CRITICAL-RULES -->` marker it is left alone; otherwise it is backed up with the label `init` and overwritten. When `CLAUDE.local.md` exists, only its `## Project Info` section is rewritten, with a backup if the content changed; when it is missing it is created, and `CLAUDE.local.md` and `docs/state/` are added to `.gitignore` if absent. `init` then prints that it added both entries, even when both were already present and nothing was added.

### DSGN-B — Configuration

The global file is `~/.coworker/coworker.yaml`; the project file is the nearest `.coworker/coworker.yaml` found by walking up from the current folder. The walk checks every parent folder except the filesystem root, so from any folder under the home folder it reaches the home folder and finds the global file itself. In a folder under the home folder with no project file of its own, the global file therefore also counts as the project file: it is merged with itself, which changes nothing, and `status` reports a project configuration as found.

Top-level fields are `version`, `scope`, `mcp` (servers, each with a name, command, arguments, environment, and an enabled flag), `skills` (name, path, description, enabled), `permissions` (allow and deny lists), and per-tool sections. The `claude` section holds `effortLevel`, `skipDangerousModePermissionPrompt`, and an `extra` map; the `gemini` and `opencode` sections hold only an `extra` map (a set of key-value pairs). Unknown keys are dropped when a file is read, at the top level and inside these sections, so a key such as `gemini: {theme: dark}` is silently ignored (QUES-P).

The merge takes the global file as the base. A project MCP server is added, replacing a global server of the same name. A project skill is added only when its name is new, so the global skill wins a clash. Non-empty project allow and deny lists replace the global ones. The per-tool sections come from the global file only. This implements PRD-C, except that an invalid file ends the command with a Python traceback and exit status 1 (QUES-C).

### DSGN-C — `sync`

`sync [--tool claude|gemini|opencode|all] [--project]` runs the selected adapters, `all` by default, against the global targets or, with `--project`, the current folder's targets. The configuration used is always the merged one. Each adapter reports its actions; a failing adapter prints an error and the others still run. The command ends with "Done." or "Finished with errors" and exits 0 in both cases. `--global` is accepted and has no effect (QUES-F).

| Adapter | Files (global / `--project`) | What it writes |
|---|---|---|
| Claude Code | `~/.claude/settings.json`, `~/.claude.json`, `~/.claude/skills/` / the same under `<project>/.claude/` and `<project>/.mcp.json` | Permissions merged as a sorted union with the user's; MCP servers into `~/.claude.json` or `.mcp.json`; it removes the `coworker state-update` Stop hook an earlier release added (ARD-G); each enabled skill copied into `skills/<name>/`. Any `mcpServers` block in `settings.json` is deleted, even when the `mcp` list is empty, and its servers are not moved to the other file (QUES-O) |
| Gemini CLI | `~/.gemini/settings.json` / `<project>/.gemini/settings.json` | The keys of the `gemini.extra` map, and MCP servers |
| OpenCode | `~/.config/opencode/config.json` / `<project>/.opencode/config.json` | The keys of the `opencode.extra` map, MCP servers in OpenCode's local-server shape, and a permission allowing `coworker *` in bash |

No adapter writes the `claude` section: `effortLevel`, `skipDangerousModePermissionPrompt`, and `claude.extra` have no effect, although the global template ships the first two (QUES-P).

For every adapter, MCP servers the user wrote are kept, and a configured server replaces a same-named one. A server is removed only when walter-worker's record at `~/.coworker/mcp-managed.json` shows it wrote that server, the server is no longer configured, and the file still holds exactly what was written. With an empty `mcp` list nothing is pruned. Claude Code and Gemini writes are atomic and backed up under the label `json-sync` when the content changes. The OpenCode adapter writes in place with no backup (QUES-E). Permissions are only ever added: `sync` never removes a permission, even one it added earlier that the configuration no longer lists. It adds no hook, and it removes the `coworker state-update` Stop hook while keeping other hooks in the same group (ARD-G).

Skills removed from the configuration are never deleted from the tool. A skill folder that contains a subfolder makes the Claude Code adapter fail with an "Is a directory" error: the adapter is reported as failed, the files listed after the subfolder (possibly including `SKILL.md`) are not copied, and the skills after it in the configuration are not installed (QUES-J). With `--project`, the files are written in the current folder even when the project file was found in a parent folder, and every relative skill path is resolved against the current folder. Global skill paths are relative to `~/.coworker/`, so under `--project` they are reported as "skill path not found" (QUES-U). These rules implement PRD-D, except for QUES-J, QUES-O, and QUES-U; no adapter makes a network call, which implements PRD-E.

### DSGN-D — `status`

`status` prints a table of the global and project configuration files, with their paths and the number of MCP servers and skills in each. When a feature is active in the project (see the [feature system](../../feature-system/design/feature-system-design.md)), it also prints the feature's details, the files under `docs/features/<name>/`, the number of commits mentioning the feature since it was created, session and summary counts from the analytics database, recent topics, and the remaining work. Because the project-file search reaches the home folder (DSGN-B), the project row says "found" in every folder under the home folder. It writes no file; the one side effect is that reading an active feature may create the empty folder `~/.coworker/features/`. This implements PRD-F.

### DSGN-E — `project`

The catalog is `~/.coworker/project.yaml`; a missing file counts as empty. Each entry has a name, a local path, a repository, a team, an environment, upstream and downstream project names, knowledge pools, and references to GitHub, Slack, and Reddit. `add NAME` defaults the path to the current folder and fails on a duplicate name; `edit NAME` changes the path or repository and adds upstream, downstream, or knowledge-pool entries; `list`, `show`, and `remove` work by name. An unknown name in `show`, `edit`, or `remove` is an error with exit status 1. `add`, `edit`, and `remove` rewrite `~/.coworker/project.yaml` from the parsed catalog with no backup, and the rewrite drops comments and any key the catalog format does not define (QUES-T).

`project sync` writes the catalog, knowledge pools, references, and documentation layout into the current project's `CLAUDE.md` between `<!-- COWORKER:STATIC START -->` and `<!-- COWORKER:STATIC END -->`, replacing an earlier block or appending one, with no backup (QUES-K). When `CLAUDE.md` holds the START marker but not the END marker, everything from START to the end of the file is replaced by the new block, so any text the user wrote after START is deleted (QUES-S). This implements PRD-G, except for QUES-S and QUES-T.

### DSGN-F — `skill`

`skill list` prints the skills in the merged configuration. `skill new NAME` scaffolds `~/.coworker/skills/<name>/SKILL.md`, or `<project>/.coworker/skills/<name>/SKILL.md` with `--project`, and refuses to overwrite an existing file. Proposed skills wait in `~/.coworker/pending/skills/` as JSON files, each carrying a status such as pending, approved, or rejected. `skill pending` lists every item in that folder whatever its status, ordered by file modification time, newest first, so approving or rejecting an item moves it to the top.

`skill pending --approve-all` runs the approval below on every item whose status is pending and prints how many it approved; the count also includes items that failed the safety check and were rejected (QUES-R). `--type TYPE` limits `--approve-all` to items whose `type` field equals TYPE, but staged items have no `type` field, so with `--type` nothing is approved (QUES-R).

`skill approve ID` runs a safety check (a name of at least three characters, no shell metacharacters, no dangerous commands in the description, a source session) and, on success, promotes the skill. The promoted folder is `~/.coworker/skills/<folder>/`, where the folder name is the skill's name in lower case with spaces turned into dashes. It receives a `SKILL.md` stub when none is there and a `usage.json` record of where the skill came from, and the skill is copied to the Claude Code and OpenCode command folders when absent. The check does not reject `/` or `..` in a name, so such a name can place the promoted folder outside `~/.coworker/skills/` (QUES-W).

A failed check marks the item rejected. `skill reject ID` marks it rejected. `approve` does not look at the item's current status, so a rejected item is promoted if a later `approve` passes the check (QUES-Q). For both commands an unknown ID prints "Not found" and exits 0. This implements PRD-H, except for QUES-Q, QUES-R, QUES-W, and the fact that a failed safety check is also reported as "Not found" (QUES-D).

### DSGN-G — `upgrade`

`upgrade [--dry-run] [-y] [--force]` compares `~/.claude/CLAUDE.md`, section by section (a section is a heading and the text under it), with the current template. These sections are kept: a section inside a protected span or containing a `<!-- FEATURE:` or `<!-- INITIATIVE:` marker, a section identical to the template, a section the user only appended to, a section whose template text is still a placeholder such as `_(none configured)_`, and a section the template does not have. Any other differing section is decided against the merge base `~/.coworker/claude-md-base.md`, the template as last written (ARD-H). Only the template changed means overwrite, only the user changed means keep, and both changed means a conflict. Without a base, a section where the user added lines and the template added none is a conflict and is kept, and any other differing section is overwritten. A template section with a new heading is appended.

The command prints the plan. An overwrite made without a base lists up to five of the lines it replaces; a conflict lists up to five lines it would lose. `--force` turns conflicts into overwrites. `--dry-run` stops after the plan. With no `~/.claude/CLAUDE.md` it prints a hint to run the installer and exits 0. Without a terminal and without `-y` it prints a refusal and exits 0. When no section would be overwritten or appended it prints "Already up to date"; otherwise it asks for confirmation.

It then backs up the file under the label `upgrade`, merges in memory, and checks every protected span, pairing spans by order and comparing their text (QUES-N). On a violation the command stops without writing the file and exits 1. After a write, or when nothing needed writing, it stores the template as the new base; a conflicted section keeps its old base, so it is reported again. This implements PRD-I.

### DSGN-H — `restore`

Backups are folders named `<YYYYMMDD-HHMMSS>-<label>` under `~/.coworker/backups/`, each holding copies at their original absolute paths. At most twenty folders are kept per label; the `pristine` folder is never pruned. `restore BACKUP` accepts a path, a folder name, or a label, and a label picks the newest folder whose name ends with it. It lists up to ten files, asks for confirmation unless `-y` is given, and copies every file back. It does not back up the current files first and does not delete files absent from the backup. An unknown backup, or a backup folder that holds no files, is an error with exit status 1. Besides folders under `~/.coworker/backups/`, `restore` accepts any existing directory given as a path, and copies each file in it to the absolute path that mirrors its place in that directory (QUES-V). This implements PRD-J; the label match can pick a longer label (QUES-I).

### DSGN-I — `state-update`

`state-update [TASK] [-s SUMMARY]` walks up from the current folder to the first folder containing a `.coworker/` folder or a `CLAUDE.local.md` file, and exits silently with status 0 if none is found. It writes `<root>/docs/state/state-<TASK>.md`, where TASK defaults to today's date. A new file gets a heading, a start time, a status line, and a `## Progress` section; an existing file gets a timestamped update with the summary.

Once `~/.coworker/` exists (`init --global` creates it), the walk from any folder under the home folder stops at the home folder at the latest. A repository that walter-worker does not manage therefore gets its note written to `~/docs/state/state-<date>.md` when someone runs the command there by hand (QUES-L). Since ARD-G, no Stop hook runs it. PRD-K is therefore not met: it requires doing nothing outside a managed project. The summary is also ignored when the file is first created (QUES-H).

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
| Sync deletes a user's MCP server | Only servers recorded as written, and still unchanged, are removed (DSGN-C). Not mitigated for a `mcpServers` block in Claude Code's `settings.json`, which is always deleted (QUES-O) |
| Upgrade loses user lines | Conflicts are shown and kept unless `--force`. With a merge base, a section both sides changed is a conflict; without one, the plan lists the lines replaced (ARD-H). Protected spans are checked after the merge (DSGN-G) |
| An overwrite cannot be undone | Backups before overwriting, and `restore` (DSGN-H); gaps in QUES-B, QUES-E, QUES-K, QUES-S, QUES-T |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | `upgrade` crashed, before PR #20, when one section is a conflict and another is an overwrite or an addition, and `--force` was not given; the backup is taken and nothing is written. Fix the merge to keep conflicts? | Fixed in PR #20 (`8e3b48c`); see `test_upgrade_conflict_beside_overwrite_does_not_crash`. | cicidi | no |
| **QUES-B** | `init --project` overwrites an existing `.coworker/coworker.yaml` with no backup. Back it up, or refuse? | Found in the code at `a0f4ce0`. Run in the home folder, it overwrites the global `~/.coworker/coworker.yaml` the same way (`../raw/review/2026-11-24-spec-review-core-cli-gaps.md`). | cicidi | yes |
| **QUES-C** | An invalid `coworker.yaml` ends any command with a traceback. Print a one-line error naming the file? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-D** | `skill approve` reports a failed safety check as "Not found" and exits 0. Report the real reason? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-E** | The OpenCode adapter writes its file in place, twice, with no backup. Make it atomic and backed up like the others? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-F** | `sync --global` has no effect. Remove the flag, or make it skip the project layer? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-G** | MCP environment values are copied literally, so a secret written in `coworker.yaml` lands in every tool's file. Expand references instead? | Not implemented; the 2026-11-04 draft claimed it was. | cicidi | no |
| **QUES-H** | `state-update -s` is ignored when the state file is first created. Write the summary then too? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-I** | A `restore` label also matches longer labels ending in it, so `sync` can pick a `json-sync` backup. Match the label exactly? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-J** | `sync` never removes a skill dropped from the configuration. A skill folder with a subfolder makes the Claude Code adapter fail with "Is a directory", so later files and later skills are not installed. Fix both? | Found in the code at `a0f4ce0`; the failure was reproduced by the 2026-11-24 review (I2). | cicidi | no |
| **QUES-K** | `project sync` rewrites `CLAUDE.md` with no backup. Back it up? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-L** | `state-update` treats the home folder as a managed project whenever `~/.coworker/` exists, so it writes `~/docs/state/` from any unmanaged repository under the home folder. Exclude the home folder, or require `.coworker/coworker.yaml`? | Reproduced by the 2026-11-24 review (C1). The existing test sets the home folder to a folder without `.coworker/`, so it does not catch this. Since PR #19 (`b03f596`, ARD-G) no hook runs it, so only a manual run writes there. | cicidi | no |
| **QUES-M** | Before PR #21, `upgrade` overwrote a section that both the user and the template changed, discarding the user's lines without listing them. This contradicts PRD-I. List them and keep the section as a conflict, or change the requirement? | Reproduced by the 2026-11-24 review (C2). Fixed in PR #21 (`f917bbf`) by a three-way merge (ARD-H). Without a base, the section is still overwritten, but its lines are listed first. | cicidi | no |
| **QUES-N** | Before PR #20, the protected-span check compared spans by line number, so a change in line count above an untouched span is reported as a violation and `upgrade` exits 1. Compare span text instead? | Reproduced by the 2026-11-24 review (I1); fixed in PR #20 (`8e3b48c`). | cicidi | no |
| **QUES-O** | `sync` deletes a `mcpServers` block from Claude Code's `settings.json` and does not move its servers to `~/.claude.json`. Migrate them, or keep the block? | Reproduced by the 2026-11-24 review (I3). A `json-sync` backup is taken, but the action list does not mention the removal. | cicidi | yes |
| **QUES-P** | Keys in the `gemini` and `opencode` sections outside `extra` are dropped, and the `claude` section is never written to any file. Accept these keys, or remove the `claude` section from the template? | Reproduced by the 2026-11-24 review (I4). | cicidi | no |
| **QUES-Q** | `skill approve` promotes an item that was rejected earlier. This contradicts PRD-H. Refuse to approve a rejected item? | Reproduced by the 2026-11-24 review (I5). | cicidi | no |
| **QUES-R** | `skill pending --approve-all` counts items that failed the safety check as approved, and `--type` filters on a field staged items never have. Count only promotions, and remove or fix `--type`? | Found by the 2026-11-24 review (I6) and confirmed in the code at `a0f4ce0`. | cicidi | no |
| **QUES-S** | `project sync` deletes everything after a START marker that has no END marker, with no backup. Refuse, or stop at the next heading? | Reproduced by the 2026-11-24 review (I7). The test `test_replace_or_append_truncated_block_appends_after_start` pins today's behavior. | cicidi | yes |
| **QUES-T** | `project add`, `edit`, and `remove` rewrite `~/.coworker/project.yaml` with no backup, dropping comments and unknown keys. Back it up and keep them? | Found by the 2026-11-24 review (W2) and confirmed in the code at `a0f4ce0`. | cicidi | yes |
| **QUES-U** | `sync --project` resolves global skill paths against the project folder, so they are not found. Resolve each skill against the file that declared it? | Found by the 2026-11-24 review (W4) and confirmed in the code at `a0f4ce0`. | cicidi | no |
| **QUES-V** | `restore` accepts any directory and copies its files onto the mirrored absolute paths. Restrict it to `~/.coworker/backups/`? | Found by the 2026-11-24 review (W5) and confirmed in the code at `a0f4ce0`. | cicidi | no |
| **QUES-W** | The safety check allows `/` and `..` in a skill name, so promotion can write outside `~/.coworker/skills/`. Reject them? | Found by the 2026-11-24 review (minor) and confirmed by reading the code at `a0f4ce0`; not reproduced. | cicidi | no |

## Reversibility

Files backed up before a change can be restored with `coworker restore <label>`: `init` for `init`, `json-sync` for Claude Code and Gemini settings, `upgrade` for the global `CLAUDE.md`. Writes without a backup (QUES-B, QUES-E, QUES-K, QUES-S, QUES-T, and the `.gitignore` lines `init` appends) are not reversible by the tool. Removing a server from `coworker.yaml` and syncing again prunes that server only while at least one server stays configured; with an empty `mcp` list nothing is pruned. Permissions that `sync` adds are never removed by a later sync, so they must be removed by hand or restored from a backup. A `mcpServers` block that `sync` deletes from `settings.json` comes back only from a `json-sync` backup (QUES-O).

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
| 0.3 | 2026-11-24 | Review fixes: false claims corrected (backups, rollback, per-tool sections, project-file search, reversibility); exit statuses and `skill pending` options added; gaps recorded as QUES-L to QUES-W (ARD-D, ARD-F) |
| 0.4 | 2026-11-24 | QUES-A, QUES-M, and QUES-N answered by PRs #20 and #21; QUES-L not blocking after PR #19 (ARD-G, ARD-H) |
