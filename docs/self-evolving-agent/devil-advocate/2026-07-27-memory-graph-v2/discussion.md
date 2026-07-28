# Devil's Advocate Review — Memory Graph (v2, Independent Re-Review)

**Documents reviewed:**
- `docs/self-evolving-agent/spec/memory-graph-spec.md` (§0–§11)
- `docs/self-evolving-agent/test-plan/memory-graph-test-plan.md`

**Date:** 2026-07-27
**Model:** glm-5.2 (independent re-review after model switch)
**Method:** 3-agent debate (CON / PRO / JUDGE), max 5 rounds, majority-vote fallback
**Independence constraint:** Subagents do NOT read the prior review
(`devil-advocate/2026-07-27-memory-graph/`). They form fresh judgment.
Comparison with prior review happens only in Phase 4.
**Status:** Round 1 — in progress

## Prior-Review Weaknesses Being Addressed

The v1 review (same date) had structural weaknesses this re-review must avoid:
1. PRO surrendered on all 12 CON findings without arguing (anti-pattern:
   "Pro won't concede").
2. Round 1 resolved everything (suggesting insufficient adversarial depth).
3. CON's findings skewed toward "not yet implemented" rather than design-logic
   flaws.

This re-review instructs PRO to genuinely search for counter-evidence, and CON
to attack design logic, not just absence of code.

---

## Round 1 — Full Document Review

### CON Agent — 14 Findings (verified against codebase)

| # | Claim | Section/Line | Severity | Evidence |
|---|-------|--------------|----------|----------|
| 1 | "capture.py already supports both IDEs" — FALSE for OpenCode, partial for Claude Code | §4.0 L173-186 | HIGH | `adapters/opencode.py` writes only MCP/permission config, no hooks. Claude `PostToolUse` routes to analytics JSONL, never invokes `coworker memory sync`. Per-session capture call not firing today. |
| 2 | Reinforcement guard `if edge["confidence"] < "EXTRACTED":` — string-compare bug | §3.1 L126, §3.3 L162 | HIGH | Python verify: `'AMBIGUOUS'<'EXTRACTED'`=True only; INFERRED/WEAK = False. Only AMBIGUOUS gets reinforced — opposite of intent. |
| 3 | §4.3 dedup runs in capture.py on full graph; §8.3 forbids capture.py from touching graph.json | §4.3 L242-255 vs §8.3 L425-437 | HIGH | Mutually exclusive write path. Either dedup misplaced (race on session_count) or queue redundant. |
| 4 | `verify_finding`/`record_traversal` have zero callers | §3.3 L149-166, §6.3 L347 | HIGH | `grep` → 0 hits in src/. No caller → last_traversed_at stays null → decay never fires (§2.3 L107). Self-cleaning property unmechanized. |
| 5 | Spec decay formula ignores existing curator.py step-function decay | §2.1 L85-97 | MED | `memory/curator.py` L171 has different decay (<7d=1.0, 7-30d=0.5...). No reconciliation spec. |
| 6 | "Baseline data already exists" — graph_queries table + graph_enabled column don't exist | §9.1 L463, §9.5 L528-537 | MED | §9.1 marks graph_queries "to implement"; graph_enabled absent from `analytics/db.py` schema. Dashboard SQL returns empty. |
| 7 | `_similarity()` threshold 0.7 but function undefined | §4.3 L247 | MED | Jaccard/cosine/Levenshtein behave wildly differently at 0.7. Tests D1/D3 can't both hold. |
| 8 | LLM emits freeform IDs → edges dangle against non-existent Graphify nodes | §4.1 L198-202 | MED | LLM sees tool-call file_path, not resolved symbol IDs. No format constraint, no dangling-target test. |
| 9 | "Graphify IDs never collide with capture IDs" — substring-prefix is fragile | §1.4 L75-77 | MED | A file `session_20260101_001.py` → Graphify ID mis-classified as capture node. Needs structural marker. |
| 10 | `_confidence_to_score` and `_map_gf_confidence` both undefined, two names | §4.2 L230, §5.2 L297 | LOW | grep → 0 hits. Two names invite drift. |
| 11 | Failed traversal resets last_traversed_at while decrementing weight | §3.2 L135-137 | LOW | Decay clock reset every failure → never ages out via decay, only via -0.1 ratchet. Undocumented interaction. |
| 12 | "graph.json is NetworkX node-link format, same as Graphify export" — unverified | §7.1 L356 | MED | No graphify-out/, no graphify import verifiable. Confidence naming assumption unconfirmed. |
| 13 | File rename silently orphans accumulated weights | §5.4 L312-315 | LOW | Active codebases rename routinely. Slow data-quality leak; test S5 normalizes it. |
| 14 | "~50 lines" for pyvis dashboard — unsubstantiated | §7.2 L387 | LOW | Real pyvis+FastAPI+weight-driven+detail panel typically 200-400 lines. |

