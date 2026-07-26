# ai-coworker Technical Specification

## Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2026-03-30 | 0.1.0 | Initial commit – unified dev environment, all skills in single repo. |
| 2026-05-06 | 0.2.0 | Skills moved to `public/skills/`; meta-import added. |
| 2026-06-12 | 0.3.0 | Analytics listener, SQLite DB schema, backend + frontend dashboard implemented. |
| 2026-06-23 | 0.4.0 | Major cleanup: removed global/ and personal/ skills; renamed CLI commands; introduced three-layer CLAUDE.md, auto-scan init, analytics daemon with checkpoint. |
| 2026-07-08 | 0.5.0 | Fix round B1 – hermetic tests, polish loop, backup safety, MCP/CLI integration, state-files in `docs/state/`. |
| 2026-07-17 | 0.6.0 | Skills moved to `~/.claude/skills/`; dual-format frontmatter; doc-organise conventions; only 5 core skills kept – others moved to skill-factory. |
| 2026-07-25 | 0.7.0 | Memory subsystem (mem0 + DeepSeek LLM); auto-worker skill; dashboard expanded with Projects/Hotspots/Errors/Memory Control/Cost views; 96%+ test coverage. |

---

## 1. System Architecture Overview

ai-coworker is a **context manager and skill orchestration system** for AI coding assistants (Claude Code, OpenCode). It provides a unified environment for managing project context, executing skills, collecting analytics, and building autonomous agent capabilities.

### 1.1 High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     user's terminal / IDE                     │
│              (Claude Code / OpenCode / Tmux)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ CLI commands, hooks
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 ai-coworker core                             │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐  │
│  │ CLI Engine  │  │ Skill Mgr  │  │ Installer / Upgrader │  │
│  │ (coworker)  │  │ (index)    │  │ (init, upgrade)     │  │
│  └─────┬──────┘  └─────┬──────┘  └──────────┬───────────┘  │
│        │               │                     │               │
│  ┌─────▼───────────────▼─────────────────────▼───────────┐  │
│  │                Skills directory (~/.claude/skills/)   │  │
│  │  session-memory  │  auto-worker  │  bug-report  │ …  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Analytics Engine                         │  │
│  │  Auto-import daemon → SQLite DB → Web Dashboard      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Memory Substrate (mem0 + DeepSeek)       │  │
│  │  Capture → Embed → Curate → Inject → Training        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               Three-layer CLAUDE.md system                   │
│  ~/.claude/CLAUDE.md (global)                                │
│  .claude/CLAUDE.md (project)                                 │
│  .claude/CLAUDE.local.md (local overrides)                   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Layer Responsibilities

- **CLI Engine** – single entry point `coworker` that dispatches to installed skills.
- **Skill Manager** – indexes `~/.claude/skills/`, resolves skill dependencies, provides auto-completion.
- **Installer / Upgrader** – `coworker init` auto-scans project (language, deps, IDE), generates three-layer CLAUDE.md, prompts for DeepSeek API key, copies skills.
- **Analytics Engine** – background daemon that reads session logs (JSONL) from Claude Code / OpenCode, deduplicates, stores in SQLite, powers dashboard.
- **Memory Substrate** – mem0-based persistent memory with DeepSeek LLM for semantic knowledge dedup and injection.
- **Self-heal Hooks** – global hooks for Claude Code and OpenCode (`.claude/hooks/`) that capture file operations and inject context into CLAUDE.md.

---

## 2. Key Interfaces / APIs

### 2.1 CLI Commands

All commands are implemented as skills with Claude Code / OpenCode dual-format frontmatter. They are installed to `~/.claude/skills/` and indexed at startup.

| Category | Command | Description |
|----------|---------|-------------|
| General | `coworker init` | Auto-scan project, generate config, install skills, write three-layer CLAUDE.md |
| General | `coworker upgrade` | Upgrade existing project CLAUDE.md using semantic merge engine |
| General | `coworker status` | Show project status (analytics, memory, skills) |
| Analytics | `analytics-import` | Trigger manual import of session logs |
| Analytics | `analytics-dashboard` | Launch dashboard web UI |
| Initiative | `initiative-list` | List global initiatives |
| Initiative | `initiative-create` | Create new initiative |
| Project | `project-status` | Gather project state (files, deps, errors) |
| Project | `project-catalog` | List all projects tracked |
| Bug Management | `bug-report` | Create unified issue report (merged from bug-create) |
| Bug Management | `bug-hunt` | Collect evidence, then reason with given context |
| Memory | `memory-query` | Search semantic memory |
| Memory | `memory-train` | Trigger training pipeline |
| Skills | `skill-doc-organize` | Organise documentation by type (9 types) |
| Skills | `skill-session-memory` | Query/replay session history |
| Skills | `skill-auto-worker` | Launch autonomous agent loop (Claude SDK) |

### 2.2 Skill System

Each skill is a markdown file with frontmatter supporting **both Claude Code and OpenCode v1 formats**.

**Frontmatter schema (canonical)**:
```yaml
---
name: skill-name
description: short description
trigger: command           # how this skill is invoked (CLI command name)
args:
  - name: arg1
    type: string
    required: true
---
```

Skills are installed to `~/.claude/skills/`. The `coworker init` command copies them from the repository's `skills/` directory.

### 2.3 Analytics API (Internal)

The analytics engine exposes a RESTful HTTP API on the dashboard web server (default port 8080 – not explicitly stated, but typical Flask dev server). Endpoints include:

- `GET /api/sessions` – list all sessions with metadata
- `GET /api/sessions/<id>` – full session details
- `GET /api/file_ops` – file operation timeline
- `GET /api/knowledge` – semantic knowledge entries
- `GET /api/projects` – per-project analytics
- `GET /api/hotspots` – high-activity files
- `GET /api/errors` – error frequency
- `GET /api/memory` – memory control overview
- `GET /api/cost` – token consumption / cost
- `GET /api/efficiency` – skill usage vs. prompt ratios

All endpoints query the SQLite database directly.

### 2.4 Memory API (Internal)

Provided by the `mem0