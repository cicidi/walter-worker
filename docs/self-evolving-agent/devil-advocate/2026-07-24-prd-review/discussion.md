# Devil's Advocate Review — PRD

**Document:** `docs/self-evolving-agent/prd/self-evolving-agent-prd.md`
**Date:** 2026-07-24
**Topic:** Self-Evolving Agent PRD
**Rounds:** max 5

---

## Round 1 — Full Document Review

### Con Agent: 21 Claims

| # | Claim | Impact |
|---|-------|--------|
| 1 | Hermes architecture has unresolved IP contamination risk (EvoMap plagiarism) | HIGH |
| 2 | PostToolUse hooks have 9+ documented failure modes | HIGH |
| 3 | Per-turn sync architecturally broken (stdout dropped, peak pricing) | HIGH |
| 4 | "Self-improvement" conflates file management with model improvement | MEDIUM |
| 5 | Cross-IDE hook reliability not assessed (OpenCode) | MEDIUM |
| 6 | Zero safety/alignment guardrails for autonomous evolution | HIGH |
| 7 | "Goal achieved" detection unspecified — loop unimplementable | HIGH |
| 8 | No cost estimation or budget mechanism | MEDIUM |
| 9 | No error handling or degraded-mode specification | MEDIUM |
| 10 | No quality metrics for evolution effectiveness | MEDIUM |
| 11 | Per-turn sync broken by hook limitations (subagent findings lost) | HIGH |
| 12 | Guild Agent solves cross-IDE memory more simply | MEDIUM |
| 13 | FTS5 degrades between weekly curator runs | MEDIUM |
| 14 | `coworker run --loop` has no implementable specification | HIGH |
| 15 | Auto-approved skills risk quality degradation (65.5% unsafe rate) | HIGH |
| 16 | Curator archiving risks irreversible data loss | MEDIUM |
| 17 | DeepSeek single-provider dependency | MEDIUM |
| 18 | Snapshot injection guarantees stale context | MEDIUM |
| 19 | Guild Agent simpler, ignored alternative — violates "优先复用" | HIGH |
| 20 | Pioneer provides proven model improvement that PRD defers | MEDIUM |
| 21 | 5+ tool call threshold unvalidated for ai-coworker | LOW |

### Pro Agent: 5 REFUTED, 16 ACCEPTED

**REFUTED:** Claims 1 (IP risk — MIT license protects), 3 (sync arch — PRD writes to disk for next session, not mid-session injection), 4 (self-improvement — knowledge accumulation IS valid improvement, PRD never claims model weight mod), 12 (Guild — different problem space), 20 (Pioneer — complementary, correctly deferred for MVP)

**ACCEPTED:** Claims 2, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 21

**Positive arguments added:**
1. Three-layer knowledge taxonomy (SOP/Experience/State) is genuine innovation
2. Approval model is more nuanced than "auto-approve" (graduated per content type)
3. Cross-IDE source-of-truth skill architecture solves real problem
4. "Earn your way up" promotion prevents skill-factory spam
5. Snapshot model correctly prioritizes stability over freshness

### Judge Rulings

| Claim | Ruling | Key Reason |
|-------|--------|------------|
| 1 | **PRO** | MIT license is operative. PRD reimplements patterns, not code. Modules explicitly replaceable. |
| 2 | **CON** | Pro concedes — 9 failure modes confirmed. |
| 3 | **PRO** | Con attacked straw man. PRD never claims mid-session context injection. Architecture is eventual-consistency (write-now, read-later). |
| 4 | **PRO** | PRD transparent about scope. Knowledge accumulation is genuine self-improvement. |
| 5 | **CON** | Pro concedes. |
| 6 | **CON** | Pro concedes. Most critical finding — self-modifying agent with zero safety = non-starter. |
| 7 | **CON** | Pro concedes. Core command cannot be built from PRD. |
| 8 | **CON** | Pro concedes. |
| 9 | **CON** | Pro concedes. |
| 10 | **CON** | Pro concedes. |
| 11 | **CON** | Pro concedes. Subagent findings invisible to memory system. |
| 12 | **DEFERRED** | Both sides have comparable evidence. Needs Round 2 with specific Guild memory capability analysis. |
| 13 | **CON** | Pro concedes. |
| 14 | **CON** | Pro concedes. Product's defining command is unspecified. |
| 15 | **CON** | Pro concedes. 65.5% unsafe rate makes auto_approve: true irresponsible. |
| 16 | **CON** | Pro concedes. |
| 17 | **CON** | Pro concedes. |
| 18 | **CON** | Pro concedes. |
| 19 | **CON** | Pro concedes. PRD violates own "优先复用" principle. |
| 20 | **PRO** | Pioneer requires training infra. PRD approach is model-agnostic and complementary. Good MVP scoping. |
| 21 | **CON** | Pro concedes. |

