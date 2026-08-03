# AI Coworker System — Blueprint

> **Purpose:** Complete specification of the AI Coworker context management system. Give this to any LLM to recreate it.

> **What is AI Coworker?** A Python CLI tool that manages a three-layer CLAUDE.md architecture (Global → Project → Local), keeps your AI coding assistants aware of your projects and initiatives, syncs skills from [skill-factory](https://github.com/cicidi/skill-factory), and tracks session analytics. It's the data foundation for building an autonomous coding agent.

> **What it is NOT:** A development workflow tool. Skills for coding, testing, reviewing, debugging — those come from skill-factory, not walter-worker. AI Coworker provides the context, memory, and data layer that makes those skills effective.

> **Evidence base:** Design validated against [CLAUDE.md Engineering: Best Practices and Anti-Patterns](docs/spec/2026-07-01-claude-md-best-practices-paper.md) — systematic review of 22 sources including Anthropic Applied AI, Chroma context-rot experiments, Superpowers (244k stars), and Andrej Karpathy's behavioral principles.

---

## Table of Contents

1. [Core Purpose](#1-core-purpose)
2. [Three-Layer CLAUDE.md Architecture](#2-three-layer-claudemd-architecture)
3. [Directory Structure](#3-directory-structure)
4. [Template System](#4-template-system)
5. [Context Injection System](#5-context-injection-system)
6. [Project Catalog](#6-project-catalog)
7. [Initiative Management](#7-initiative-management)
8. [State Persistence](#8-state-persistence)
9. [CLI Commands](#9-cli-commands)
10. [Skill Management](#10-skill-management)
11. [Analytics](#11-analytics)
12. [Configuration Layer](#12-configuration-layer)
13. [IDE Adapters](#13-ide-adapters)
14. [Installer Specification](#14-installer-specification)
15. [Cross-Tool Compatibility](#15-cross-tool-compatibility)

---

## 1. Core Purpose

AI Coworker solves four problems:

### Problem 1: AI doesn't know your project

AI assistants start with zero context. They don't know your team's projects or how they relate.

**Solution:** `coworker init` generates a Project CLAUDE.md with guardrails, context management framework, workflow heuristics, project identity, relationships, and knowledge repo.

### Problem 2: Context drifts across sessions

You're working on initiative "auth-migration" across 3 projects. Your AI knows about project A but not B or C. Task goals and approach are lost between sessions.

**Solution:** `coworker initiative activate` injects the initiative context (goal, approach, testing, recommended skills, reference docs) into `CLAUDE.local.md` — your personal, non-committed working context.

### Problem 3: Skills are scattered

Team skills live in skill-factory, personal tweaks in random folders, nothing is synced.

**Solution:** `coworker sync` reads `coworker.yaml` → copies configured skills to all installed IDEs. During initiative creation, user reviews and selects only relevant skills.

### Problem 4: No memory across sessions

Every AI session starts from zero. Past learnings, effective workflows, and mistakes are lost. State is lost on compaction.

**Solution:** State persistence via `coworker state-update` (hook-driven on Stop). Analytics pipeline imports session data into SQLite. Knowledge extraction identifies repeatable patterns.

---

## 2. Three-Layer CLAUDE.md Architecture

```
┌────────────────────────────────────────────────┐
│  Global CLAUDE.md (~/.claude/CLAUDE.md)         │
│  Karpathy 8 Programming Principles | <100 lines │
│  Shared across all projects, rarely updated      │
├────────────────────────────────────────────────┤
│  Project CLAUDE.md (<project>/CLAUDE.md)         │
│  Lean Meta-Controller, committed to git          │
│  - Local Override (read local.md first)          │
│  - Mandatory Guardrails (git/code safety)        │
│  - Compaction & State Persistence                │
│  - Context Management (5-step checklist)         │
│  - Workflow Selection (auto + confirm)           │
│  - Auto Memory                                   │
│  - Project Identity (repo URL)                   │
│  - Project Relationships (upstream/downstream)   │
│  - Knowledge Repo (docs/ organized by topic)   │
│  - Team Links (wikis, Slack, shared refs)        │
├────────────────────────────────────────────────┤
│  CLAUDE.local.md (<project>/CLAUDE.local.md)     │
│  Personal, NOT committed to git                  │
│  - Config Paths (~/.coworker/project.yaml)       │
│  - Initiative Context (goal, approach, testing)  │
│  - Reference Docs (must read before starting)    │
│  - Recommended Skills (user-reviewed)            │
│  - Current Task State (goal, state file path)    │
│  - Current Workflow (approach, testing, skills)  │
│  - Personal Preferences                          │
├────────────────────────────────────────────────┤
│  Skills (SKILL.md × N from skill-factory)        │
│  Auto-matched by task description                │
└────────────────────────────────────────────────┘
```

### Design principles

| Principle | Source | Enforcement |
|-----------|--------|-------------|
| Attention budget (<200 lines) | Anthropic, Chroma | Tests assert line counts |
| Critical rules at top | Superpowers (94% PR rejection) | Section order test |
| Heuristics over if-else | Anthropic Applied AI | Workflow Selection uses principles |
| Escape hatches for trivial tasks | Karpathy | "Reality check" clause |
| Auto-discoverable info excluded | Anthropic, Karpathy | No language/framework/test in CLAUDE.md |
| Compaction-aware design | Chroma context-rot | State persistence + 50-70% timing |
| Cross-tool compatible | OpenCode docs | CLAUDE.md as shared format |

### Size budget

| File | Target | Content |
|------|--------|---------|
| Global CLAUDE.md | < 100 lines | Karpathy 8 principles |
| Project CLAUDE.md | < 200 lines | Meta-controller + project identity |
| CLAUDE.local.md | < 50 lines (template) | Personal context (grows with initiative) |
| docs/state-{task}.md | < 100 lines | Progress tracking, loaded on demand |

---

## 3. Directory Structure

```
walter-worker/
├── CLAUDE.md              # Project-level meta-controller (committed)
├── CLAUDE.local.md        # Personal working context (gitignored)
├── CLAUDE.md.bak          # Backup of pre-redesign CLAUDE.md
├── README.md
├── coworker-blueprint.md  # This document
├── pyproject.toml
├── src/coworker/
│   ├── cli.py             # All CLI commands (init, sync, state-update, etc.)
│   ├── config.py          # Config loading/merging
│   ├── models.py          # Pydantic data models (incl. InitiativeConfig with goal/approach/testing)
│   ├── semantic_merge.py  # Semantic merge engine for CLAUDE.md updates
│   ├── adapters/
│   │   ├── claude.py      # Claude Code: settings, skills, context → CLAUDE.local.md
│   │   ├── opencode.py    # OpenCode: config, permissions, context → CLAUDE.local.md
│   │   └── gemini.py      # Gemini CLI: settings
│   ├── templates/         # Canonical CLAUDE.md templates
│   │   ├── global_claude_md.py   # Karpathy 8 principles (<100 lines)
│   │   ├── project_claude_md.py  # Meta-controller template (<200 lines)
│   │   └── local_claude_md.py    # Local context template
│   ├── initiatives/
│   │   └── manager.py     # Create, activate (→local.md), deactivate
│   ├── analytics/         # Session tracking
│   │   ├── db.py          # SQLite schema
│   │   ├── import_data.py # Import JSONL → SQLite
│   │   ├── auto_import.py # Daemon + one-shot import
│   │   └── knowledge.py   # Knowledge extraction
│   └── dashboard/         # Web dashboard (FastAPI)
├── skills/                # CLI command skills (SKILL.md format)
│   ├── walter-worker-setup-in-project/  # Interactive project setup
│   ├── init/              # Quick non-interactive init
│   ├── initiative-create/ # Interview-based initiative creation
│   └── ...                # 25+ other skills
├── docs/
│   ├── specs/             # Design docs, spec conclusions (committed)
│   ├── discussion/        # Discussion records, decision logs (committed)
│   ├── plan/              # Implementation plans (committed)
│   ├── state-*.md         # Task progress state (gitignored)
│   └── spec/
│       └── 2026-07-01-claude-md-design.md           # Design spec
│       └── 2026-07-01-claude-md-best-practices-paper.md  # Research paper
├── setup/
│   ├── install.sh         # Global CLAUDE.md + skills + analytics hooks
│   ├── update.sh          # Pull + re-install
│   └── uninstall.sh
└── tests/python/          # 86 tests (templates, semantic merge, models, CLI, injection)
```

---

## 4. Template System

Canonical templates live in `src/coworker/templates/`. These are the source of truth for CLAUDE.md content.

### Global template (`global_claude_md.py`)

```python
generate_global_claude_md() -> str
# Returns: Karpathy 8 principles, <100 lines
# Content: Ask & Confirm, Evidence, Simplicity, Surgical Changes,
#          Goal-Driven, Decompose, Plan & Track, Model Upgrade
# No tool references, no project-specific rules
```

### Project template (`project_claude_md.py`)

```python
generate_project_claude_md(
    project_name, repo, relationships, doc_map, team_links
) -> str
# Returns: meta-controller, <200 lines
# Section order (by priority):
#   1. Local Override (CRITICAL: read local.md)
#   2. Mandatory Guardrails (git/code safety)
#   3. Compaction & State Persistence
#   4. Context Management (4-step checklist)
#   5. Workflow Selection (auto/confirm + escape hatch)
#   6. Auto Memory
#   7. Development Loop (lint + tests + commit)
#  10. Team Links
```

### Local template (`local_claude_md.py`)

```python
generate_local_claude_md() -> str
# Returns: personal context template, <50 lines
# Sections: Config Paths, Reference Docs, Current Task State,
#           Current Workflow, Personal Preferences
# Initiative context injected via inject_initiative_into_local_md()
```

### Semantic merge (`semantic_merge.py`)

```python
classify_sections(current, future) -> list[SectionClassification]
apply_merge(classifications, current, future) -> str
# Categories: KEEP, OVERWRITE, MERGE_ADD, OUTDATED
# PROTECTED blocks → always KEEP
# INITIATIVE blocks → always KEEP (managed by initiative system)
```

---

## 5. Context Injection System

### Block types

**Static block** — project catalog, injected by `coworker project sync` into `CLAUDE.md`:
```
<!-- COWORKER:STATIC START --> ... <!-- COWORKER:STATIC END -->
```

**Initiative block** — injected into `CLAUDE.local.md` (NOT CLAUDE.md):
```
<!-- INITIATIVE:<name> START -->
## Active Initiative: <name>
> <description>

### Goal
<what this task is trying to achieve>

### Approach
<how to tackle it>

### Testing
<how to verify correctness>

### Recommended Skills
- `brainstorming`
- `TDD`
- `commit`

### Projects in scope
| Project | Role | Branches |

### Key Decisions

### Reference Docs
- `path/to/doc.md` — Title

### Links
- [Title](URL)
<!-- INITIATIVE:<name> END -->
```

### Injection targets

| Block | Target file | Committed? |
|-------|------------|------------|
| Static (project catalog) | `CLAUDE.md` | ✅ Yes |
| Initiative (goal, approach, testing, skills) | `CLAUDE.local.md` | ❌ No |

### Injection logic

```
coworker initiative activate
  → builds initiative block (with goal/approach/testing/recommended_skills)
  → reads CLAUDE.local.md (or creates from template)
  → removes existing INITIATIVE blocks
  → injects new block
  → writes CLAUDE.local.md

coworker initiative deactivate
  → removes INITIATIVE blocks from CLAUDE.local.md
```

---

## 6. Project Catalog

Tracks all projects and their relationships. Stored at `~/.coworker/project.yaml`.

```yaml
projects:
  - name: walter-worker
    local_path: ~/project/walter-worker
    upstream: []
    downstream:
      - name: skill-factory
    knowledge_pool:
      - type: github
        url: https://github.com/cicidi/walter-worker
```

Project relationships are injected into Project CLAUDE.md's `## Project Relationships` section. The catalog file path is listed in `CLAUDE.local.md`'s Config Paths.

---

## 7. Initiative Management

Initiatives carry **task context** — not just links and project references, but the actual goal, approach, testing method, and recommended skills for the current work.

### Data model

```yaml
# ~/.coworker/initiatives/<name>.yaml
name: claude-md-design
description: Design global and project-level CLAUDE.md
goal: |
  Design and implement a three-layer CLAUDE.md architecture.
approach: |
  brainstorming → spec → implement → dogfood → self-optimize.
testing: |
  Unit tests (86 pass). Behavioral validation by dogfooding.
recommended_skills:
  - brainstorming
  - walter-worker-skill-create
  - commit
status: active
created: "2026-07-01"
projects:
  - name: deterministic-workflow
    role: peer
    branches: [master]
links: [...]
decisions: [...]
reference_docs: [...]
```

### Initiative → CLAUDE.local.md mapping

| InitiativeConfig field | Injected into local.md section |
|------------------------|-------------------------------|
| `goal` | Current Task State > Goal |
| `approach` | Current Workflow > Approach |
| `testing` | Current Workflow > Testing |
| `recommended_skills` | Recommended Skills (user-reviewed) |
| `reference_docs` | Reference Docs (AI must read before starting) |
| `projects` | Projects in scope |
| `links` | Links |
| `decisions` | Key Decisions |

### Interview process (`initiative-create` skill)

1. Name (kebab-case)
2. Description
3. **Goal** — what does success look like?
4. **Approach** — how to tackle it (TDD / brainstorming→spec / direct)
5. **Testing** — how to verify correctness
6. **Recommended Skills** — scan available skills, user selects relevant ones
7. Projects (role, branches)
8. Links (wikis, PRDs)
9. Decisions (date, decision, rationale, by)
10. Reference docs (local files AI must read)

---

## 8. State Persistence

### `coworker state-update` command

```bash
coworker state-update                    # Called by Stop hook
coworker state-update -s "finished auth"  # Manual milestone save
```

Behavior:
1. Finds state file path from `CLAUDE.local.md` (parses `State file:` line)
2. Creates or appends to `docs/state-{task}.md`
3. Adds timestamp + optional summary

### Hook configuration

**Claude Code** (`~/.claude/settings.json` or `.claude/settings.json`):
```json
{
  "hooks": {
    "Stop": [
      {"type": "command", "command": "coworker state-update"}
    ]
  }
}
```

**OpenCode** (`.opencode/config.json`):
```json
{
  "permission": {
    "bash": {
      "coworker *": "allow"
    }
  }
}
```

OpenCode has no event hooks. The CLAUDE.md Compaction section instructs the AI to run `coworker state-update` on compaction. Both tools use the same command.

### Gitignore

```
CLAUDE.local.md
docs/state-*.md
```

State files and local context are personal — never committed.

---

## 9. CLI Commands

```
coworker init              # Quick non-interactive: scan → generate CLAUDE.md + local.md + docs/
coworker sync              # Sync config to all IDEs (skills, hooks, permissions)
coworker status            # Show config status
coworker state-update      # Write task state (called by hook or manually)

coworker project add/edit/list/remove/show/sync

coworker initiative start/create/edit/activate/deactivate/list/show/remove

coworker skill list/new

coworker analytics create-db/import/daemon/once/dashboard
```

### init behavior

`coworker init --project`:
1. Scan project (language, framework, deps — for display only, NOT written to CLAUDE.md)
2. Generate Project CLAUDE.md from canonical template
3. Generate CLAUDE.local.md from template
4. Create `docs/` directory
5. Add `CLAUDE.local.md` and `docs/state-*.md` to `.gitignore`

For full interactive setup with interview, use the `walter-worker-setup-in-project` skill.

---

## 10. Skill Management

AI Coworker manages skill **distribution**, not skill **creation**. Skills are created in [skill-factory](https://github.com/cicidi/skill-factory).

### Skill lifecycle

```
skill-factory → coworker.yaml → coworker sync → IDE config dirs
```

### Recommended skills in initiatives

During `initiative-create`, the user reviews available skills and selects only relevant ones. These are stored in `InitiativeConfig.recommended_skills` and injected into `CLAUDE.local.md` on activation. The AI sees only the curated list, not all 82 installed skills.

---

## 11. Analytics & Memory Management

Tracks AI session activity across Claude Code and OpenCode. Records skill usage, tool calls, token costs, and extracts reusable knowledge.

### Database schema

```sql
-- ~/.coworker/analytics/analytics.db
CREATE TABLE sessions (id, title, model, cost, tokens_input, tokens_output);
CREATE TABLE messages (id, session_id, role, content, timestamp);
CREATE TABLE tool_calls (id, session_id, tool_name, input, output, duration_ms);
CREATE TABLE knowledge (id, title, type, session_id, project, skills, summary, evidence);
```

### Commands

```
coworker analytics create-db   → Initialize SQLite database
coworker analytics import      → Import session JSONL → SQLite
coworker analytics once        → One-shot import of new sessions
coworker analytics daemon      → Auto-import every 30 minutes
coworker analytics dashboard   → Web UI at http://localhost:8080
```

### Analytics Dashboard

The dashboard provides real-time monitoring of AI coding sessions:

- **Overview**: total sessions, messages, tool calls, skills used, daily chart
- **Monitor**: active sessions, top skills by invocation count, top files by read/write ops — at a glance view of "what the AI is doing"
- **Sessions**: chronological list with drill-down to per-session detail
- **Session Detail**: unified timeline mixing messages, tool calls, and file ops in chronological order with icons — shows exactly what happened in a session and how
- **Skills**: which skills were invoked, how often
- **Tools**: tool call distribution and avg duration
- **Files**: per-file read/write/delete stats, ranked by total operations, with project attribution
- **Knowledge**: LLM-generated insights extracted from sessions
- **Initiatives**: cross-session workstreams grouped by initiative tag

### Analytics Database

- **Schema**: sessions, messages, tool_calls, file_ops, session_stats, skills, knowledge, session_summaries
- **File ops** record every Read/Write/Edit/Glob/Bash operation with file_path, op_type, timestamp, and session attribution
- **Tool calls** capture tool name, args, duration, and session — Skill invocations link to the skills registry

---

## 12. Configuration Layer

### Global config — `~/.coworker/coworker.yaml`

```yaml
version: "1"
scope: global
mcp: []
skills: []
permissions:
  allow: [Bash(git *), Read(*), Write(*)]
claude:
  effortLevel: medium
```

### Project config — `./coworker/coworker.yaml`

```yaml
version: "1"
scope: project
skills: []
permissions:
  allow: []
  deny: []
```

### Removed: `.local_config.yaml`

Previously stored identity, docs paths, and session analysis config. **Removed** — all personal config now lives in `CLAUDE.local.md`. No duplication.

---

## 13. IDE Adapters

| Adapter | Sync target | Context injection | State hook |
|---------|------------|-------------------|------------|
| `claude.py` | `~/.claude/settings.json`, `~/.claude/commands/` | `CLAUDE.local.md` (initiative) | Stop hook: `coworker state-update` |
| `opencode.py` | `.opencode/config.json` | `CLAUDE.local.md` (delegates to claude.py) | Permission: `coworker *` allow |
| `gemini.py` | `.gemini/settings.json` | (not yet) | (not yet) |

### Claude Code adapter

- `sync()`: writes settings.json (permissions, MCP, hooks), copies skills
- `inject_initiative()`: writes to `CLAUDE.local.md` (not CLAUDE.md)
- `remove_initiative()`: removes from `CLAUDE.local.md`
- `_resolve_local_md()`: finds `CLAUDE.local.md` path
- `_build_initiative_block()`: builds block with goal/approach/testing/skills

### OpenCode adapter

- `sync()`: writes config.json (MCP, permissions)
- `inject_initiative()`: delegates to claude.py (same file: `CLAUDE.local.md`)
- `remove_initiative()`: delegates to claude.py

Both tools read the same `CLAUDE.local.md`. Claude Code auto-loads it natively. OpenCode reads it via the "Local Override" instruction in Project CLAUDE.md.

---

## 14. Installer Specification

### Dependencies

- Python 3.10+
- `click`, `rich`, `pyyaml`, `pydantic`
- Optional: `uvicorn` (analytics dashboard)

### Install

```bash
git clone https://github.com/cicidi/walter-worker.git
cd walter-worker
pip install --break-system-packages -e .
```

### First run

```bash
coworker init        # Creates global + project config, CLAUDE.md, CLAUDE.local.md, docs/
coworker sync        # Syncs skills to IDEs, configures state-update hooks
coworker status      # Verify everything is set up
```

### What gets created

| Step | Creates |
|------|---------|
| `coworker init --global` | `~/.coworker/coworker.yaml`, `~/.coworker/skills/` |
| `coworker init --project` | `./coworker.yaml`, `CLAUDE.md`, `CLAUDE.local.md`, `docs/`, `.gitignore` entries |
| `coworker initiative create` | `docs/<initiative>/{prd,plan,spec}/` |
| `coworker sync` | Copies skills to IDE dirs, writes settings, configures Stop hook |
| Global CLAUDE.md | `~/.claude/CLAUDE.md` (from canonical template, not overridden if exists) |

### install.sh changes

- Global CLAUDE.md content now extracted from `templates/global_claude_md.py` (not hardcoded string)
- If `~/.claude/CLAUDE.md` already exists: **warn, do NOT override**

---

## 15. Cross-Tool Compatibility

### Mandatory rules

| Rule | Reason |
|------|--------|
| `CLAUDE.md` as shared format | OpenCode reads it as AGENTS.md fallback |
| `CLAUDE.local.md` referenced from Project CLAUDE.md | OpenCode doesn't auto-load it — instruction tells AI to Read it |
| No `.claude/rules/` | OpenCode doesn't support path-scoped rules |
| No `.local_config.yaml` | Removed — all personal config in `CLAUDE.local.md` |
| Skills declare `compatibility: claude-code,opencode` | Both tools must work |

### Enforcement layer

| Tool | Mechanism | Config file |
|------|-----------|-------------|
| Claude Code | Event hooks (Stop) | `~/.claude/settings.json` |
| OpenCode | Tool permissions (allow/ask/deny) | `opencode.json` |

Same intent (enforce `coworker state-update`), different mechanisms. `coworker sync` configures both.

### Degradation strategy

If a feature only works in one tool:
- Claude Code only → `.claude/` directory, document as CC-only
- OpenCode only → `opencode.json`
- Both → `CLAUDE.md` (single source of truth)
- Missing in one tool → graceful degradation via CLAUDE.md instructions
