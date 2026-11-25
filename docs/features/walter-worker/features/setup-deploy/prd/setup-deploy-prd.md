---
feature: setup-deploy
type: prd
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Setup and Deploy — PRD

## Overview

walter-worker ships three shell scripts that put it onto a developer's machine and take it off again: `setup/install.sh`, `setup/update.sh`, and `setup/uninstall.sh`. Installing means four things. It deploys skills (instruction files an AI coding tool loads on demand) into Claude Code, Cursor, and OpenCode. It registers hooks (commands Claude Code runs on events such as "the user sent a prompt") in `~/.claude/settings.json`. It creates a global `CLAUDE.md` when none exists. It records what it wrote in an install manifest, a JSON file at `~/.coworker/install-manifest.json` that lets a later run undo exactly that work and nothing else.

This document states what the scripts must do. How they do it, and where the code does not yet meet a requirement, is in the [design](../design/setup-deploy-design.md); terms are defined in its Terms section. The facts below were checked against the scripts at commit `a0f4ce0`, and against `634adf1` after walter-worker PRs #16 to #23.

## Goals and Success Metrics

| Goal | Success metric |
|---|---|
| A new machine works after one command | After `install.sh --global`, every hook in PRD-F is registered and every the-super-lab skill is loadable in all three tools |
| Re-running is safe | A second run with the same answers changes no file (PRD-H) |
| Uninstall is exact | Uninstall removes every path the manifest claims and no other path (PRD-J) |
| The user's own files survive | No run deletes or overwrites a file the installer did not create (PRD-B, PRD-G) |

## User Stories

As a developer setting up a new machine, I want one install command, so that hooks and skills work in every AI tool I use without copying files by hand.

As a developer who already has a `CLAUDE.md` and my own hooks, I want the installer to leave them alone, so that installing walter-worker never costs me my configuration.

As a maintainer, I want `update.sh` to pull the latest code and re-apply it with the answers I gave last time, so that an update never asks a question it already has the answer to.

As a developer leaving walter-worker, I want uninstall to remove what was installed and only that, so that my session history and my own tools survive.

## Functional Requirements

| ID | Requirement |
|---|---|
| **PRD-A** | The installer runs in global mode (writes under the home directory, the default) or project mode (writes under one project path given with `--project`). |
| **PRD-B** | The installer creates the global `CLAUDE.md` when it is missing and never overwrites one that exists. It points the user to `coworker upgrade` for merging template changes. |
| **PRD-C** | Before its first change on a machine, the installer saves a pristine snapshot of `settings.json` and `CLAUDE.md`, recording which of them did not exist. `uninstall.sh --restore-pristine` returns the machine to that state. |
| **PRD-D** | Every skill in the-super-lab's `skills/` and `personal-skills/` reaches Claude Code, Cursor, and OpenCode, and reaches each tool exactly once. |
| **PRD-E** | walter-worker's own bundle skills are offered for selection and installed as Claude Code commands. The core `init` skill is always installed. |
| **PRD-F** | The installer registers its analytics hooks and its session-summary hook in `~/.claude/settings.json`. It never adds a hook that is already present and never removes an entry it did not add. |
| **PRD-G** | Every path the installer writes is recorded in the manifest by name. A path an earlier run recorded and this run did not produce is removed. A path the installer did not write is never recorded. |
| **PRD-H** | A second run with the same answers produces the same files and the same manifest. |
| **PRD-I** | `update.sh` updates the walter-worker checkout, then re-runs the installer in the recorded mode with the recorded skill selection, without asking the skill question again. Updating the-super-lab is offered and can be declined. |
| **PRD-J** | `uninstall.sh` asks for confirmation, backs up `settings.json`, and removes only manifest-claimed paths and walter-worker's own hook entries. It keeps `~/.coworker/analytics/` and `~/.coworker/backups/`. It refuses to delete anything listed in a manifest older than schema version 2. |
| **PRD-K** | A missing optional dependency does not stop the install. If the-super-lab cannot be pulled, or the `coworker` command is not installed, the installer warns and continues. |

## Out of Scope

Installing the Python package itself is not part of these scripts; the installer only tells the user to run `pipx install` when the `coworker` command is missing. Cursor hooks are not deployed; OpenCode receives only the analytics plugin, and only when the plugin directory exists in the checkout. Tmux and status-line presentation belong to the computer-config feature. Release packaging for PyPI is not covered.

## Resources Needed

The scripts need bash, python3, and git on the machine. Skills come from a the-super-lab checkout at `~/project/the-super-lab`. The bats test suites in `tests/setup/` are the regression net; they run in CI.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft from README and bats install tests (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the scripts at `a0f4ce0`; requirements renamed to letter IDs; false claims about `pipx install` and managed CLAUDE.md regions removed (ARD-D) |
| 0.3 | 2026-11-24 | Out of Scope corrected for the OpenCode plugin; requirements the code does not meet are tracked in the design's Open Questions (ARD-E) |
| 0.4 | 2026-11-24 | PRD-F names the one session-summary hook (walter-worker PR #22) |
