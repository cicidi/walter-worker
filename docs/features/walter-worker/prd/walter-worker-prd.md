---
feature: walter-worker
type: prd
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# walter-worker — PRD

## Overview

walter-worker is a Python package and a set of shell scripts that set up and support AI coding tools on a developer's machine. Its command-line tool is `coworker`. It keeps the configuration of Claude Code, Gemini CLI, and OpenCode in one place, deploys skills into those tools and Cursor, records sessions and shows them on a local dashboard, remembers lessons across sessions, and can run an unattended review loop.

This is the parent document: each area has its own specification, listed in Functional Requirements, and this page states only the requirements that span them. The [parent design](../design/walter-worker-design.md) holds the module map and the glossary used by every sub-feature. Facts were checked against the code at commit `a0f4ce0`.

Older product documents for this feature are kept as parts of this PRD until they are folded into the sub-features: [core PRD](2026-06-11-core-prd.md), [dashboard PRD](2026-06-11-dashboard-prd.md), [knowledge skill PRD](2026-06-11-knowledge-skill-prd.md), and [ai-coworker PRD](ai-coworker-prd.md). Where they disagree with a sub-feature specification, the sub-feature wins.

## Goals and Success Metrics

| Goal | Success metric |
|---|---|
| One place for AI tool configuration | `coworker sync` brings Claude Code, Gemini CLI, and OpenCode to the same MCP servers and permissions |
| Nothing of the user's is lost | No walter-worker command deletes or overwrites a user file without a backup the user can restore |
| Every shipped module is specified | Each area below has the five specification documents, and each passes the spec checks |

## User Stories

As a developer setting up a machine, I want one installer and one command-line tool, so that every AI tool I use shares the same configuration and skills.

As a maintainer, I want one specification per area, so that a change to one area can be checked against its own contract.

## Functional Requirements

| ID | Requirement |
|---|---|
| **PRD-A** | Installing, updating, and uninstalling are reversible and touch only what walter-worker wrote; see [setup-deploy](../features/setup-deploy/prd/setup-deploy-prd.md). |
| **PRD-B** | Configuration is defined once and synced into each AI tool without removing the user's own entries; see [core-cli](../features/core-cli/prd/core-cli-prd.md). |
| **PRD-C** | Work spanning projects is recorded as a feature and activated per project; see [feature-system](../features/feature-system/prd/feature-system-prd.md). |
| **PRD-D** | Sessions are recorded locally and shown on a local dashboard; see [analytics-listener](../features/analytics-listener/prd/analytics-listener-prd.md) and [analytics-dashboard](../features/analytics-dashboard/prd/analytics-dashboard-prd.md). |
| **PRD-E** | Lessons are kept across sessions and curated; see [memory-platform](../../memory-platform/prd/memory-platform-prd.md). |
| **PRD-F** | An unattended review loop can run against a project and reports failures honestly; see [autoworker](../../autoworker/prd/autoworker-prd.md). |
| **PRD-G** | No component blocks or noticeably slows an AI tool's session because of its own failure. |
| **PRD-H** | Session content leaves the machine only where a sub-feature documents it. |

## Out of Scope

Tmux and status-line presentation are the [computer-config](../../computer-config/) feature. The self-evolving-agent feature has its own tree under [self-evolving-agent](../../self-evolving-agent/). Skills themselves are written in the-super-lab repository; walter-worker only deploys them.

## Resources Needed

Python 3.10 or later, bash, and git. Optional: mem0 and its dependencies for memory, FastAPI and uvicorn for the dashboard, the `claude` command for the review loop. API keys for a language-model provider where a sub-feature says so.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft by another agent (never committed) |
| 0.2 | 2026-11-24 | Written as the parent entry: links every sub-feature and every legacy PRD part; requirements span sub-features only (ARD-A) |
