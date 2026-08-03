# Self-Evolving Agent — PRD

> Goal: Ship an autonomous agent that self-evolves in a continuous loop to achieve a goal. The agent is Claude Code (and OpenCode), harnessed by walter-worker. The agent takes real action — monitor, orchestrate — grounded in real sources.

## Status

| St | Date | Author |
|----|------|--------|
| 🚧 draft v7 | 2026-07-25 | cicidi + Claude |

## Change Log

| Date | Change |
|------|-------|
| 2026-07-25 | v7: Added §5.8 Evolution Observability — 8 new requirements (R8–R15) for dashboard Evolution page: auto-train flags (skills + experiences), session traceability, reuse counts, pending queue visibility, evolution score, filtering. |
| 2026-07-25 | v6: **Requirements-only restructure.** PRD now states *what/why* only; *how* (tech, storage, schemas, hook configs, cost, reuse analysis) moved to [spec](../spec/self-evolving-agent-spec.md). Specific changes: (1) Removed §1.4 Hermes-as-basis, §6 Architecture, §7 Integration & Implementation, Appendix A Guild evaluation — all solution-level, now in spec. (2) Generalized tech-specific terms (DeepSeek/Hermes/sqlite-vec/hook names/storage paths) to tech-neutral requirement language. (3) Reversed §5.4 privacy model: default is now a **remote** background LLM (was: local-default). (4) MEMORY.md reclassified from Tier 3 storage to a read-only curator export (§3.5). (5) Vector/embedding memory moved **back into scope** (mem0) — removed from OOS. (6) Added requirements: evolution-effectiveness metrics (§5.7), pending-queue non-overflow (§5.1). |
| 2026-07-25 | v5: Fixed 3 blocking issues from adversarial review. (1) Added `async: true` to PostToolUse hook config — sync no longer blocks tool calls. (2) Corrected hook name to real Claude Code hook `Stop` (was `SessionEnd` which doesn't exist). (3) Added privacy model: transcript summarization defaults to local model (Ollama), remote API (DeepSeek) is opt-in. *(v6 reverses #3.)* |
| 2026-07-25 | v4: Restructured memory to three-tier architecture (§3). |
| 2026-07-24 | v3: Reframed primary experience as Hook-embedded implicit evolution. |
| 2026-07-24 | v2/v1: safety architecture, loop state machine, hook mitigations, cost model, Guild evaluation. |

> **Companion spec:** [`../spec/self-evolving-agent-spec.md`](../spec/self-evolving-agent-spec.md) — the authoritative *how* (mem0 substrate, Hermes loop adaptation, dual-IDE capture, schemas, error handling). PRD references requirements (R1–R7); spec satisfies them.

---

## 1. Overview

### 1.1 Vision

A Claude Code / OpenCode agent that continuously improves itself by working on real tasks. Each session, each turn, each mistake feeds back into the system — skills are auto-created, memory persists, behaviors evolve. The agent gets smarter the more you use it.

**How you experience it:** You use Claude Code (or OpenCode) normally. Behind the scenes, the platform captures what happens, a background LLM extracts lessons, and the agent quietly builds skills and memory. Session by session, the agent accumulates knowledge — conventions you like, bugs you've hit, workflows that work. There's no separate "training mode." Evolution is embedded in everyday use.

### 1.2 Primary Experience: Hook-Embedded Implicit Evolution

```
You use Claude Code / OpenCode naturally
         │
         ▼
  After every tool call
  ─────────────────────
  The platform records state and syncs memory
  in the background (does not block your work)
         │
         ▼
  When the session ends
  ─────────────────────
  A background LLM reads the full transcript,
  extracts lessons, identifies reusable workflows,
  and stages skills for review
         │
         ▼
  Next session: richer context, better skills,
  smarter agent
```

**No separate command, no external driver.** The agent evolves in the background while you work. This is the primary UX. The exact hook/event wiring per IDE is in the spec (§3).

### 1.3 SDK Mode

For programmatic use cases (CI/CD, batch processing, scheduled autonomous runs), an explicit state-machine-driven loop is exposed as a CLI for scripts and automation — not the primary human experience. See §2.2 for the loop behavior.

### 1.4 Implementation Choices

Implementation choices (memory substrate, skill-refinement patterns, hook wiring, LLM/embedder selection, cost) are **not** specified in this PRD. They live in the [spec](../spec/self-evolving-agent-spec.md). The PRD is intentionally tech-neutral so the substrate can be replaced without changing requirements.

### 1.5 Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary experience | **Hook-embedded implicit evolution** — you use the IDE, the platform does the rest | Evolution shouldn't feel like a separate tool or mode |
| SDK mode | Explicit loop CLI for CI/CD, batch, headless automation | Same infrastructure, CLI entry point for scripts |
| Goal model | Meta-goal: self-improvement as primary driver, real work as training ground | The agent evolves through use |
| Evolution scope | Skills + Context + Code + Config (full scope) | Everything the agent touches can improve |
| Memory architecture | Three-tier: Session → Project-State → Long-Term | Per-turn sync, cross-IDE/cross-project search, semantic + exact retrieval, periodic cleanup |
| Skill creation | Reuse existing `skill-create` / `skill-edit` | Don't reinvent — trigger them automatically |
| Orchestration | The agent decides how to decompose tasks | walter-worker doesn't hardcode workflows |
| Principles | 优先复用 → 不够改造 → 没轮子造轮子 | Pragmatic, not dogmatic |

### 1.6 Knowledge Taxonomy

The agent generates three types of knowledge, each mapping to a memory tier:

| Type | Definition | Example | Memory Tier | Trigger |
|------|-----------|---------|-------------|---------|
| **SOP** | 可重复的操作流程 — step-by-step procedure for a specific task | "修复 lint 错误的标准流程"、"部署到 production 的检查清单" | Skill store → promoted to skill-factory | 复杂任务完成后自动判断 → `skill-create` |
| **经验总结** | 对/错的教训、发现的模式、坑点 — lessons, patterns, pitfalls learned through experience | "MCP 首次请求总是 403 超时，需重试"、"ruff E501 在这个项目被忽略" | **Tier 3** — Long-Term Memory store (cross-project, permanent) | 每 turn sync + session 结束 LLM 总结 |
| **State / 进度** | 当前状态 — what was done, what's right/wrong, what's done/pending, who's doing it, when it'll be done | "Dashboard 5 页完成 2 页 pending，blocker 是数据源 API 未就绪" | **Tier 2** — State files (`docs/<initiative>/state/YYYY-MM-DD-state.md`) | 每 turn / 每个 phase 完成 |

**SOP vs 经验 vs State：** SOP 是"怎么做"（可复用流程，晋升到 skill-factory 共享），经验是"发生了什么/学到了什么"（长期记忆，跨项目持久化），State 是"当前在哪"（中期记忆，项目完成即归档）。

---

## 2. How Evolution Happens

### 2.1 The Implicit Loop (Primary Experience)

Each session IS one evolution cycle. There's no separate "run" command — evolution happens automatically as you work:

```
Session N                            Session N+1
┌──────────────────────┐            ┌──────────────────────┐
│  You do real work    │            │  Smarter agent       │
│  ──────────────────── │            │                       │
│  After each tool call │            │  • Richer context     │
│  → state recorded     │  ──────►   │    (snapshot has new  │
│  → memory synced      │  Session   │     memory)           │
│                       │   ends     │                       │
│  On session end       │            │  • Better skills      │
│  → lessons summarized │            │    (staged from last  │
│  → skills staged      │            │     session)          │
└──────────────────────┘            └──────────────────────┘
```

**What triggers what:**

| Trigger | When | What happens |
|---------|------|-------------|
| **Per-tool** | After every tool call | State recorded. Memory synced to the long-term store in the background. Subagent results also captured. |
| **Session end** | Session ends | Full transcript → background LLM → extract lessons → long-term memory. Identify reusable workflows → stage skills for review. Update memory snapshot for next session. |
| **Skill usage** | During session | Usage tracked. If a skill is wrong/outdated → the agent patches it. |
| **Curator** | Periodic (idle) | Cleanup: archive stale entries, merge duplicates, generate report. Never touches hand-written content. |

**The key insight:** Evolution isn't a separate mode. Every session where you do real work becomes training data. The more you use it, the more skills and memory accumulate.

### 2.2 SDK Mode

For programmatic use, the same infrastructure is exposed as a CLI with an explicit loop. Default max time: **12 hours**; the loop gracefully stops when time expires, saving state. Without the loop flag, one cycle runs and exits.

**One cycle** = Observe → Decide → Spawn agent → Record. Each cycle produces concrete output or a deliberate no-op.

**Termination conditions** (the loop stops when ANY is met):

| # | Condition | Detection |
|---|-----------|-----------|
| 1 | **Goal achieved** | User-provided success criteria evaluated true (e.g., `pytest --exitfirst` returns 0, `ruff check` returns 0) |
| 2 | **Stagnation** | 3 consecutive cycles produce no new changes (no code diff, no skill created/patched, no memory entry added) |
| 3 | **Time expired** | Default 12h max time reached. Graceful stop: save state, run summarization, exit. |
| 4 | **Human halt** | Human confirms "done" or "stop" |

**Error recovery** (degrade, don't crash):

| Failure | Recovery |
|---------|----------|
| Agent session errors (API timeout, rate limit) | Retry up to 3 times with exponential backoff; if all fail, record error in state and continue to next cycle |
| Per-tool capture fails | Session-end pass captures the full summary; audit trail records the gap |
| Background LLM outage | Fallback to secondary provider; if all down, defer sync to next cycle (no data loss — raw transcripts preserved) |
| Search index corruption | Auto-rebuild from the source of truth; log event |
| Concurrent session conflict | Lock the shared store; second session queues or skips |

> The detailed state-machine diagram and SDK internals are in the spec.

> **What gets auto-updated vs. what doesn't:** Auto-evolution modifies only **CLAUDE.local.md** (personal, not committed), skills in the shared skill store, and memory in the long-term store. **CLAUDE.md** (shared, committed) is NEVER auto-modified — the self-evolution rules are written once by the human. This separation ensures the agent evolves its personal context without altering team-wide conventions.

### 2.3 No Publish / Transact (MVP)

- `publish` and `transact` are out of scope for MVP
- `orchestrate` is delegated to the agent — walter-worker doesn't hardcode task decomposition

---

## 3. Memory — Three-Tier Architecture

### 3.1 Requirements

The agent must persist what it learns across sessions, projects, and IDEs:

- **R1 — IDE-agnostic (dual-IDE):** Memory shared by **both Claude Code and OpenCode** as first-class. Every requirement in this section must have a working solution path for each IDE. Not locked to any single IDE's config directory.
- **R2 — Per-turn persistence:** Every turn's key information persisted without the agent manually invoking a save command.
- **R3 — Cross-session search:** Search across all past sessions, regardless of project or IDE. Must support both exact key-based lookup (find by project + topic) and fuzzy/semantic search (find conceptually similar content). Keyword search alone is insufficient.
- **R4 — Agent-managed notes:** Agent can write, patch, and remove its own notes about the project (conventions, tool quirks, lessons) and user (preferences, workflow habits).
- **R5 — Frozen snapshot:** Each session starts with a stable snapshot of accumulated knowledge. Mid-session writes go to disk but don't perturb the active session's context.
- **R6 — Periodic cleanup:** Stale and unused entries are archived automatically. Hand-written entries are never touched.
- **R7 — Lightweight:** No mandatory always-on background server process. The LLM is used for summarization/retrieval, not continuously running.

### 3.2 Three-Tier Memory Model

Memory is organized in three tiers, from short-lived to permanent:

```
┌─────────────────────────────────────────┐
│  TIER 1 — Session Memory                │
│  What's happening NOW                    │
│  Lifetime: session duration              │
└──────────┬──────────────────┬───────────┘
           │ session ends     │ per-turn sync
           ▼                  │
┌──────────────────────────┐ │
│   Session Transcript     │ │
│   (raw, preserved)       │ │
└──────────┬───────────────┘ │
           │ LLM summarizes  │
           ▼                  │
┌──────────────────────────┐ │
│  TIER 3 — Long-Term      │◄┘
│  Memory (all projects,   │
│  permanent)              │
│  Lessons, patterns,      │
│  conventions, prefs      │
│  Search: exact + semantic│
└──────────┬───────────────┘
           │ snapshot at session start
           ▼
┌─────────────────────────────────────────┐
│  TIER 2 — Project State Memory          │
│  What was DONE / PENDING / BLOCKED       │
│  Lifetime: initiative duration           │
│  Key lessons promoted to Tier 3 on done  │
└─────────────────────────────────────────┘
```

**Data flow:**
- **Session → Tier 3 (primary):** Session-end LLM summarizes transcripts into long-term memory. Main capture path — every session produces learning.
- **Session → Tier 2 (per-turn):** State changes written to initiative state files throughout the session.
- **Tier 2 → Tier 3 (on completion):** When an initiative completes, key lessons promote to long-term memory.
- **Tier 3 → Tier 1 (session start):** Frozen snapshot of relevant long-term memory injected into new sessions.

| Tier | Scope | Lifetime | What It Stores | Key Operations |
|------|-------|----------|---------------|----------------|
| **Session** | Current session | Session duration | Active context, tool calls, conversation | Auto-capture |
| **Project State** | Current initiative | Initiative duration | Progress, decisions, blockers, phase tracking | Per-turn sync, phase snapshots |
| **Long-Term** | All projects | Permanent (curated) | Lessons, patterns, conventions, user preferences | Session-end summarization, cross-session search, periodic curation |

### 3.3 Tier 1 — Session Memory

The agent's working memory — what it "sees" during a session.

- **Content:** The current conversation, tool-call history, and a frozen snapshot of long-term knowledge injected at session start (§3.8).
- **Capture:** Automatic. No manual "save."
- **Lifetime:** Session duration. When the session ends, raw content is preserved in transcripts; a background LLM extracts key lessons and promotes them to Tier 2 and Tier 3.
- **Constraint:** Mid-session writes to long-term memory do NOT refresh the session's snapshot. A manual refresh is available for long-running sessions (>2h).

### 3.4 Tier 2 — Project State Memory

Tracks "where we are" in the current initiative. Medium-term — detailed, project-specific, complete when the initiative finishes.

- **Content:** Three dimensions — what was done (concrete output), what's right/wrong (lessons), and current status (done/not done/who/when/dependencies).
- **Storage:** State files at `docs/<initiative>/state/YYYY-MM-DD-state.md`. Live documents updated continuously. Previous entries can be modified as status changes (e.g., `🚧 → ✅`).
- **Recording criteria:** Record when any dimension changes. See §4.
- **Lifetime:** Initiative duration. On completion, the state file becomes historical; key lessons promote to Tier 3.

### 3.5 Tier 3 — Long-Term Memory

Cross-project, cross-session knowledge that persists indefinitely. This is what makes the agent "smarter over time."

- **Content:** Lessons learned, reusable patterns/workflows, project conventions, tool quirks, user preferences, distilled experience from completed initiatives.
- **Storage:** A long-term memory store that MUST support:
  - **Exact retrieval:** Find entries by project, topic, or problem key.
  - **Fuzzy/semantic search:** Find conceptually similar entries across projects.
  - **Human-readable export:** A read-only, curator-generated mirror of the store for git-diffability and offline reading. (The store itself is the source of truth; the export is derived.)
  - **Unified search scope:** All projects, all sessions, both IDEs — one search surface.
- **Capture:**
  - **Per-turn (secondary, reliability):** Key information from each significant tool call is extracted and written incrementally. Best-effort — failures don't block the session.
  - **Session-end summarization (primary, quality):** When a session ends, a background LLM reads the full transcript, extracts lessons/patterns, identifies reusable workflows, and reconciles/dedups against per-turn captures. Every session produces learning.
- **Lifetime:** Permanent, with automated maintenance (§3.7).
- **Retrieval:** CLI for scripts and a skill for humans. The agent can proactively search memory when it encounters situations similar to past experience.

### 3.6 Memory Sync Flow

- **Per-turn sync:** After each significant tool call, key information is extracted to Tier 2 (state) and Tier 3 (long-term). Lightweight, non-blocking. Coverage gaps are mitigated by the end-of-session pass.
- **End-of-session sync:** Full transcript summarized by a background LLM; lessons/patterns written to Tier 3. Captures what per-turn missed (subagent results, dropped output). Also triggers post-session summarization (§5.4).
- **Provider fallback:** If the primary background LLM is unavailable, fall back to a secondary provider. Both fail → defer to next cycle. No data loss — raw transcripts are preserved.
- **Audit trail:** Every sync writes a timestamped audit record, enabling gap detection.
- **Subagent content:** Captured via a dedicated subagent-completion trigger, with session-end summarization as a secondary path.

### 3.7 Memory Maintenance (Curator)

Periodic maintenance keeps the long-term store healthy:

- **Trigger:** Periodic, during agent idle time.
- **Actions:** Track usage per entry; mark unused (30 days → `stale` → 90 days → `archived`); pin high-value entries; merge duplicates; generate reports; regenerate the human-readable export. Only touch agent-created entries — never hand-written.
- **Recovery:** Archived entries can be restored.

### 3.8 Context Injection (Snapshot)

At session start, a frozen snapshot of relevant long-term memory is injected into the session context. Both Claude Code and OpenCode read the personal context file at session start, so the snapshot is available immediately — no tool call required.

- **Frozen at start:** Captured once. Mid-session writes don't refresh the active snapshot.
- **Replaced each session:** Old snapshot is entirely replaced on next session start, guarded by a merge layer so human content is never corrupted.
- **Mid-session refresh:** A manual command reloads the snapshot from disk. Useful for long-running sessions (>2h). Default behavior remains frozen.
- **Agent-managed, human-readable:** Written by the agent, readable/editable by humans.

---

## 4. State Engine

### 4.1 Trigger

Every turn → capture fires → the platform writes to the state file. No manual action needed — state recording is a side effect of using the IDE.

### 4.2 State File

```
docs/<initiative>/state/YYYY-MM-DD-state.md
```

- Live document, updated continuously (not just daily snapshot)
- Appends new events AND modifies previous entries (e.g., `🚧 → ✅`)
- Phase completion (PRD/spec/design/plan/test) forces a state update

### 4.3 Recording Criteria

Three dimensions — record if ANY one is met:

| Dimension | What it means |
|-----------|--------------|
| **做了什么** | Concrete output: code, docs, config, research conclusion, external action, automation |
| **对/错** | Lessons: what worked, what didn't, bugs found, blind spots exposed, compaction risks |
| **进度** | Tracking: done/not done/who's doing it/when done/dependencies |

**Always record:** code/doc/config changes; system events (MCP setup, model config, backup/restore, compaction); research with conclusions; failed attempts; subagent conclusions.

**Never record:** instant queries (just looking); single-command atomic ops; pure chat/curiosity; transient status checks.

---

## 5. Self-Evolution Engine

### 5.1 Auto Skill Creation

**Triggers (dual):**

1. **Post-session trigger — PRIMARY:** When the background LLM summarizes the session (§5.4), it also assesses whether any workflows/patterns are reusable. If yes → invokes `skill-create` with the full session transcript as context. Most powerful — it has the complete session picture.
2. **In-session trigger — SECONDARY:** Completing a task with a significant tool-call footprint (default threshold: 10+ tool calls). Configurable.

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
| **Review mode** (`auto_approve: false`, DEFAULT) | Skills staged to a pending queue — user reviews |
| **Auto mode** (`auto_approve: true`) | Skills auto-created without prompting (opt-in) |

**Pending queue must not grow unbounded** (requirement): the queue supports batch approve/reject and auto-expires items untouched for 30 days (auto-rejected, never silently promoted). The queue persists across restarts. *(Simple v1; quality scoring deferred.)*

- Memory writes: lightweight, reviewed inline
- Skill writes: always staged (too large for inline preview)
- **Safety gates** (see §5.6): circuit breaker, sandbox test, rollback.

### 5.2 Skill Lifecycle & Promotion

Skills are created **locally first**, not directly in skill-factory. They earn their way up.

**Rules:**
- **0–9 uses:** shared store, both IDEs can sync
- **10+ uses:** auto-flag for promotion → copy to `skill-factory/personal-skills/` → human reviews and commits
- **Usage tracking:** sidecar JSON with atomic writes. Failures are best-effort — a broken counter never blocks a skill invocation. Tracks use/view/patch counts, state, provenance.
- **Quality metrics:** `error_rate`, `patch_frequency`, `user_override_rate`, regression detection (rollback if post-patch error rate exceeds pre-patch).
- **Lifecycle:** active → stale (30d unused) → archived (90d). Pinned/high-history-use skills exempt.
- **Provenance:** agent-created / bundled / skill-factory / hub. Curator only touches agent-created.

### 5.3 Auto Skill Patching

**Trigger:** Using an existing skill and discovering it's outdated, incomplete, or wrong → invoke `skill-edit` (surgical: `old_string → new_string`). `patch_count` feeds the curator and promotion. Same approval model + safety gates as creation. Rollback available.

### 5.4 Post-Session Summarization (Central Evolution Mechanism)

**Trigger:** Session ends.

This is the primary mechanism for the implicit evolution experience. Every session produces two outputs in a single LLM pass over the full transcript:

1. **Summarize experience** → lessons/patterns/pitfalls to memory → indexed → next session's snapshot includes this knowledge.
2. **Identify reusable workflows** → assess whether any task patterns are worth capturing as skills → if yes, stage via `skill-create`.

Using a single pass for both avoids extra API calls. The full transcript provides richer context for skill identification than any individual in-session trigger.

**Privacy model:** Session transcripts may contain proprietary code and credentials. By default, summarization sends session content to the configured **remote** background LLM (the project's chosen provider). Users who need local-only processing for sensitive content may opt in to a local model. The provider fallback chain (§3.6) applies when the configured provider is unavailable.

> v5 defaulted to local; v6 reverses this to remote-default per owner decision (the configured provider is used by default; local is opt-in for sensitive sessions).

**This is what makes evolution feel automatic.** You finish your work, close the IDE, and next time the agent has learned from your last session.

### 5.5 Curator

**Trigger:** Periodic (idle). Index maintenance runs more frequently.

**Actions:** Track usage metrics; archive stale (30d → 90d); pin high-use; merge duplicates; generate report; regenerate the human-readable export; only touch agent-created entries. Restore via unarchive commands.

### 5.6 Safety & Alignment Architecture

> **Why this exists:** Shanghai AI Lab research (2026) documented safety erosion across all four self-evolution pathways: model evolution raised phishing-risk triggers 18.2%→71.4%; memory evolution dropped malicious-code refusal 99.4%→54.4%; tool evolution showed 65.5% unsafe auto-created tools; workflow evolution collapsed malicious-request refusal 46.3%→6.3%. AgentWorm (Peking University, 2026) demonstrated 63% attack success against self-propagating agent vulnerabilities. A self-modifying autonomous agent without safety infrastructure is indefensible.

**Defaults:** All self-evolution defaults to **review mode**. Auto-approval is opt-in and scoped per operation type.

| Operation | Default | Can opt-in to auto? |
|-----------|---------|---------------------|
| Skill creation | Review (pending queue) | Yes, per skill domain |
| Skill patching | Review (pending queue) | Yes, per skill |
| Memory writes | Inline review | N/A (lightweight) |
| Background creation | Always staged | No |

**Circuit breaker:** If >3 skills are created or patched within 24 hours, halt all auto-evolution (suspend create/patch, keep pending queue, notify user, resume only after review).

**Sandbox testing:** Before a pending skill is promoted, dry-run it in a sandboxed session (no side effects) and verify minimal safety checks. Fail → stays pending with reason logged.

**Rollback:** Every auto-created/patched skill supports rollback to the last known-good version. Automatic if post-patch error rate exceeds pre-patch by 50%+. Version history retains last 5 versions.

**Safety monitoring:** Track `refusal_rate`, `unsafe_output_rate`, `skill_error_rate`, `circuit_breaker_trips` per session; feed into curator decisions.

> **Known gap (semantic threats):** Sandbox checks are syntactic (e.g., dangerous shell patterns). The cited threats are semantic (phishing, refusal collapse). A semantic guard is a recognized need; tracked as a follow-up rather than an MVP blocker.

### 5.7 Effectiveness Metrics

The vision is "smarter over time." Beyond safety metrics (§5.6), the system MUST measure whether it is actually getting more useful. These are requirements:

| Metric | Signal | Target trend |
|--------|--------|--------------|
| `skill_reuse_rate` | fraction of sessions invoking an auto-created skill | rising |
| `user_correction_rate` | user overrides/corrects the agent per task | falling |
| `task_first_pass_rate` | tasks completed without rework | rising |
| `memory_hit_rate` | searches returning a useful entry | rising; non-zero baseline means memory is used |

Collection is automatic per session and surfaced in curator reports. Exact formulas are an implementation detail (spec).

### 5.8 Evolution Observability (Dashboard)

The agent evolves in the background — but the user MUST be able to verify that evolution is actually happening, and inspect what was created. The existing analytics dashboard gains a new "Evolution" page dedicated to this.

**R8 — Auto-train flag (skills):** Every skill MUST carry a provenance flag indicating its origin:

| Flag | Meaning |
|------|---------|
| 🟢 Auto-Train | Created by the self-evolution engine from session patterns |
| 🔵 Bundled | Shipped with walter-worker or skill-factory |
| ⚪ Manual | Hand-written by the user, never auto-modified |

**R9 — Auto-train flag (experiences):** Every experience/lesson in long-term memory MUST carry the same provenance flag. Auto-extracted experiences are distinguishable from hand-written ones.

**R10 — Session traceability (skills):** For every auto-trained skill, the user MUST be able to see which sessions invoked it, how many times, and when it was last used. Zero-use skills (created but never invoked) must be visible — they are candidates for archival.

**R11 — Session traceability (experiences):** For every auto-extracted experience, the user MUST be able to see which session generated it (source) and which sessions later retrieved it (reuse). This closes the loop: "this lesson came from session X, and helped in sessions Y, Z."

**R12 — Reuse count:** Each skill and experience MUST track and display a reuse count. For skills: number of sessions that invoked it. For experiences: number of times it was retrieved in a search. This is the primary signal for "is evolution working?"

**R13 — Pending queue visibility:** Skills and experiences staged for review MUST be visible in the dashboard with approve/reject actions. Items auto-expired after 30 days of inaction must be distinguishable from explicitly rejected ones.

**R14 — Evolution score:** The dashboard MUST surface a composite evolution score derived from the effectiveness metrics (§5.7), so the user can answer "is my agent getting smarter?" at a glance.

**R15 — Filtering:** The Evolution page MUST support filtering by provenance (auto-train/all), project, status (active/stale/archived/pinned), and date range. Default view: auto-trained only, active only.

These requirements are what the dashboard must show. How (API endpoints, table schemas, frontend implementation) is in the [dashboard design](../design/dashboard-design.md) and spec.

---

## 6. Implementation

Implementation (memory substrate, skill-refinement loop, hook/event wiring, schemas, error handling, cost model, reuse analysis of existing walter-worker infrastructure) is specified in the [spec](../spec/self-evolving-agent-spec.md). This PRD intentionally omits *how* the requirements are met.

---

## 7. Out of Scope (MVP)

- Publish / Transact operations
- GEPA/DSPy prompt evolution (v2)
- Multi-agent delegation mesh (v2)
- Guild Agent integration (evaluated — complementary task-coordination layer, v2 candidate; not a replacement for the memory architecture)
- Semantic safety guards beyond syntactic sandbox checks (follow-up; see §5.6)

---

## 8. Open Questions

### Resolved

1. ✅ **SDK loop termination:** Three conditions (§2.2): goal criteria, stagnation (3 cycles), time expired (12h).
2. ✅ **Search index rebuild:** Incremental primary; full rebuild on integrity failure from source of truth.
3. ✅ **Snapshot injection:** Separate per-project snapshot blocks; mid-session refresh available.
4. ✅ **Primary UX:** Hook-embedded implicit evolution; SDK loop reserved for automation.
5. ✅ **Vector/embedding memory:** In scope (MVP). Substrate choice (mem0) in spec.
6. ✅ **Privacy default:** Remote background LLM by default; local opt-in (v6 reversal of v5).
7. ✅ **Long-term store schema & MEMORY.md role:** Store is source of truth with a defined entry schema; MEMORY.md is a read-only curator export (spec §2.3, §5.2).

### New (v2+)

1. **OpenCode capture coverage:** Does OpenCode's per-tool event fire for all tool types, equivalent to Claude Code? Needs empirical validation before declaring dual-IDE production parity (spec §8 spike).
2. **Skill quality auto-detection:** Can skill degradation be auto-detected without waiting for user override signals?
3. **Cross-project skill promotion:** When should a project-local skill promote to skill-factory?
4. **Loop stagnation sensitivity:** Is 3 cycles the right SDK threshold? Needs real-run tuning.
