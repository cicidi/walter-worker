## Change Log
| Date | Version | Description |
|------|---------|-------------|
| 2026-03-30 | 0.1.0 | Initial commit – unified dev environment |
| 2026-05-06 | 0.2.0 | Skills moved to public/skills/; meta-import |
| 2026-06-12 | 0.3.0 | Analytics listener, SQLite DB, dashboard |
| 2026-06-23 | 0.4.0 | Three-layer CLAUDE.md, auto-scan init, analytics daemon |
| 2026-07-08 | 0.5.0 | Hermetic tests, polish loop, backup safety, MCP/CLI integration |
| 2026-07-17 | 0.6.0 | Skills to ~/.claude/skills/; dual-format frontmatter; doc-organize |
| 2026-07-25 | 0.7.0 | Memory subsystem (mem0+DeepSeek); auto-worker; dashboard expansion; 96% coverage |
| 2026-07-26 | 0.8.0 | Cross-project decision extraction; evolution queries; wrong-history prevention |

---


# walter-worker Technical Specification

**Version:** 1.2 (2026-07-25)  
**Status:** Active Development – Waves 2–4 Memory, Self-Evolving Agent  

---

## 1. System Architecture

### 1.1 High‑Level Component Diagram (ASCII)

```
+------------------------------------------------------------------+
|                         USER / IDE                                 |
|  Claude Code, OpenAI Codex, Cursor, OpenCode                      |
+------------------------------------------------------------------+
         |  CLI commands (walter-worker ...)
         |  Hooks: pre/post-session, file ops, tool calls
         v
+------------------------------------------------------------------+
|                    CLI ENGINE (coworker.cli)                       |
|  Parse commands, route to skill manager, invoke skills            |
|  Orchestrates: analytics capture, memory injection, auto-worker   |
+------------------------------------------------------------------+
         |
         +--------->+-----------------------------------------------+
         |          |           SKILL MANAGER                       |
         |          |  (coworker.skills)                            |
         |          |  - Install/upgrade skills from registry       |
         |          |  - Run skill: parse frontmatter → execute     |
         |          |  - 50+ skills: coworker-{category}-{action}   |
         |          +-----------------------------------------------+
         |
         +--------->+-----------------------------------------------+
         |          |         ANALYTICS ENGINE                      |
         |          |  (coworker.analytics)                         |
         |          |  - Capture: sessions, messages, tool_calls,   |
         |          |    file_ops (via listener)                    |
         |          |  - Import pipeline: parse IDE logs → SQLite   |
         |          |  - Auto-import watcher (inotify on log dir)   |
         |          |  - Knowledge extraction (LLM-assisted)        |
         |          +-----------------------------------------------+
         |
         +--------->+-----------------------------------------------+
         |          |         MEMORY SUBSTRATE                      |
         |          |  (coworker.memory)                            |
         |          |  - mem0 vector store (qdrant backend)         |
         |          |  - DeepSeek LLM client                        |
         |          |  - 5 layers: capture, engine, injection,      |
         |          |    curator, training                          |
         |          |  - Pending queue, safety filter, audit log    |
         |          +-----------------------------------------------+
         |
         +--------->+-----------------------------------------------+
         |          |         SELF-EVOLUTION AGENT                  |
         |          |  (coworker.autoworker)                        |
         |          |  - Auto-worker engine                         |
         |          |  - Self-improvement loop: analyze → propose   |
         |          |    → apply changes to skill/codebase          |
         |          |  - CI/CD hooks, change review                 |
         |          +-----------------------------------------------+
         |
         v
+------------------------------------------------------------------+
|                    CLAUDE.md THREE-LAYER SYSTEM                    |
|  1. Global  ~/.claude/CLAUDE.md  (user-wide preferences, API key) |
|  2. Project <project>/.claude/CLAUDE.md (project rules)           |
|  3. Local   <project>/.claude/session/CLAUDE.md (task context)    |
|  Every CLI invocation syncs layers → env variables                |
+------------------------------------------------------------------+
```

### 1.2 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **CLI Engine** | Parse `walter-worker <command> [args]`; dispatch to skill manager or dashboard server; manage lifecycle (init, self-update). |
| **Skill Manager** | Install/upgrade skills from `skills/` directory (public registry); validate skill frontmatter; execute skill code with context. |
| **Analytics Engine** | Collect, store, query all IDE interactions: session metadata, chat messages, tool calls, file operations. Produce dashboards and insights. |
| **Memory Substrate** | Store and retrieve semantic knowledge using mem0 vector DB; LLM-based deduplication, summarization, and curation. |
| **Self‑Evolution Agent** | Periodically analyze analytics + memory; propose improvements to skills, CLAUDE.md files, or workflows; optionally auto‑apply with review. |
| **CLAUDE.md System** | Merge three levels of instructions (global, project, local) into a single context that is injected into every Claude Code session. |

