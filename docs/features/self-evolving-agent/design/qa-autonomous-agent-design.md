# QA Autonomous Agent — Design ⚠️ DEFERRED

> **Status: DEFERRED (2026-07-25)**
>
> This document has been renamed conceptually to **auto-worker** — a self-discovering, self-fixing agent that depends on the three-tier memory system. It will be rewritten after the memory platform (PRD v4) is built.
>
> For now, focus is on the memory infrastructure: Session → Project State → Long-Term (see PRD §3).
>
> This document is preserved as-is for reference. Do NOT implement from it until it is rewritten.

> Initiative: self-evolving-agent | Type: design | Status: **DEFERRED**
>
> Builds on: [self-evolving-agent PRD v3](../prd/self-evolving-agent-prd-zh.md)
> Backend (Path 1b, chosen 2026-07-24): MEMORY.md (content) + **sqlite-vec + fastembed** (semantic search, 384-dim, in-process) + slimmed SQLite `knowledge_index` (exact queries only). Task tracking + session continuity via state files. Self-contained — does **not** depend on the unbuilt self-evolution-engine modules. See the "v2 Backend" section below and [dependency-and-sequencing.md](../dependency-and-sequencing.md).

## Overview

A skill pipeline within self-evolving-agent that autonomously:

1. Reads scattered PRD/goal/context docs
2. Audits project state against those docs
3. Finds unfinished work + optimization opportunities
4. Searches prior knowledge/decisions — same project, same topic, same problem, time-ordered, newest wins
5. Self-executes remaining work and optimizations
6. Persists progress via the PRD's State Engine (§4)

**Relationship to PRD:** This is a concrete application of the self-evolving-agent loop (§2). **(v2 / Path 1b)** It uses MEMORY.md + sqlite-vec + fastembed for knowledge retrieval and semantic search (see v2 Backend). Task tracking and session continuity use the existing state file pattern. It does **not** depend on the PRD's FTS5 (§3), State Engine (§4), or self-evolution engine (§5), which are not yet built. This design focuses on the _QA-specific logic_ that the general PRD doesn't cover: gap detection methodology, continuous discovery dimensions, test plan lifecycle, and weak-model compensation strategies.

**v3 implicit evolution integration:** In v3, evolution happens implicitly after every session — skills are created/refined from session context without an explicit "evolve" command (§5.4). The QA pipeline integrates with this in two modes: (1) **SDK mode** — QA runs via `coworker run --skill qa-orchestrator` for scheduled audits, producing session context that feeds implicit evolution; (2) **Post-session trigger** — QA is triggered automatically after a development session via the SessionStop hook, analyzing that session's work for gaps and feeding findings back into the implicit evolution pipeline.

**Target model constraint:** Primary execution uses DeepSeek v4 Pro/Flash — not a frontier model. Architecture compensates via decomposition, structured schemas, multi-pass verification, and leveraging the vec0 index as a pre-filter (avoid asking the model to "remember" or "understand" raw documents in one shot).

**Time constraint:** Each run starts by asking the user for max duration (default 12 hours). When time expires, loop gracefully stops and saves state via the State Engine.

---

## v2 Backend: sqlite-vec + fastembed (Path 1b)

> **Decision (2026-07-24):** sqlite-vec (in-process SQLite extension) + fastembed (ONNX, `BAAI/bge-small-en-v1.5`, 384-dim) on the existing `analytics.db`. Zero new services, zero API keys, zero external binaries. Spike validated 6/6 semantic queries on real knowledge entries (2026-07-24). See [dependency-and-sequencing.md](../dependency-and-sequencing.md).

### What sqlite-vec replaces (v1 → v2)

| v1 (self-built) | v2 (sqlite-vec + fastembed) |
|---|---|
| `knowledge_index.py` + FTS5 full-text search | **sqlite-vec vec0** — in-process KNN (L2) with SQL metadata filtering; `knowledge_index.py` handles exact queries only |
| state file • gap list (manual markdown) | **state file** (unchanged) — pending / fixing / done status per gap and optimization item |
| state file • progress snapshot | **state file** (unchanged) — section headers track current phase, progress, decisions made |
| (no semantic search) | **fastembed** — ONNX, `BAAI/bge-small-en-v1.5`, 384-dim, no GPU, 100% offline |

