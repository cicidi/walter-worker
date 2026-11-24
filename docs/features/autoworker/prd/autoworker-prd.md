---
feature: autoworker
type: prd
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Auto-worker — PRD

## Overview

The auto-worker runs unattended review of a project. `coworker run --loop` repeatedly starts a headless Claude Code session (one that runs a single prompt and exits, with no interactive window) whose prompt asks it to audit the project against its specifications, fix real problems, and report what it found; each round's report is appended to a dated state file. `coworker find-issues run` is a quick inspection that counts requirement and specification entries and runs the test suite. Both are meant for long, unwatched runs, so they must stop on their own, leave a record, and never claim success they did not have.

This document states what the auto-worker must do. The [design](../design/autoworker-design.md) states how it behaves today, including where the code does not yet meet a requirement. Facts were checked against the code at commit `a0f4ce0`.

## Goals and Success Metrics

| Goal | Success metric |
|---|---|
| Unattended runs end by themselves | A loop never runs past its time budget by more than one round, nor past its round cap |
| Every round leaves a record | The state file shows each round, including rounds whose agent failed to start |
| Failures are visible | A run where every round failed does not report success |

## User Stories

As a maintainer, I want to start a review loop before I leave, so that I come back to findings and fixes instead of an untouched backlog.

As a maintainer, I want a quick inspection command that fails when tests fail, so that a script or a scheduled job can tell a healthy project from a broken one.

## Functional Requirements

| ID | Requirement |
|---|---|
| **PRD-A** | `coworker run` does nothing unless `--loop` is given. |
| **PRD-B** | The loop stops when its time budget (`--max-hours`) is spent or after a fixed maximum number of rounds, and each round has a time limit. |
| **PRD-C** | Each round runs the agent with the project's specifications and the prior round's state as its context, and appends the agent's report to a dated state file for the project. |
| **PRD-D** | A round whose agent cannot start or fails is recorded as failed, and a run whose rounds all failed exits with a failure status. |
| **PRD-E** | `find-issues run` inspects the chosen phases (requirements, specification, web, code), writes a dated report, and exits with a failure status when the code phase finds failing tests or when a phase name is unknown. |
| **PRD-F** | Lessons recorded as critical in the project's wrong-history are given to the agent before the first round. |

## Out of Scope

What the agent changes in the repository is governed by the user's Claude Code permission settings, not by this feature. The rule classes for gap checking in `src/coworker/autoworker/rules.py` are not called by either command and are not part of this contract. Creating GitHub issues, commits, or branches is not done by the Python code.

## Resources Needed

The `claude` command-line tool on the path for `run`; Python with pytest for `find-issues`. Tests are under `tests/python/`.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0`; the nonexistent `coworker autoworker` command and in-code gap detection removed (ARD-A) |