### CON Top 5 Risks

1. **Reinforcement broken on day one (#2 + #4)** — graph cannot self-reinforce or decay. Static append-only log disguised as stigmergy.
2. **Concurrency design self-contradictory (#3)** — must resolve before any code.
3. **"No per-IDE changes" masks missing infra (#1)** — prompt extension fires on zero sessions.
4. **Baseline ROI unmeasurable (#6)** — dashboard SQL hits non-existent table/column.
5. **Silent data-quality drift (#7,#8,#9,#13)** — no integrity tests; graph looks healthy while degrading.

### CON: What the spec gets right
- Decay table arithmetic correct (all 12 rows match formula).
- Atomic write pattern sound, already used in `adapters/claude.py:59`, `gemini.py:13`.
- analytics.db columns cited do exist (`db.py` L68-78); duration_min is INTEGER not float (minor).
- Write-ahead queue sound choice — IF #3 resolved.
- Weakest dimension: **mechanization** (behaviors described, functions/callers/modules not nailed). Strongest: **numerical model**.

### PRO Agent — Verdicts (independently verified CON's evidence)

**ACCEPT (HIGH, both aligned):**
- #1 hook wiring missing — confirmed: `adapters/opencode.py` no hooks; Claude `PostToolUse`→analytics JSONL only; `coworker.yaml` has no `hooks:` section.
- #2 string-compare bug — re-ran Python: `'INFERRED'<'EXTRACTED'`=False, `'AMBIGUOUS'<'EXTRACTED'`=True. Confirmed.
- #3 §4.3 vs §8.3 contradiction — confirmed unreconciled.
- #4 zero callers — `grep` 0 hits; no CLI/MCP/hook bridge.

**ACCEPT (MED/LOW):** #7 (`_similarity` undefined), #8 (dangling IDs), #10 (dual naming), #13 (rename orphan, documented), #14 (~50 lines underestimated 4-8×).

**PARTIAL (CON factually right, severity/design-flaw framing disputed):**
- #5 — different decay for mem0 cards vs graph edges is **sound architecture** (different stores). Doc gap, not design flaw. REFUTE implied inconsistency.
- #6 — spec is **honest** (graph_queries marked "to implement", graph_enabled is §9.5 step 1). Historical baseline data exists. Understates that comparison queries non-functional until table populated.
- #11 — clock reset on failure **consistent** with "decay=unused" semantics; -0.1 ratchet handles failure. Undocumented rationale, not a bug.
- #12 — Graphify uninstalled (confirmed), but spec §5.1 has translation layer (`_map_gf_confidence`). Vendor/format risk, not design flaw.

**REFUTE:**
- #9 — CON overreaches. `session_20260101_001.py::symbol` ≠ `session_20260101_001::sub` (`.py::` vs `::` after seq). `type`+`provenance` fields already provide the structural marker CON demands.

### PRO: Spec Strengths
- Write-ahead queue (§8.3) = standard WAL/event-sourcing pattern, correct.
- Decay-at-query-time (§2.4) avoids cron/O(N) writes — sound.
- Confidence tiers (§1.3) map cleanly to source quality; EXTRACTED dominance rule sensible.
- Atomic writes (§8.4) correct (`os.replace` atomic on POSIX).
- Schema versioning (§8.2) correct forward-compat pattern.
- Test plan C1-C5 would catch the §3.1 bug if implemented as tests.

### PRO: Genuine design flaws blocking correctness
**#2 (string-compare), #3 (write-path contradiction), #4 (no caller), #1 (hook wiring)** — all HIGH, need spec revision before implementation.

### Disputed items for JUDGE (CON/PRO disagree)
#5 (decay model), #6 (baseline), #9 (ID collision), #11 (clock reset), #12 (Graphify format).

## Round 1 — JUDGE Ruling

### Summary: Con-wins 9 | Pro-wins 5 | Deferred 0 → no Round 2 needed

**Con-wins (9):** #1 #2 #3 #4 (HIGH), #7 #8 #12 (MED), #10 #14 (LOW)
**Pro-wins (5):** #6, #9, #13 outright; #5, #11 on architecture (doc-fix only)

### Rulings on disputed points
| # | Ruling | Reason |
|---|--------|--------|
| 5 | **Pro-wins (doc-fix)** | Different decay models for different stores (graph edges vs mem0 cards) is sound architecture. Spec must state the boundary explicitly. |
| 6 | **Pro-wins** | §9.5 is honest + concrete; historical session data IS the baseline. graph_queries/graph_enabled are tracked v1 work, not hidden gaps. Not a contradiction. |
| 9 | **Pro-wins** | Spec sets `type` at node creation (test N1-N5), never derives it from ID prefix. Collision risk is speculative — depends on a matching algorithm the spec doesn't define. |
| 11 | **Pro-wins (doc-fix)** | -0.1 ratchet is primary failure penalty; clock reset records "edge was exercised." Sound; spec needs 1-line rationale. |
| 12 | **Con-wins** | PRO's translation-layer defense is misapplied: §5.1 defends Graphify→us (input); §7.1 claims Graphify consumes OUR graph.json (output). Translation layer doesn't defend §7.1. Reuse genuinely unverified. |

### Top 5 Risks
1. **Reinforcement loop non-existent in v1** (#4) — pheromone-trail value-prop is dead code. Graph only ever weakens.
2. **§4.0 false premise** (#1) — all of §4 inherits a hook integration that doesn't exist.
3. **§4.3 vs §8.3 contradiction** (#3) — two implementers reading different sections produce incompatible code.
4. **String-compare bug** (#2) — silent; wrong edges reinforced, correct skipped.
5. **Dangling edges + undefined helpers** (#8, #7, #10) — LLM→graph wiring blockers.

### Verdict: NOT implementation-ready
Design largely sound (WAL, atomic writes, decay-at-query-time, confidence tiers, schema versioning, test C1-C5 well-targeted). But 4 HIGH findings block implementation.

### Must-fix (blocking, before any code)
1. **§4.0 rewrite** — honest hook state; add to §10: wire Claude PostToolUse/Stop → `coworker memory sync`/`close`; add OpenCode hook integration.
2. **§3.1 fix** — `if edge["confidence"] != "EXTRACTED":` (or `confidence_score < 0.9`); add tier-rank helper to §1.3.
3. **§4.3/§8.3 reconcile** — move dedup into merge worker; capture.py writes raw nodes to `pending/`; update §4.3 + §8.3 diagram.
4. **§3.3/§6.3 wire callers** — add `coworker graph verify` CLI + agent-protocol + integration test; OR move to v2 Out-of-Scope and drop from v1 value-prop.

### Should-fix (non-blocking)
5. #5 doc-fix decay boundary. 6. #7/#10 define `_similarity` + unify mapper name. 7. #8 ID validation in §4.2. 8. #11 doc-fix clock rationale. 9. #12 mark §7.1 TBD. 10. #14 revise line estimate.

---