> Task tracking and session continuity are handled by the existing state file pattern (`docs/<initiative>/state/`) — no external task board or "principles engine" needed for a single-skill QA pipeline.

### Storage (same database, one file)

| Surface | Holds | Lifetime |
|---|---|---|
| `MEMORY.md` | full decision content (reasoning, context, evidence) | durable, human-readable |
| SQLite `knowledge_index` (`analytics.db`) | metadata for exact `WHERE project=? AND topic=? AND problem=?` queries (schema in §1.2) | durable |
| **SQLite `knowledge_vec`** (`analytics.db`, same DB) | 384-dim embeddings keyed to `knowledge_index.rowid` — KNN semantic search via vec0 | durable |

> All three share `analytics.db` — **one file, no new service.** The existing analytics dashboard reads the same database unchanged.

### Data flow

```
Ingestion:  source → standardizer → SQLite + MEMORY.md + fastembed.encode() → knowledge_vec
Query:      PRD item → SQLite exact → (miss?) vec0 KNN → LLM semantic filter
Gap tracking: state file (docs/self-evolving-agent/state/) — per-gap status: pending/fixing/done
Run continuity: state file — reads prior run's section → resume where left off
Discovery:  7 dimensions (grep / coverage / deps / perf / security / error-handling)
```

### Module roles (`src/coworker/qa/`)

| File | Role |
|---|---|
| `knowledge_extract.py` | source → standardizer → SQLite + MEMORY.md + fastembed → knowledge_vec |
| `knowledge_search.py` | Layer 1 SQLite exact → Layer 2 vec0 KNN → LLM filter |
| `gap_check.py` | PRD-vs-reality, three-layer verification |
| `fix.py` | fix with state file tracking + mini test plan |
| `discovery.py` | 7-dimension discovery |
| `orchestrator.py` | state-driven phase management, time budget |

### Dependencies

- **`sqlite-vec`** — Python package (`pip install sqlite-vec`), loads as SQLite extension in-process. No server, no config.
- **`fastembed`** — ONNX runtime, `BAAI/bge-small-en-v1.5`, 384-dim. `pip install fastembed`. First run downloads ~50MB model. No API key, no GPU. Already validated in this environment.
- **`onnxruntime`** — already installed.

### Why not Guild OSS / Mem0

- **Guild OSS** — adds a Go binary, MCP server, and external state dir (`~/.guild/`). Its Quests/Briefs/Oaths primitives overlap with existing state files. Go binary ≠ Python-callable API (execution-model ambiguity). Overkill for single-skill, single-agent use.
- **Mem0** — requires a vector DB backend (Qdrant/Chroma) plus an extraction LLM. Heavier than needed.
- **sqlite-vec** — extends the existing `analytics.db`; zero new services; Python-native API (no MCP proxying); dashboard reads the same file unchanged.

### Error handling (spec §5.2)

| Code | Fault | Behavior |
|---|---|---|
| `QA_E011` | Embedding model unavailable (fastembed) | Degrade: SQLite exact-match only, mark `confidence: low` |
| `QA_E004` | vec0 index corrupted | Rebuild from knowledge table + fastembed re-embed |

---

## Core Loop (extends PRD §2.2 — SDK mode)

> **Mode: SDK.** This loop runs via `coworker run --skill qa-orchestrator` — the SDK mode execution path. In SDK mode, the agent operates without an interactive conversation context; all user interaction (time budget prompt, test plan confirmation) goes through the State Engine and skill hooks. The loop is also triggerable post-session via SessionStop hook, where it reads the just-completed session's context and runs discovery/repair on that scope.

