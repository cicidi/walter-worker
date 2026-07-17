# Analytics Listener — Design Document

> Unified chat history / tool call / skill call collector for Claude Code and OpenCode.
> Raw data stored locally as JSONL, later imported into database for analysis.

## 1. Requirements Summary

| Dimension | Decision |
|------|------|
| Purpose | Usage analytics |
| Scope | Local, personal use |
| Granularity | Full content recording (chat messages, tool args/results) |
| Strategy | Claude Code + OpenCode each implement independently, unified storage format |
| Time | Local timezone |

## 2. Architecture Overview

```
                    ~/.coworker/analytics/
                      sessions/{session-id}/
                        messages.jsonl
                        tools.jsonl
                        session.yaml
                      index.jsonl
                      hooks/              (Claude Code scripts)
                        on-user-prompt.sh
                        on-pre-tool.sh
                        on-post-tool.sh
                        on-stop.sh
                   ↗                    ↖
           Claude Code Hooks      OpenCode Plugin
           (settings.json)        (.opencode/plugin)
```

- Claude Code: Driven by `.claude/settings.json` hooks that invoke shell scripts for recording
- OpenCode: Driven by `@opencode-ai/plugin` SDK with TypeScript recording
- Both operate independently, writing to the same local directory
- Eventually imported into SQLite/PostgreSQL for analysis (future design)

## 3. Data Model

### 3.1 session.yaml — Session Metadata

```yaml
session_id: "2026-06-11-T143052-a1b2c3"
created: "2026-06-11T14:30:52+08:00"
closed: "2026-06-11T15:45:10+08:00"
ide: opencode
project: ai-coworker
cwd: /home/cicidi/project/ai-coworker
initiative: auth-migration     # Read from CLAUDE.md, can be appended mid-session
branch: feat/oauth2             # git branch --show-current
```

### 3.2 messages.jsonl — Chat Messages

Each message is one line of JSON:

```json
{"ts":"2026-06-11T14:30:52+08:00","type":"user","seq":1,"content":"Help me write a listener"}
{"ts":"2026-06-11T14:31:05+08:00","type":"assistant","seq":2,"content":"Ok, let me explore first..."}
```

| Field | Description |
|------|------|
| `ts` | Local time, ISO 8601 with timezone |
| `type` | `user` / `assistant` |
| `seq` | Global auto-increment sequence number |
| `content` | Message text |

### 3.3 tools.jsonl — Tool Calls

Each is one tool call. Pre and post are written separately and independently:

```json
{"ts":"2026-06-11T14:31:05+08:00","phase":"before","tool":"bash","tool_type":"builtin","call_id":"toolu_01","seq":3,"args":{"command":"ls","description":"List files"}}
{"ts":"2026-06-11T14:31:10+08:00","phase":"after","tool":"bash","tool_type":"builtin","call_id":"toolu_01","seq":4,"result":"README.md\nsrc/","duration_ms":5230}
```

| Field | Description |
|------|------|
| `ts` | Local time, ISO 8601 with timezone |
| `phase` | `before` / `after` |
| `tool` | Tool name (Bash/Read/Write/Edit/Skill/Glob/Grep/TodoWrite/WebFetch...) |
| `tool_type` | `builtin` / `mcp` |
| `server_name` | MCP server name (mcp type only) |
| `call_id` | Tool call ID, links before and after |
| `seq` | Global auto-increment sequence number |
| `args` | Tool arguments (before only) |
| `result` | Tool result (after only) |
| `duration_ms` | Execution duration in ms (after only) |

Design notes:
- Pre and post are recorded independently; whoever triggers writes, no inter-dependency
- Claude Code often drops pre or post hooks — this design preserves at least half the data
- Group by `call_id` to reconstruct the full call

### 3.4 index.jsonl — Session Index

One line appended when each session ends:

```json
{"session_id":"a1b2c3","created":"2026-06-11T14:30:52+08:00","ide":"opencode","project":"ai-coworker","message_count":45,"tool_count":12}
```

## 4. Claude Code Implementation

### 4.1 Hook Configuration

In `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [{ "command": "~/.coworker/analytics/hooks/on-user-prompt.sh" }],
    "PreToolUse":       [{ "command": "~/.coworker/analytics/hooks/on-pre-tool.sh" }],
    "PostToolUse":      [{ "command": "~/.coworker/analytics/hooks/on-post-tool.sh" }],
    "Stop":             [{ "command": "~/.coworker/analytics/hooks/on-stop.sh" }]
  }
}
```

### 4.2 Hook Script Responsibilities

