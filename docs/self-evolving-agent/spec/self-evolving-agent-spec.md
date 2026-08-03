# Self-Evolving Agent — Memory Platform Spec

> Initiative: self-evolving-agent | Type: spec | Status: **draft v1.2**
>
> Derived from: [PRD v5](../prd/self-evolving-agent-prd.md) (requirements). Target PRD v6 (requirements-only).
>
> This is the spec for the **memory platform + self-evolution engine** (PRD §3–§5). It is NOT the QA/auto-worker spec — that one (`qa-autonomous-agent-spec.md`) is **DEFERRED** and preserved as reference for a separate downstream product.

---

## §0 How to Read This Spec

### 0.1 PRD ↔ Spec split

| Layer | Lives in | Contents |
|---|---|---|
| **Requirements** (what / why) | PRD v6 | R1–R7, three-tier model, taxonomy, skill lifecycle *behavior*, safety *behavior*, evolution metrics *as requirements* |
| **Solution** (how) | **this spec** | mem0 config, hook wiring, Hermes loop adaptation, schemas, error codes, dual-IDE coverage |

PRD v6 will be restructured to requirements-only (removing current §1.4, §6, §7, Appendix A — those move here). Until that restructure lands, this spec is the authoritative "how" and references PRD v5 section numbers.

### 0.2 The three external anchors and what we take from each