### 1.3 Data Flow

```
IDE Event (tool_call, message, file_save)
   │
   ▼
Analytics Listener (coworker.analytics.auto_import) 
   │  writes to SQLite DB
   ▼
Analytics Queries (coworker.dashboard) 
   │  exposes REST API
   ▼
Web Dashboard (HTML/JS) 
   │
   ▼
User views insights → optionally triggers Memory Capture (coworker.memory.capture)
   │
   ▼
LLM processes → stores in mem0 vector store → later retrieved by Memory Injection (coworker.memory.inject) 
   │
   ▼
Injected into Claude Code session via CLAUDE.md local layer.
```

---

## 2. API / Interface Specifications

### 2.1 CLI Commands

All commands are invoked as `walter-worker <command> [subcommand] [options]`.

| Command | Purpose |
|---------|---------|
| `init` | First‑run setup: create config `.local_config.yaml`, ask for DeepSeek API key, scaffold CLAUDE.md layers. |
| `status` | Show current project state: active session, installed skills, memory usage. |
| `analytics` | Launch analytics dashboard (`--port 8080`) or run ad‑hoc queries (`analytics query <sql>`). |
| `skills` | List, install, upgrade, or remove skills. Subcommands: `list`, `install <name>`, `upgrade <name>`, `remove <name>`. |
| `initiative` | Manage initiatives (project‑level goals). Subcommands: `list`, `create <name>`, `close <id>`. |
| `project` | Manage projects: `list`, `sync` (sync global→project CLAUDE.md). |
| `knowledge` | Query knowledge base (`knowledge search <query>`), add/remove entries (`knowledge add/remove`). |
| `session-memory` | Summarize current session, inspect memory (`session-memory show`), force capture. |
| `mcp` | Configure MCP (Model Context Protocol) block in IDE config (e.g., install.sh hook). |
| `self-evolve` | Trigger the auto‑worker analysis and proposal (`self-evolve run`), review pending changes (`self-evolve review`). |

### 2.2 Dashboard REST API

