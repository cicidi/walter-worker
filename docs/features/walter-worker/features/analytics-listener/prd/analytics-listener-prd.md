---
feature: analytics-listener
type: prd
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Listener — PRD

## Overview

The analytics listener records what happens in Claude Code sessions so that walter-worker can later show statistics, summarize sessions, and learn from them. It has two halves. Hooks (commands Claude Code runs on events such as "the user sent a prompt" or "a tool finished") append records to per-session files under `~/.coworker/analytics/sessions/<session id>/`. Importers then load those files, and Claude Code's own session transcripts, into a local SQLite database at `~/.coworker/analytics/analytics.db`, which the [analytics dashboard](../../analytics-dashboard/prd/analytics-dashboard-prd.md) and the memory features read. A third, smaller hook watches prompts for signs that the user is correcting the agent and writes a draft note when it finds one.

This document states what the listener must do. The [design](../design/analytics-listener-design.md) states how it behaves today, including where the code does not yet meet a requirement. Facts were checked against the code at commit `a0f4ce0`.

## Goals and Success Metrics

| Goal | Success metric |
|---|---|
| Sessions are recorded | Every prompt and every tool call in a Claude Code session appears in the database after an import |
| Recording never gets in the way | No hook failure stops or slows the user's session noticeably |
| Data stays on the machine | No hook or importer sends session content anywhere |

## User Stories

As a developer, I want my sessions recorded automatically, so that I can later see which tools and files I use most and how long sessions take.

As a developer, I want recording to be invisible, so that a full disk or a malformed event never interrupts my work.

As a developer, I want my session data kept locally and easy to find, so that I control what is stored and can delete it.

## Functional Requirements

| ID | Requirement |
|---|---|
| **PRD-A** | Each prompt the user submits and each tool call, before and after it runs, is appended to that session's files with a timestamp and a per-session sequence number. |
| **PRD-B** | A hook never blocks the session: it finishes quickly and exits successfully even when it cannot write. |
| **PRD-C** | Records that arrive without a session id are kept apart from attributed sessions instead of being lost or mixed in. |
| **PRD-D** | The importers load hook records, Claude Code transcripts, and OpenCode session metadata into the database. Running an import twice gives the same database. |
| **PRD-E** | The database location can be overridden with the `COWORKER_ANALYTICS_DB` environment variable, and the database is created with its full schema on first use. |
| **PRD-F** | When a prompt reads as a correction of the agent, a draft trace is written for later review. |
| **PRD-G** | All recorded data stays on the machine. Secrets in prompts and tool inputs are not stored in plain text. |
| **PRD-H** | Raw session directories are removed once they are imported and old; the database itself is kept until the user deletes it. |

## Out of Scope

The web dashboard is the [analytics dashboard](../../analytics-dashboard/prd/analytics-dashboard-prd.md) feature. Session summaries and knowledge cards (`coworker knowledge`) belong to the memory platform. Registering the hooks is done by the installer ([setup-deploy](../../setup-deploy/prd/setup-deploy-prd.md)). Gemini CLI sessions are not recorded.

## Resources Needed

bash and python3 for the hooks; Python with the walter-worker package for the importers; SQLite through Python's standard library. Tests are pytest suites under `tests/analytics/` and `tests/python/` plus bats tests under `tests/hooks/`.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0`; the false OpenCode plugin and `index.jsonl` claims removed (ARD-A) |