| Anchor | What it is | What we adopt | What we reject/replace |
|---|---|---|---|
| **mem0** ([github](https://github.com/mem0ai/mem0)) | Memory layer: LLM extraction + vector store + hybrid retrieval | **The memory substrate** — store, retrieve, extract facts (Tier 3). Library mode (in-process, no server). Hybrid retrieval (semantic + BM25 + entity). | Its default `gpt-5-mini` LLM and `text-embedding-3-small` embedder → swapped for DeepSeek Flash + local embedder |
| **Hermes Agent** ([docs](https://hermes-agent.nousresearch.com/docs/)) | Standalone self-improving agent with a closed learning loop | **The loop patterns** — skill create/patch/curator lifecycle, session-end summarization trigger, MEMORY.md/USER.md agent-curated philosophy, "smart approval system". Re-hosted on Claude Code/OpenCode hooks. | Its FTS5+SQLite recall layer (replaced by mem0); running Hermes itself (we are not a Hermes fork) |
| **walter-worker existing infra** | analytics.db, hooks, semantic_merge, templates, CLI | analytics.db as raw capture/audit layer; semantic_merge for CLAUDE.local.md injection; CLI/templates/adapters | analytics.db `knowledge` table as the memory store (mem0 owns memory now; analytics.db keeps raw session/tool capture) |

### 0.3 Boundary decision (mem0 vs Hermes — resolves the overlap)

Hermes and mem0 both have a "cross-session memory" story (Hermes = FTS5+summarization; mem0 = vector+BM25+entity). They overlap. The split:

- **mem0 = memory substrate.** Owns Tier 3 storage, retrieval, and fact extraction. **Replaces Hermes's FTS5.**
- **Hermes = the self-evolution loop.** Owns *when* to create/patch skills, the curator lifecycle, the session-end summarization trigger, and the agent-curated memory philosophy. Its loop is re-hosted on our hooks and **reads/writes mem0 instead of FTS5.**

---

## §1 Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │           CLAUDE CODE / OPENCODE         │
                    │           (the agent, doing real work)   │
                    └───────────────────┬─────────────────────┘
                                        │  tool calls / session lifecycle
                    ┌───────────────────▼─────────────────────┐
                    │        DUAL-IDE CAPTURE LAYER (§3)       │
                    │  Claude Code: PostToolUse + SubagentStop │
                    │               + Stop (async, stdin)      │
                    │  OpenCode:     tool.execute.after        │
                    │               + session.end              │
                    │  + audit trail + reconciliation          │
                    └───────┬──────────────────────┬───────────┘
                            │                      │
              per-turn (every tool call)           │  session-end (one more pass)
                            │                      │
                    ┌───────▼──────────────────────▼───────────┐
                    │        SELF-EVOLUTION LOOP (§4, Hermes)   │
                    │  • extract facts → mem0.add               │
                    │  • assess reusable workflow → skill-create│
                    │  • skill patch when outdated              │
                    │  • smart approval (staged review)         │
                    └───────┬────────────────────────────┬──────┘
                            │                            │
                ┌───────────▼───────────┐    ┌───────────▼────────────┐
                │  mem0 SUBSTRATE (§2)  │    │  STATE FILES (Tier 2)  │
                │  Tier 3 long-term     │    │  docs/<init>/state/    │
                │  store + retrieve +   │    │  per-turn progress     │
                │  extract (DeepSeek)   │    └────────────────────────┘
                └───────────┬───────────┘
                            │ frozen snapshot at session start
                    ┌───────▼───────────────────────────────────┐
                    │  CLAUDE.local.md injection (§5)            │
                    │  <!-- MEMORY:<project> START/END -->       │
                    └───────────────────────────────────────────┘
```

**LLM policy (global):** Every component that needs an LLM uses **DeepSeek Flash** (extraction, summarization, semantic filter, skill-reuse assessment, curator decisions). Fallback chain for outages only: DeepSeek Flash → Gemini Flash → Claude Haiku (§9). Embeddings are **not** an LLM call → use a **local embedder** (fastembed, BAAI/bge-small, 384-dim) to stay offline and avoid an OpenAI dependency.

**Cost:** per-turn extraction runs one DeepSeek Flash call per tool call. DeepSeek Flash is cheap (PRD §6.6: ~$0.0004/turn off-peak); cost is not a concern.

---

## §2 Memory Substrate — mem0

### 2.1 Why mem0 + library mode

| PRD requirement | mem0 satisfies it how |
|---|---|
| R1 (IDE-agnostic) | mem0 state lives in `~/.coworker/memory/`, not any IDE's config dir. Both IDEs hit the same store. |
| R2 (per-turn persistence, no manual save) | Hooks call `memory.add()` automatically after every tool call. |
| R3 (cross-session, exact + semantic search) | mem0 hybrid retrieval = semantic (vector) + BM25 (keyword/exact) + entity matching, fused. Temporal reasoning ranks the right dated instance. |
| R4 (agent-managed notes) | `memory.add/update/delete` — agent writes/patches/removes its own notes. |
| R5 (frozen snapshot) | Snapshot is read from mem0 at session start and injected via CLAUDE.local.md; mid-session mem0 writes do not refresh the active snapshot. |
| R6 (periodic cleanup) | Curator (§4.3) marks stale/archived via mem0 metadata; mem0 entries carry `state`/`last_used` fields. |
| R7 (no background server) | **mem0 library mode** (`pip install mem0ai`, in-process vector store). No Docker, no always-on process. |

> **R7 resolution:** Earlier concern that mem0 implies a background server is resolved — library mode is in-process. Self-hosted server / cloud modes exist but are **not used**.

### 2.2 Configuration

```python
from mem0 import Memory

config = {
    # Extraction + reasoning LLM = DeepSeek Flash (global policy)
    "llm": {
        "provider": "openai",                      # DeepSeek API is OpenAI-compatible
        "config": {
            "model": "deepseek-chat",              # "DeepSeek Flash" alias
            "base_url": "https://api.deepseek.com",
            "api_key": "env:DEEPSEEK_API_KEY",
        },
    },
    # Embeddings = local, NOT an LLM, NOT OpenAI
    "embedder": {
        "provider": "huggingface",                 # local ONNX via fastembed family
        "config": {
            "model": "BAAI/bge-small-en-v1.5",     # 384-dim, already spiked 6/6
        },
    },
    # In-process vector store (library mode — satisfies R7)
    "vector_store": {
        "provider": "qdrant",                      # embedded/local mode
        "config": {"path": "~/.coworker/memory/vector"},
    },
}

memory = Memory.from_config(config)
```

> **Spike (Task 0 of impl):** verify mem0's exact provider/field names for (a) DeepSeek as an OpenAI-compatible `llm`, (b) local `embedder`, (c) embedded `vector_store`. The config shape above is the target; exact keys to be confirmed against the installed mem0 version and pinned in `how-to/mem0-setup-how-to.md`.

### 2.3 Memory entry ↔ PRD taxonomy mapping

PRD §1.6 defines three knowledge types. mem0 stores two of them; the third is skills (not mem0):

| PRD type | Where it lives | mem0 representation |
|---|---|---|
| **SOP** (怎么做, reusable procedure) | `~/.coworker/skills/<name>/SKILL.md` → promoted to skill-factory | **Not in mem0.** Skills are a separate store (§5). |
| **经验总结** (lessons/patterns/pitfalls) | **mem0 Tier 3** | `memory.add(...)` entry, `type=lesson` |
| **State / 进度** (current status) | Tier 2 state files `docs/<init>/state/*.md` | mem0 entry with `type=state` (mirror, for cross-session search) |

**mem0 entry fields** (our schema, layered on mem0's memory model):

```json
{
  "memory": "MCP first request always 403-times-out; retry once before failing.",
  "user_id": "<user>",
  "agent_id": "walter-worker",
  "run_id": "<session-id>",
  "metadata": {
    "type": "lesson",                       // lesson | state | convention | preference
    "project": "walter-worker",
    "topic": "mcp",
    "problem": "first-request-403",
    "source_session": "<session-id>",
    "provenance": "agent",                  // agent | hand-written
    "state": "active",                      // active | stale | archived | pinned
    "last_used": "2026-07-25T10:00:00Z",
    "use_count": 0
  }
}
```

> This resolves PRD's "Tier 3 has no schema" gap. `metadata` lets us do exact keyed lookup (`project`+`topic`+`problem`) **and** semantic search in one store — satisfying R3's both-modes requirement natively via mem0 hybrid retrieval.

### 2.4 Operations

| Operation | mem0 call | When |
|---|---|---|
| Add lesson (per-turn) | `memory.add(messages=[turn], user_id=, run_id=session, metadata=)` | Every PostToolUse / SubagentStop (§3) |
| Add lesson (session-end) | `memory.add(messages=[full_transcript_summary], ...)` | Stop hook (§3) — reconciliation pass |
| Search | `memory.search(query, filters={"project":...}, top_k=)` | CLI `coworker memory search` / `/memory-search` |
| Update / dedup | `memory.update(id, ...)` | Session-end reconciliation, curator |
| Pin / archive | `memory.update(id, metadata={"state":"archived"})` | Curator (§4.3) |
| Snapshot read | `memory.search(query="project context", filters={"project":...}, top_k=N)` | Session start → inject into CLAUDE.local.md (§5) |

### 2.5 What mem0 replaces (vs prior plans)

| Prior plan (PRD v5 / QA spec) | Now |
|---|---|
| sqlite-vec `knowledge_vec` for semantic search (QA spec §2.5) | **mem0 hybrid retrieval** (semantic + BM25 + entity) |
| analytics.db `knowledge` table as the memory store (PRD §7.2.3) | **mem0 store**. analytics.db keeps **raw** session/tool capture only (the audit + analytics source). |
| LLM-synthesis-at-query-time for semantic layer | mem0's built-in hybrid retrieval (no per-query LLM needed except optional filter) |
| MEMORY.md as hand-rolled §-delimited file | mem0 is source of truth; MEMORY.md becomes a curator-generated read-only export (§5.2) |

---

## §3 Dual-IDE Capture Layer

This is the reliability-critical layer. PRD R2 demands per-turn persistence; the user demands **guaranteed data accuracy** across both IDEs. PostToolUse alone is unreliable (9 documented failure modes) and blind to subagents — so we use a **multi-trigger + audit + reconciliation** design.

### 3.1 Claude Code hooks

```json
// ~/.claude/settings.json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "",
      "command": "coworker memory sync --ide claude --trigger posttooluse",
      "async": true
    }],
    "SubagentStop": [{
      "matcher": "",
      "command": "coworker memory sync --ide claude --trigger subagentstop",
      "async": true
    }],
    "Stop": [{
      "matcher": "",
      "command": "coworker memory close --ide claude --trigger stop"
    }]
  }
}
```

- `async: true` on the per-turn hooks → extraction does not block the tool call (PRD v5 fix; carried forward).
- `session_id` arrives via **stdin JSON**, not an env var — hook command reads it from stdin.

### 3.2 OpenCode plugin events

Extend the existing `.opencode/coworker-analytics/` plugin:

```typescript
tool.execute.after → spawnSync('coworker', ['memory','sync','--ide','opencode','--trigger','posttooluse'])
session.end        → spawnSync('coworker', ['memory','close','--ide','opencode','--trigger','stop'])
// subagent-equivalent: opencode has no first-class subagent hook — see §8 gap
```

### 3.3 Reliability mechanism (how we "guarantee accuracy")

| Layer | Mechanism |
|---|---|
| **Multi-trigger** | PostToolUse (per tool) + SubagentStop (subagent results — the content-richest calls, previously invisible) + Stop (session-end reconciliation). |
| **Audit trail** | Every sync writes a timestamped record to `~/.coworker/memory/audit.log`. If a session has no records for an interval → flagged for investigation. |
| **Reconciliation** | Session-end Stop pass reads the full transcript, compares against per-turn captures, and back-fills anything missed (subagent results, dropped stdout, failed triggers). This is the "one more pass" the user required. |
| **Source of truth** | The raw session transcript (in analytics.db) is ground truth. mem0 entries are derived; if mem0 is corrupt, re-extract from transcript. |

### 3.4 per-turn vs session-end — both, complementary (per owner decision)

| | per-turn (PostToolUse / SubagentStop) | session-end (Stop) |
|---|---|---|
| **Purpose** | **Reliability** — don't lose data if the session is killed / runs long / never closes cleanly | **Quality** — full-context reconciliation, dedup, cross-task pattern extraction |
| |  |  |
| What it does | Extract lessons from this tool call → `memory.add` (exact I/O in §3.5) | Re-read full transcript → back-fill misses → `memory.add` reconciliation → trigger skill-create assessment |
| LLM cost | One DeepSeek Flash call per tool call (cheap, ~$0.0004) | One DeepSeek Flash call for the whole session |

> Rationale (owner): a session may not close for a long time, or may be killed without a Stop. session-end alone cannot guarantee capture. Therefore per-turn is the reliability floor; session-end is the quality pass on top. Both are mandatory.

### 3.5 Anatomy of one per-turn DeepSeek call

**Input** (what we pass to `memory.add`):
- The current tool event: `{tool, input, result}`
- A bounded recent window: the last ~3–5 turns (context to judge "is this a lesson?" — e.g. to see the error that led to a workaround)
- A cheap mem0 recall of related existing lessons on the same topic (retrieval, no LLM) — passed as "already known" so DeepSeek avoids obvious duplicates

**Not** passed: the full session history (session-end's job — see "history" below).

**Output** (single structured DeepSeek pass):
- `lessons`: 0..N extracted facts (经验总结). **Most tool calls → 0** ("ran `git status`" yields nothing). Some → 1+ facts.
- `state_delta`: optional one-line Tier 2 progress note (做了什么 / 进度), or null if the turn doesn't meet PRD §4.3 recording criteria.
- Each lesson → written to mem0; `state_delta` → appended to Tier 2 state file.

**Not** done per-turn: no narrative summary, no skill creation (skill-create needs ≥10 tool calls / full-task context → §4.1 threshold or session-end).

**Concrete example:**
- Tool event: agent edits `auth.py`, first MCP request 403s, retries, succeeds.
- Input: `{tool: Edit, diff, result} + last 3 turns + mem0 recall(topic=mcp)`.
- Output: `lessons: [{type: lesson, topic: mcp, problem: first-request-403, memory: "MCP first request 403-times-out; retry once before failing"}], state_delta: "fixed token refresh in auth.py"`.

**"What about previous history?"** — per-turn does **not** reprocess history. Each turn is extracted once, when it happens. The recent window is just context for judging the current turn, not re-summarization. Full-history reconciliation, cross-turn dedup, cross-task pattern detection, and skill-reuse assessment all happen at **session-end** (§3.4). So nothing is lost if a session is killed mid-way — per-turn already captured each turn incrementally; session-end just cleans up and connects the dots.

---

## §4 Self-Evolution Loop (Hermes patterns, re-hosted)

We adopt Hermes's closed learning loop. Hermes is a standalone agent; we **borrow its loop design** and run it on our hooks + mem0, not run Hermes itself.

### 4.1 Skill creation

| | Hermes | Ours |
|---|---|---|
| Trigger | after 5+ tool calls | after **10+ tool calls** (PRD §5.1: a single Claude Code task easily generates 50+; Hermes's 5 is too low). Configurable via `coworker config set skill.create.threshold`. |
| Standard | `SKILL.md`, agentskills.io | Same — reuse existing `skill-create` |
| Output | skill in skills dir | staged to `~/.coworker/pending/skills/` (review mode, §6) |

Two triggers (PRD §5.1), both invoke `skill-create` with the session transcript as context:
1. **In-session** — task completes with ≥ threshold tool calls.
2. **Post-session** — the Stop reconciliation pass also assesses reusable workflows (full session picture → catches cross-task patterns).

### 4.2 Skill patching

When a skill is used and found outdated/wrong → invoke `skill-edit` with surgical `old_string → new_string` (Hermes `patch` action). `patch_count` feeds the curator. Same approval model + safety gates as creation.

### 4.3 Curator

| | Hermes | Ours |
|---|---|---|
| Schedule | every 7 days, after 2h+ idle | Same |
| Lifecycle | active → stale (30d) → archived (90d) | Same |
| Metrics | view/use/patch counts | + `error_rate`, `patch_frequency`, `user_override_rate`, regression detection (PRD §5.2) |
| Scope | never touches bundled/hub | never touches hand-written / skill-factory bundled |
| Recovery | — | `coworker skill/memory unarchive` |

### 4.4 Smart approval system

Hermes has a "smart approval system that learns safe commands over time" — **not** `write_approval` (that pattern name in PRD v5 §5.1 is unverified and should be corrected). We adopt the *concept*: staged review by default (`auto_approve: false`), with per-domain opt-in to auto for low-risk operation types. Safety gates (circuit breaker, sandbox, rollback) per PRD §5.6.

---

## §5 Context Injection & Snapshot (Tier 3 → Tier 1)

### 5.1 Frozen snapshot at session start

At session start, read relevant mem0 entries → inject into CLAUDE.local.md between markers. Both Claude Code and OpenCode read CLAUDE.local.md at start, so the snapshot is available with **zero tool calls** (R5).

```markdown
<!-- MEMORY:walter-worker START -->
## Memory Snapshot (frozen at session start)
- Project uses ruff, E501 ignored
- MCP first request 403-times-out — retry once
- Prefers Chinese; prefers discussing before implementing
<!-- MEMORY:walter-worker END -->
```

- **Frozen:** captured once at start; mid-session mem0 writes do not refresh it.
- **Replaced:** old marker block is fully replaced next session start (reuse `templates/local_claude_md.py` `inject_initiative_into_local_md()` pattern, guarded by `semantic_merge.py` so human content is never corrupted).
- **Manual refresh:** `coworker memory refresh` for long sessions (>2h).

### 5.2 MEMORY.md role — read-only export (decision B)

mem0 is the source of truth. **MEMORY.md is kept as a read-only, curator-generated human-readable mirror** — for git-diffability, offline reading, and as a human-inspectable view of Tier 3. The curator (§4.3) regenerates it from mem0 on each run.

- **Never written directly** by per-turn sync or the agent mid-session (mem0 is written; MEMORY.md is exported).
- **Format:** section-delimited per project (`## Project: <name>` → grouped entries), regenerated wholesale each curator run (not incrementally patched).
- **PRD v5 §6.2** lists `MEMORY.md` as Tier 3 storage; this spec supersedes that — mem0 owns storage, MEMORY.md is a derived export. PRD v6 §3.5/§6.2 must be updated to match.

---

## §6 Pending Queue (simple version)

Per owner: a simple solution first. Requirements (go in PRD v6): staged skills are reviewable; the queue must not grow unbounded.

| Capability | Simple v1 |
|---|---|
| Stage | auto-created/patched skills → `~/.coworker/pending/skills/<id>.json` |
| Review | `coworker skill pending` lists queue; `coworker skill approve <id>` / `reject <id>` |
| **Batch** | `coworker skill pending --approve-all --type lesson` (batch by type) |
| **Auto-expiry** | pending items untouched for **30 days → auto-rejected** (not promoted silently) |
| Quality score | deferred to v2 (just `use_count` + `patch_count` for now) |
| Persistence | survives restarts (JSON files, not in-memory) |

Safety gates still apply (circuit breaker >3 skills/24h, sandbox dry-run before promotion, rollback) — see PRD §5.6.

---

## §7 Evolution Metrics

PRD currently has only **safety** metrics (§5.6.5). The vision is "smarter over time" — we add **effectiveness** metrics. These become requirements in PRD v6.

| Metric | Signal | Target |
|---|---|---|
| `skill_reuse_rate` | fraction of sessions that invoke an auto-created skill | rising over time |
| `user_correction_rate` | user overrides/corrects agent per task | falling over time |
| `task_first_pass_rate` | tasks completed without rework | rising over time |
| `memory_hit_rate` | searches that return a useful entry | rising; non-zero baseline means memory is being used |
| `refusal_rate` (safety) | agent refusing unsafe requests | stays high |
| `unsafe_output_rate` (safety) | harmful output | near 0 |
| `circuit_breaker_trips` (safety) | runaway auto-evolution | near 0 |

Collection: logged to analytics.db per session; surfaced in curator `REPORT.md`. Exact formulas + dashboard → impl detail, not spec.

---

## §8 Dual-IDE Coverage Matrix

Per owner: PRD + spec must cover **both** Claude Code and OpenCode as first-class. This promotes PRD Open Question #4 (OpenCode reliability) from deferred to must-assess.

| Concern | Claude Code | OpenCode | Status / mitigation |
|---|---|---|---|
| Per-tool capture | PostToolUse (async) | `tool.execute.after` | **OpenCode coverage unverified** — spike needed: does it fire for all tool types incl. MCP/subprocess? |
| Subagent capture | SubagentStop | **no first-class equivalent** | OpenCode gap. Mitigation: session-end reconciliation back-fills from transcript. |
| Session end | Stop | `session.end` | both OK |
| Session id source | stdin JSON | plugin context | OK |
| stdout injection | dropped (by design) | TBD | sync writes to disk, not context (both) |
| Settings location | `~/.claude/settings.json` | `.opencode/coworker-analytics/` plugin | OK |

**Spec requirement:** before declaring dual-IDE production-ready, run the OpenCode coverage spike. Until then OpenCode memory is best-effort with audit-trail verification (PRD §6.5 stance, now a work item not a footnote).

---

## §9 Error Handling & Degraded Mode

Adapted from QA spec §5.2 error philosophy (degrade, don't crash). LLM provider fallback applies to **all** DeepSeek Flash calls:

| Component | Failure | Degraded behavior |
|---|---|---|
| DeepSeek Flash (any LLM call) | rate-limited / down | → Gemini Flash → Claude Haiku. All three down → defer to next cycle; raw transcript preserved (no data loss). |
| mem0 store | corrupt / unreadable | rebuild from raw session transcripts (analytics.db) via re-extraction. Log event. |
| mem0 vector index | corrupt | mem0 re-index from memory entries. |
| PostToolUse hook | fails to fire | SubagentStop + Stop reconciliation back-fill; audit trail records the gap. |
| SubagentStop hook | not configured / fails | session-end Stop reads full transcript (subagent results are in transcript). |
| CLAUDE.local.md lock | concurrent sessions | file lock (fcntl); second session queues 3× w/ 1s backoff, then conflict file for later merge. |
| Curator | fails mid-run | partial results persisted; resumes from checkpoint next run. |
| Skill `.usage.json` | corrupt | rebuild from skill dir listing; counts reset to 0 (lossy, non-blocking). |
| Circuit breaker | >3 skills/24h | halt auto-evolution, keep pending queue, notify user, `coworker skill resume` to re-enable. |

Error codes: reuse the QA `E0xx` style registry, namespaced `MEM_E0xx` (mem0/extraction), `SYNC_E0xx` (capture), `SKILL_E0xx` (lifecycle). Exact table → impl.

---

## §10 Open Questions

1. **mem0 exact config shape** — provider/field names for DeepSeek-as-LLM, local embedder, embedded vector store. Task-0 spike.
2. **OpenCode coverage** — does `tool.execute.after` fire for all tool types? §8 spike.
3. **mem0 extraction quality** — DeepSeek Flash on session content: accuracy of lesson extraction to be validated on real sessions (feeds evolution metrics baseline).
4. **GEPA/DSPy prompt evolution** — deferred to v2 (out of MVP scope, per PRD §8).

---

## §11 Dashboard API & Data Layer

This section specifies the **how** for PRD §5.8 (R8–R15). The Evolution page is a new tab in the existing analytics dashboard, served by the same FastAPI app (`src/coworker/dashboard/app.py`) and matching the existing vanilla JS + CSS patterns.

### 11.1 API Endpoints

New endpoints added to `app.py`:

| Endpoint | Method | Returns | Satisfies |
|----------|--------|---------|-----------|
| `/api/evolution/overview` | GET | Stat card data | R14 (evolution score) |
| `/api/evolution/skills` | GET | Skills list, filtered | R8, R10, R12, R15 |
| `/api/evolution/skills/{id}` | GET | Single skill detail + session trace | R10 |
| `/api/evolution/experiences` | GET | Experiences list, filtered | R9, R11, R12, R15 |
| `/api/evolution/experiences/{id}` | GET | Single experience detail + retrieval history | R11 |
| `/api/evolution/pending` | GET | Pending queue items | R13 |
| `/api/evolution/approve/{id}` | POST | Approve pending item | R13 |
| `/api/evolution/reject/{id}` | POST | Reject pending item | R13 |

### 11.2 Data Sources

The Evolution page reads from three stores — unified in the API layer, not in a separate DB:

| Data | Source | Query pattern |
|------|--------|---------------|
| Skills (auto-train flag, status, created) | Skill store `~/.coworker/skills/<name>/SKILL.md` + `usage.json` sidecar | Filesystem scan + JSON parse |
| Skills (session trace, call count) | analytics.db `tool_calls` table: `WHERE tool='Skill' AND detail LIKE '%<skill_name>%'` | SQL join on session_id |
| Experiences (memory text, metadata) | mem0: `memory.search()` with filters | mem0 Python API, no SQL |
| Experiences (retrieval count, last retrieved) | mem0 metadata: `use_count`, `last_used` | Read from mem0 entry metadata |
| Pending queue | `~/.coworker/pending/skills/<id>.json` | Filesystem scan |

### 11.3 Query: Evolution Overview

```python
def query_evolution_overview() -> dict:
    """Stat cards for the Evolution page."""
    skills = list_skills(provenance="agent")        # filesystem scan
    experiences = mem0.search(filters={"metadata.provenance": "agent"})
    total_sessions = db.count("sessions")
    sessions_with_auto_skill = db.count_sessions_using_skill(provenance="agent")

    return {
        "auto_trained_skills": len(skills),
        "auto_trained_experiences": len(experiences),
        "pending_review": len(list_pending()),
        "skill_reuse_rate": sessions_with_auto_skill / max(total_sessions, 1),
        "evolution_score": compute_evolution_score(skills, experiences, total_sessions),
    }
```

### 11.4 Query: Skills with Trace

```python
def query_skills(auto_train_only=True, project=None, status="active") -> list[dict]:
    """Skills list for the Evolution page table."""
    skills = []
    for skill in list_skills():
        if auto_train_only and skill.provenance != "agent":
            continue
        if project and skill.project != project:
            continue
        if status != "all" and skill.state != status:
            continue

        # Session trace from analytics.db
        sessions = db.query("""
            SELECT DISTINCT session_id
            FROM tool_calls
            WHERE tool = 'Skill' AND detail LIKE ?
        """, (f"%{skill.name}%",))

        skills.append({
            "name": skill.name,
            "provenance": skill.provenance,
            "status": skill.state,
            "created_at": skill.created_at,
            "sessions_invoked": len(sessions),
            "total_calls": skill.usage.total_calls,
            "last_used": skill.usage.last_used,
            "reuse_rate": len(sessions) / max(total_sessions, 1),
            "session_ids": [s[0] for s in sessions],
        })
    return skills
```

### 11.5 Query: Experiences with Trace

```python
def query_experiences(auto_train_only=True, project=None, status="active") -> list[dict]:
    """Experiences list for the Evolution page table."""
    results = mem0.search(
        query="",  # empty = return all, filtered by metadata
        filters=build_filters(auto_train_only, project, status),
        top_k=200,
    )
    return [
        {
            "id": r.id,
            "memory": r.memory,
            "provenance": r.metadata.get("provenance"),
            "topic": r.metadata.get("topic"),
            "project": r.metadata.get("project"),
            "source_session": r.metadata.get("source_session"),
            "use_count": r.metadata.get("use_count", 0),
            "last_used": r.metadata.get("last_used"),
            "state": r.metadata.get("state"),
        }
        for r in results
    ]
```

### 11.6 Provenance Determination

```python
def get_skill_provenance(skill_name: str) -> str:
    """Determine skill origin."""
    path = Path(f"~/.coworker/skills/{skill_name}/SKILL.md").expanduser()
    if not path.exists():
        return "unknown"
    # Check usage.json sidecar
    usage = read_usage_json(skill_name)
    if usage.get("provenance") == "agent":
        return "agent"        # 🟢 Auto-Train
    if usage.get("source") in ("skill-factory", "bundled"):
        return "bundled"      # 🔵 Bundled
    return "manual"           # ⚪ Manual (default for hand-written)
```

### 11.7 Frontend Integration

The Evolution page is a new SPA view in the existing dashboard:

- **Sidebar:** Add `{id:'evolution', label:'Evolution', icon:'◉', section:'Monitoring'}` to the `views` array in `dashboard.js`
- **Loader:** `loadEvolution()` function following the existing pattern (`loadSkills`, `loadKnowledge`)
- **HTML:** No new page — rendered dynamically via `innerHTML` like all other views
- **CSS:** Reuse existing `.tag-auto`, `.tag-manual`, `.tag-bundled`, `.tag-pending`, `.tag-stale`, `.tag-active`, `.tag-archived` classes (add to `dashboard.css`)
- **Expand:** Click-to-expand rows for session trace using the `expand-row` pattern

---

## §12 Auto-Worker Loop

This section specifies the **how** for the auto-worker (design: [auto-worker-design.md](../design/auto-worker-design.md)). The auto-worker is a CLI-driven SDK-mode agent that audits project state against declared intent and self-executes improvements.

### 12.1 Entry Point

```bash
coworker run --loop --skill auto-worker [--max-hours 12] [--project walter-worker]
```

Runs on the same infrastructure as the implicit evolution loop — same mem0 store, same state files, same capture hooks. The difference: SDK mode (explicit loop) vs hook-embedded (implicit).

### 12.2 Loop State Machine

```
                  ┌──────────┐
                  │   INIT    │
                  │ load context│
                  └─────┬─────┘
                        │
                        ▼
                  ┌──────────┐     nothing to check
                  │  CHECK    │──────────────────▶ STOP
                  │ gap detection│
                  └─────┬─────┘
                        │ findings
                        ▼
                  ┌──────────┐
                  │ DECIDE    │
                  │ per finding│
                  └─────┬─────┘
                        │
              ┌─────────┼──────────┐
              ▼         ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │  FIX   │ │  ASK   │ │  SKIP  │
         │ execute│ │ user   │ │ note it│
         └───┬────┘ └───┬────┘ └───┬────┘
             │          │          │
             ▼          ▼          │
         ┌────────┐ ┌────────┐     │
         │ VERIFY │ │ WAIT   │     │
         │ test   │ │ answer │     │
         └───┬────┘ └───┬────┘     │
             │          │          │
             └──────────┼──────────┘
                        │
                        ▼
                  ┌──────────┐
                  │  NOTE    │
                  │ state file│
                  └─────┬─────┘
                        │
                        ▼
                  ┌──────────┐
                  │ LOOP     │
                  │ back to   │
                  │ CHECK     │
                  └──────────┘
```

### 12.3 Rule Implementation

8 rules from the design doc, mapped to implementation:

| Rule | Implementation |
|------|---------------|
| R1: Validate against raw data | `GapCheck.verify()` reads analytics.db raw tables, runs `grep` on codebase, executes tests fresh. Never reads derived tables or mem0 summaries as truth. |
| R2: Dead code detection | `DeadCodeDetector` class: scans skill `usage.json` for zero-call skills, scans session transcripts for tool-call-less sessions, scans config keys against codebase grep. |
| R3: Three-layer attribution | `RequirementAuditor.audit()` → per PRD/spec item: Layer 1 (grep for code) → Layer 2 (run tests) → Layer 3 (semantic comparison of intent vs implementation). Each layer is a separate method. |
| R4: Working Notes | `StateFile.has_been_checked(item_id)` → skip. `StateFile.mark_checked(item_id, verdict)` after each check. Before any work, consult state file. |
| R5: Vision Check | `VisionCheck.evaluate(change)` → prompt: "Self-evolving agent 的愿景是让 agent 越来越聪明。这个改动是否靠近此愿景？" → `{verdict: proceed\|skip, reason}`. |
| R6: Research → Advocate | `ResearchAdvisor.advise(change)` → 1. WebSearch for similar solutions → 2. Invoke `contrarian-review` skill on proposed change → 3. Return `{action: fix\|ask\|skip, rationale}`. |
| R7: Context-Aware Input | `ContextLoader.load()` → reads PRD items, spec sections, design decisions, Open Questions, devil's advocate findings, prior state files. Cross-references for contradictions. |
| R8: Ask, Don't Block | `UserGate.ask(question)` → sends Telegram notification → writes to State File Open Questions → returns `ASK_PENDING`. Next loop: `UserGate.check_pending()` → answered? → process. Still unanswered? → skip again. |

### 12.4 Training Pipeline (Batch Extraction)

Before the auto-worker runs its first loop, a batch pass extracts initial knowledge from historical sessions:

```bash
coworker memory train --sessions all --target 10-skills 10-experiences
```

**Implementation:**
1. Read **all** past sessions from analytics.db (`sessions` + `tool_calls` + `messages` tables). No limit — every session is training data.
2. For each session: pass full transcript through DeepSeek Flash
3. Output per session: `{lessons: [...], skill_candidates: [...]}`
4. Aggregate across sessions: merge similar lessons, deduplicate, identify recurring patterns
5. Write top 10 skills to `~/.coworker/pending/skills/` (staged, not auto-approved)
6. Write top 10 experiences to mem0 via `memory.add()`
7. Generate training report: `~/.coworker/memory/training-report-{date}.md` — includes total sessions processed, lessons extracted, skills identified

**Selection criteria for top 10:**
- Skills: highest pattern frequency across sessions (same task pattern appearing ≥3 times)
- Experiences: highest retrieval likelihood (lessons that would have helped in the most past sessions)

### 12.5 Claude SDK Validation Harness

After training, validate that knowledge is useful:

```bash
coworker memory validate --task <task-definition> --compare-baseline
```

**Implementation:**
1. Define a task (e.g., "Add a `coworker stats` CLI command") — task definition is in `docs/self-evolving-agent/test-plan/`
2. Spawn **Agent A** (baseline): Claude SDK session, no CLAUDE.local.md snapshot, no mem0
3. Spawn **Agent B** (with memory): Claude SDK session, CLAUDE.local.md snapshot injected, mem0 accessible
4. Both agents run the same task
5. Compare transcripts:

```python
def compare_runs(baseline: RunResult, with_memory: RunResult) -> ComparisonReport:
    return {
        "baseline_tool_calls": baseline.tool_call_count,
        "memory_tool_calls": with_memory.tool_call_count,
        "tool_call_reduction": baseline.tool_call_count - with_memory.tool_call_count,
        "baseline_incorrect_assumptions": count_incorrect(baseline.transcript),
        "memory_incorrect_assumptions": count_incorrect(with_memory.transcript),
        "memory_skills_invoked": extract_skill_calls(with_memory.transcript),
        "memory_experiences_retrieved": extract_memory_searches(with_memory.transcript),
        "verdict": "improved" if with_memory.tool_call_count < baseline.tool_call_count else "no_change",
    }
```

### 12.6 Model Routing

```python
MODEL_ROUTING = {
    "gap_detection": "deepseek-flash",       # per-item yes/no, mechanical
    "numerical_validation": None,            # SQL queries, no LLM
    "dead_code_detection": None,             # grep + analytics.db, no LLM
    "investigation": "deepseek-pro",         # git history + multi-source synthesis
    "vision_check": "deepseek-pro",          # subjective, needs judgment
    "research_web": None,                    # WebSearch tool, no LLM reasoning
    "advocate_review": "claude",             # safety-critical, strongest model
    "code_fix": "deepseek-flash",            # mechanical, cheap
    "report": "deepseek-pro",                # narrative quality
    "extraction": "deepseek-flash",          # lesson extraction from transcript
}
```

### 12.7 State File Format

The auto-worker writes to `docs/self-evolving-agent/state/auto-worker-YYYY-MM-DD-state.md`:

```markdown
# Auto-Worker Run State

**Started:** 2026-07-25T10:00:00Z
**Status:** in_progress
**Max Duration:** 12h (elapsed: 2h15m, remaining: 9h45m)
**Current Phase:** gap_detection (round 1)

## Open Questions
| ID | Question | Asked At | Status |
|----|----------|----------|--------|
| Q-1 | Is ruff E501 intentionally ignored project-wide? | 2026-07-25T10:30:00Z | pending |
| Q-2 | Should skill-create threshold be 10 or 15? | 2026-07-25T11:00:00Z | answered: 10 |

## Checked (Round 1)
| ID | What | Source | Verdict | Date |
|----|------|--------|---------|------|
| C-1 | R3 semantic search (PRD §3.1) | grep + mem0 test | NOT DONE | 2026-07-25 |
| C-2 | PostToolUse async:true (PRD §5.1) | settings.json | DONE RIGHT | 2026-07-25 |
| C-3 | skill "session-memory" usage count | analytics.db vs usage.json | MISMATCH (3 vs 7) | 2026-07-25 |

## Fixed (Round 1)
| ID | What | Action | Date |
|----|------|--------|------|

## Skipped (Round 1)
| ID | What | Reason | Date |
|----|------|--------|------|
| S-1 | E501 line-length rule | Deliberate project choice (git log: abc123) | 2026-07-25 |
```

---

## Change Log

| Date | Change |
|---|---|
| 2026-07-25 | v1: New spec for memory platform + self-evolution engine. mem0 substrate (library mode, DeepSeek Flash extraction, local embedder). Hermes loop patterns re-hosted on dual-IDE hooks (PostToolUse/SubagentStop/Stop + OpenCode tool.execute.after/session.end). per-turn + session-end capture (both). Simple pending queue. Evolution metrics. Supersedes the storage/search portions of `qa-autonomous-agent-spec.md` (which remains as deferred auto-worker reference). |
| 2026-07-25 | v1.2: Added §11 Dashboard API & Data Layer (8 endpoints, 3 data source integration patterns, query specs for overview/skills/experiences, provenance determination, frontend integration). Added §12 Auto-Worker Loop (state machine, 8-rule implementation, training pipeline, Claude SDK validation harness with comparison metrics, model routing, state file format). Satisfies PRD v7 §5.8 (R8–R15) and auto-worker design. |
| 2026-07-25 | v1.1: Closed 2 open questions — MEMORY.md = read-only curator export (decision B); per-turn DeepSeek cost accepted (no tuning knobs). Added §3.5: anatomy of one per-turn DeepSeek call (input = tool event + bounded recent window + mem0 recall; output = lessons 0..N + optional state_delta; history reprocessing is session-end only). |