| Hook | Script | Writes |
|------|------|------|
| `UserPromptSubmit` | `on-user-prompt.sh` | `messages.jsonl` (type: user) + creates session on first trigger |
| `PreToolUse` | `on-pre-tool.sh` | `tools.jsonl` (phase: before) |
| `PostToolUse` | `on-post-tool.sh` | `tools.jsonl` (phase: after) |
| `Stop` | `on-stop.sh` | Updates `session.yaml` closed + appends `index.jsonl` |

### 4.3 Session ID Generation

Generated on first `UserPromptSubmit`: `$(date +%Y-%m-%d-T%H%M%S)-$(openssl rand -hex 3)`

## 5. OpenCode Implementation

### 5.1 Plugin Structure

```
.opencode/coworker-analytics/
  index.ts          # Plugin entry point
  recorder.ts       # Core write logic
  session.ts        # Session lifecycle management
```

### 5.2 Hook Mapping

| OpenCode Hook | Behavior |
|---------------|------|
| `event` | Listen `session.created` → create session dir + `session.yaml`; `session.deleted` → update closed + write `index.jsonl` |
| `chat.message` | Each message → `messages.jsonl` |
| `tool.execute.before` | → `tools.jsonl` (phase: before) |
| `tool.execute.after` | → `tools.jsonl` (phase: after) |

### 5.3 Recorder Core

- `fs.appendFileSync` appends to JSONL
- In-memory auto-increment `seq` counter
- Auto-creates session directory

## 6. Listener Responsibility Boundary

**Listener only dumps raw data, does no processing:**
- Writes messages.jsonl, tools.jsonl, session.yaml
- Does not parse file paths, infer project, or merge pre/post

**DB import script handles all data processing:**
- Merges pre+post tool calls
- Parses file operations (Read/Write/Edit/Glob → file_ops table)
- Infers project (matches path against project catalog)
- Infers file_type (from extension)
- Detects call chains (parent_call_id)
- Extracts initiative from CLAUDE.md
- Detects git branch and initiative switches

## 7. SQLite Database & Import Script

> Import script handles merge / clean / parse, writes to SQLite.

### 7.1 Table Schema

```sql
CREATE TABLE sessions (
    id            TEXT PRIMARY KEY,
    ide           TEXT NOT NULL,
    project       TEXT,
    cwd           TEXT,
    model         TEXT,
    initiative    TEXT,
    branch        TEXT,
    created_at    TEXT NOT NULL,
    closed_at     TEXT
);

CREATE TABLE messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL REFERENCES sessions(id),
    seq           INTEGER NOT NULL,
    type          TEXT NOT NULL,
    content       TEXT,
    ts            TEXT NOT NULL
);
CREATE INDEX idx_msg_session_seq ON messages(session_id, seq);

CREATE TABLE tool_calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    call_id         TEXT NOT NULL,
    tool            TEXT NOT NULL,
    tool_type       TEXT DEFAULT 'builtin',    -- builtin | mcp
    server_name     TEXT,                      -- MCP server name
    parent_call_id  TEXT,
    parent_skill    TEXT,                      -- Skill name context
    args            TEXT,
    result          TEXT,
    duration_ms     INTEGER,
    seq_before      INTEGER,
    seq_after       INTEGER,
    ts              TEXT NOT NULL
);
CREATE INDEX idx_tc_session ON tool_calls(session_id);
CREATE INDEX idx_tc_parent ON tool_calls(parent_call_id);
CREATE INDEX idx_tc_tool ON tool_calls(tool);

CREATE TABLE file_ops (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    call_id     TEXT NOT NULL,
    op          TEXT NOT NULL,
    path        TEXT NOT NULL,
    file_type   TEXT,
    project     TEXT,
    skill_name  TEXT,                           -- Which skill triggered this file operation
    seq         INTEGER NOT NULL,
    ts          TEXT NOT NULL
);
CREATE INDEX idx_fo_session ON file_ops(session_id);
CREATE INDEX idx_fo_type ON file_ops(file_type);
CREATE INDEX idx_fo_project ON file_ops(project);

CREATE TABLE session_stats (
    session_id    TEXT PRIMARY KEY REFERENCES sessions(id),
    message_count INTEGER DEFAULT 0,
    tool_count    INTEGER DEFAULT 0,
    skill_count   INTEGER DEFAULT 0,
    read_count    INTEGER DEFAULT 0,
    write_count   INTEGER DEFAULT 0,
    bash_count    INTEGER DEFAULT 0,
    duration_min  INTEGER,
    updated_at    TEXT NOT NULL
);

-- Skill metadata (aggregated by import script from tool_calls)
CREATE TABLE skills (
    name           TEXT PRIMARY KEY,
    total_calls    INTEGER DEFAULT 0,
    last_invoked   TEXT,
    first_invoked  TEXT
);

-- Knowledge cards (written by Knowledge Skill)
CREATE TABLE knowledge (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    type            TEXT NOT NULL,              -- trap | best_practice | pattern | decision | constraint
    session_id      TEXT REFERENCES sessions(id),
    project         TEXT,
    skills          TEXT,                       -- JSON array
    summary         TEXT,
    evidence        TEXT,                       -- JSON array
    generated_at    TEXT NOT NULL,
    merged_to_skill TEXT
);
CREATE INDEX idx_knowledge_project ON knowledge(project);
CREATE INDEX idx_knowledge_session ON knowledge(session_id);

-- Session summaries (written by Knowledge Skill)
CREATE TABLE session_summaries (
    session_id             TEXT PRIMARY KEY REFERENCES sessions(id),
    sop_workflows          TEXT,                -- JSON array
    context_to_remember    TEXT,
    effective_operations   TEXT,                -- JSON array
    pitfalls_and_fixes     TEXT,                -- JSON array
    wasted_actions         TEXT,                -- JSON array
    bottlenecks            TEXT,                -- JSON array
    efficiency_tip         TEXT,
    efficiency_score       REAL,
    think_action_ratio     REAL,
    edit_redundancy        REAL,
    loop_count             INTEGER,
    user_wait_minutes      REAL,
    memory_keywords        TEXT,                -- Extracted keywords for Obsidian graph
    generated_at           TEXT NOT NULL
);
```

