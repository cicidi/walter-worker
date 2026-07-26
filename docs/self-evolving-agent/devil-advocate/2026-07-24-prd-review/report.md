# Devil's Advocate Report — Self-Evolving Agent PRD

**Document reviewed:** `docs/self-evolving-agent/prd/self-evolving-agent-prd.md`
**Date:** 2026-07-24
**Reviewers:** Con Agent, Pro Agent, Judge Agent
**Result:** 16 CON wins, 5 PRO wins, 0 unresolved

---

## Round Summary

| Round | Scope | CON wins | PRO wins | Deferred |
|-------|-------|----------|----------|----------|
| 1 | Full document review (21 claims) | 16 | 4 | 1 |
| 2 | Claim 12 — Guild Agent evaluation | 0 | 1 | 0 |
| **Total** | | **16** | **5** | **0** |

---

## Top 10 Risks (CON-won HIGH impact claims)

### 1. 🛑 Zero Safety/Alignment Guardrails (Claim 6)
**Severity: CRITICAL**

The PRD's default `auto_approve: true` for autonomous skill creation has no safety filters, no sandbox testing, no rollback mechanism, and no circuit breaker. Shanghai AI Lab research documents safety erosion across all four evolution pathways (model, memory, tool, workflow). AgentWorm demonstrates 63% attack success rate against self-evolving agent ecosystems. **A self-modifying autonomous agent with zero safety infrastructure is a non-starter.** This must be resolved before any code is written.

**Recommendation:** Default to review mode (`auto_approve: false`), add sandbox testing for auto-created skills, implement circuit breaker (halt auto-creation if N skills created/patched within time window T), add automatic rollback on degradation detection.

### 2. 🛑 Loop Termination Unspecified (Claim 7)
**Severity: CRITICAL**

The primary CLI command (`coworker run --loop`) has no defined termination conditions. The PRD lists "how to detect goal achieved?" as an open question (Section 9.1). Without this, the loop is unimplementable — it will either terminate prematurely or loop indefinitely. The core loop diagram shows "Observe analytics → Decide evaluate gaps" with zero decision criteria.

**Recommendation:** Define specific termination conditions: explicit user-provided success criteria, stagnation detection (N cycles with no new changes), budget limits (max iterations, max cost, max wall-clock time), and human-in-the-loop confirmation on Stop hook.

### 3. 🛑 `coworker run --loop` No Implementable Spec (Claim 14)
**Severity: CRITICAL**

The core loop (Section 2.1) is described in 3 sentences with no state machine, no cycle definition, no analytics-to-action mapping, no error handling within the loop, and no max iterations. Compare with Hermes's documented 10-step loop — the PRD's defining feature has no operational specification.

**Recommendation:** Specify the loop as a state machine: define what constitutes a cycle, map analytics signals to decisions, define error recovery behavior, set max iterations and budget guards.

### 4. 🛑 PostToolUse Hooks Unreliable (Claim 2)
**Severity: HIGH**

At least 9 documented failure modes in Claude Code PostToolUse hooks: global regression across 42 sessions, no firing for MCP/Agent/Skill tool calls, stdout silently dropped, HTTP hooks not dispatched, intermittent Windows failures. The entire per-turn memory sync and state recording pipeline depends on this hook layer.

**Recommendation:** Add dual-trigger mechanism (PostToolUse + Stop hook fallback), add file-based audit trail as third safety net, document known failure modes and their impact on memory completeness, add periodic full-session sync independent of individual tool call hooks.

### 5. 🛑 Subagent Findings Invisible to Memory (Claim 11)
**Severity: HIGH**

PostToolUse hooks do not fire for Agent tool completions. Since Claude Code's Agent tool is the primary mechanism for task decomposition (Section 2.1: "Claude Code decides how to decompose and execute tasks"), subagent exploration results are systematically invisible to the memory system. This is a structural blind spot in the most content-rich tool calls.

**Recommendation:** Explore alternative capture mechanisms for subagent output (e.g., Claude Code session transcript parsing, Monitor tool, or explicit subagent write-back). Document the gap and its impact on memory completeness.

### 6. 🛑 Auto-Approved Skills Risk Quality Degradation (Claim 15)
**Severity: HIGH**

Shanghai AI Lab documented 65.5% unsafe rate in auto-created tools. The PRD has no circuit breaker — a frequently-used but subtly wrong skill would never be archived under the time-based (30d/90d) cleanup model. The only quality signal is `use_count`, which is a popularity metric, not a quality metric.

**Recommendation:** Change default to review mode, add quality gates (sandbox test before promotion), add circuit breaker (halt auto-creation if >3 skills patched within 24 hours), track error rate per skill, not just use count.

### 7. 🛑 Hermes IP Contamination Risk (Claim 1) — PRO WIN
**Severity: RESOLVED**

The con raised IP concerns about Hermes Agent's alleged plagiarism from EvoMap's Evolver engine. The judge ruled PRO: MIT license protects downstream use of architectural patterns, the PRD describes clean-room reimplementation (not code forking), and modules are explicitly replaceable (Section 6.5). **Verdict: No action required**, but documenting the controversy in the PRD's Risk section is good practice.

### 8. ⚠️ Guild Agent Evaluation Missing — "优先复用" Violation (Claim 19)
**Severity: HIGH → MITIGATED**

The PRD's own principle says "prioritize reusing existing tools." Guild Agent is listed as a downstream project in the initiative scope but receives zero evaluation in the PRD. The judge ruled CON on this claim (pro conceded). Round 2 ruled that Guild cannot REPLACE the PRD's memory architecture (fails R2 no-manual-save and R7 no-background-server), but the PRD should evaluate Guild and document the decision.

