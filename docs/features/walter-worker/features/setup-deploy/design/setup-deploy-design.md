---
feature: setup-deploy
type: design
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Setup and Deploy — Design

Requirements are in the [PRD](../prd/setup-deploy-prd.md). Decisions and their reasons are in the [decision history](../decision-history/setup-deploy-decision-history.md). Behavior below was read from the scripts at commit `a0f4ce0`.

## Problem Statement

Copying hooks and skills onto a machine by hand drifts from the source: files go stale, renamed skills leave old copies behind, and nobody can say afterwards which files belong to walter-worker. Earlier versions of the installer made this worse in two ways. They wrote the same skill to several places, so it showed up twice in a tool's menu. They also recorded whole directories as their own, so uninstall deleted files that belonged to the user.

## Solution

Three bash scripts own the machine-side lifecycle. `install.sh` writes files and records each written path by name in the install manifest. `update.sh` refreshes the code and replays the install with the answers recorded last time. `uninstall.sh` reverses the manifest. Because the manifest names exactly what was written, every run can remove what it wrote earlier and no longer produces, and uninstall can remove exactly the installed files.

## User Stories

The user stories are in the [PRD](../prd/setup-deploy-prd.md#user-stories). This design adds no new ones.

## Implementation Decisions

The skill source of truth is a the-super-lab checkout. The installer runs `git pull --ff-only` on it and copies skills from it, but never writes files into it (ARD-B). Claude Code and Cursor get a directory copy of each skill, so files that sit next to `SKILL.md` travel with it. OpenCode gets a symlink to the source directory instead. The manifest claims paths by name, not by directory (ARD-A). A the-super-lab skill is deployed as a skill only, never also as a Claude Code command (ARD-C).

## Design

### DSGN-A — Install modes and destinations

The installer accepts `--global`, `--project <path>`, `--skills "<names>"` (a space-separated selection that skips the skill question, used by update), and `--help`. Any other argument prints an error and exits with status 1. Without `--global` or `--project` it asks which mode to use; global is the default answer. The skill source can be moved with the `THE_SUPER_LAB_DIR` environment variable; the default is `~/project/the-super-lab`.

Global mode writes Claude Code commands to `~/.claude/commands` and OpenCode instructions to `~/.opencode/instructions`. Project mode writes those two to `<path>/.claude/commands` and `<path>/.opencode/instructions`. It also symlinks `<path>/AGENTS.md` to `<path>/CLAUDE.md` when that file exists, and appends eight entries (such as `CLAUDE.local.md`, `.env`, and the state directory) to `<path>/.gitignore`. Neither change is recorded in the manifest. Project mode still writes everything that is global: the CLAUDE.md check, the snapshot, the hooks, and the the-super-lab skill mirrors, because those tools load personal skills only from the home directory. This clause implements PRD-A.

### DSGN-B — Pristine snapshot and the global CLAUDE.md

On the first install on a machine, before any other change, the installer copies `~/.claude/settings.json` and `~/.claude/CLAUDE.md` into `~/.coworker/backups/pristine/`. It writes the path of each file that did not exist into `absent.txt`, and it writes a `.taken` marker file so the snapshot is never taken again. `uninstall.sh --restore-pristine` copies the two files back and deletes each path listed in `absent.txt`, because for a fresh machine the pristine state of that file is "absent". The global `CLAUDE.md` is created from the template only when it is missing. The manifest claims it only when this run created it. These rules implement PRD-B and PRD-C.

### DSGN-C — Skill deployment

The installer deploys skills from two sources in different forms.

| Source | Claude Code | Cursor | OpenCode |
|---|---|---|---|
| the-super-lab `skills/` | `~/.claude/skills/<name>/` (directory copy) | `~/.cursor/skills/<name>/` (directory copy) | `~/.config/opencode/skills/the-super-lab/<name>` (symlink) |
| the-super-lab `personal-skills/` | same as above | same as above | `~/.config/opencode/skills/the-super-lab-personal/<name>` (symlink) |
| walter-worker bundle `skills/` | `~/.claude/commands/<name>.md`, only when selected | not deployed | `~/.config/opencode/skills/walter-worker/` (a copy of the whole bundle `skills/` directory, made on every run) |

In addition, every command in the Claude Code commands directory, including commands the user wrote, is mirrored as a symlink into `~/.opencode/instructions/`, and dangling symlinks there are deleted. The script's own comment notes that current OpenCode does not read that directory. Why the mirror is still written is UNKNOWN.

A "directory copy" copies the files at the top level of the skill directory only; subdirectories such as `tests/` stay behind, and a file deleted from the source stays in the copy. A real directory found where the OpenCode symlink should go is deleted and replaced by the symlink.

The the-super-lab skills are deployed on every run, whatever the user answered to the skill question. Only bundle skills are offered in that question, so a the-super-lab skill never also becomes a command (ARD-C). A command copy of a the-super-lab skill that an earlier release wrote is removed while it is still identical to its source; a copy that differs is kept and reported. If a destination file is the same file as its source, which happens when the destination directory is a symlink back into the-super-lab, the copy is skipped instead of failing the install. The `init` skill is always installed as a command. These rules implement PRD-D and PRD-E.

### DSGN-D — Hook registration

The installer adds seven hook commands to `~/.claude/settings.json`: four analytics scripts under `~/.coworker/analytics/hooks/` (prompt submitted, before a tool runs, after a tool runs, session stop), the correction detector on prompt submit, and `coworker memory capture` and `coworker memory close` on stop. A hook is added only when no existing entry for that event has the same command string. Entries the installer did not add are never changed or removed. When the OpenCode analytics plugin directory exists in the checkout, the installer also registers it in `~/.config/opencode/config.json`; when it does not exist, nothing is registered. This implements PRD-F. A known gap is tracked as QUES-A.

### DSGN-E — Install manifest

The last step writes `~/.coworker/install-manifest.json` with `schema_version: 2`. There is one manifest per machine, whichever mode wrote it. It holds the install mode, the project path, a list of claimed files, the walter-worker hook commands, and a list of owned directories.

The claimed files are, by full path: the selected commands and their OpenCode mirrors, every file found in the hooks directory, every file found under each the-super-lab skill's Claude Code and Cursor destination, the OpenCode symlinks, and the global `CLAUDE.md` when this run created it. The owned directories are `~/.coworker` and `~/.config/opencode/skills/walter-worker`; uninstall treats them specially (DSGN-G). The list does not match PRD-G exactly: some written paths are not claimed and some claimed paths were not written by this run, which is tracked as QUES-G.

Before writing, the installer compares the new list with the previous manifest. A path the previous manifest claimed, that still exists, and that this run did not claim is removed, and any directory that removal empties is removed too, but never a root such as `~/.claude/skills` itself. When the user answers "None" to the skill question, previously claimed paths under `~/.claude/commands/` are carried forward instead of removed, because "install nothing new" does not mean "delete what I have"; project-mode commands and OpenCode mirrors are not carried (QUES-I).

Two consequences of the comparison break PRD-H today. A second run deletes the global `CLAUDE.md` that the first run created, because only the creating run claims it (QUES-C). A project-mode run prunes the paths the global install claimed, because both share one manifest (QUES-F). These rules implement PRD-G and PRD-H, except where those questions record a conflict.

### DSGN-F — Update

`update.sh` fetches the default branch of the walter-worker checkout from `upstream` when that remote exists and from `origin` otherwise, and merges it. It reads the install mode and the previously selected command names from the manifest, then runs `install.sh` with `--skills <names>`, which skips the skill question. It then offers to pull the-super-lab; the user may decline. When the manifest records no commands, `--skills` is not passed and the installer asks the skill question again. This implements PRD-I. Declining the the-super-lab pull currently has no effect, because the installer already ran `git pull --ff-only` on the-super-lab in its step 3 before the question is asked (QUES-H).

### DSGN-G — Uninstall

`uninstall.sh` exits with status 1 when there is no manifest, and stops unless the user answers `y`. It copies `settings.json` to a backup, then runs four passes. First it removes each claimed file; when the manifest has no `schema_version` this pass is skipped and a message says nothing was removed. Second it strips walter-worker's hook commands from `settings.json`, including one added after the manifest was written. Third it empties each owned directory: every entry of `~/.coworker` except `analytics/` and `backups/` is deleted, which includes `.env`, `coworker.yaml`, and the memory graph. Fourth it removes the directories its removals emptied.

The second and third passes run even for a manifest without `schema_version`. So today uninstall does not meet PRD-J in two ways: it deletes user data in `~/.coworker` that no manifest claims (QUES-D), and its refusal of an old manifest protects only the file list (QUES-E). This clause is meant to implement PRD-J.

### DSGN-H — Optional dependencies

A failed `git pull` of the-super-lab prints a warning and the install continues with the checkout as it is. When the `coworker` command is present, the installer runs `coworker sync`, which writes MCP server settings (MCP, the Model Context Protocol, is how AI tools connect to external tool servers) into each tool's config and registers the `coworker state-update` Stop hook. When the command is missing, the installer prints the `pipx install` command to run and continues. Several other steps also warn and continue on failure, and the install still exits with status 0: writing hooks, registering the OpenCode plugin, creating the analytics database, running `coworker sync`, and writing the manifest. This implements PRD-K.

### Sub-problem ownership (子问题归属)

| 子问题 | 归属 | 依据 |
|---|---|---|
| Which paths each tool loads skills from | AI 查 | ARD-B; Cursor and OpenCode layout verified on the author's machine, 2026-11-23 |
| Whether Cursor and OpenCode should get hooks | 人决定 | QUES-B |
| Whether a hand-joined compound hook counts as present | AI 查完人决定 | QUES-A |
| Behavior on macOS bash 3.2 | AI 查 | UNKNOWN; the scripts avoid associative arrays for it, but no CI job runs macOS |

## Testing Decisions

Every requirement is covered by a bats test that runs the real script against a temporary home directory with git and the `coworker` command mocked. The cases and their order are in the [test plan](../test-plan/setup-deploy-test-plan.md).

## Out of Scope

Installing the Python package, Cursor and OpenCode hooks, tmux presentation, and PyPI packaging are out of scope, as stated in the [PRD](../prd/setup-deploy-prd.md#out-of-scope).

## Further Notes

`install.sh` embeds Python inside double-quoted bash strings. A double quote, a backtick, or a dollar-parenthesis inside those blocks ends or rewrites the Python silently; an earlier comment containing backticks pasted CLI usage text into the code and stopped hooks from being written while the installer still reported success. The rule is to describe such characters in words.

## Alternatives Considered

Symlinking every Claude Code and Cursor skill to the source was rejected, because a directory copy keeps working when the source checkout moves and lets the manifest list each file. Recording whole directories in the manifest was rejected, because uninstall then deleted the user's own files (ARD-A). Keeping the-super-lab skills selectable as commands was rejected, because each selected skill appeared twice in the menu (ARD-C).

## Drawbacks

Directory copies go stale until the next install or update; editing a skill in the-super-lab does not reach Claude Code or Cursor until then. The installer's Python lives inside bash strings, which is fragile (see Further Notes).

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| A hook is registered twice and runs twice | The exact-match check in DSGN-D; QUES-A covers the compound case |
| Uninstall deletes a user file | Files are claimed by name; but the owned-directory pass still deletes user data in `~/.coworker` (QUES-D, open) |
| A re-install deletes a file the first install created | Not mitigated today (QUES-C, open) |
| An edited command copy is lost when retired | Only byte-identical copies are removed (DSGN-C) |
| The prune removes a skill the user still wants | Only paths an earlier run claimed are pruned, and "None" carries commands forward (DSGN-E) |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | Should a hook command that appears as one step of a hand-joined compound hook (such as `coworker memory capture; coworker memory close`) count as already present? | Yes, proposed in walter-worker PR #16, not yet merged. Until then each install adds the two commands back as separate hooks. | cicidi | no |
| **QUES-B** | Should Cursor and OpenCode receive hooks too? | Deferred by the owner on 2026-11-23. | cicidi | no |
| **QUES-C** | A second install deletes the global `CLAUDE.md` that the first install created, losing any edits. Fix the code (claim the file whenever an earlier manifest claimed it), or change PRD-H? | Reproduced by the 2026-11-24 review. Code fix proposed, not made. | cicidi | yes |
| **QUES-D** | Uninstall deletes everything in `~/.coworker` except `analytics/` and `backups/`, including API keys in `.env`, `coworker.yaml`, and the memory graph. Should the owned-directory pass be removed or narrowed so PRD-J holds? | Reproduced by the 2026-11-24 review. Do not run `uninstall.sh` on a machine with data in `~/.coworker` until this is fixed. | cicidi | yes |
| **QUES-E** | For a manifest without `schema_version`, uninstall skips the file list but still strips hooks and empties `~/.coworker`. Should it stop entirely? | Reproduced by the 2026-11-24 review; the bats test checks only the file list. | cicidi | yes |
| **QUES-F** | One manifest serves both modes, so a project-mode install prunes the global install's commands and mirrors. Should each mode keep its own manifest? | Reproduced by the 2026-11-24 review. | cicidi | yes |
| **QUES-G** | The claim list misses written paths (`init.md`, the AGENTS.md symlink, `.gitignore` lines, the OpenCode plugin entry) and claims paths this run did not write (every file in the hooks directory and every file in a skill destination). Should claims be built from the write steps instead of from globs? | Found by the 2026-11-24 review. | cicidi | no |
| **QUES-H** | Declining the the-super-lab update in `update.sh` has no effect because the installer already pulled it. Should the installer stop pulling, so the question means something? | Found by the 2026-11-24 review. | cicidi | no |
| **QUES-I** | Answering "None" carries forward only global commands, so project-mode commands and all OpenCode mirrors are pruned. Should the carry cover every path class step 10 and step 11 write? | Reproduced by the 2026-11-24 review. | cicidi | no |

## Reversibility

Every install is reversible through the manifest: `uninstall.sh` removes what was written, and `--restore-pristine` restores `settings.json` and `CLAUDE.md` to their state before the first install. A single bad install can also be undone by restoring the `settings.json` backup that uninstall writes. Skill copies can be regenerated at any time by re-running the installer.

## Terms

The parent walter-worker design has no glossary yet, so the terms this feature uses are defined here.

| Term | Meaning |
|---|---|
| Skill | An instruction file (`SKILL.md`, plus files beside it) that an AI coding tool loads when a task matches its description |
| Bundle skill | A skill shipped inside the walter-worker repository's own `skills/` directory, as opposed to one from the-super-lab |
| Command | A Claude Code slash command, a single markdown file under `.claude/commands/` |
| Mirror | A copy or symlink of a skill placed where one AI tool looks for it |
| Hook | A command Claude Code runs on an event, registered in `~/.claude/settings.json` |
| Manifest | `~/.coworker/install-manifest.json`, the record of what the installer wrote |
| Claim | To list a path in the manifest, which makes it eligible for pruning and uninstall |
| Prune | Removing a path an earlier install claimed and this install no longer produces |
| MCP | Model Context Protocol, the way AI tools connect to external tool servers |
| pipx | A tool that installs a Python command-line program into its own isolated environment |
| bats | Bash Automated Testing System, the test runner for the shell scripts |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the scripts at `a0f4ce0`; added the 13 required sections; removed the false managed-region clause (ARD-D) |
| 0.3 | 2026-11-24 | Review fixes: CLI contract, project-mode side effects, Step 6 copy, real manifest and uninstall behavior; code conflicts recorded as QUES-C to QUES-I (ARD-E); Terms section added |