### 7.2 Import Flow

```
JSONL raw data
      ↓
  import.py
      ├─ Merge pre+post tool call (by call_id)
      ├─ Extract file_ops (Read/Write/Edit/Glob → path, type, project)
      ├─ Infer parent_call_id + parent_skill (call chain)
      ├─ Aggregate skills table
      ├─ Extract initiative from CLAUDE.md
      ├─ Compute session_stats
      └─ Detect git branch and initiative switches
      ↓
  analytics.db
```

### 7.3 Knowledge Skill (Session Summaries)

Standalone skill that calls OpenCode SDK in non-interactive mode, reads SQLite data, feeds to LLM for structured summarization.

**Trigger methods:**
- Auto-run on session close (hook after import script completes)
- Manual trigger: `coworker knowledge summarize <session_id>`
- Batch mode: `coworker knowledge analyze --since yesterday`

**Process:**
```
SQLite (session data) → Knowledge Skill (LLM) → SQLite (session_summaries, knowledge)
```

**Tables written:**
- `session_summaries` — per-session structured summaries
- `knowledge` — cross-session knowledge cards (patterns triggered ≥2 times)
- `skills` — update skill metadata

### 7.4 Analytics Queries

```sql
-- skill/tool call stats (by session/initiative/branch)
SELECT s.initiative, s.branch, t.tool, COUNT(*) AS cnt
FROM tool_calls t JOIN sessions s ON s.id = t.session_id
WHERE t.tool = 'Skill'
GROUP BY s.initiative, s.branch;

-- file read/write stats (by type/project)
SELECT project, file_type, op, COUNT(*) AS cnt
FROM file_ops GROUP BY project, file_type, op
ORDER BY cnt DESC;

-- session complete timeline
SELECT seq, type, content, tool, args, result FROM messages m
LEFT JOIN tool_calls t ON t.call_id = m.tool_call_id
WHERE m.session_id = ?
ORDER BY seq;
```

## 8. Installation

`setup/install.sh` handles:

1. Creates `~/.coworker/analytics/sessions/` directory
2. Copies 4 hook scripts to `~/.coworker/analytics/hooks/`
3. Merges hook config into project `.claude/settings.json`
4. Creates SQLite database `~/.coworker/analytics/analytics.db` and executes DDL

OpenCode side requires no install — plugin ships with `.opencode/` directory.

## 9. Error Handling

Core principle: listener errors must not affect normal AI operation.

| Scenario | Strategy |
|------|------|
| Disk full | Silent failure, do not block AI |
| Permission denied | Write to `~/.coworker/analytics/.errors.log`, do not throw |
| Data format error | Write raw data to `.errors.log`, skip the entry |
| Concurrent writes | JSONL O_APPEND atomic operation is inherently safe |
| Directory missing | recorder auto-creates |

All hook scripts and plugin entry points use try-catch + silent degradation.

## 10. Testing Strategy

Manual verification flow:

1. Start an AI session (Claude Code or OpenCode)
2. Perform several operations (send messages, call tools, use skills)
3. End the session
4. Check that correct files were generated under `~/.coworker/analytics/sessions/`
5. Verify each JSONL line is valid JSON, timestamps correct, seq increments without gaps

## 11. TODO / Dependencies

- **Initiative tracking**: Currently `initiative-create/activate` injects INITIATIVE block into CLAUDE.md. DB import script needs to parse CLAUDE.md to extract current initiative. The listener's own session.yaml may not contain initiative (to be filled in by the import script).
- **Skill 5/6** (session summaries + memory-search): Not in current scope, separate design to follow.
