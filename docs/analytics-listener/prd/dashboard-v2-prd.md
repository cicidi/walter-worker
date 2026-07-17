# Dashboard v2 — PRD

> **Status**: DRAFT
> **Owner**: Walter Chen
> **Date**: 2026-07-14
> **Scope**: Full rewrite of analytics dashboard with 9 views, token/cost tracking, expandable context, and interactive graphs

---

## 1. Overview

A local-first web monitoring dashboard for AI coding sessions. Realtime visibility into agent behavior across Claude Code, OpenCode, and Gemini.

### 1.1 Architecture

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLite |
| Frontend | Vanilla JS + CSS (no framework) |
| Styling | Dark theme, stat cards, expandable list-items |
| Data | Shared SQLite with analytics pipeline |

### 1.2 Design Principles

- Everything clickable → drill down to detail
- Expandable list-items (not tables) for primary content
- Stat cards at top of each page with totals
- Real-time auto-refresh (15s for overview)
- All data actionable → navigate to sub-views

---

## 2. Views

### 2.1 Overview (HOME)

**Purpose**: At-a-glance health of the AI coding system.

**Elements**:
| Element | Behavior |
|---------|----------|
| Total Sessions | Click → Sessions page |
| Messages | Static (no dedicated page, shown in session timeline) |
| Tool Calls | Click → Tools page |
| Skills Used | Click → Skills page |
| Knowledge Cards | Click → Knowledge page |

**Daily Sessions Chart**:
- Bar chart showing sessions per day
- Range selector: `[7d] [14d] [30d] [90d] [180d] [365d]`
- Fetches live data on range change via `/api/daily-sessions?days=N`

**Tool Distribution**:
- Top tools by call count
- Click any tool → Tools page
- "View all N tools →" link at bottom

**Recent Sessions**:
- 10 most recent sessions
- Each expandable with detail panel
- Shows: project, initiative, message count, tool count, duration, start time
- "View Full Timeline" button in expanded panel

### 2.2 Projects

**Purpose**: Track work across projects, merge worktree sessions into base projects.

**Elements**:
| Element | Detail |
|---------|--------|
| Row | Project name, session count, initiative count, tool count |
| Expand | Lazy-load sessions for that project |
| Root merging | Empty project → "root". Worktree paths (`-home-cicidi-project-X`) → `X` |
| Project type | java / python / ai-agent / ai-harness / ui (future) |
| Dependency graph | Starlink-style interactive force-directed graph with draggable nodes |

**Future**:
- Meta repo, upstream, downstream per project
- Skill call count per project
- Project type classification

### 2.3 Sessions

**Purpose**: All recorded AI coding sessions with full message timeline.

**Elements**:
| Element | Detail |
|---------|--------|
| Row | Session ID, IDE, project, initiative, msg count, tool count, duration, start time |
| Expand | Lazy-loads message timeline |
| Timeline | User prompts (👤) + AI responses (🤖) + tool calls, reverse chronological |
| Turn count | Total user+assistant message pairs |
| Model | Model name used (empty for Claude Code sessions — import issue) |
| Flow diagram | UML-style process flowchart showing session steps with arrows (future) |

