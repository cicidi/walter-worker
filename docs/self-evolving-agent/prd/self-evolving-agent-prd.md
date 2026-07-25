# Self-Evolving Agent — PRD

> Goal: Ship an autonomous agent that self-evolves in a continuous loop to achieve a goal. The agent is Claude Code, harnessed by ai-coworker. The agent takes real action — monitor, orchestrate — grounded in real sources.

## Status

| St | Date | Author |
|----|------|--------|
| 🚧 draft v2 | 2026-07-24 | cicidi + Claude |

## Change Log

| Date | Change |
|------|--------|
| 2026-07-24 | v2: Added safety architecture (Section 5.6), loop state machine spec (Section 2.1), hook reliability mitigations (Section 3.3), cost model (Section 6.6), error handling (Section 6.7), quality metrics (Section 5.2), Guild evaluation (Appendix A). Resolved 3 open questions. |
| 2026-07-24 | Initial draft |

---

## 1. Overview

### 1.1 Vision

A Claude Code agent that continuously improves itself by working on real tasks. Each session, each turn, each mistake feeds back into the system — skills are auto-created, memory persists, behaviors evolve. The agent gets smarter the more you use it.

### 1.2 Implementation Reference

**Current choice:** [Hermes Agent](https://github.com/NousResearch/hermes-agent) (Nous Research, MIT, v0.18.2) as implementation basis for memory architecture and self-evolution patterns. Hermes's closed learning loop — auto skill creation, skill patching, persistent MEMORY.md — maps directly to our requirements. We adapt only the trigger mechanism (hook/plugin instead of built-in agent loop), keeping the rest replaceable if a better alternative emerges later.

> **Note on Hermes-EvoMap controversy (April 2026):** Hermes has been accused of drawing from EvoMap's Evolver engine without attribution. Our use is protected: Hermes is MIT-licensed (permissive, irrevocable), and ai-coworker reimplements architectural patterns (section-delimited memory files, FTS5 schema, sidecar JSON usage tracking) rather than copying code. All modules are explicitly replaceable per Section 6.5. See Appendix A for evaluation of Guild Agent as alternative backend.

### 1.3 Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Loop architecture | Hybrid: ai-coworker = control plane, Claude Code = execution plane | ai-coworker already manages context; Claude Code executes |
| Goal model | Meta-goal: self-improvement as primary driver, real work as training ground | Mode C — agent evolves through use |
| Evolution scope | Skills + Context + Code + Config (full scope) | Mode D — everything the agent touches can improve |
| Memory architecture | MEMORY.md + FTS5 + Curator | Per-turn sync, cross-IDE/cross-project search, periodic cleanup |
| Background LLM | DeepSeek Flash (primary) + fallback (Gemini Flash or Claude Haiku) | Cheap, fast; fallback prevents single-provider outage |
| Background LLM cost note | DeepSeek Flash peak pricing (9-12, 14-18 Beijing) = 2x base rate | Budget limits needed for peak-hour autonomous runs |
| Skill creation | Reuse existing `skill-create` / `skill-edit` | Don't reinvent — trigger them automatically |
| Orchestration | Claude Code decides how to decompose tasks | ai-coworker doesn't hardcode workflows |
| Implementation basis | Hermes Agent (MIT) for memory + skill lifecycle | Reusable, proven, replaceable |
| Principles | 优先复用 → 不够改造 → 没轮子造轮子 | Pragmatic, not dogmatic |

### 1.4 Knowledge Taxonomy

The agent generates three types of knowledge. Each has distinct storage, lifecycle, and triggers:

| Type | Definition | Example | Storage | Trigger |
|------|-----------|---------|---------|---------|
| **SOP** | 可重复的操作流程 — step-by-step procedure for a specific task | "修复 lint 错误的标准流程"、"部署到 production 的检查清单" | `SKILL.md`（本地 `~/.coworker/skills/`） | 复杂任务完成后自动判断 → `skill-create` |
| **经验总结** | 对/错的教训、发现的模式、坑点 — lessons, patterns, pitfalls learned through experience | "MCP 首次请求总是 403 超时，需重试"、"ruff E501 在这个项目被忽略" | `MEMORY.md`（§ 条目，`~/.coworker/memory/<project>/`） | 每 turn sync 自动提取 + session 结束 LLM 总结 |
| **State / 进度** | 当前状态 — what was done, what's right/wrong, what's done/pending, who's doing it, when it'll be done | "Dashboard 5 页完成 2 页 pending，blocker 是数据源 API 未就绪" | State 文件（`docs/<initiative>/state/YYYY-MM-DD-state.md`） | 每 turn / 每个 phase 完成 |

**SOP vs 经验：** SOP 是"怎么做"，经验是"发生了什么"。SOP 晋升到 skill-factory 分享给其他项目，经验留在项目 MEMORY.md 作为 context 参考。

**经验总结的提取：** LLM（DeepSeek Flash）分析每 turn 对话内容，识别：新发现的规则/约定、修正了之前的认知、可以复用的模式。提取结果写入 MEMORY.md 的对应项目条目。

---

## 2. Core Loop

```
┌─────────────────────────────────────────────────────────┐
│                ai-coworker (Control Plane)               │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐      │
│  │ Observe  │ →  │  Decide  │ →  │ Update Context│      │
│  │ analytics│    │ evaluate │    │ CLAUDE.local.md│    │
│  │ state    │    │ gaps     │    │ skills/memory │      │
│  └──────────┘    └──────────┘    └──────────────┘      │
│       ↑                              │                  │
│       │                              ↓                  │
│  ┌──────────┐                  ┌──────────────┐        │
│  │  Record  │ ←─────────────── │  Spawn Claude │        │
│  │ state    │   Execution      │  Code session │        │
│  │ memory   │   Plane          └──────────────┘        │
│  └──────────┘                                          │
└─────────────────────────────────────────────────────────┘
```

### 2.1 `coworker run` — Loop State Machine

```bash
coworker run --goal "fix all lint errors in this project" [--loop] \
    --max-iterations 20 --max-cost 10.00 --max-time 4h
```

#### 2.1.1 Cycle Definition

One cycle = **Observe → Decide → Spawn Claude Code → Record**. Each cycle produces concrete output or a deliberate no-op decision.

**States:**

```
                    ┌──────────────────────┐
                    │    INIT              │
                    │  Load snapshot       │
                    │  Parse goal + budget │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
              ┌────→│    OBSERVE           │
              │     │  Read analytics      │
              │     │  Read state file     │
              │     │  Read memory snapshot│
              │     └──────────┬───────────┘
              │                │
              │                ▼
              │     ┌──────────────────────┐
              │     │    DECIDE            │
              │     │  Evaluate vs goal    │
              │     │  Check termination   │
              │     │  Plan next action    │
              │     └──────────┬───────────┘
              │                │
              │        ┌───────┴───────┐
              │        │               │
              │        ▼               ▼
              │ ┌──────────┐   ┌──────────────┐
              │ │ TERMINATE│   │    SPAWN      │
              │ │ (success,│   │  Claude Code  │
              │ │  stalled,│   │  session with │
              │ │  budget) │   │  sub-goal     │
              │ └──────────┘   └──────┬─────────┘
              │                       │
              │                       ▼
              │              ┌──────────────────────┐
              └──────────────│    RECORD            │
                             │  Sync memory         │
                             │  Update state file   │
                             │  Update CLAUDE.local.md│
                             └──────────────────────┘
```

#### 2.1.2 Termination Conditions

The loop terminates when ANY of these are met:

| # | Condition | Detection |
|---|-----------|-----------|
| 1 | **Goal achieved** | User-provided success criteria evaluated true (e.g., `pytest --exitfirst` returns 0, `ruff check` returns 0) |
| 2 | **Stagnation** | 3 consecutive cycles produce no new changes (no code diff, no skill created/patched, no memory entry added) |
| 3 | **Budget exhausted** | `--max-iterations` reached, `--max-cost` exceeded, or `--max-time` elapsed |
| 4 | **Human halt** | Stop hook fires; human confirms "done" or "stop" in the prompt |

On terminate: write closing state, run post-session summarization (Section 5.4), mark initiative state as complete or paused.

#### 2.1.3 Error Recovery

| Failure | Recovery |
|---------|----------|
| Claude Code session errors (API timeout, rate limit) | Retry up to 3 times with exponential backoff; if all fail, record error in state and continue to next cycle |
| PostToolUse hook fails to fire | Stop hook fallback captures session summary; file-based audit trail (`~/.coworker/memory/audit.log`) provides third safety net |
| DeepSeek Flash API outage | Fallback to secondary provider (Gemini Flash or Claude Haiku); if both down, defer sync to next cycle |
| FTS5 index corruption | Auto-rebuild from MEMORY.md source of truth; log event |
| Concurrent session conflict | File lock (fcntl) on MEMORY.md; second session queues or skips |

#### 2.1.4 Budget Guards

| Flag | Default | Description |
|------|---------|-------------|
| `--max-iterations` | 20 | Maximum loop cycles |
| `--max-cost` | $5.00 | Maximum total API cost (Claude Code + DeepSeek Flash) |
| `--max-time` | 4h | Maximum wall-clock time |

Without `--loop`, `coworker run` executes ONE cycle and exits (spawn → record).

> **What gets auto-updated vs. what doesn't:** The "Update Context" and "Record" steps modify only **CLAUDE.local.md** (personal working context, not committed to git), skills in `~/.coworker/skills/`, and memory in `~/.coworker/memory/`. **CLAUDE.md** (shared team file, committed to git) is NEVER auto-modified — the self-evolution rules in Section 5.1/5.3 are written once by the human, not the agent. This separation ensures the agent evolves its personal context without altering team-wide conventions.

### 2.2 No Publish / Transact (MVP)

- `publish` and `transact` are out of scope for MVP
- `orchestrate` is delegated to Claude Code — ai-coworker doesn't hardcode task decomposition

---

## 3. Memory

### 3.1 Requirements

The agent must persist what it learns across sessions, projects, and IDEs:

- **R1 — IDE-agnostic:** Memory shared by Claude Code and OpenCode. Not locked to any single IDE's config directory.
- **R2 — Per-turn persistence:** Every turn's key information persisted without the agent manually invoking a save command.
- **R3 — Cross-session search:** Search across all past sessions, regardless of project or IDE. Keyword-based, fast, no external dependencies.
- **R4 — Agent-managed notes:** Agent can write, patch, and remove its own notes about the project (conventions, tool quirks, lessons learned) and user (preferences, workflow habits).
- **R5 — Frozen snapshot:** Each session starts with a stable snapshot of accumulated knowledge. Mid-session writes go to disk but don't perturb the active session's context.
- **R6 — Periodic cleanup:** Stale and unused entries are archived automatically. Hand-written entries are never touched.
- **R7 — Lightweight:** No vector database, no background server process. LLM used only for summarization/retrieval (one-shot), not continuously running.

### 3.2 Implementation: Hermes Memory Architecture

We use Hermes Agent's memory design as the implementation basis. Core components:

**MEMORY.md + USER.md** — Agent-managed note files with entries separated by `§`. Frozen snapshot at session start, mid-session writes via `coworker memory add|replace|remove` (writes disk immediately, snapshot unchanged).

**Storage layout:**

```
~/.coworker/memory/
├── fts5_index.db              ← Unified search across all projects + IDEs
├── audit.log                  ← File-based audit trail for hook failure recovery
├── <project>/
│   ├── MEMORY.md              ← Agent notes on this project
│   └── USER.md                ← Agent understanding of the user
└── curator/
    └── REPORT.md              ← Curator run reports
```

Storage in `~/.coworker/` (not IDE-specific directories) ensures both Claude Code and OpenCode can access the same memory.

### 3.3 Sync Flow — Dual-Trigger with Fallback

**Known PostToolUse hook limitations (Claude Code):** PostToolUse hooks have documented failure modes: global regression across sessions (v2.1.119+), no firing for MCP/Agent/Skill tool calls, stdout silently dropped, intermittent Windows failures (14% for Edit tools). Additionally, subagent findings (Agent tool) are structurally invisible to PostToolUse — a blind spot for the most content-rich tool calls.

**Mitigation: Dual-trigger + audit trail.**

```
┌──────────────┐        ┌──────────────┐
│  Claude Code  │        │   OpenCode    │
│              │        │              │
│ PostToolUse  │        │ tool.execute │
│    hook      │        │   .after     │
│              │        │              │
│ SessionStop  │        │ session.end  │
│    hook      │        │              │
└──────┬───────┘        └──────┬───────┘
       │                       │
       └───────────┬───────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │  coworker memory sync        │
    │  --session-id $SESSION_ID    │
    │  --ide claude|opencode       │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │  DeepSeek Flash (primary)    │
    │  ↓ fallback                  │
    │  Gemini Flash / Claude Haiku │
    │  提取关键信息                  │
    │  → MEMORY.md (project)       │
    │  → FTS5 index (global)       │
    │  → audit.log (timestamp)     │
    └──────────────────────────────┘
```

- **Trigger 1 (PostToolUse):** Per-tool-call sync for supported tool types. Covers most tool calls.
- **Trigger 2 (SessionStop):** End-of-session full sync as fallback. Captures what PostToolUse missed (Agent tool results, Skill invocations, MCP calls). Also triggers post-session summarization (Section 5.4).
- **Audit trail:** Every sync writes a timestamped record to `~/.coworker/memory/audit.log`. Enables detection of gaps: if session has no sync records for >N turns, flag for investigation.
- **Subagent blind spot:** Agent tool findings are invisible to PostToolUse. Mitigation: SessionStop summarization captures aggregate subagent results. For critical subagent work, the driving agent should explicitly invoke `coworker memory add` with key findings.

Fallback LLM: if DeepSeek Flash is unavailable (rate limit, outage), fall back to Gemini Flash or Claude Haiku. Both providers fail = defer sync to next cycle (no data loss — raw turn content preserved in session transcript).

### 3.4 Cross-Session Retrieval

```
coworker memory search "state engine design decision"
```

- SQLite FTS5 full-text index at `~/.coworker/memory/fts5_index.db`
- Each record tagged: `session_id`, `project`, `ide`, `timestamp`, `content`
- Search: FTS5 keyword match → candidate sessions → LLM (DeepSeek Flash) synthesizes answer
- Scope: all projects, all sessions, both IDEs
- No vector database for MVP (FTS5 is sufficient for keyword-based retrieval; hybrid BM25+vector deferred to v2)

### 3.5 Curator (Background Maintenance)

- **Trigger:** Every 7 days, after 2+ hours of agent idle time
- **FTS5 maintenance:** `PRAGMA optimize` runs daily (not weekly) to prevent index fragmentation from per-turn write load. WAL mode enabled for concurrent access. `automerge` for background incremental merging.
- **Actions:**
  - Track `view_count`, `use_count` per memory entry
  - 30 days unused → `stale` → 90 days unused → `archived`
  - High-count protection: entries used 50+ times are pinned (never archived)
  - Seasonal analysis: was this entry heavily used before going idle? If `historical_use_count > 20`, extend stale threshold 2x
  - Merge duplicate/overlapping entries
  - Generate `REPORT.md` in `~/.coworker/memory/curator/`
  - Only touches agent-created entries (never hand-written ones)
- **Un-archive:** `coworker memory unarchive <id>` recovers an archived entry
- **LLM:** DeepSeek Flash (with provider fallback)

### 3.6 Snapshot Injection

Both IDEs read CLAUDE.local.md at session start. The memory snapshot is injected there:

```markdown
<!-- MEMORY:ai-coworker START -->
## Memory Snapshot (frozen at session start)

### Project: ai-coworker
§ 项目使用 ruff linter，E501 忽略
§ 所有 PR 需通过 CI 才能合并
§ 上次 dashboard 开发在 session 71979623，5 页完成 2 页 pending

### User Preferences
§ 偏好中文交流
§ 喜欢先讨论再实现
§ 优先复用现有方案
<!-- MEMORY:ai-coworker END -->
```

- Snapshot updated on session start only (not during session)
- Mid-session writes go to disk but don't refresh the snapshot
- Old snapshot lines replaced entirely on next session start
- **Mid-session refresh:** `coworker memory refresh` reloads snapshot from disk into active context. Agent can invoke when it suspects stale context (e.g., long-running sessions >2h). Default behavior remains frozen snapshot.

---

## 4. State Engine

### 4.1 Trigger

Every turn → `PostToolUse` hook → async subagent writes to state file.

### 4.2 State File

```
docs/<initiative>/state/YYYY-MM-DD-state.md
```

- Live document, updated continuously (not just daily snapshot)
- Background subagent appends new events AND modifies previous entries (e.g., `🚧 → ✅`)
- Phase completion (PRD/spec/design/plan/test) forces a state update

### 4.3 Recording Criteria

Three dimensions — record if ANY one is met:

| Dimension | What it means |
|-----------|--------------|
| **做了什么** | Concrete output: code, docs, config, research conclusion, external action, automation |
| **对/错** | Lessons: what worked, what didn't, bugs found, blind spots exposed, compaction risks |
| **进度** | Tracking: done/not done/who's doing it/when done/dependencies |

**Always record:**
- Code changes, doc creation, config changes
- System events: MCP setup, model config, backup/restore, worktree, compaction, INDEX updates
- Research with conclusions, failed attempts, blind spot discoveries
- Initiative lifecycle, convention creation process
- Subagent exploration results (record conclusions, intermediate process optional)

**Never record:**
- Instant queries (just looking, no output)
- Single-command atomic ops (one `git commit` and done)
- Pure chat/curiosity/no decision made
- Transient status checks (just reading a number)

**Reference:** 24 confirmed case examples in `docs/self-evolving-agent/spec/state-recording-cases-spec.md` (to be written)

---

## 5. Self-Evolution Engine

### 5.1 Auto Skill Creation

**Triggers (dual):**

1. **In-session trigger:** Completing a task with a significant tool-call footprint. Default threshold: 10+ tool calls (calibrated for ai-coworker's multi-agent patterns; Hermes's 5+ threshold is too low — a single Claude Code task can generate 50+ tool calls). Threshold is configurable via `coworker config set skill.create.threshold`.

2. **Post-session trigger (SessionStop):** When DeepSeek Flash summarizes the session for MEMORY.md (Section 5.4), it simultaneously assesses whether any workflows, patterns, or problem-solving approaches from the session are reusable. If yes → invokes `skill-create` with the full session transcript as context. This trigger is more powerful than the in-session trigger because it has the complete session picture — it can identify cross-task patterns that individual task triggers miss.

**Rule in CLAUDE.md:**
```markdown
## Self-Evolution Rules

When you complete a complex task using significant tool calls:
1. Assess whether the workflow/pattern/knowledge is reusable
2. If yes → invoke `skill-create` to generate SKILL.md automatically
```

**Approval model:**

| Mode | Behavior |
|------|----------|
| **Review mode** (`auto_approve: false`, DEFAULT) | Skills staged to `~/.coworker/pending/skills/` — user reviews with `coworker skill pending` |
| **Auto mode** (`auto_approve: true`) | Skills auto-created without prompting (opt-in) |

- Memory writes: lightweight, reviewed inline
- Skill writes: always staged (too large for inline preview)
- Background creation: always staged (no user present)
- Pending store: `~/.coworker/pending/{memory,skills}/<id>.json`, survives restarts
- **Safety gates** (see Section 5.6 for full safety architecture):
  - Circuit breaker: if >3 skills are created or patched within 24 hours, halt all auto-evolution and notify user
  - Sandbox test: auto-created skills must pass a dry-run before promotion from pending
  - Rollback: any skill auto-patched can be reverted to previous version via `coworker skill rollback <name>`

> Implementation: follows Hermes `write_approval` pattern, modified with safety-first defaults.

### 5.2 Skill Lifecycle & Promotion

Skills are created **locally first**, not directly in skill-factory. They earn their way up.

```
Agent 创建 skill
       │
       ▼
~/.coworker/skills/<name>/SKILL.md    ← 共享存储（IDE 无关）
       │
       │  coworker sync
       ├──────────────→ ~/.claude/skills/<name>/        (Claude Code)
       │
       └──────────────→ ~/.config/opencode/skills/<name>/  (OpenCode)
```

**为什么不用 IDE 原生目录作为源？** Claude Code 和 OpenCode 的 skill 目录不同，不能直接共享。用 `~/.coworker/skills/` 作为 source of truth，`coworker sync` 自动推送到两边。

**Rules:**
- **0-9 uses:** 共享存储中，两个 IDE 都能通过 sync 获取
- **10+ uses:** Auto-flag for promotion → copy to `skill-factory/personal-skills/` → human reviews and commits
- **Usage tracking:** Sidecar JSON at `~/.coworker/skills/.usage.json`. Atomic writes (tempfile + os.replace + fcntl lock). Failures are best-effort — a broken counter never blocks a skill invocation. Tracks: `use_count`, `view_count`, `patch_count`, `last_invoked`, `state`, `provenance`.
  > Implementation: follows Hermes `skill_usage.py` sidecar pattern.
- **Quality metrics (beyond usage counts):**
  - `error_rate`: fraction of invocations where user rejected or corrected the skill's output
  - `patch_frequency`: patches per month. High frequency (>3/month) signals quality issues → flag for review
  - `user_override_rate`: how often the user overrides skill behavior
  - **Regression detection:** when a skill is patched, compare pre-patch and post-patch `error_rate`. If post-patch rate is higher → auto-rollback and flag
- **Lifecycle:** active → stale (30d unused) → archived (90d, move to `.archive/`). Pinned skills exempt. High historical use (>20 uses before idle period) extends stale threshold 2x. `coworker skill unarchive <name>` recovers archived skills.
- **Provenance:** agent-created / bundled (ai-coworker core) / skill-factory / hub. Curator only touches agent-created.

### 5.3 Auto Skill Patching

**Trigger:** Using an existing skill and discovering it's outdated, incomplete, or wrong

**Rule in CLAUDE.md:**
```markdown
When using a skill and finding it incorrect or outdated:
→ invoke `skill-edit` to patch it (surgical edit: old_string → new_string)
```

- `patch_count` tracked per skill — feeds into Curator and promotion decisions
- Patches follow same approval model and safety gates as creation (staged for review in default mode)
- Rollback available: `coworker skill rollback <name>` reverts to last good version
- Circuit breaker applies (Section 5.6)

### 5.4 Post-Session Summarization

**Trigger:** Session Stop hook

**Actions (single LLM pass over full session transcript):**

1. **Summarize experience** → write lessons, patterns, and pitfalls to MEMORY.md → index in FTS5
2. **Identify reusable workflows** → assess whether any task patterns from the session are worth capturing as skills → if yes, invoke `skill-create` with the session transcript as context (see Section 5.1 trigger 2)
3. **Provider fallback** applies (DeepSeek Flash → Gemini Flash → Claude Haiku)

Using a single LLM pass for both summarization and skill identification avoids extra API calls. The full session transcript provides richer context for skill creation than any individual in-session trigger.

### 5.5 Curator

**Trigger:** Cron every 7 days (idle 2h+). FTS5 OPTIMIZE runs daily.

**Actions:**
- Track `view_count`, `use_count`, `patch_count`, `error_rate` per skill and memory entry
- 30 days unused → `stale` → 90 days → `archived`
- High-count protection: entries/skills used 50+ times are pinned
- Seasonal analysis: historically high-use entries get extended stale threshold
- Merge duplicate/overlapping entries
- Generate `REPORT.md`
- Only touches agent-created entries (never hand-written or skill-factory bundled)
- `coworker memory unarchive <id>` and `coworker skill unarchive <name>` for recovery

### 5.6 Safety & Alignment Architecture

> **Why this exists:** Shanghai AI Lab research (2026) documented safety erosion across all four self-evolution pathways: model evolution caused phishing risk triggers to jump from 18.2% to 71.4%; memory evolution caused malicious-code refusal rates to drop from 99.4% to 54.4%; tool evolution showed 65.5% unsafe rate in auto-created tools; workflow evolution collapsed malicious request refusal from 46.3% to 6.3%. AgentWorm (Peking University, 2026) demonstrated 63% attack success rate exploiting self-propagating vulnerabilities in agent ecosystems. A self-modifying autonomous agent without safety infrastructure is indefensible.

#### 5.6.1 Defaults

All self-evolution operations default to **review mode** (`auto_approve: false`). Auto-approval is opt-in and scoped per operation type.

| Operation | Default | Can opt-in to auto? |
|-----------|---------|---------------------|
| Skill creation | Review (pending queue) | Yes, per skill domain |
| Skill patching | Review (pending queue) | Yes, per skill |
| Memory writes | Inline review | N/A (lightweight) |
| Background creation | Always staged | No |

#### 5.6.2 Circuit Breaker

If **>3 skills are created or patched within a 24-hour window**, the system halts all auto-evolution:

1. Auto-creation and auto-patching are suspended
2. All pending skills remain in queue (no data loss)
3. User is notified: "Auto-evolution halted: 4 skills modified in 24h. Review pending queue and run `coworker skill resume` to re-enable."
4. `coworker skill resume` re-enables after user review

#### 5.6.3 Sandbox Testing

Before a pending skill is promoted (approved for use):

1. Dry-run the skill in a sandboxed session (no side effects)
2. Verify the skill's output against a minimal safety check: no shell commands with `rm -rf`, no credential exposure, no unauthorized network calls
3. If sandbox pass → skill enters active pool
4. If sandbox fail → skill stays in pending with failure reason logged

#### 5.6.4 Rollback

Every auto-created or auto-patched skill supports rollback:

- `coworker skill rollback <name>` reverts to the last known-good version
- Rollback is automatic if post-patch `error_rate` exceeds pre-patch `error_rate` by 50%+
- Version history retains last 5 versions per skill

#### 5.6.5 Safety Monitoring

Track these metrics per session and feed into curator decisions:

| Metric | Signal |
|--------|--------|
| `refusal_rate` | Agent refusing unsafe requests (should stay high) |
| `unsafe_output_rate` | Agent producing potentially harmful output (should stay near 0) |
| `skill_error_rate` | Auto-created skills producing incorrect results |
| `circuit_breaker_trips` | Number of times circuit breaker activated |

---

## 6. Architecture

### 6.1 New Modules

```
src/coworker/memory/
├── __init__.py
├── memory_store.py     # MEMORY.md + USER.md read/write with atomic_replace + file lock
├── fts5_index.py       # SQLite FTS5 full-text index over session content
├── curator.py          # Periodic cleanup (7-day cycle, daily OPTIMIZE)
└── sync.py             # Dual-trigger sync: PostToolUse + SessionStop with provider fallback

src/coworker/skills/
├── __init__.py
├── lifecycle.py        # Usage tracking (.usage.json), quality metrics, promotion flagging, rollback, archive
└── pending.py          # Staged skill/memory approval queue with sandbox testing
```

### 6.2 New Storage Locations

```
~/.coworker/
├── memory/              # Cross-IDE memory (see Section 3)
│   ├── fts5_index.db
│   ├── audit.log        # File-based audit trail
│   └── <project>/
│       ├── MEMORY.md
│       └── USER.md
├── skills/              # Shared skill store (source of truth)
│   ├── <name>/SKILL.md
│   └── .archive/
├── pending/             # Approval queue
│   ├── memory/<id>.json
│   └── skills/<id>.json
└── curator/
    └── REPORT.md
```

### 6.3 Hooks & Plugins (Both IDEs)

**Claude Code:**
```json
// ~/.claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "",
        "command": "coworker memory sync --session-id $SESSION_ID --ide claude"
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "command": "coworker memory close --session-id $SESSION_ID --ide claude"
      }
    ]
  }
}
```

**OpenCode:**
```typescript
// .opencode/coworker-analytics/ plugin (extend existing)
tool.execute.after → spawnSync('coworker', ['memory', 'sync', '--session-id', sessionId, '--ide', 'opencode'])
session.end        → spawnSync('coworker', ['memory', 'close', '--session-id', sessionId, '--ide', 'opencode'])
```

**Known limitations (documented):**
- PostToolUse does not fire for: MCP tool calls, Agent tool completions, Skill invocations. SessionStop fallback partially mitigates.
- OpenCode hook reliability is unassessed — needs analysis before production use. File-based audit trail provides ground truth for cross-IDE comparison.
- stdout from hook commands is dropped in Claude Code — sync output cannot inject into active context. This is by design: sync writes to disk for next session (Section 3.6).

### 6.4 Cron Jobs

```cron
# Curator: every 7 days
0 3 * * 1 coworker memory curator run

# FTS5 OPTIMIZE: daily (prevents index fragmentation from per-turn writes)
0 4 * * * coworker memory optimize

# Memory organization: daily 10am, 8pm — organize + consolidate entries
0 10,20 * * * coworker memory organize
```

### 6.5 OpenCode Plugin Extension

The existing OpenCode analytics plugin (`.opencode/coworker-analytics/`) already hooks `tool.execute.before/after` and `session.compacting`. Extend it to also hook:

| Event | Action |
|-------|--------|
| `tool.execute.after` | `coworker memory sync --ide opencode` |
| `session.end` | `coworker memory close --ide opencode` |

**OpenCode hook reliability:** Requires analysis before production use. OpenCode's `tool.execute.after` event may have different coverage than Claude Code's PostToolUse (need to verify: does it fire for all tool types? What about subprocess tool calls?). Until assessed, treat OpenCode memory as best-effort with audit trail verification.

### 6.6 Cost Model

**DeepSeek Flash (primary background LLM):**

| Metric | Off-peak | Peak (9-12, 14-18 Beijing) |
|--------|----------|---------------------------|
| Input (per 1M tokens) | $0.14 | $0.28 |
| Output (per 1M tokens) | $0.28 | $0.56 |

**Per-operation estimates:**

| Operation | Tokens (in/out) | Off-peak cost | Peak cost |
|-----------|-----------------|---------------|-----------|
| Per-turn sync | ~2K / ~500 | ~$0.0004 | ~$0.0008 |
| Post-session summarization | ~8K / ~1K | ~$0.0014 | ~$0.0028 |
| Curator run (weekly) | ~20K / ~2K | ~$0.0034 | ~$0.0067 |
| Memory search (LLM synthesis) | ~4K / ~500 | ~$0.0007 | ~$0.0014 |

**Session/month estimates (100 turns/session, 20 sessions/month):**

| Scenario | Monthly cost |
|----------|-------------|
| Light use (10 sessions, 50 turns each, off-peak) | ~$0.25 |
| Moderate use (20 sessions, 100 turns each, mixed peak/off-peak) | ~$2-5 |
| Heavy autonomous loop (8h run, 500+ turns, mixed) | ~$15-30 |

**Budget enforcement:** `coworker run --max-cost $X.XX` caps total API spend per invocation. CLI warns at 50%, 80%, 95% thresholds. Exceeding budget triggers graceful termination (save state, run summarization, exit).

**Provider fallback pricing:** Gemini Flash and Claude Haiku are comparable or cheaper than DeepSeek Flash at off-peak. Fallback adds negligible cost in outage scenarios.

### 6.7 Error Handling & Degraded Mode

| Component | Failure | Degraded Behavior |
|-----------|---------|-------------------|
| PostToolUse hook | Fails to fire for a turn | No immediate action; SessionStop captures at end of session. Audit trail records gap. |
| PostToolUse hook | Global regression (all hooks fail) | SessionStop fallback captures full session summary. File-based audit trail provides ground truth for recovery. |
| DeepSeek Flash | Rate limited or unavailable | Fallback to Gemini Flash or Claude Haiku. Both fail → defer sync to next cycle (no data loss; raw turn content in session transcript). |
| FTS5 index | Corruption (power loss, disk full) | Auto-rebuild from MEMORY.md source of truth on next access. Log event. |
| MEMORY.md | File lock contention (concurrent sessions) | Second session queues write; retries 3 times with 1s backoff. After 3 failures, writes to separate conflict file for later merge. |
| Curator | Fails mid-run | Partial results persisted. Next run resumes from last checkpoint. REPORT.md notes incomplete run. |
| Skill store | `.usage.json` corruption | Rebuild from skill directory listing. Usage counts reset to 0 (lossy but non-blocking). |
| Claude Code session | API timeout / rate limit | Retry 3x with exponential backoff (1s, 2s, 4s). All fail → record error in state file, continue to next cycle. |

**FTS5 rebuild strategy (resolves Open Question 2):** Incremental updates are the primary path. Full rebuild triggered only on index corruption (detected via `PRAGMA integrity_check`). Rebuild reads all MEMORY.md files and re-indexes — ~100ms for typical project corpus.

### 6.8 Implementation Basis

Memory, skill lifecycle, and curator implementations follow Hermes Agent's patterns (MIT licensed). Key modules mapped:

- `memory_store.py` ← Hermes `tools/memory_tool.py` (§ delimiter, atomic_replace, file lock)
- `fts5_index.py` ← Hermes FTS5 query + schema patterns
- `curator.py` ← Hermes curator lifecycle rules (30d stale → 90d archived, extended with quality metrics and seasonal analysis)
- `lifecycle.py` ← Hermes `skill_usage.py` (sidecar JSON, atomic writes, extended with error_rate and regression detection)

These implementation choices are not locked in — any module can be replaced if a better alternative emerges.

---

## 7. Integration Points

### 7.1 Existing ai-coworker infrastructure to reuse

| Module | Reuse for |
|--------|-----------|
| `coworker skill new` | Auto skill creation trigger |
| `skill-create` / `skill-edit` skills | Self-evolution actions |
| Analytics pipeline (hooks, DB) | FTS5 data source |
| `analytics/knowledge.py` | LLM dedup logic for memory entries |
| `session-memory` skill | LLM summarization pipeline (adapt for Claude Code + DeepSeek Flash, remove Ollama dependency) |
| OpenCode analytics plugin (`.opencode/coworker-analytics/`) | Extend with memory sync hooks |

### 7.2 What's NEW

| Component | Why new |
|-----------|---------|
| `coworker run` | ai-coworker has no loop driver today |
| `memory_store.py` | MEMORY.md read/write doesn't exist |
| `fts5_index.py` | No cross-session search exists |
| `curator.py` | No periodic cleanup exists |
| `sync.py` | Dual-trigger sync with provider fallback |
| `pending.py` | Sandbox testing for staged skills |
| Safety architecture | Circuit breaker, rollback, monitoring |
| CLAUDE.md self-evolution rules | Claude Code needs behavioral instructions |

---

## 8. Out of Scope (MVP)

- Publish / Transact operations
- Embedding-based / vector long-term memory (FTS5 is sufficient for MVP; hybrid BM25+vector search deferred to v2)
- GEPA/DSPy prompt evolution (v2)
- Multi-agent delegation mesh (v2)
- Guild Agent integration (evaluated in Appendix A — complementary task coordination layer, v2 candidate)

---

## 9. Open Questions

### Resolved

1. ✅ **Loop termination detection:** Four conditions defined (Section 2.1.2): goal criteria, stagnation (3 cycles no change), budget exhaustion, human halt.
2. ✅ **FTS5 rebuild strategy:** Incremental updates primary; full rebuild on `integrity_check` failure from MEMORY.md source of truth (Section 6.7).
3. ✅ **MEMORY.md snapshot injection:** Separate `<!-- MEMORY:project-name -->` blocks in CLAUDE.local.md. Mid-session refresh available via `coworker memory refresh` (Section 3.6).

### New (v2+)

4. **OpenCode hook reliability:** Does OpenCode's `tool.execute.after` cover all tool types equivalent to Claude Code PostToolUse? Needs empirical validation before declaring production-ready cross-IDE consistency.
5. **Skill quality auto-detection:** Can we auto-detect when a skill is degrading without waiting for user override signals? Anomaly detection on skill output patterns?
6. **Cross-project skill promotion:** When should a skill created in one project be promoted to skill-factory vs staying project-local?
7. **Loop stagnation sensitivity:** Is 3 cycles the right threshold? Needs empirical tuning based on real autonomous run data.

---

## Appendix A: Guild Agent Evaluation

*Per "优先复用" principle — evaluate existing tools before building.*

### A.1 Guild Agent Summary

[Guild Agent](https://github.com/mathomhaus/guild) (Apache 2.0) is a single Go binary containing an MCP server backed by embedded SQLite. Four primitives: Quests (tasks with atomic claiming), Lore (knowledge entries typed by kind), Oaths (project principles), Briefs (session handoff notes). Hybrid BM25 + vector search via reciprocal-rank fusion. Cross-IDE via MCP protocol. State in `~/.guild/`.

### A.2 Comparison Against PRD Memory Requirements

| Req | PRD Approach | Guild Approach | Assessment |
|-----|-------------|----------------|------------|
| R1 (IDE-agnostic) | Memory in `~/.coworker/`, hooks per IDE | MCP server — any MCP client connects | Guild has broader IDE reach. PRD needs hook config per IDE. |
| R2 (No manual save) | Unconditional PostToolUse hook → auto sync | Agent must call `lore_inscribe` explicitly | **Guild fails R2.** `lore_inscribe` IS a manual save command. R2 explicitly requires persistence "without the agent manually invoking a save command." |
| R3 (Cross-session search) | FTS5 keyword → LLM synthesis | Hybrid BM25 + vector via reciprocal-rank fusion | Guild's search is objectively more capable. PRD's LLM synthesis at query time is a lighter-weight semantic layer. Vector search disabled on Windows. |
| R4 (Agent-managed notes) | MEMORY.md with § entries, `add|replace|remove` | `lore_inscribe` with kind/summary/topic | Tradeoff: Guild has more structure (SQLite rows, per-kind TTL). PRD has more transparency (human-readable, git-diffable, directly injectable as LLM context). |
| R5 (Frozen snapshot) | CLAUDE.local.md injection at session start | `guild_session_start` returns oath + brief + quest | Both satisfy. PRD snapshot is zero-tool-call (in context immediately). Guild requires a tool call but is more self-contained. |
| R6 (Periodic cleanup) | Usage-based staleness (30d → 90d) + curator merge | Per-kind TTL (30d/180d/permanent) | Guild's per-kind TTL is more elegant for pure knowledge. PRD's curator handles broader scope (skills + memory + merge + reporting). |
| R7 (No background server) | Hooks → CLI commands (run-and-exit) | MCP server (persistent process) + embedded ONNX runtime | **Guild fails R7.** MCP server IS a background process. ONNX runtime qualifies as vector DB. R7 explicitly excludes both. |

### A.3 What Guild Does NOT Provide

Guild is a **task coordination substrate**. It does not provide any of the PRD's self-evolution features:

- ❌ Auto skill creation (no skill concept)
- ❌ Auto skill patching (no mechanism to edit knowledge in-place)
- ❌ CLAUDE.md modification (writes to AGENTS.md for registration only)
- ❌ Three-layer knowledge taxonomy (lore kinds ≠ SOP/Experience/State)
- ❌ State engine (quests track task completion, not initiative progress)
- ❌ `coworker run` loop driver
- ❌ Approval model with sandbox testing and circuit breaker

### A.4 Decision

**Guild is not a replacement for the PRD's memory architecture.** Guild fails R2 and R7, and provides none of the self-evolution features that are the PRD's defining purpose.

**Guild is a complementary v2 candidate.** Guild's quest board, cascade unblocking, and hybrid search could complement the PRD's task coordination layer (out of scope for MVP). Also worth evaluating as an alternative to FTS5 for v2 when vector search is considered.
