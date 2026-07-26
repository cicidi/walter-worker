# Feasibility Review — PRD v5 (Final)

**Document:** `docs/self-evolving-agent/prd/self-evolving-agent-prd.md` (v5)
**Date:** 2026-07-25
**Method:** 3-agent debate (Con / Pro / Judge), 1 round
**Focus:** Feasibility, Spec-Capability, Plan Reasonableness

---

## Verdict: QUALIFIED YES — Can be built

The hooks infrastructure (15K+ tool calls, 37 sessions), analytics DB, knowledge dedup, semantic merge, backup, and templates exist in production. The architecture is sound. The greenfield scope (~2,290 adjusted lines) is bounded and decomposable. The three risks below must be managed, but none are architectural blockers.

---

## Dimension 1: Feasibility

| # | Claim | Ruling | Key Evidence |
|---|-------|--------|-------------|
| 1 | Hooks reliable enough for evolution loop | **PRO_WINS** | 37 sessions, 15K tool calls captured. PostToolUse+Stop live in settings.json. async:true added in v5. |
| 2 | Analytics DB + knowledge dedup reusable | **PRO_WINS** | 8 tables, WAL mode. Three-tier dedup (hash + edit + LLM). `get_session_data()` retrieves full sessions. |
| 3 | CLAUDE.local.md snapshot injection exists | **PRO_WINS** | `inject_initiative_into_local_md()` pattern. Extend for MEMORY blocks. |
| 4 | Post-session summarization feasible | **QUALIFIED PRO** | session-memory skill (379 lines) already does full pipeline. Adaptation needed: Ollama→local default, Obsidian→MEMORY.md. |
| 5 | Subagent capture gap manageable | **CON_WINS** | SubagentStop hook NOT configured. `/memory-add` workaround violates R2. Rich subagent work invisible to primary capture. |
| 6 | Semantic merge prevents corruption | **PRO_WINS** | 329 lines, PROTECTED block enforcement, KEEP/OVERWRITE/MERGE classification. |
| 7 | Safety architecture implementable | **QUALIFIED PRO** | Circuit breaker + sandbox + rollback specified. Gap: syntactic defenses vs semantic threats. |

### Key Risk: Subagent blind spot
PostToolUse fires for MCP and Skill calls but NOT for Agent (subagent) completions. Modern Claude Code leans heavily on subagents for parallel research, code search, multi-step analysis. This content — often the richest per session — is structurally invisible. Mitigation: configure SubagentStop hook + end-of-session transcript summarization.

---

## Dimension 2: Spec-Capability

| # | Claim | Ruling | Key Evidence |
|---|-------|--------|-------------|
| 1 | Three-tier memory sufficiently specified | **PRO_WINS** | Data flow diagrams, per-tier scope/lifetime/storage tables, storage paths, snapshot format, sync triggers |
| 2 | Hook configuration correctly specified | **PRO_WINS** | Exact JSON for Claude Code. Stop matches real hook. async:true correct syntax. |
| 3 | SDK state machine sufficiently specified | **PRO_WINS** | 5-state diagram, 4 termination conditions, 6 error recovery scenarios |
| 4 | Error handling sufficiently specified | **PRO_WINS** | 8 failure modes with degraded behavior. Provider fallback chain. Retry with backoff. |
| 5 | Cost model specified with concrete numbers | **PRO_WINS** | Per-operation tokens + cost. Peak/off-peak pricing. ~$0.002/session. |
| 6 | Tier 3 lesson schema underspecified | **CON_WINS** | No entry fields. "Structured" claimed but undefined. Analytics DB `knowledge` table schema could be adopted. |
| 7 | Pending queue management underspecified | **CON_WINS** | No batch ops, auto-expiry, quality scoring. 35-210 items/week unmanageable. |
| 8 | MEMORY.md entry format missing | **CON_WINS** | §-delimited claimed but no schema. Engineer must invent format for `memory_store.py`. |

### Top 3 Missing Specs
1. **Tier 3 lesson schema**: Adopt analytics DB knowledge table fields: `{project, topic, problem, type, summary, evidence, source_session}`
2. **Pending queue management**: Add batch approve/reject, 30-day auto-expiry, quality score per item
3. **MEMORY.md entry format**: Define § entry fields: summary, reasoning, decision, evidence, timestamp

---

## Dimension 3: Plan Reasonableness

| # | Claim | Ruling | Key Evidence |
|---|-------|--------|-------------|
| 1 | 11 components verified production-ready | **PRO_WINS** | All 11 verified in code. 3 fully ready, 6 partial, 2 need adaptation. |
| 2 | ~1,840 lines credible as direction | **CON_WINS (adjusted)** | Current avg module ~160 lines. But: loop driver ~450 (not 200), CLI scaffolding missing (~200), summarization ~300 (not 200). **Adjusted: ~2,290 lines.** |
| 3 | P0→P1→P2 ordering correct | **PRO_WINS** | Core loop before search before automation is correct dependency chain. |
| 4 | `coworker run --loop` ~200 lines | **CON_WINS** | Real scope: state machine (100), subprocess (100), 4 termination detectors (80), error recovery (60), graceful shutdown (50), CLI args (30). **~450 lines realistic.** |
| 5 | CLI scaffolding missing from estimate | **CON_WINS** | 16+ `coworker memory *` commands need Click registration. **~200 lines missing.** |
| 6 | Reuse of 5 existing skills realistic | **QUALIFIED PRO** | All 5 exist. session-memory needs most adaptation (Ollama→local, Obsidian→MEMORY.md, OpenCode→Claude Code). |
| 7 | Post-session summarization in P0 is ambitious | **CON_WINS (partial)** | Most complex component. Transcript access from bash hook (~10s timeout) underspecified. Background processing mechanism TBD. |

### Top 3 Plan Corrections
1. **Recalibrate total**: ~2,290 lines (+450 from claimed 1,840)
2. **Add CLI scaffolding row**: ~200 lines for 16+ subcommands
3. **Split loop driver estimate**: ~450 lines (not 200)

---

## Summary

| Dimension | Result |
|-----------|--------|
| Feasibility | **QUALIFIED YES** — 15K tool calls captured today. Infrastructure is real. |
| Spec-Capability | **ADEQUATE** — 3 key specs missing (Tier 3 schema, queue mgmt, MEMORY.md format) but structural guidance sufficient |
| Plan Reasonableness | **DIRECTIONALLY CORRECT** — Estimates ~25% low (~2,290 vs ~1,840). P0/P1/P2 ordering correct. |

### Top 3 Risks (all dimensions)
1. **Subagent data loss** — richest content structurally invisible to PostToolUse
2. **LLM extraction quality** — entire pipeline depends on cheap model extracting accurate lessons
3. **Safety asymmetry** — syntactic defenses vs semantic threats (phishing, refusal collapse)
