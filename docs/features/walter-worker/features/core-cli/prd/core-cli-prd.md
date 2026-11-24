---
feature: core-cli
type: prd
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Core CLI — PRD

## Overview

`coworker` is walter-worker's command-line tool. This feature covers its configuration core: `init` creates configuration files, `sync` writes that configuration into each AI coding tool's own settings files, `status` summarizes it, `project` keeps a catalog of the user's repositories, `skill` manages skills and the review queue for skills the memory loop proposes, `upgrade` merges template updates into the global `CLAUDE.md`, `restore` brings back files from the automatic backups, and `state-update` keeps a daily progress note in the project. Analytics, the feature system, memory, and the auto-worker have their own specifications.

The configuration lives in `coworker.yaml` files: one global file at `~/.coworker/coworker.yaml` and an optional project file at `<project>/.coworker/coworker.yaml`. It lists MCP servers (MCP, the Model Context Protocol, is how AI tools connect to external tool servers), skills, and permissions. The [design](../design/core-cli-design.md) states how the commands behave today, including where the code does not yet meet a requirement. Facts were checked against the code at commit `a0f4ce0`.

## Goals and Success Metrics

| Goal | Success metric |
|---|---|
| One source of configuration | After `coworker sync`, Claude Code, Gemini CLI, and OpenCode each list the MCP servers in `coworker.yaml` |
| The user's own settings survive | A sync, init, or upgrade never removes a setting the user wrote, and every overwrite of a user-visible file can be undone with `coworker restore` |
| Local only | No configuration command contacts the network |

## User Stories

As a developer on a new project, I want `coworker init --project` to detect the language and tools and write a starting configuration, so that I do not write it by hand.

As a developer using three AI tools, I want one `coworker sync`, so that the same MCP servers and permissions reach all of them.

As a developer whose global `CLAUDE.md` has my own edits, I want `coworker upgrade` to bring in template changes without losing my lines, and to show me the plan first.

As a developer whose file was changed by mistake, I want `coworker restore <label>` to bring back the copy taken before the change.

## Functional Requirements

| ID | Requirement |
|---|---|
| **PRD-A** | `init --global` creates `~/.coworker/coworker.yaml` from a template when it is missing and never overwrites it. |
| **PRD-B** | `init --project` detects the project's language, frameworks, and AI tools, asks for confirmation, and writes the project configuration, the project's `CLAUDE.md` and `CLAUDE.local.md`, and `.gitignore` entries. A file that already exists is backed up before it is overwritten, and the user's text in `CLAUDE.local.md` survives. |
| **PRD-C** | The effective configuration is the global file merged with the nearest project file, with documented precedence. An invalid file is reported with a message naming the file, not a stack trace. |
| **PRD-D** | `sync` writes the configured MCP servers, permissions, skills, and walter-worker's own hook into each selected tool. It keeps every entry the user wrote, removes only entries it wrote earlier that are no longer configured, and backs up a file before changing it. A failure in one tool does not stop the others. |
| **PRD-E** | No configuration command makes a network request. |
| **PRD-F** | `status` prints the configuration and the active feature's progress without changing any file. |
| **PRD-G** | `project` adds, edits, lists, shows, and removes catalog entries, and `project sync` writes the catalog into the project's `CLAUDE.md` between markers without touching other text. |
| **PRD-H** | `skill list` and `skill new` show and scaffold skills. `skill pending`, `approve`, and `reject` let the user review proposed skills; an approved skill is promoted only after a safety check, and a rejected or failed one is never promoted. |
| **PRD-I** | `upgrade` merges template updates into `~/.claude/CLAUDE.md`. It shows the plan first, never changes a protected block or a feature block, never drops a line the user added unless told to, backs up before writing, and supports a dry run. |
| **PRD-J** | `restore` brings back the files of a backup chosen by path, folder name, or label, after confirmation. |
| **PRD-K** | `state-update` appends a progress note to the managed project's state file, and does nothing outside a managed project. |

## Out of Scope

A Cursor adapter: `sync` does not write Cursor configuration; skills reach Cursor through the installer ([setup-deploy](../../setup-deploy/prd/setup-deploy-prd.md)). Expanding `$VARIABLE` references or reading `~/.coworker/.env` for secrets: values are copied as written (QUES-G in the design). The feature commands, analytics, memory, and the auto-worker.

## Resources Needed

Python 3.10 or later with Click, Pydantic 2, PyYAML, and Rich. The pytest suites under `tests/python/` are the regression net.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft from the legacy core PRD (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0`; the false Cursor adapter and secret-reference claims removed; letter IDs (ARD-A) |
