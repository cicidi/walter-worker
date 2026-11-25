---
feature: analytics-dashboard
type: prd
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Dashboard — PRD

## Overview

The analytics dashboard is a local web page, started with `coworker analytics dashboard`, that shows what the [analytics listener](../../analytics-listener/prd/analytics-listener-prd.md) recorded: sessions, the tools and files they used, skills, knowledge cards (entries that `coworker knowledge` derives from recorded sessions and stores in the analytics database), features, costs, errors, and the memory graph. It must also let the user act on a few things from the page, such as approving a skill that the memory loop proposed. The memory loop is the part of the [memory platform](../../../../memory-platform/prd/memory-platform-prd.md) that extracts candidate skills from finished sessions and stages them for review. The dashboard reads the local analytics database and a few other local stores. By default it must be reachable only from the machine it runs on.

This document states what the dashboard must do. The [design](../design/analytics-dashboard-design.md) states how it behaves today, including where the code does not yet meet a requirement. Facts were checked against the code at commit `a0f4ce0`.

## Goals and Success Metrics

| Goal | Success metric |
|---|---|
| See recent work at a glance | The summary page shows session totals, active sessions, recent sessions, top tools, and a 14-day activity chart |
| Drill into one session | A session's page shows its messages, tool calls, files, summary, and statistics in time order |
| Safe by default | A fresh start listens only on the loopback address (`127.0.0.1`, reachable only from the same machine), and a write request from another site is refused |

## User Stories

As a developer, I want a dashboard of my recent sessions, so that I can see which projects and tools take my time.

As a developer, I want to open one session and read what happened in order, so that I can understand a long session after the fact.

As a developer reviewing skills the memory loop proposed, I want to approve or reject them from the page, so that I do not need the command line for it.

## Functional Requirements

| ID | Requirement |
|---|---|
| **PRD-A** | `coworker analytics dashboard` starts the page on a chosen port and host, defaulting to the loopback address, warns when bound elsewhere, and can point at a different database. |
| **PRD-B** | The page shows activity (summary, sessions, files), insights (usage, cost, quality, knowledge), and system state (health, errors, evolution, memory graph). |
| **PRD-C** | Every page reads data through a documented HTTP interface; each read endpoint answers without a server error even when the database is empty or new. |
| **PRD-D** | Actions that change state are accepted only from the dashboard's own page. These actions are approving or rejecting proposed skills, changing a skill's status, refreshing the memory snapshot (the block of remembered facts written into `~/CLAUDE.local.md`), and resetting the memory circuit breaker (the counter that limits how many skills are proposed per day). |
| **PRD-E** | Every number on the page comes from recorded data; a figure that has no data behind it is shown as missing, not as zero. |
| **PRD-F** | The summary refreshes itself while the page is open. |
| **PRD-G** | The user can open one session and see its messages, tool calls, file operations, summary, and statistics, and a timeline that merges them in time order. |

## Out of Scope

Recording and importing sessions is the [analytics listener](../../analytics-listener/prd/analytics-listener-prd.md). The memory graph itself and the skill proposal loop belong to the [memory platform](../../../../memory-platform/prd/memory-platform-prd.md). Access from other machines with login is not provided.

## Resources Needed

Python with FastAPI and uvicorn; a browser. Tests are pytest suites under `tests/python/` and `tests/analytics/`.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0`; the false Flask, read-only, waterfall, replay, and heatmap claims removed (ARD-A) |
| 0.3 | 2026-11-24 | Review fixes: the Overview states requirements, not current behavior; terms explained; memory platform linked; PRD-G added for viewing one session (ARD-E) |