**Summary:** 16 CON wins, 4 PRO wins, 1 DEFERRED (Claim 12).

---

## Round 2 — Claim 12: Guild Agent Cross-IDE Memory

### Focus
Does Guild Agent provide a simpler cross-IDE memory solution that the PRD should evaluate or adopt per the "优先复用" principle?

### Con Position (Round 2)
Guild is strictly superior on all 7 PRD memory requirements:
- R1: Works with ANY MCP client vs PRD's 2-IDEs
- R2: Direct lore_inscribe call, no external LLM, no hook chain
- R3: Hybrid BM25+vector search > keyword-only FTS5
- R4: Structured SQLite entries > flat MEMORY.md
- R5: guild_session_start bakes in snapshot vs separate mechanism
- R6: Per-kind TTL (30d/180d/permanent) > blanket 7-day curator
- R7: Single binary with embedded vector search
- PRD builds 5 components, Guild replaces with 1 — violation of "优先复用"

### Pro Position (Round 2)
- R1: PARTIAL ACCEPT — Guild broader reach, but hook-based capture is automatic vs agent-initiated
- R2: REFUTE — R2 explicitly requires "without the agent manually invoking a save command." Guild's lore_inscribe IS a manual save command.
- R3: ACCEPT with caveats — hybrid search wins, but vector disabled on Windows and PRD uses LLM synthesis at query time
- R4: REFUTE — MEMORY.md is human-readable, git-friendly, directly injectable as LLM context. "No metadata" claim is false (FTS5 stores session_id, project, timestamp)
- R5: ACCEPT with tradeoff — both approaches work
- R6: ACCEPT with caveats — Guild's TTL is elegant, but PRD curator is broader (skills + memory + merge + reporting)
- R7: REFUTE — Guild runs a background MCP server + embedded ONNX runtime. This VIOLATES R7's "no background server process" criterion.
- CORE: Guild lacks auto-skill-creation, auto-skill-patching, CLAUDE.md modification, three-layer taxonomy, and unconditional capture — the PRD's DEFINING features

### Judge Ruling (Round 2)

**Verdict: PRO wins on Claim 12.**

Guild fails two PRD requirements explicitly:
- **R2:** `lore_inscribe` IS a manual save command — the agent must decide to call it, choose kind/topic, formulate content. R2 explicitly requires persistence "without the agent manually invoking a save command."
- **R7:** Guild's MCP server IS a background server process, violating R7's explicit "no background server process" criterion. The embedded ONNX runtime also qualifies as a vector database.

Guild provides NONE of the PRD's defining self-evolution features: auto-skill-creation, auto-skill-patching, CLAUDE.md modification, three-layer knowledge taxonomy, state engine.

The "优先复用" principle explicitly allows custom builds "if existing solutions don't meet requirements" — and Guild doesn't meet R2 and R7. However, the PRD should evaluate Guild and document why it was not adopted wholesale. This addresses the valid kernel in Claim 19 without conceding Claim 12.

### Final Resolutions

**16 CON wins, 5 PRO wins, 0 DEFERRED.** No unresolved items remain. Debate complete.
