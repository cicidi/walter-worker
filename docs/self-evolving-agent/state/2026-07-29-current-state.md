# Self-Evolving Agent — Current State

**Date:** 2026-07-29
**Initiative:** self-evolving-agent
**Status:** **Steady state** -- Memory platform Waves 1-4 complete. Auto-worker operational. Waves 5-7 (Dashboard, Auto-Worker full, Hooks) deferred.

---

## 1. Current Status

### Delivered
- **Memory platform** (Waves 1-4): 9 modules, 143 tests passing
- **Auto-worker** (Round 1-19 + loop mode): Bug-fix loop operational, 101 issues found, 47 fixed
- **Dashboard** (basic): 21 API endpoints / 200, frontend JS 566 lines / CSS 443 lines, up on port 8099
- **Design docs**: PRD v4, spec, design (Guild-aligned), impl-plan, dependency-and-sequencing decision

### In Progress / Deferred
- Waves 5-7: Dashboard full frontend, Auto-Worker state/rules/engine, Hook configuration + E2E -- deferred
- Memory training pipeline backfill: summaries at 9.3% coverage (needs `coworker memory train`)
- Validate.py test coverage: untested module (T-4 gap)

### Blocked / Risk
- Guild OSS + Jam.dev MCP not installed (Path 1b foundation never done -- design chose Guild but never spiked it)
- Execution-model ambiguity: QA orchestrator as Python pipeline vs. Claude Code agent skill never resolved
- Spec still references FTS5 in 3 spots (never aligned to Guild)

---

## 2. Architecture Delivered (Waves 1-4)

```
src/coworker/memory/
├── __init__.py       # Module init, public exports
├── llm.py            # DeepSeek-v4-Flash + Gemini fallback, reasoning token handling
├── mem0_client.py    # mem0 v2 CRUD wrapper, fastembed (BGE-small, 384-dim)
├── audit.py          # Audit trail (write records, gap detection)
├── capture.py        # Per-turn extraction + session-end reconciliation
├── engine.py         # Evolution engine (extract_and_store, reconcile)
├── inject.py         # CLAUDE.local.md snapshot injection
├── pending.py        # Staged skill review queue (approve/reject/expire, auto-promote)
├── curator.py        # Periodic maintenance (stale/archive/export, recency-weighted scoring)
├── train.py          # Batch training pipeline
├── errors.py         # Error classes
├── metrics.py        # Metrics tracking
├── safety.py         # Safety guard
├── validate.py       # Validation module (untested)
└── wrong_history.py  # Auto-record wrong-history entries after fixes
```

```
src/coworker/autoworker/
├── __init__.py
├── engine.py         # Auto-worker fix loop engine
├── rules.py          # Auto-worker rules (24 tests)
└── state.py          # Auto-worker state tracking (24 tests)
```

### Wave Summary

| Wave | Scope | Tests | Status |
|------|-------|-------|--------|
| Wave 1 | Foundation: LLM client + mem0 substrate | 60 | Complete |
| Wave 2 | Capture layer: audit + per-turn extraction | 17 | Complete |
| Wave 3 | Evolution engine: engine + inject + pending | 29 | Complete |
| Wave 4 | Curator + Training pipeline | 8 | Complete |
| Wave 5 | Dashboard API + frontend | N/A | Deferred (partial) |
| Wave 6 | Auto-worker state/rules/engine | N/A | Deferred (partial) |
| Wave 7 | Hook config + E2E deploy | N/A | Deferred |

---

## 3. Key Metrics

### Test Coverage
- **143 tests** (119 core memory + 24 autoworker)
- Tier 1 (deterministic fixed-scenario): 143/143 passed
- Tier 2 (simulated LLM): Deferred -- requires session simulation infra
- Tier 3 (quality judge Agent-D): Not yet applied

### Test File Breakdown

| Test File | Tests | Type |
|-----------|-------|------|
| test_llm.py | 17 | 12 unit + 5 real (DeepSeek v4 Flash) |
| test_mem0_client.py | 43 | All real (mem0 + fastembed + Qdrant) |
| test_audit.py | 10 | All unit |
| test_inject.py | 11 | All unit (mock mem0) |
| test_pending.py | 11 | All unit |
| test_curator.py | 8 | All unit (mock mem0) |
| test_engine.py | 7 | 5 unit + 2 real |
| test_capture.py | 7 | 4 unit + 3 real |
| test_errors.py | +14 | Unit |
| test_metrics.py | + included | Unit |
| test_train.py | + included | Unit |
| test_wrong_history.py | +5 | Unit |
| test_autoworker_state.py | 12 | Unit |
| test_autoworker_rules.py | 12 | Unit |
| **Total** | **143** | |

### Dashboard Health
- Sessions: 569, Messages: 6,897, Tools: 12,110, Skills: 28
- Projects: 17, Models: 22, Project coverage: 28.3%
- All 21 API endpoints return 200
- Frontend: JS 566 lines (55 functions), CSS 443 lines, init+expand OK

