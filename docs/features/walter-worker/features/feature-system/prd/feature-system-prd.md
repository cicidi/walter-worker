---
feature: feature-system
type: prd
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Feature System — PRD

## Overview

A feature, in walter-worker, is a named piece of work that may span several repositories: for example "spec-driven-development" touching two projects. The `coworker feature` commands create and edit a feature's record, and activate it in a project. Activating writes a context block into that project's `CLAUDE.local.md`, the personal, uncommitted instruction file Claude Code reads at the start of every session, so the AI starts each session knowing the goal, the projects involved, the key decisions, and the reference documents. The system was called "initiative" until walter-worker PR #12 renamed it.

This document states what the feature system must do. The [design](../design/feature-system-design.md) states how it behaves today, including where the code does not yet meet a requirement. Facts were checked against the code at commit `a0f4ce0`.

## Goals and Success Metrics

| Goal | Success metric |
|---|---|
| A session starts with the right context | After `coworker feature activate <name>`, the project's `CLAUDE.local.md` contains that feature's block and no other feature's block |
| The user's own notes survive | Activating or deactivating changes only the text between the feature markers |
| Old installs keep working | A machine that stored initiatives under the old name can list, show, activate, and remove them |

## User Stories

As a developer starting work that spans two repositories, I want one command that records the feature and activates it here, so that I do not hand-write the same context into each project.

As a developer switching tasks, I want to activate a different feature, so that the previous feature's context is replaced rather than piled on top.

As a developer who used walter-worker before the rename, I want my initiatives to keep working, so that the rename costs me nothing.

## Functional Requirements

| ID | Requirement |
|---|---|
| **PRD-A** | A feature has a kebab-case name (lowercase letters and digits joined by single hyphens). Every command rejects any other name with a clear error and a non-zero exit status. |
| **PRD-B** | A feature's record is stored once per machine and shared by every project. It holds a description, the projects in scope with a role and branches each, links, decisions, and reference documents. |
| **PRD-C** | `create` records a new feature and scaffolds its documentation folders in the current project. Creating a name that exists reports it and changes nothing. |
| **PRD-D** | `start` creates the feature if needed, adds the current project to its scope, and activates it, in one command. |
| **PRD-E** | `activate` makes a feature the only active feature of one project, by writing its context block into that project's `CLAUDE.local.md`. `deactivate` removes the block. Text outside the block is never changed. |
| **PRD-F** | `edit` adds projects, links, decisions, and reference documents, changes the description, or archives the feature. Every option given in one command takes effect, or none does. |
| **PRD-G** | `list` and `show` display features without changing anything. |
| **PRD-H** | `remove` asks for confirmation, deletes the record, removes the feature's block from every project in the project catalog (the list kept by `coworker project`) that has it, and keeps the documentation folders. |
| **PRD-I** | Records, markers, and commands from the old "initiative" name keep working until the user migrates them. |
| **PRD-J** | A command that changes `CLAUDE.local.md` in a project other than the current one takes a backup first. |

## Out of Scope

The project catalog (`coworker project`) and `coworker status` belong to the [core CLI](../../core-cli/prd/core-cli-prd.md); this feature only supplies the active feature's name and record to them. The daily state file written by `coworker state-update` is not feature-aware and is also covered there. Writing a feature's specification documents is the job of the spec skills, not of this command group.

## Resources Needed

Python 3 with the walter-worker package installed. The pytest suites under `tests/python/` cover the commands and the block injection.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft as `initiative-system` (never committed) |
| 0.2 | 2026-11-24 | Renamed to `feature-system` and rewritten from the code at `a0f4ce0` (ARD-A) |
| 0.3 | 2026-11-24 | Review fixes: PRD-H names the project catalog; requirements unchanged (ARD-D, ARD-E) |