**Recommendation:** Add a section comparing Guild's capabilities against the PRD's memory requirements, documenting why Guild was not adopted as the backend (R2/R7 failures, missing self-evolution features).

### 9. ⚠️ No Cost Estimation or Budget Mechanism (Claim 8)
**Severity: MEDIUM**

No per-session or per-month cost model. DeepSeek Flash peak-hour pricing doubles costs during working hours (July 2026 change). An autonomous loop running for hours could generate hundreds of dollars with no guardrail. Pro's back-of-envelope estimate suggests ~$2-5/month for typical use, but this is not in the PRD.

**Recommendation:** Add cost model (per-turn, per-session, per-month estimates), add budget limits to `coworker run --loop`, document cost implications of peak vs off-peak DeepSeek pricing.

### 10. ⚠️ No Quality Metrics for Evolution (Claim 10)
**Severity: MEDIUM**

The PRD tracks usage counts (`use_count`, `view_count`) which measure popularity, not quality. A frequently-used wrong skill registers as "successful." Pioneer's architecture includes regression gates with auto-rollback — the PRD has no equivalent.

**Recommendation:** Add quality metrics: skill success rate, patch frequency (high patch rate signals quality issues), regression detection, user override rate. Pioneer's regression gate pattern is a good reference.

---

## Consensus Items

All parties agree on:

1. **Safety architecture is the #1 gap** — must be addressed before any code
2. **Hook reliability is a material risk** — per-turn sync pipeline needs fallback mechanisms
3. **Core loop is underspecified** — `coworker run --loop` cannot be implemented from current spec
4. **Operational fundamentals missing** — no cost model, error handling, quality metrics, or degraded-mode paths
5. **Implementation details need calibration** — FTS5 maintenance rhythm, 5-tool-call threshold, curator data loss risks, DeepSeek single-provider dependency, snapshot staleness
6. **Knowledge taxonomy is genuinely innovative** — the SOP/Experience/State distinction with different storage, lifecycle, and triggers per type
7. **Guild Agent is complementary, not competitive** — evaluates as a task coordination layer, not a self-evolution memory replacement
8. **Pioneer's model-level improvement is correctly deferred** — requires training infrastructure that is out of MVP scope

---

## PRO-Won Claims (Architectural Strengths)

The debate confirmed these aspects of the PRD are sound:

| Claim | Strengths Validated |
|-------|-------------------|
| 1 (Hermes IP) | MIT license protects pattern reuse. Clean-room architecture with replaceable modules. |
| 3 (Sync architecture) | Eventual-consistency model (write-now, read-later) is coherent. PRD never claims mid-session injection. |
| 4 (Self-improvement scope) | Knowledge accumulation IS valid self-improvement. PRD is transparent about scope. |
| 12 (Guild alternative) | Guild fails R2 (manual save) and R7 (background server). Not a replacement. Evaluate as complementary. |
| 20 (Pioneer deferral) | Pioneer requires GPU training infrastructure. Model-level improvement correctly deferred to v2. |

**Plus 5 positive arguments** validated in the debate:
1. Three-layer knowledge taxonomy is genuine architecture innovation
2. Approval model has nuanced defaults per content type
3. Cross-IDE skill source-of-truth solves a real problem
4. "Earn your way up" promotion prevents skill-factory spam
5. Snapshot model correctly prioritizes stability

---

## Unresolved Items

**None.** All 21 claims resolved across 2 rounds.

---

## Recommendations

### Must Fix Before Implementation (BLOCKING)

1. **Add safety architecture** (Claim 6, 15): Review mode default, sandbox testing, circuit breaker, rollback mechanism
2. **Specify loop termination** (Claim 7, 14): State machine, exit conditions, budget limits, error recovery
3. **Address hook reliability** (Claim 2, 11): Fallback triggers, audit trail, document blind spots

### Should Fix Before Implementation (HIGH)

4. **Evaluate Guild Agent** (Claim 19): Document comparison and decision rationale per "优先复用"
5. **Add cost model** (Claim 8): Per-session estimates, budget limits, peak pricing awareness
6. **Add quality metrics** (Claim 10): Success rate, patch frequency, regression detection
7. **Add error handling** (Claim 9): Degraded-mode paths for hook failure, API outage, concurrent sessions
8. **Assess OpenCode hooks** (Claim 5): Reliability analysis for cross-IDE consistency

### Should Fix for Production (MEDIUM)

9. **FTS5 maintenance** (Claim 13): Add automerge, daily OPTIMIZE, WAL mode
10. **Provider abstraction** (Claim 17): Add fallback LLM for background processes
11. **Snapshot refresh** (Claim 18): Optional mid-session refresh command
12. **Curator safety** (Claim 16): Un-archive command, seasonal analysis, high-count protection
13. **Threshold calibration** (Claim 21): Data-driven calibration for ai-coworker's tool call patterns

---

## Bottom Line

The PRD's **conceptual architecture** is sound — the hybrid control/execution plane, three-layer knowledge taxonomy, earn-your-way-up skill promotion, and snapshot-based memory model are well-reasoned. The PRD survives architectural scrutiny.

The **specification and safety** do not. The core loop is unimplementable as written, the safety architecture is empty, and the infrastructure (hooks) that the system depends on has documented reliability gaps. These are fixable gaps for a draft document, but they must be addressed before implementation begins.

**Recommended path:** Revise the PRD with the "Must Fix" items above, then proceed to spec and implementation. The architecture is worth building — it just needs guardrails and specificity.