```
Run:
  0. Ask user: "这次跑多久？" (default: 12h)
     → store in state.max_duration_seconds
  1. Load context:
     - PRD & goal docs (filesystem)
     - Knowledge snapshot (MEMORY.md via PRD §3.6)
     - Prior state (State Engine §4)
     - Search relevant decisions (vec0 KNN via sqlite-vec)
  2. Check test plan → missing? → discuss with user → generate → write to docs/
  3. Execute test plan → results → State Engine update
  4. Gap check: PRD items × three-layer verification (static → test → dynamic)
  5. Repair phase:
     - Report gaps (Claude/GLM — PRD §6.6 model routing)
     - Fix gaps (DeepSeek Flash)
     - Each fix → mini test plan → verify → State Engine update
  6. Discover optimizations (see Discovery Dimensions below)
  7. Each optimization → mini test plan → execute → result → State Engine
  8. If time remains → loop back to step 6 (continue discovering)
  9. Time up → final state snapshot → session post-summary (PRD §5.4) → done
```

### Model Routing

| Task | Model | Why |
|------|-------|-----|
| Knowledge extraction from sources | DeepSeek v4 Pro | Structured schema, two-step prompting |
| Gap detection (per-item comparison) | DeepSeek v4 Pro | Decomposed to yes/no per PRD item |
| Report generation | Claude / GLM | Narrative quality matters |
| Code fixes | DeepSeek v4 Flash | Cheap, mechanical — PRD §6.6 |
| Test generation | DeepSeek v4 Flash | "Copy existing pattern, replace assertion" |
| Arbitration (conflicting decisions) | Claude / GLM | Needs best judgment |
| External reference search | WebSearch (no model) | Retrieval, not reasoning |
| Memory extraction / embedding (fastembed) | DeepSeek Flash | ingestion pipeline (§1.4) |
| Hash / SQL / grep operations | No model | Deterministic |

---

## 1. Knowledge Retrieval (extends PRD §3)

> **ℹ️ v2-aligned (Path 1b).** §1.1 shows the storage model (MEMORY.md content + SQLite exact + knowledge_vec semantic). §1.2's SQLite schema applies for exact queries only (**FTS5 removed**). §1.5's query flow uses vec0 KNN for semantic search. See "v2 Backend" above.

> **Tools used (v2):** `sqlite_vec` + `fastembed` — Python APIs. `fastembed.encode(text)` produces 384-dim embeddings. `vec0` virtual table provides KNN search (`ORDER BY embedding <-> query`). The QA orchestrator calls these directly in-process — no MCP proxying needed.

### 1.1 Architecture: Content + Exact + Semantic (v2)

Three surfaces sharing `analytics.db` (see v2 Backend). Zero new services.

```
MEMORY.md              SQLite knowledge_index        knowledge_vec (analytics.db)
─────────              ──────────────────────        ─────────────────────────────
存: 完整决策内容       存: project, topic, problem,  存: 384-dim embedding vectors
   reasoning, context,    type, source, timestamp,      (BAAI/bge-small-en-v1.5)
   evidence               source_hash, memory_ref,   用途: KNN 语义检索 (L2)
   (LLM 读这里)           superseded_by              索引: sqlite-vec vec0 in-process
用途: LLM 阅读 + 人类   用途: 精确查询 + 去重 + 冲突
                       索引: B-tree (project,topic,problem)

                    ┌────────────────────┐
                    │  vec0 KNN +        │
                    │  LLM filter        │
                    └─────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼                               ▼
         SQLite 精确过滤                vec0 KNN 语义检索
         WHERE topic='auth'            'token refresh' (384-dim)
         AND problem='token-*'
              │                               │
              └───────────────┬───────────────┘
                              ▼
                    合并 → memory_ref → 读 MEMORY.md 原文 → 给 LLM
```

**类比**: SQLite = 图书馆目录（精确定位），knowledge_vec = 语义索引（按意思找），MEMORY.md = 书架上的书（内容）。三者同在 `analytics.db` 一个文件。

### 1.2 SQLite Metadata Schema

