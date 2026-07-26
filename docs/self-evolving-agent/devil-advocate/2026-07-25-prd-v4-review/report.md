# Devil's Advocate Review — Self-Evolving Agent PRD v4 (Final)

**Document reviewed:** `docs/self-evolving-agent/prd/self-evolving-agent-prd.md`
**Date:** 2026-07-25
**Method:** 3-agent debate (Con / Pro / Judge), 1 round
**Status:** Complete

---

## Final Results

| Outcome | Count |
|---------|-------|
| 🟥 CON wins | **10** |
| 🟩 PRO wins | **3** |
| 🟨 DEFERRED | **1** |
| 🤝 Consensus | **8** |

---

## CON Wins (Must Fix Before Implementation)

| # | Finding | Severity |
|---|---------|----------|
| 1 | Hook config missing `async: true` — PostToolUse blocks every tool call | **BLOCKING** |
| 2 | Hook name `SessionEnd` doesn't exist — real Claude Code hook is `Stop` | **BLOCKING** |
| 3 | Privacy contradiction — PRD sends transcripts to DeepSeek, `session-memory` skill requires local-only | **BLOCKING** |
| 4 | Safety defenses are syntactic (rm -rf grep) but cited threats are semantic (phishing 71.4%, refusal collapse 54.4%) | HIGH |
| 5 | 3 of 5 hook errors from prior review (2026-07-24) remain unfixed | HIGH |
| 6 | 经验总结 has no schema or dedup strategy — Tier 3 becomes unstructured text dump | MED |
| 7 | Review-mode creates unbounded pending queue — 35-210 items/week with no batch ops | MED |
| 8 | `coworker run --loop` estimate too low — ~200→~450 lines for state machine + subprocess mgmt | MED |
| 9 | Hermes pattern names (`write_approval`, `skill_usage.py`) not verifiable in reference docs | LOW |
| 10 | Greenfield estimate missing CLI scaffolding for 16+ commands | MED |

## PRO Wins (Confirmed Correct)

| # | Finding |
|---|---------|
| 1 | Frozen snapshot vs per-turn learning is a valid design tradeoff, not contradiction |
| 2 | Non-blocking sync is architecturally achievable (backgrounding is trivial) |
| 3 | Overall progress: 3 blocking issues from prior review addressed at framework level |

## Consensus (Both Sides Agree)

- Three-tier memory architecture is correctly designed and separates concerns
- Guild Agent correctly rejected as replacement; complementary v2 candidate
- Hook infrastructure in production is the right foundation
- Semantic merge, backup/rollback, CLAUDE.local.md injection exist in production
- Post-session summarization as central mechanism is architecturally sound
- Implicit-evolution UX (no separate mode) is correct primary experience
- Cost model is viable (~$0.002/session)
- "Earn your way up" promotion prevents skill-factory spam

---

## Priority Fixes for PRD v5

1. **[BLOCKING]** Add `async: true` to hook config; change `SessionEnd` → `Stop`
2. **[BLOCKING]** Add privacy section: acknowledge transcript-to-remote-API tradeoff, default to local (Ollama), DeepSeek as opt-in
3. **[HIGH]** Acknowledge safety gap: current defenses are syntactic, cited threats are semantic; add semantic guard as P1
4. **[MED]** Define Tier 3 lesson schema: `{project, topic, problem, solution, confidence, source_session}`
5. **[MED]** Add pending queue management: batch ops, auto-expiry, quality scoring
6. **[MED]** Recalibrate greenfield: ~2,200 total (add CLI scaffolding ~200, split loop driver ~450)
7. **[LOW]** Cite Hermes concepts ("smart approval system") not pattern names ("write_approval")

---

## Verdict

The three-tier architecture and requirements-first approach are solid and well-defended by PRO. However, 10 of 14 disputed claims went to CON — the implementation-level details have significant gaps. Three issues are **blocking**: hook config (async + wrong hook name) and privacy contradiction. These must be resolved before any code is written.
