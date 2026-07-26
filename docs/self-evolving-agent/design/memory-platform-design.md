# Memory Platform — Design

> Initiative: self-evolving-agent | Type: design | Status: **draft v1**
>
> Builds on: [PRD v6](../prd/self-evolving-agent-prd.md) (requirements), [Spec v1.1](../spec/self-evolving-agent-spec.md) (technical detail)
>
> This is the architecture design for the self-evolving-agent memory platform. It covers component architecture, interfaces, data flow, and design rationale — the "what connects to what and why." For exact config shapes, API parameters, hook JSON, and error codes, see the [spec](../spec/self-evolving-agent-spec.md).

---

## 1. Architecture Overview

```
                          ┌──────────────────────────────────────┐
                          │          IDE LAYER (§2)                │
                          │  Claude Code  │  OpenCode              │
                          │  ─────────────────────────             │
                          │  PostToolUse  │  tool.execute.after    │
                          │  SubagentStop │  (session.end)         │
                          │  Stop         │                         │
                          └───────┬──────────────────┬────────────┘
                                  │ per-turn         │ session-end
                                  │ (async, best-    │ (sync, reconcil-
                                  │  effort)         │  iation pass)
                                  ▼                  ▼
                          ┌───────────────────────────────────────┐
                          │      CAPTURE LAYER (§3)               │
                          │  CLI: coworker memory sync            │
                          │  CLI: coworker memory close           │
                          │  Audit trail: audit.log               │
                          └───────────┬───────────────────────────┘
                                      │
                          ┌───────────▼───────────────────────────┐
                          │      EVOLUTION ENGINE (§4)             │
                          │                                        │
                          │  per-turn: extract facts → mem0.add   │
                          │  session-end: reconcile + skill-create │
                          │  curator: periodic cleanup             │
                          └─────┬──────────────┬──────────────────┘
                                │              │
                  ┌─────────────▼──┐    ┌──────▼─────────────┐
                  │  mem0 (§5)     │    │  STATE FILES (§6)   │
                  │  Tier 3        │    │  Tier 2             │
                  │  Long-term     │    │  docs/<init>/state/ │
                  │  store +       │    │  per-turn progress  │
                  │  search        │    └─────────────────────┘
                  └───────┬────────┘
                          │ frozen snapshot at session start
                  ┌───────▼────────────────────────────────────┐
                  │  CLAUDE.local.md INJECTION (§7)             │
                  │  <!-- MEMORY:<project> START/END -->         │
                  │  Guarded by semantic_merge.py               │
                  └────────────────────────────────────────────┘
```

**LLM policy (global):** Every component that needs an LLM uses the project's configured provider (remote by default per PRD §5.4). Embeddings use a local model (fastembed, BAAI/bge-small, 384-dim) — no API call, no cost. Provider fallback chain: primary → secondary → defer to next cycle. Raw transcripts always preserved — no data loss.

---

## 2. IDE Layer

The platform captures data from two IDEs. This is an existing infrastructure — 37 sessions, 15K+ tool calls already captured via PostToolUse + Stop hooks in settings.json.

### 2.1 Triggers

| IDE | Per-turn | Subagent completion | Session end |
|-----|----------|--------------------|-------------|
| Claude Code | PostToolUse (async) | SubagentStop (async) | Stop (sync, stdin JSON) |
| OpenCode | tool.execute.after | — (no first-class equivalent) | session.end |