```sql
-- 知识条目元数据表（只存导航信息，不存正文）
CREATE TABLE knowledge_index (
    id              TEXT PRIMARY KEY,  -- hash(project + topic + problem + source)
    project         TEXT NOT NULL,
    topic           TEXT NOT NULL,     -- normalized slug, e.g. "auth"
    problem         TEXT NOT NULL,     -- normalized slug, e.g. "token-expiry-on-reload"
    type            TEXT NOT NULL,     -- 'decision' | 'knowledge' | 'requirement' | 'bug-fix'
    source          TEXT NOT NULL,     -- file path, URL, or git ref
    source_type     TEXT NOT NULL,     -- see table below
    source_hash     TEXT NOT NULL,     -- SHA-256 of source content at index time
    timestamp       TEXT NOT NULL,     -- ISO 8601
    memory_ref      TEXT NOT NULL,     -- pointer: "project/mfangdai/MEMORY.md#L89" or "session:sess_789"
    superseded_by   TEXT,              -- ID of newer record that overrides this one
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_exact_match ON knowledge_index(project, topic, problem);
CREATE INDEX idx_timeline ON knowledge_index(project, topic, problem, timestamp);
CREATE INDEX idx_hash_check ON knowledge_index(source_type, source_hash);
```

**MEMORY.md 中的对应条目**（内容存这里，SQLite 只存指针）：

```markdown
§ 修复 token 过期问题，改用 sessionStorage 并在过期前 5 分钟自动续期
  → reasoning: localStorage 在 iOS Safari private mode 不可用
  → decision: sessionStorage + 5min pre-expiry refresh
  → evidence: git:abc123, 2026-07-20
```

### 1.3 Source Types

| source_type | Mutable? | What's indexed |
|-------------|----------|----------------|
| `session` | No | Session transcript / decision |
| `git-commit` | No | Commit message |
| `git-pr` | No | PR title + body |
| `issue` | No | GitHub issue |
| `prd` | **Yes** | docs/prd.md or equivalent |
| `claude-md` | **Yes** | CLAUDE.md initiative blocks |
| `spec` | **Yes** | Design spec documents |
| `state` | **Yes** | State Engine §4 state files |

**Mutable source handling:** At start of each run, SELECT all `source_type IN ('prd','claude-md','spec','state')` → compute current SHA-256 → compare with stored `source_hash` → different? → re-extract → update SQLite row + update MEMORY.md entry.

**Immutable sources** (session, git, issue): indexed once, source_hash never rechecked.

### 1.4 Ingestion Pipeline

```
Source → Collector (extract raw_text) → Standardizer (LLM)
                                            │
                              ┌─────────────┼─────────────┐
                              ▼                           ▼
                      INSERT INTO                   UPSERT into
                      knowledge_index               MEMORY.md
                      (metadata only)               (full content + context)
```

**Two-step extraction for weak models:**

```
Step 1: Classify topic
  "This text discusses which functional domain?
   Check existing topics: {SELECT DISTINCT topic FROM knowledge_index WHERE project=?}
   Reuse an existing one if it matches. Output one word only."

Step 2: Structured extraction (given topic from step 1)
  "Extract per schema:
   { problem: stable-slug, type: decision|knowledge|requirement|bug-fix,
     summary: 2-3 sentences, key_points: string[] }"
```

### 1.5 Query Flow

```
PRD item → extract topic + problem keywords
    │
    ▼
  ┌─ SQLite precise lookup ──────────────────────┐
  │ SELECT * FROM knowledge_index                 │
  │ WHERE project=? AND topic=? AND problem LIKE ?│
  │ ORDER BY timestamp DESC                       │
  └───────────────────────────────────────────────┘
    │
    ├── exact match found? → read MEMORY.md via memory_ref → done
    │
    ├── no exact match? → broaden to topic level
    │   SELECT * WHERE project=? AND topic=?
    │   → vec0 KNN (sqlite-vec)
    │
    └── LLM filter (minimal tokens):
        "Does this result discuss the same problem as the PRD item?"
        → {relevant: bool, reason: one sentence}
```

