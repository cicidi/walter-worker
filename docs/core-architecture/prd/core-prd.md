# Core CLI & Initiative System PRD

<!-- PROTECTED -->
Project: ai-coworker
Owner: cicidi
Last Updated: 2026-06-11
Status: COMPLETE
<!-- END PROTECTED -->

## Overview

The foundation of ai-coworker: a Python CLI that manages AI tool configurations across IDEs, plus a 3-level context model for cross-project workstream management.

## Goals

1. Provide a single `coworker` CLI for init, sync, skill management, and MCP management
2. Synchronize skills, MCP servers, and permissions to Claude Code, OpenCode, Gemini CLI, and Cursor
3. Enable cross-project workstreams via Initiative System with automatic context injection into AI sessions
4. Support peer-to-peer initiative sharing via git fork (publish/import)

## Requirements

### Core CLI

- `coworker init` — scaffold global or project-level `coworker.yaml`
- `coworker sync` — propagate config, skills, MCP to all IDEs
- `coworker status` — Rich-formatted config overview
- `coworker skill list/new` — skill inventory
- `coworker install` / `coworker import-mcp` — MCP server management
- Adapters: Claude Code (`~/.claude/`), OpenCode (`~/.opencode/`), Gemini CLI (`~/.gemini/`), Cursor (`.cursor/rules/`)

### Initiative System (3-Level Context Model)

- **Level 1 — Project Catalog:** `~/.coworker/project.yaml` with paths, repo, upstream/downstream, knowledge pools. CLI: `coworker project`
- **Level 2 — Initiatives:** `~/.coworker/initiatives/<name>.yaml` per workstream with branches, decisions, links. CLI: `coworker initiative create/edit/activate/deactivate/publish/import`
- **Level 3 — Task Planning:** Freeform markdown docs, no schema
- **Context Injection:** Writes initiative context into `CLAUDE.md` and OpenCode instructions via HTML comment markers on activate

## Non-Goals

- No multi-initiative simultaneous activation
- No automatic branch checkout on initiative activation
- No Gemini CLI context injection (deferred)

## Spec

`docs/spec/2026-06-11-core-architecture-design.md`

## Plan

`docs/plan/2026-06-11-initiative-system.md`