The dashboard is a Flask web app (port 8080). All endpoints return JSON.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/sessions` | List all sessions (paginated). Query params: `?limit=50&offset=0&project=xxx`. |
| `GET` | `/api/overview` | Aggregate stats: total sessions, messages, tool calls, active projects. |
| `GET` | `/api/skills` | List installed skills with metadata (version, description, usage count). |
| `GET` | `/api/tools` | Tool call statistics: per‑tool frequency, success rate. |
| `GET` | `/api/files` | File operation stats: most edited files, operations per project. |
| `GET` | `/api/knowledge` | Query knowledge base entries. Supports text search via `?q=term`. |
| `GET` | `/api/initiatives` | List initiatives, their progress and associated sessions. |
| `GET` | `/api/evolution/*` | Self‑evolution agent endpoints: `/api/evolution/proposals`, `/api/evolution/apply`. |
| `GET` | `/api/projects` | Per‑project breakdown: sessions, active skills, memory usage. |
| `GET` | `/api/hotspots` | Hot files and error‑prone patterns (based on tool call and error history). |
| `GET` | `/api/errors` | Error log: captured exceptions, failed tool calls, warnings. |
| `GET` | `/api/memory-stats` | Vector store statistics: total documents, clusters, last capture time. |
| `GET` | `/api/cost-analytics` | Cost estimation per session (token usage, LLM calls). |
| `GET` | `/api/models` | Available LLM models (DeepSeek, Gemini, Claude) and their status. |
| `GET` | `/api/model-usage` | Per‑model token consumption over time. |
| `GET` | `/api/efficiency` | Speed metrics: time per tool call, session duration, wasted tool failures. |
| `GET` | `/api/data-quality` | Knowledge quality scores: dedup ratio, freshness, completeness. |

### 2.3 Skill Frontmatter Schema

Every skill (Python file in `skills/` directory) must contain a YAML frontmatter block.

```yaml
---
name: coworker-analytics-status
version: 1.2.0
description: "Display real‑time analytics overview"
category: analytics
dependencies:
  - flask>=2.0
  - sqlite3
inputs:
  - name: session_id
    type: string
    required: false
outputs:
  - type: JSON
    schema: "dashboard/overview"
tags:
  - dashboard
  - monitoring
---
```

### 2.4 Memory API (coworker.memory)

Internal Python API exposed to other modules:

| Function | Description |
|----------|-------------|
| `capture( session_id, content: str, metadata: dict )` | Send content to mem0 vector store after LLM dedup and safety check. |
| `inject( context: dict ) -> str` | Retrieve relevant knowledge for current context (vector search + summarization). |
| `curate( limit=50 ) -> list` | Review pending captures for quality (freshness, redundancy) and promote to long‑term memory. |
| `train( corpus: list[dict] ) -> report` | Fine‑tune embedding model on curated knowledge (optional, Wave 4). |
| `validate( candidate: dict ) -> bool` | Check that candidate memory does not violate safety rules. |
| `metrics() -> dict` | Return memory substrate health: document count, avg embedding distance, last capture timestamp. |

---

## 3. Data Models

### 3.1 Analytics Database Schema (SQLite)

File: `~/.walter-worker/analytics.db`

```sql
-- Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,                      -- UUID or IDE session ID
    project TEXT NOT NULL,                    -- project name derived from cwd
    start_time TEXT NOT NULL,                 -- ISO 8601
    end_time TEXT,                            -- ISO 8601
    session_type TEXT DEFAULT 'manual',       -- 'manual', 'auto', 'background'
    tags TEXT DEFAULT '[]'                    -- JSON array of user tags
);

-- Chat messages (turns)
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    timestamp TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    tokens INTEGER,
    cost REAL DEFAULT 0.0
);

-- Tool calls (function calls by LLM)
CREATE TABLE tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    timestamp TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments TEXT,                           -- JSON
    result TEXT,                              -- JSON or error
    duration_ms INTEGER,
    success INTEGER DEFAULT 1                -- 0 = failure
);

-- File operations (read/write/create/delete)
CREATE TABLE file_ops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    timestamp TEXT NOT NULL,
    op TEXT NOT NULL,                         -- 'read','write','create','delete','move'
    path TEXT NOT NULL,
    size_bytes INTEGER,
    checksum TEXT
);

-- Pre‑computed session statistics (updated on session end)
CREATE TABLE session_stats (
    session_id TEXT PRIMARY KEY REFERENCES sessions(id),
    total_messages INTEGER,
    total_tool_calls INTEGER,
    total_file_ops INTEGER,
    total_tokens INTEGER,
    total_cost REAL,
    duration_min REAL,
    tool_failure_rate REAL,
    unique_files_edited INTEGER
);

-- Installed skills metadata
CREATE TABLE skills (
    name TEXT PRIMARY KEY,
    version TEXT,
    description TEXT,
    category TEXT,
    install_time TEXT,
    upgrade_time TEXT,
    usage_count INTEGER DEFAULT 0
);

-- Knowledge entries (LLM-extracted facts)
CREATE TABLE knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id),
    content TEXT NOT NULL,
    source TEXT,                              -- e.g. 'file:src/main.py'
    confidence REAL DEFAULT 0.5,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT,
    tags TEXT DEFAULT '[]'
);

-- Session summaries (generated after session end)
CREATE TABLE session_summaries (
    session_id TEXT PRIMARY KEY REFERENCES sessions(id),
    summary TEXT NOT NULL,
    key_actions TEXT,                         -- JSON list of actions taken
    key_decisions TEXT,                       -- JSON list of decisions
    generated_by TEXT DEFAULT 'walter-worker',
    created_at TEXT DEFAULT (datetime('now'))
);
```

### 3.2 Memory Substrate (mem0 / Qdrant)

```
Collection: "walter-worker-memory"
  Vector dimension: 768 (text-embedding-ada-002 compatible)
  Distance metric: Cosine

Document payload schema:
  {
    "id": "uuid",
    "text": "<captured knowledge text>",
    "metadata": {
      "session_id": "...",
      "project": "...",
      "layer": "capture|curated|trained",
      "source": "analytics|manual|self-evolve",
      "timestamp": "ISO8601",
      "llm_dedup_hash": "sha256 of text",
      "tags": ["dev", "architecture", "decision"],
      "confidence": 0.0..1.0,
      "embedding_model": "deepseek-embedding-v2"
    },
    "score": 0.0
  }

Indexes:
  - payload["project"] – list filter
  - payload["timestamp"] – range filter
  - payload["tags"] – tag filter
```

### 3.3 CLAUDE.md Three‑Layer Structure

**Global Layer** (`~/.claude/CLAUDE.md`):
```markdown
# Global CLAUDE.md – walter-worker User Global Preferences
- User: <name>
- Preferred LLM: DeepSeek (fallback: Gemini, Claude)
- Default memory_injection: true
- Autoworker: enabled (review required)
- Skills: all installed
- API keys: stored in .local_config.yaml
```

**Project Layer** (`<project>/.claude/CLAUDE.md`):
```markdown
# Project CLAUDE.md – <project_name>
- Project root: /path/to/project
- Language: Python, TypeScript
- Build tool: poetry, npm
- Coding style: Google style, 2‑space indent
- Excluded dirs: vendor, .cache
- Memory injection: true (restricted to project scope)
- Initiatives: [initiative_1, initiative_2]
```

**Local Layer** (`<project>/.claude/session/CLAUDE.md` – auto‑generated per session):
```markdown
# Local CLAUDE.md – Session <session_id>
- Context: Current task (injected by walter-worker from memory)
- Relevant knowledge: <summary of top‑3 memory entries>
- Recent changes: <last 5 file ops>
- Active initiative: <initiative_name>
- Session state: active
```

The three layers are merged at session start by the CLI engine, with local overriding project, and project overriding global.

---

## 4. Module Details

### 4.1 `coworker.analytics`

**Submodules:**

| Submodule | Path | Description |
|-----------|------|-------------|
| `db` | `coworker/analytics/db.py` | Database connection, schema creation, helper functions for INSERT/UPDATE/SELECT. |
| `import_data` | `coworker/analytics/import_data.py` | Parse IDE log files (JSON Lines) and insert into analytics DB. Deduplication logic. |
| `auto_import` | `coworker/analytics/auto_import.py` | File watcher (inotify) on IDE log directory; calls `import_data` on new log entries. |
| `knowledge` | `coworker/analytics/knowledge.py` | Extract knowledge from session summaries using DeepSeek LLM. Upsert into `knowledge` table and memo. |

### 4.2 `coworker.dashboard`

| Submodule | Path | Description |
|-----------|------|-------------|
| `app` | `coworker/dashboard/app.py` | Flask application, route definitions, startup logic. |
| `queries` | `coworker/dashboard/queries.py` | SQL query builders for each API endpoint, aggregation functions. |
| `static` | `coworker/dashboard/static/` | HTML/CSS/JS files for the single‑page dashboard. |

### 4.3 `coworker.memory`

| Submodule | Path | Description |
|-----------|------|-------------|
| `mem0_client` | `coworker/memory/mem0_client.py` | Wrapper for mem0 Python SDK (Qdrant backend). |
| `llm` | `coworker/memory/llm.py` | DeepSeek LLM client with provider fallback chain. |
| `capture` | `coworker/memory/capture.py` | Receives content → safety filter → LLM dedup → store to mem0. |
| `engine` | `coworker/memory/engine.py` | Orchestrates capture, curation, training workflows. |
| `inject` | `coworker/memory/inject.py` | Vector search → LLM summarization → context string for CLAUDE.md. |
| `curator` | `coworker/memory/curator.py` | Periodically reviews pending captures, merges duplicates, promotes to long‑term. |
| `train` | `coworker/memory/train.py` | Fine‑tuning pipeline (future: LORA‑style embedding adaptation). |
| `pending` | `coworker/memory/pending.py` | Queue for incoming captures awaiting curation. |
| `safety` | `coworker/memory/safety.py` | Blocklist, regex patterns, PII scanner. |
| `audit` | `coworker/memory/audit.py` | Log every memory operation (capture, delete, promote) to audit table. |
| `metrics` | `coworker/memory/metrics.py` | Collect vector store stats and LLM call statistics. |
| `validate` | `coworker/memory/validate.py` | Ensure memory consistency (no orphan sessions, proper metadata). |

### 4.4 `coworker.templates`

| Submodule | Path | Description |
|-----------|------|-------------|
| `global_claude_md` | `coworker/templates/global_claude_md.py` | Generate the global CLAUDE.md content based on user config. |
| `local_claude_md` | `coworker/templates/local_claude_md.py` | Generate the local session CLAUDE.md with memory injection. |

### 4.5 `coworker.autoworker`

| Submodule | Path | Description |
|-----------|------|-------------|
| `engine` | `coworker/autoworker/engine.py` | Main loop: collect analytics → propose improvements → apply changes. Sub‑modules for analysis, proposal, review, apply. |

---

## 5. Error Handling & Resilience

### 5.1 Circuit Breaker Pattern

Implemented in `coworker.memory.llm` and `coworker.autoworker.engine`.

```
State machine: CLOSED → OPEN (after N consecutive failures) → HALF_OPEN (after timeout) → CLOSED.
- Threshold: 5 failures in 60 seconds → trip breaker.
- Timeout: 30 seconds before HALF_OPEN.
- On HALF_OPEN: allow 1 request; if success → CLOSED; if fail → OPEN again.
- Cooldown: exponential backoff (30s, 60s, 120s).
```

### 5.2 Provider Fallback Chain

Failover order for LLM calls:

```
DeepSeek (primary) → Gemini (secondary) → Claude (tertiary) → fallback rule: use local heuristic/rule‑based response.
```

Each provider is wrapped with its own circuit breaker. If all three fail, the system falls back to a static response (“Unable to process request; please check network and API keys.”).

### 5.3 Audit Logging

All operations that change state (memory capture, skill install, auto‑worker apply) are logged to an audit table in analytics.db:

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    action TEXT NOT NULL,                     -- 'memory_capture', 'skill_install', 'autoworker_apply'
    actor TEXT,                               -- 'user', 'system', 'autoworker'
    target TEXT,                              -- ID or path
    details TEXT,                             -- JSON with context
    success INTEGER DEFAULT 1,               -- 0 = failure
    error_message TEXT
);
```

### 5.4 Wrong‑History Prevention Rules

To avoid injecting irrelevant or hallucinated knowledge:

1. **Time decay**: Memory entries older than 90 days are deprioritised (unless explicitly tagged “archived”).
2. **Source trust**: Only entries from validated sessions (where `session_type='auto'` or manual flag) are injected. Entries from test/fake sessions are discarded.
3. **LLM dedup**: Before capture, content is hashed and compared against existing documents (cosine similarity > 0.92 triggers merge).
4. **Keyword filter**: Memory injection is blocked if injected context contains banned phrases from `safety.txt` (e.g., credential leakage, production credentials).
5. **Manual override**: Users can `walter-worker knowledge block <id>` to suppress a specific memory entry.

---

## 6. Dependencies

### 6.1 Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `click` | >=8.1 | CLI framework |
| `pyyaml` | >=6.0 | Frontmatter parsing |
| `flask` | >=2.3 | Dashboard webserver |
| `werkzeug` | >=2.3 | WSGI toolkit |
| `sqlite3` | (stdlib) | Analytics database |
| `mem0` | >=0.3.0 | Vector memory substrate |
| `qdrant-client` | >=1.6 | Vector DB backend for mem0 |
| `openai` (deep‑seek‑ compatible) | >=1.0 | DeepSeek API calls |
| `google-genai` | >=0.2 | Gemini provider fallback |
| `anthropic` | >=0.30 | Claude provider fallback |
| `aiofiles` | >=23 | Async file reading (analytics watcher) |
| `watchdog` | >=3.0 | Inotify‑based auto‑import |
| `requests` | >=2.31 | HTTP client for dashboard tests |
| `pytest` | >=7.4 | Testing framework |
| `black`, `isort`, `ruff` | latest | Code formatting |

### 6.2 External Services

| Service | Usage | Authentication |
|---------|-------|----------------|
| **DeepSeek API** | Primary LLM for knowledge extraction, memory dedup, summarization. | API key in `.local_config.yaml` |
| **Qdrant (self‑hosted or cloud)** | Vector store for mem0. | Optional: `QDRANT_URL`, `QDRANT_API_KEY` |
| **GitHub (optional)** | Auto‑worker change proposals via PRs. | GitHub token for repo operations |

### 6.3 IDE Integrations

| IDE | Integration Method | Details |
|-----|-------------------|---------|
| **Claude Code** | Hook via `install.sh` | Wraps session start/end; injects CLAUDE.md; captures tool calls. |
| **OpenCode / Continue** | Separate MCP block in config | `walter-worker mcp install` adds profile for model loader. |
| **Cursor** | Post‑session script | Reads `.cursor/sessions/` logs; calls `analytics.import`. |
| **VS Code (generic)** | Extension (planned) | Listens to `vscode‑debug` and file save events. |

---

This specification documents all active architectural decisions as of 2026-07-25. For upcoming changes (Wave 4 memory training, self‑evolution UI), see `docs/roadmap.md`.