### 1.6 Conflict Resolution

```
Same (project, topic, problem), multiple rows:

  v1 (2026-01): "use Redux"
  v2 (2026-03): "use Context"
  v3 (2026-06): "use Zustand"        ← auto-select newest

  BUT: LLM checks if v3's key_points contain different preconditions
       than v2 → if yes, flag "needs resolution"
       → escalate to Claude/GLM for arbitration

  Old rows NOT deleted. Set superseded_by → v3.id.
```

---

## 2. Gap Detection (new)

### 2.0 Time Budget

```
Ask user: "这次任务最多跑多久？" (default: 12h)
Store in state.max_duration_seconds
Start timer.
Each loop iteration: check elapsed < max → continue; else → graceful stop.
```

Extends PRD §2.2.2 termination condition #3 (time expired, default 12h).

### 2.1 Test Plan Gate

Before any gap detection or fixing, a test plan must exist. If missing, STOP and discuss:

```
1. Parse PRD → list modules
2. For each module, propose test scenarios:
   "auth 模块至少需要: 正常登录, 错误密码, token过期, 并发登录..."
3. Ask user:
   "我识别出这些测试场景。这是完整的吗？哪些是 P0？验收标准是什么？"
4. User confirms → generate test-plan.md → write to docs/ → begin execution
5. Store test plan path in state file (State Engine §4)
```

Agent does 80% of the work (scenario identification), user provides 20% (prioritization + acceptance criteria).

### 2.2 Three-Layer Verification

For each PRD item:

```
Layer 1 — Static Evidence (fast, cheap)
  grep/code search for implementation
  → verdict: found / not_found
  → evidence: file:line or "no matching code found"

Layer 2 — Test Evidence (slower, more reliable)
  Run existing tests for this feature
  → verdict: tested / not_tested / test_failed
  → evidence: test file:line + pass/fail result

Layer 3 — Dynamic Verification (slowest, most reliable)
  No test exists? → generate minimal test following existing patterns
  → run it
  → verdict: verified / not_working
  → evidence: generated test code + run result
```

Output per PRD item:

```json
{
  "prd_item": "token auto-refresh on expiry",
  "static": {"verdict": "found", "evidence": "src/auth/tokenRefresh.ts:42"},
  "test": {"verdict": "tested", "evidence": "tests/auth/token.test.ts:89, pass"},
  "dynamic": null,
  "gap": false,
  "confidence": "high",
  "reasoning": "Implementation exists + test covers it + test passes"
}
```

**Weak-model compensation:** Each layer asks the model a single yes/no question with evidence already provided by grep/test runner. The model never "remembers" or "understands" the full codebase — it judges one piece of evidence at a time.

### 2.3 Repair

```
Gaps collected → Claude/GLM narrative report → user reviews
  → each confirmed gap → DeepSeek Flash fix → verification → State Engine update
```

---

## 3. Continuous Discovery (new)

After gaps are fixed, the loop continues discovering optimization opportunities. This is the "never truly done" engine — the agent doesn't stop at "tests pass."

### 3.1 Discovery Dimensions

| Dimension | Check | Method |
|-----------|-------|--------|
| External Reference | Official docs, best practices, sample projects vs current code | WebSearch + diff analysis |
| Code Pattern Consistency | Same pattern implemented multiple ways? | grep + pattern matching across codebase |
| Test Coverage Gaps | Which branches/edge cases are untested? | Coverage tool + PRD boundary analysis |
| Dependency Debt | Outdated/vulnerable dependencies? | `npm outdated`, `npm audit` (or lang equivalent) |
| Performance Signals | Bundle size, slow queries, unoptimized assets? | Lighthouse, bundler analyzer, query profiler |
| Security Signals | Hardcoded secrets, missing auth checks? | Secret scanning, pattern grep |
| Error Handling | Missing error boundaries, uncaught promise chains? | Static analysis |