**Reliability strategy:** per-turn is the reliability floor (don't lose data if session is killed), session-end is the quality pass (full-context reconciliation). Per-turn hooks are `async: true` — they never block the user's tool calls.

**OpenCode subagent gap:** OpenCode has no first-class subagent hook. Mitigation: session-end pass reads the full transcript and back-fills subagent results. Covered by the audit trail — any gap is recorded.

### 2.2 Session ID

Claude Code: hook command reads session_id from **stdin JSON** (not an env var — more reliable across hook invocations).

OpenCode: plugin context provides session identity.

---

## 3. Capture Layer

Two CLI commands, both thin wrappers that call the evolution engine:

| Command | Trigger | Behavior |
|---------|---------|----------|
| `coworker memory sync` | PostToolUse / SubagentStop / tool.execute.after | Input: tool event + recent window + mem0 recall → LLM extraction → `mem0.add`. Output: 0..N lessons + optional state_delta. Non-blocking (async). |
| `coworker memory close` | Stop / session.end | Full transcript reconciliation → back-fill gaps → assess skill-reuse → stage skills. Single LLM pass for summarization + skill detection. |

### 3.1 Audit Trail

Every capture writes a timestamped record to `~/.coworker/memory/audit.log`:

```
2026-07-25T10:00:01Z  sync   posttooluse  sess_abc  tool=Edit  lessons=1  ms=420  ok
2026-07-25T10:05:00Z  sync   subagentstop sess_abc  agent=code-explorer  lessons=2  ms=380  ok
2026-07-25T10:30:00Z  close  stop         sess_abc  reconciled=3  skills_staged=0  ms=2100  ok
```

If a session has time gaps with no records → flagged for investigation. Raw transcripts are the source of truth — mem0 entries are derived and can be rebuilt.

---

## 4. Evolution Engine

### 4.1 Core Loop

The engine does two things on every event:

1. **Extract facts** (lessons, patterns, conventions) → write to mem0 Tier 3
2. **Assess skill-worthiness** (10+ tool call task pattern ?) → stage skill for review

Detailed extraction anatomy (input window size, mem0 recall, output schema) is in spec §3.5. This design covers the **interfaces** — what the engine exposes to other components.

### 4.2 Engine API

```python
# Called by capture layer
def process_turn(tool_event: dict, recent_window: list[dict], session_id: str) -> TurnResult:
    """Per-turn: extract lessons + state_delta. Calls DeepSeek Flash once."""
    ...

def process_session_end(session_id: str, transcript_path: str) -> SessionEndResult:
    """Session-end: reconcile + summarise + skill-create assessment. Single LLM pass."""
    ...

# Called by curator (periodic)
def run_curator() -> CuratorReport:
    """Archive stale entries, merge duplicates, regenerate MEMORY.md export."""
    ...
```

### 4.3 LLM Provider Fallback

```
DeepSeek Flash → Gemini Flash → Claude Haiku → defer
```

All three down → extraction deferred to next cycle. Raw transcript preserved. No data loss — re-extraction from transcript when provider recovers.

---

## 5. mem0 Substrate (Tier 3)

mem0 is the long-term memory store. It owns Tier 3 storage, retrieval, and the LLM-powered fact extraction pipeline.

### 5.1 Why mem0

| Concern | mem0 answer |
|---------|-------------|
| Cross-IDE | Lives at `~/.coworker/memory/`, not any IDE config dir |
| No background server | Library mode — in-process, `pip install mem0ai` |
| Hybrid search | Semantic (vector) + BM25 (keyword) + entity matching — one call |
| Agent-managed entries | `memory.add/update/delete` with `provenance: agent` metadata |
| Frozen snapshot | Read at session start; mid-session writes don't refresh active snapshot |

### 5.2 Entry Schema

Each mem0 entry carries our metadata layer on top of mem0's memory model:

| Field | Purpose | Example |
|-------|---------|---------|
| `memory` | The lesson/pattern text | "MCP first request 403-times-out; retry once before failing" |
| `user_id` | Which user | `<user>` |
| `agent_id` | Which agent | `ai-coworker` |
| `run_id` | Which session | `<session-id>` |
| `metadata.type` | lesson / state / convention / preference | `lesson` |
| `metadata.project` | Which project | `ai-coworker` |
| `metadata.topic` | Subject area slug | `mcp` |
| `metadata.problem` | Specific problem slug | `first-request-403` |
| `metadata.provenance` | agent / hand-written | `agent` |
| `metadata.state` | active / stale / archived / pinned | `active` |
| `metadata.last_used` | Last retrieval timestamp | `2026-07-25T10:00:00Z` |
| `metadata.use_count` | Retrieval counter | `3` |

`metadata.topic` + `metadata.problem` enable exact keyed lookup. `metadata.project` scopes search. The `memory` text field is the semantic search target.

### 5.3 Knowledge Type Mapping

PRD §1.6 defines three knowledge types. Where each lives:

| PRD Type | Storage | mem0? |
|----------|---------|-------|
| **经验总结** (lessons/patterns/pitfalls) | mem0 Tier 3 | ✅ Yes — `type=lesson` |
| **State / 进度** (current status) | Tier 2 state files | ⚠️ Mirror entry with `type=state` (for cross-session search) |
| **SOP** (reusable procedures) | Skill store → promoted to skill-factory | ❌ No — skills are a separate store |

### 5.4 What mem0 Replaces

| Prior plan | Now |
|------------|-----|
| sqlite-vec `knowledge_vec` (QA spec) | mem0 hybrid retrieval |
| analytics.db `knowledge` table as memory store | mem0 store. analytics.db keeps **raw** session/tool capture only (audit + analytics). |
| FTS5-based exact search | mem0 BM25 + B-tree metadata filters |
| MEMORY.md as hand-rolled storage | mem0 is source of truth; MEMORY.md is a curator-generated read-only export |

---

## 6. State Files (Tier 2)

Project-state memory lives in `docs/<initiative>/state/YYYY-MM-DD-state.md`. Live documents, updated continuously. Per-turn writes append; phase completions force a full state refresh.

### 6.1 Recording Criteria

Record when any of three dimensions change:
- **做了什么** — concrete output
- **对/错** — lessons, bugs, blind spots
- **进度** — done/not done/who/dependencies

Full criteria and exceptions in PRD §4.3.

### 6.2 State → Tier 3 Promotion

When an initiative completes, key lessons from the state file are promoted to mem0 Tier 3. This ensures cross-project knowledge persists after the initiative's state files become historical.

---

## 7. Context Injection (Tier 3 → Tier 1)

At session start, a frozen snapshot of relevant mem0 entries is injected into `CLAUDE.local.md` between markers. Both Claude Code and OpenCode read `CLAUDE.local.md` at session start → zero tool calls required.

### 7.1 Format

```markdown
<!-- MEMORY:ai-coworker START -->
## Memory Snapshot (frozen at 2026-07-25T10:00:00Z)
- Project uses ruff, E501 ignored
- MCP first request 403-times-out — retry once
- Prefers Chinese; prefers discussing before implementing
<!-- MEMORY:ai-coworker END -->
```

### 7.2 Behavior

| Property | Behavior |
|----------|----------|
| Frozen | Captured once at session start. Mid-session mem0 writes don't refresh it. |
| Replaced | Old marker block fully replaced next session start. Guarded by `semantic_merge.py` — human content outside markers is never touched. |
| Manual refresh | `coworker memory refresh` for long sessions (>2h). |
| Multi-project | Separate blocks per project: `<!-- MEMORY:<project> START -->` |

### 7.3 MEMORY.md Role

mem0 is the source of truth. `MEMORY.md` is a **read-only curator export** — regenerated wholesale on each curator run. Never written directly by per-turn sync or the agent. Format: section-delimited per project (`## Project: <name>` → grouped entries).

---

## 8. Pending Queue

Auto-created and auto-patched skills are staged for review, not applied immediately.

| Property | v1 |
|----------|-----|
| Location | `~/.coworker/pending/skills/<id>.json` |
| Review | `coworker skill pending` / `coworker skill approve <id>` / `reject <id>` |
| Batch | `coworker skill pending --approve-all --type lesson` |
| Auto-expiry | 30 days untouched → auto-rejected (never silently promoted) |
| Persistence | JSON files — survives restarts |
| Quality score | Deferred to v2 |

---

## 9. Curator

Periodic maintenance, triggered during agent idle time (≥2h idle, or ≤7 days since last run).

| Action | Mechanism |
|--------|-----------|
| Track usage | Increment `use_count` on retrieval |
| Archive stale | 30d unused → `state: stale`; 90d → `state: archived` |
| Pin valuable | High use_count entries → `state: pinned` (exempt from archival) |
| Merge duplicates | mem0 `memory.update()` to deduplicate |
| Regenerate export | Rebuild MEMORY.md from mem0 |
| Scope | **Only agent-created entries** (`provenance: agent`). Never touches hand-written (`provenance: hand-written`) or skill-factory-bundled content. |

Recovery: `coworker memory unarchive <id>` restores archived entries.

---

## 10. Safety Architecture

> Referenced from PRD §5.6. This section covers the **design** of safety mechanisms — how they're wired. Policy (thresholds, defaults, review modes) lives in the PRD.

### 10.1 Circuit Breaker

```
if skills_created + skills_patched in 24h > 3:
    halt all auto-evolution
    keep pending queue (don't discard)
    notify user
    require manual review to resume: coworker skill resume
```

### 10.2 Sandbox Testing

Before a pending skill is promoted: dry-run in isolated session → verify minimal safety checks → fail → stays pending with reason logged.

### 10.3 Rollback

Every auto-created/patched skill supports rollback to last known-good version. Automatic if post-patch error rate exceeds pre-patch by 50%+. Version history retains last 5 versions.

### 10.4 Known Gap

Sandbox checks are syntactic (dangerous shell patterns). Semantic threats (phishing, refusal collapse) are a recognized gap — tracked as v2 follow-up, not MVP blocker.

---

## 11. Error Handling Strategy

One principle: **degrade, don't crash.**

| Component | Failure | Degraded behavior |
|-----------|---------|-------------------|
| DeepSeek Flash (any LLM call) | Rate-limited / down | Provider fallback chain → defer to next cycle |
| mem0 store | Corrupt / unreadable | Rebuild from raw session transcripts (analytics.db) |
| mem0 vector index | Corrupt | mem0 re-index from memory entries |
| PostToolUse hook | Fails to fire | SubagentStop + Stop reconciliation back-fill; audit trail records gap |
| SubagentStop hook | Not configured / fails | Stop reads full transcript (subagent results in transcript) |
| `CLAUDE.local.md` lock | Concurrent sessions | fcntl lock; second session queues 3× with 1s backoff → conflict file |
| Curator | Fails mid-run | Partial results persisted; resumes from checkpoint next run |
| Skill `.usage.json` | Corrupt | Rebuild from skill dir listing; counts reset to 0 (lossy, non-blocking) |
| Circuit breaker | >3 skills/24h | Halt auto-evolution; pending queue preserved; `coworker skill resume` |

For detailed error codes and recovery procedures, see spec §9.

---

## 12. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Memory substrate | mem0 (library mode) | Hybrid retrieval (semantic + BM25 + entity), in-process, Python-native. No Docker, no always-on server. |
| Capture strategy | Per-turn + session-end (both) | Per-turn = reliability floor (session may be killed). Session-end = quality pass (full context). |
| Subagent capture | SubagentStop hook + transcript fallback | PostToolUse alone is blind to subagents — the richest content. |
| Embeddings | Local (fastembed, BAAI/bge-small, 384-dim) | Zero API cost, no network dependency, fast enough for single-user use. |
| Extraction LLM | Configured provider (remote default) | One LLM for all extraction/summarization. User's configured provider. |
| MEMORY.md | Read-only curator export | mem0 is source of truth. MEMORY.md stays for git-diffability and offline reading. |
| Pending queue | Simple JSON files v1 | Simplicity. Quality scoring and richer review UI deferred to v2. |
| Auto-evolution target | `CLAUDE.local.md` only, never `CLAUDE.md` | Personal context evolves; team-wide conventions are hand-written and reviewed. |

---

## 13. Component Dependency Graph

```
analytics.db (raw capture)
       │
       ▼
capture layer ──→ evolution engine ──→ mem0 (Tier 3)
       │                                    │
       │                              ┌─────▼─────┐
       │                              │ curator    │
       │                              │ (periodic) │
       │                              └─────┬─────┘
       │                                    │
       ▼                                    ▼
state files (Tier 2)              MEMORY.md (export)
       │                                    │
       └──────────┬─────────────────────────┘
                  │
                  ▼
         CLAUDE.local.md injection (session start)
```

**Build order (from this graph):**

1. mem0 setup (spike config → verify DeepSeek + local embedder + embedded vector store)
2. Capture layer (CLI commands + audit trail)
3. Evolution engine (per-turn extraction + session-end reconciliation)
4. Context injection (CLAUDE.local.md snapshot)
5. Pending queue (staging + approve/reject)
6. Curator (periodic maintenance + MEMORY.md export)

---

## 14. Interfaces to Auto-Worker

The auto-worker (design TBD, next document) is a downstream consumer of this platform:

| Auto-worker needs | Platform provides |
|-------------------|-------------------|
| Historical session data for training | analytics.db raw sessions + `coworker memory sync --batch` |
| Search past lessons | `memory.search()` via mem0 hybrid retrieval |
| Read project conventions | CLAUDE.local.md snapshot at session start |
| Write new lessons | `memory.add()` via standard capture paths |
| Stage skills | `coworker skill pending` queue |

Auto-worker runs in SDK mode (`coworker run --loop`), using the same mem0 store and capture layer — no separate infrastructure.

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-25 | Initial creation |