### Data Quality
- Project coverage: 28.3% (<50% threshold)
- Summaries: 53 (9.3% coverage -- LOW, needs `coworker memory train`)
- Knowledge entries: 7
- Initiatives: 6
- Cache hit rate: DeepSeek 97.8%, GPT 75.1%

---

## 4. Active Issues (remaining)

### HIGH
- **S-2**: Validate harness (memory/engine input validation)
- **S-3**: Skill patching (auto-apply skill updates)
- **W-6**: Benchmark (performance benchmarks for memory ops)

### MEDIUM
- **S-1**: Training dashboard (UI for training pipeline)
- **W-3**: Spend alerts (cost monitoring)

### LOW
- **W-4**: OTel config (OpenTelemetry integration)
- **P-2**: Dashboard completeness (full frontend for Waves 5-7)

### Design-Level (not auto-fixable)
- Guild feasibility spike never done (Path 1b foundation risk)
- Spec Guild alignment (3 FTS5 references need migration)
- Execution-model question (Python pipeline vs. Claude Code agent skill)
- Self-evolution engine (the actual "越来越好用" body) at 0% -- only memory platform built
- PRD hook architecture: 5 technical errors to fix before engine use

---

## 5. Historical Timeline

| Date | Milestone |
|------|-----------|
| 2026-07-24 | **Design review**: Advocate review of PRD/spec/design. 6 broken cross-refs fixed. Chose Path 1b (Guild OSS + Jam.dev MCP). 9 feasibility risks cataloged. Guild uninstalled. Execution model ambiguous. |
| 2026-07-25 AM | **Wave 1 (Foundation)**: llm.py (120 lines) + mem0_client.py (190 lines). DeepSeek v4 Flash + Gemini 2.5 Flash fallback. fastembed (BGE-small, 384-dim). 60/60 tests passing. 6 issues resolved (model names, reasoning tokens, mem0 v2 API, fastembed switch, Qdrant locks, empty LLM extraction). |
| 2026-07-25 PM | **Waves 2-4 (Capture + Engine + Curator)**: audit.py, capture.py, engine.py, inject.py, pending.py, curator.py, train.py. 114/114 tests passing. Commit: `fb7018b feat(memory): mem0 substrate + DeepSeek LLM client`. |
| 2026-07-26 | **Auto-worker Rounds 1-19**: Bug-fix loop operational. Dashboard CSS/JS restored from overwrite (Write tool regression). Tests expanded 100->143. Wrong-history entries auto-recorded. Commit: `d3d59a2`. System reaches steady state. |
| 2026-07-27 | **Auto-worker loop mode**: Rounds 1-2 loop-mode. 4 API 500 errors fixed (FIX-2 through FIX-5). Data validation skill applied. Pending.py skill promotion wired (C-1). Cache hit rate added to Dashboard (W-2). Tests 770/770 in full suite. All 21 endpoints /200. |


---

## 6. Key Design Decisions

1. **fastembed over HuggingFace**: Avoids PyTorch DTensor compatibility issues. ONNX runtime, no GPU needed.
2. **Embedded Qdrant**: `embedding_model_dims=384` explicitly configured. Session-scoped MEM0_DIR for test isolation.
3. **mem0 v2 API**: `{"results": [...]}` dict format, `openai_base_url` (not `base_url`), mandatory `user_id` in search filters.
4. **DeepSeek v4 reasoning tokens**: Fallback to `reasoning_content` when `content` is empty.
5. **Anthropic removed from fallback**: No OpenAI-compatible endpoint. Chain: DeepSeek v4 Flash -> Gemini 2.5 Flash.
6. **Pending queue**: File-based JSON (`~/.coworker/pending/skills/`). 30-day auto-expire. Approve promotes to `~/.coworker/skills/`.
7. **Frozen snapshot**: mem0 -> CLAUDE.local.md injection between `<!-- MEMORY:project START/END -->` markers. Replaced at session start.
8. **Wrong-history auto-recording**: Engine instructs agents to record after each fix via `wrong_history.py`.

---

## 7. Wrong-History Rules Active (3 critical)

From 2026-07-25/26 incidents:
1. **NEVER use Write tool on existing files** -- always use Edit with old_string/new_string
2. **After Edit at end of file**, verify original last-line initialization preserved with `tail -3`
3. **Never claim dashboard data is OK just because API returns non-empty** -- trace to source of truth

---

## 8. Commits

| Commit | Message |
|--------|---------|
| `fb7018b` | feat(memory): mem0 substrate + DeepSeek LLM client -- Wave 1 foundation |
| `d3d59a2` | Auto-worker fixes: API endpoint repairs, data validation, pending promotion |
| `c95db93` | feat: add --min-score filter for vector/mem0 results (default 0.3) |
| `2c99c43` | feat: add full-text message search to memory query |
| `b3d556c` | fix: add source tag to graph results in both mode |
| `30157e1` | fix: increase MAX_SEEDS 3->5, MAX_DEPTH 3->6, remove edge filter |
| `78d2b32` | feat: token budget instead of hard top_k for query output |

---

## Dependencies

```
openai>=2.0
mem0ai>=2.0
fastembed
qdrant-client
```