### 3.2 Optimization Workflow

```
Discovery → classify by dimension
  → for each finding: mini test plan
  → fix (DeepSeek Flash)
  → run mini test plan
  → result → State Engine update
  → continue to next finding (while time remains)
```

### 3.3 Mini Test Plan Format

```markdown
## Optimization: migrate API routes to Server Actions
**ID:** O-2026-07-24-001
**Priority:** medium
**Dimension:** external-reference
**Reference:** Next.js 14 docs recommend Server Actions over API routes

### Test Plan
- [ ] Before: existing API route tests still pass
- [ ] After: migrated code passes same tests
- [ ] Performance: response time not regressed (> baseline)
- [ ] Manual: form submission works end-to-end

### Result
- 2026-07-24: migrated 3 routes, all tests pass, perf unchanged
```

---

## 4. State Integration (uses PRD §4)

> **ℹ️ v2 (Path 1b):** gap tracking and progress snapshots use **state files** (see "v2 Backend" above). The markdown state file below is the primary artifact for run-to-run continuity and fallback.

> **Safety gate (PRD §5.6):** All `qa-fix` outputs (code changes, config edits, generated files) must pass sandbox testing before being committed or applied. The sandbox runs the generated fix in an isolated environment and verifies: tests pass, no new security issues introduced, and no regression in existing functionality. Failed sandbox results are discarded and the orchestrator re-enters the repair phase with the failure context.

QA pipeline state writes through the PRD's State Engine. State file location: `docs/self-evolving-agent/state/YYYY-MM-DD-qa-run-{task}.md`

```markdown
# QA Run State: {task-name}

**Started:** 2026-07-24 10:00
**Status:** in_progress
**Last Run:** 2026-07-24 16:30
**Max Duration:** 12h (elapsed: 6h30m, remaining: 5h30m)

## Current Phase
discovery (step 6: finding optimizations)

## Test Plan
- [x] auth: normal login → pass
- [x] auth: wrong password → pass
- [ ] auth: token refresh → gap (fix in progress)

## Gaps Found
| ID | PRD Item | Verdict | Evidence | Status |
|----|----------|---------|----------|--------|
| G-1 | auto-refresh token | not implemented | no code found in src/auth/ | fixing |
| G-2 | rate limiting | missing test | code exists, no test | todo |

## Optimizations
| ID | What | Dimension | Priority | Status | Result |
|----|------|-----------|----------|--------|--------|
| O-1 | migrate to Server Actions | external-ref | medium | todo | — |
| O-2 | compress bundle PNGs | perf | low | done | -40% bundle |

## Decisions Made This Run
- 2026-07-24: token refresh → sessionStorage + 5min pre-expiry refresh
  (source: MEMORY.md entry decision/auth-token-storage-2026-07-20)
```

State file is also ingested back into MEMORY.md as a `state` entry for future vec0 semantic search.

---

## 5. Skill Architecture

Skills to create. Each follows the PRD's self-evolution patterns (§5):

| Skill | Purpose | Model | PRD Integration |
|-------|---------|-------|-----------------|
| `qa-knowledge-extract` | Extract structured (project, topic, problem) from all source types → MEMORY.md + SQLite + knowledge_vec | DeepSeek Pro | Ingestion (§1.4); writes all three surfaces |
| `qa-knowledge-search` | SQLite exact → vec0 KNN → LLM filter | SQLite (no model) + DeepSeek Pro | Query flow (§1.5) |
| `qa-gap-check` | PRD vs reality comparison, three-layer verification | DeepSeek Pro (per-item) + Claude/GLM (report) | New |
| `qa-test-plan` | Generate/validate test plans, discuss with user | Claude/GLM (discussion) + DeepSeek Pro (generation) | Uses §4 State Engine for persistence |
| `qa-continuous-discovery` | Scan for optimizations across all dimensions | DeepSeek Pro (per-dimension) + Claude/GLM (external ref) | New |
| `qa-fix` | Execute fixes for gaps and optimizations | DeepSeek Flash | PRD §6.6 cost model |
| `qa-orchestrator` | Main loop: coordinate phases, manage time, persist state | DeepSeek Pro | Implements §2.1 loop state machine |

