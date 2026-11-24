---
feature: memory-platform
type: prd
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Memory Platform — PRD

## Overview

The memory platform lets walter-worker remember across sessions. At the end of each Claude Code session it asks a language model to extract lessons and candidate skills from the transcript; lessons go into a local vector store (a database that finds text by meaning rather than by exact words), and facts about code, documents, and decisions go into a local knowledge graph at `~/.coworker/memory/graph.json`. Later sessions query both, a weekly curator ages old memories, and a snapshot of the project's memories can be written into `~/CLAUDE.local.md` so the next session starts with them. A related command group, `coworker knowledge`, summarizes recorded sessions into the analytics database.

This document states what the memory platform must do. The [design](../design/memory-platform-design.md) states how it behaves today, including where the code does not yet meet a requirement. Facts were checked against the code at commit `a0f4ce0`.

## Goals and Success Metrics

| Goal | Success metric |
|---|---|
| Sessions leave memories | After a session ends on a configured machine, its lessons can be found with `coworker memory search` |
| Memory never gets in the way | A missing key, a missing library, or a bad dump never stops a session or blocks later captures |
| The user knows what leaves the machine | Every place session content is sent to an outside service is documented, and nothing else is sent |

## User Stories

As a developer, I want lessons from past sessions captured without my effort, so that the agent stops repeating mistakes I already corrected.

As a developer starting a session, I want the project's key memories in front of the agent, so that I do not re-explain conventions every time.

As a developer, I want old and unused memories to fade on their own, so that the store stays relevant.

As a privacy-conscious developer, I want to know which content goes to which provider, and to be able to delete what was stored.

## Functional Requirements

| ID | Requirement |
|---|---|
| **PRD-A** | At session end, the transcript is turned into lessons, candidate skills, and graph facts. Without a configured key, capture does nothing and stays quiet; no failure in capture blocks the session. |
| **PRD-B** | Graph facts are merged into the knowledge graph with duplicates folded together. A dump that cannot be merged is set aside and does not block the dumps after it, and concurrent merges do not lose updates. |
| **PRD-C** | `memory query` searches the graph and the vector store together and returns results within a size budget; `memory search` searches the vector store. |
| **PRD-D** | A curator runs at most weekly: it marks unused memories stale, archives long-stale ones, exports active memories to `MEMORY.md`, expires old pending skills, and removes raw analytics session folders that are already imported and old. |
| **PRD-E** | `memory refresh` writes the current project's memory snapshot and the critical wrong-history rules into `~/CLAUDE.local.md`, changing only the text between its markers. |
| **PRD-F** | Candidate skills are staged for human approval, at most three per day, and never promoted without approval. |
| **PRD-G** | `knowledge summarize` and `knowledge analyze` turn recorded sessions into summaries and knowledge cards in the analytics database. |
| **PRD-H** | Keys are read from the environment or from `~/.coworker/.env`. The user can delete stored memories. |
| **PRD-I** | `memory init` and `memory sync` build or extend the graph from Graphify output (a tool that maps a codebase into a graph); `init` never replaces a populated graph without `--force` and a backup. |
| **PRD-J** | `memory wrong-history record` writes a lesson entry and rebuilds the index; `index` rebuilds only. |

## Out of Scope

Recording sessions into the analytics database is the [analytics listener](../../walter-worker/features/analytics-listener/prd/analytics-listener-prd.md). Approving and rejecting staged skills is done through `coworker skill`, in the [core CLI](../../walter-worker/features/core-cli/prd/core-cli-prd.md). The model-backed validation command (`memory validate`) and batch training (`memory train`) are experimental and described only briefly.

## Resources Needed

Python with the `memory` extras: mem0, Qdrant (local), and fastembed. A DeepSeek API key for capture, the curator, search, and the snapshot; a Gemini key is an optional fallback for language-model calls. Graphify for `init` and `sync`. Tests live under `tests/memory/` and `tests/python/`.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0`; the graph pipeline added, the false write-safety and audit claims removed (ARD-A) |