**Data issues**:
- Most sessions have empty message content (import pipeline doesn't store message text from hooks)
- Model field is empty for Claude Code sessions (JSONL doesn't expose model)

### 2.4 Models (replaces Monitor)

**Purpose**: Token consumption, cost analysis, LLM performance by model.

**Elements**:
| Element | Detail |
|---------|--------|
| Stat cards | Total tokens in/out, total cost, models used |
| Model breakdown | Per model: sessions, requests, avg/max duration, tokens in/out, cost |
| Tool performance | Avg duration per tool across all models |
| Expand per model | Project-level token breakdown (future) |

**Data sources**:
- OpenCode: `cost`, `tokens_input`, `tokens_output` now stored in `session_stats`
- Claude JSONL: tokens estimated from message content length (~4 chars/token)
- Session model field: parsed from OpenCode session data

### 2.5 Skills

**Purpose**: Track skill usage, content, and invocation patterns.

**Row**:
| Column | Source |
|--------|--------|
| Skill name | From tool_calls or skills table |
| Calls | Total invocations |
| Version | From SKILL.md frontmatter |
| Body size | Calculated from SKILL.md file size |
| % of total | Percentage of all skill calls |

**Time filter**: `[1d] [7d] [30d] [90d] [365d]` — filters the call timeline

**Expand panel**:
| Section | Content |
|---------|---------|
| Metadata | Name, version, total calls, skill size (KB), origin, first/last invoked, license |
| Description | From SKILL.md frontmatter `description:` or `when-to-use:` |
| Dependencies | `depends_on` or `dependencies` from frontmatter |
| Call history | Time, project, initiative, trigger (AI 🤖 via parent_skill / Human 👤 direct), session ID |
| SKILL.md | Full markdown content with scroll (collapsed by default) |
| Used by | Grouped by project with call count and session count |

### 2.6 Tools

**Purpose**: Track tool invocations across all sessions.

**Row**:
| Column | Source |
|--------|--------|
| Tool name | From tool_calls |
| Type | MCP or Builtin |
| Calls | Total invocations |
| Avg duration | Average execution time |
| Max duration | Maximum execution time |
| Server | For MCP tools |

**Expand panel**:
| Section | Content |
|---------|---------|
| Metadata | Tool, type, total calls, unique sessions, avg duration, server, tool type |
| Call timeline | Session ID, project, initiative, duration, IDE, timestamp |
| Used in sessions | Grouped by session with call count and avg ms |

### 2.7 Files

**Purpose**: Track file read/write operations with rich filtering.

**Filters** (4 inline search boxes):
- Filename
- File type (`.py`, `.md`, `.json`, etc.)
- Project
- Initiative

**Row**:
| Column | Source |
|--------|--------|
| File path | From file_ops.path |
| Reads | Count of read operations |
| Writes | Count of write+edit operations |
| Branch | Git branch from session |
| Projects | Comma-separated project list |
| Last access | Most recent timestamp (future) |

**Expand panel**:
| Section | Content |
|---------|---------|
| Metadata | Full path, total ops, reads, writes |
| Timeline | Each operation: read(📖)/write(✏️), by IDE, by skill, project, timestamp |

**File types (future)**: Classify as prd/spec/plan/readme/web-article/slack/wiki based on path pattern.

**Link tracking**: Web URLs, Slack message links, wiki links that AI reads count as files.

### 2.8 Knowledge

**Purpose**: LLM-generated insights with rich, practical summaries.

**Row**:
| Column | Source |
|--------|--------|
| Title | knowledge.title |
| Type | knowledge.type (trap/best/pattern/insight) |
| Project | knowledge.project or session.project |
| Created | knowledge.generated_at |

**Expand panel** (4-section layout):
| Section | Purpose |
|---------|---------|
| 🎯 What I Was Working On | Project/task/problem being solved |
| ⚠️ Problems & Repeated Retries | Difficulties encountered, things retried multiple times |
| ✅ Lessons & Reusable Experience | What can be reused, shortcuts, data to remember |
| 🚫 What To Avoid | Anti-patterns, things that should never be done again |
| 🔍 Evidence & Examples | Specific examples from sessions |

**Future**:
- Knowledge recall detection — which cards were reused across sessions
- Re-run knowledge summary job with better prompts
- Link knowledge cards to the skills they inspired

### 2.9 Initiatives

**Purpose**: Cross-session workstreams with context analysis.

**Row**:
| Column | Source |
|--------|--------|
| Initiative name | sessions.initiative |
| Sessions | Count of sessions in this initiative |
| Project | Primary project |
| Tool calls | Total tool calls across initiative sessions |

**Expand panel**:
| Section | Content |
|---------|---------|
| Metadata | Name, sessions, project, first/last session time |
| Sessions list | All sessions with message count and time |
| ✅ Tools in context | Tools used BY initiative sessions (with counts) |
| ❌ Tools not in context | Tools used ELSEWHERE but not in this initiative |
| Future | Files in context vs not, skills in context vs not |

---

## 3. Backend API

### 3.1 Existing Endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/overview` | Aggregate stats + recent sessions + tool distribution + daily sessions |
| `GET /api/sessions?limit=N` | Session list with stats JOIN |
| `GET /api/sessions/{id}` | Full session detail (messages, tool_calls, file_ops, summary, stats) |
| `GET /api/sessions/{id}/timeline` | Unified chronological timeline |
| `GET /api/sessions/{id}/messages` | All messages for a session (reverse chronological) |
| `GET /api/skills` | Skills list with call counts |
| `GET /api/tools` | Tools list with aggregate stats |
| `GET /api/files` | File operations with filters |
| `GET /api/knowledge` | Knowledge cards |
| `GET /api/initiatives` | Initiative aggregate stats |
| `GET /api/projects` | Project aggregation with worktree merging |
| `GET /api/models` | Model usage with token/cost aggregation |
| `GET /api/daily-sessions?days=N` | Daily session counts for N days |
| `GET /api/tool-sessions?tool=X` | Sessions using a specific tool |
| `GET /api/skill-detail?name=X&days=N` | Skill call details |
| `GET /api/skill-timeline?name=X&days=N` | Skill timeline |
| `GET /api/tool-detail?tool=X` | Tool call details |
| `GET /api/file-detail?...` | File operations with filters (name/type/project/initiative) |

### 3.2 New Endpoints Needed

| Endpoint | Purpose |
|----------|---------|
| `GET /api/skill-usage?days=N` | Skills with N-day usage stats |
| `GET /api/knowledge-regenerate` | Trigger knowledge re-analysis |
| `GET /api/models/{model}/projects` | Per-project breakdown for a model |
| `GET /api/initiatives/{name}/context` | Full context analysis for initiative |

---

## 4. Database Schema

### 4.1 Current (`session_stats`)

```sql
session_id    TEXT PRIMARY KEY,
message_count INTEGER DEFAULT 0,
tool_count    INTEGER DEFAULT 0,
skill_count   INTEGER DEFAULT 0,
read_count    INTEGER DEFAULT 0,
write_count   INTEGER DEFAULT 0,
bash_count    INTEGER DEFAULT 0,
duration_min  INTEGER,
tokens_input  INTEGER DEFAULT 0,    -- NEW
tokens_output INTEGER DEFAULT 0,   -- NEW
cost          REAL DEFAULT 0,       -- NEW
turn_count    INTEGER DEFAULT 0,    -- NEW
updated_at    TEXT NOT NULL
```

### 4.2 Schema Needed

| Table | Purpose |
|-------|---------|
| `project_meta` | Project type, repo URL, upstream/downstream deps |
| `knowledge_recall` | Track when knowledge cards are re-used |
| `file_classifications` | File type classification rules |

---

## 5. Import Pipeline

### 5.1 OpenCode

- Reads `cost`, `tokens_input`, `tokens_output` from opencode.db → ✅ DONE
- Stores in `session_stats` → ✅ DONE

### 5.2 Claude Code JSONL

- Parses message content to estimate tokens → ✅ DONE
- Does NOT store actual message text → ❌ TODO (messages table empty)
- Does NOT expose model info → model field empty

### 5.3 Claude Code Hooks

- Stores session metadata, message count, tool count
- Does NOT store individual message content → messages table empty for hook sessions
- **Fix needed**: Store message content from hook JSON

---

## 6. Future Roadmap

| Feature | Priority | Effort |
|---------|----------|--------|
| Starlink interactive dependency graph | P0 | L |
| Knowledge re-run job | P0 | M |
| Session UML flow diagram | P1 | XL |
| Message content storage in import | P1 | M |
| File type classification (prd/spec/slack/wiki) | P1 | M |
| Project type & metadata | P1 | S |
| Knowledge recall detection | P2 | M |
| Model per-project breakdown | P2 | S |
| Token cost estimation for Claude | P2 | S |
| Session multi-model tracking | P2 | M |
| WebSocket live updates | P3 | M |