### Triggers

| Trigger | Mechanism |
|---------|-----------|
| Slash command | `/qa-run [task-name] [max-hours]` |
| Git push hook | Auto-trigger incremental extraction + gap check |
| PR merge hook | Auto-trigger: extraction + verify related PRD items |

---

## 6. Key Design Decisions

1. **sqlite-vec on analytics.db (v2).** MEMORY.md stores full content (LLM reads this); SQLite `knowledge_index` stores metadata for exact `WHERE project/topic/problem` queries (**FTS5 removed**); `knowledge_vec` provides KNN semantic search via sqlite-vec + fastembed (384-dim). All three surfaces share one `analytics.db` file — no new service, no external binary. See v2 Backend.

2. **Mutable source hash checking.** PRD/CLAUDE.md changes auto-detected via SHA-256 at run start. Stale MEMORY.md entries re-extracted.

3. **Two-step extraction for weak models.** Classify topic first, then extract details. Reduces error rate vs single-pass.

4. **Model tiering.** Strong models (Claude/GLM) for reports, arbitration, user discussion. Cheap models (DeepSeek Flash) for mechanical code fixes. DeepSeek Pro for structured extraction.

5. **Test plans are mandatory gates.** No execution without one. Agent proposes, user confirms.

6. **Continuous discovery.** After gaps are fixed, the loop continues finding optimizations until time expires. Not "done when tests pass" — done when time runs out.

7. **State continuity.** Every run reads prior state, knows what was done, and continues. State feeds back into MEMORY.md for future retrieval.

---

## 7. Out of Scope (Phase 2+)

- Adversarial multi-agent review
- Custom vector search implementation — sqlite-vec vec0 already provides in-process KNN on analytics.db; no external vector index or service needed.
- Automatic PR creation and merge (Phase 1 stops at commit)
- Cross-project knowledge transfer (single-project scope)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-24 | Initial creation |
| 2026-07-24 | Reconciled with self-evolving-agent PRD — aligned state with State Engine §4; referenced PRD loop, memory, and evolution infrastructure throughout |
| 2026-07-24 | Restored SQLite as two-tier architecture: SQLite = metadata catalog (project/topic/problem/type/hash/memory_ref), MEMORY.md = full content. FTS5 + SQLite B-tree serve complementary query paths — neither replaces the other. |
| 2026-07-24 | v3 alignment: updated PRD ref to v3, corrected termination condition #3 (budget exhaustion → time expired), added SDK mode preamble to core loop, documented v3 implicit evolution integration (SDK mode + SessionStop hook), referenced /memory-search and /memory-add skills in §1, added PRD §5.6 safety architecture gate to §4. |
| 2026-07-24 | Path 1b chosen: added "v2 Backend: Guild OSS + Jam.dev MCP" section (grounded in Appendix A v2 guidance + Guild README); marked §1 storage and §4 state as v1/partially-superseded with reconciliation notes; updated header to the Guild backend. QA skill is now self-contained — resolves the dependency conflict with the unbuilt engine. |
| 2026-07-24 | Aligned §1.1 (architecture diagram → three-surface) and §6 #1 (→ three-surface storage) to v2; swept remaining FTS5 references across Overview, Core Loop, Model Routing, §1 tools/query-flow, §4, §5 skill table, §7 — all semantic search now via Guild Lore. No residual two-tier/FTS5 wording (historical changelog rows excepted). |
| 2026-07-24 | Replaced Guild OSS with sqlite-vec + fastembed (Path 1b): rewrote "v2 Backend" section; updated header, overview, §1.1 diagram (knowledge_vec column), §1 notes, §1.5, §4, §5 skill table, §6 #1, §7. All surfaces share analytics.db — zero new services. Spike validated 6/6 semantic queries on real knowledge entries. |
