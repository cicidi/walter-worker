# Advocate Review — Self-Evolving Agent: PRD + Spec + Design + Impl-Plan

**Documents reviewed:**
- `prd/self-evolving-agent-prd.md` (v3, en) + `self-evolving-agent-prd-zh.md` (v3, zh)
- `spec/qa-autonomous-agent-spec.md`
- `design/qa-autonomous-agent-design.md`
- `impl-plan/qa-autonomous-agent-impl-plan.md`

**Date:** 2026-07-24
**Method:** Direct codebase verification + 3 parallel subagents (doc reconciliation, impl-plan feasibility, Claude Code hook ground-truth). All findings backed by code or doc line refs — not speculation.
**Question:** Can the PRD + spec enable ai-coworker to self-learn and evolve daily, producing an increasingly better agent?

---

## Verdict

**Vision is achievable and the foundation is real — but the current spec + impl-plan will NOT deliver daily self-evolution.**

The self-evolution *concept* can work: hooks are already firing, the analytics DB exists, and the reuse infrastructure is genuine (verified in code). However:

1. The spec/design/impl-plan build a **QA-agent skill** (a supplement on top of ai-coworker), **not** the self-evolution engine that actually makes the agent smarter.
2. That engine (memory_store, FTS5, sync, curator, lifecycle, pending, post-session summarization) is **entirely greenfield** with **no impl-level spec**.
3. The PRD's hook architecture has **concrete technical errors** that would prevent the primary "implicit evolution" experience from working as written.

**Answer to the question:** Yes in principle — but **not with the current spec + impl-plan.** Building them produces a (currently hollow) QA tool, not a self-evolving agent.

---

## Reframe: Platform vs Application

The doc set is **not** two competing products. It is **one platform + one application**:

| Doc | Role |
|-----|------|
| **PRD (v3)** | **Platform** — the self-evolution engine (memory + skill auto-evolution via hooks) |
| design / spec / impl-plan | **One application** — a QA-automation skill that runs on the platform |

The user's goal ("daily self-evolution, better over time") is the **platform**. The QA skill is a supplement/demo. **Critical gap: the platform is neither built nor specified at the impl level.** The QA docs claim to be "built on" platform features that do not exist.

---

## Evidence: Foundation Is Real (code-verified)

| PRD reuse claim | Exists? | Status |
|---|---|---|
| `analytics/db.py` (8 tables: knowledge, session_summaries, tool_calls, …) | ✅ 141 lines | Real |
| `analytics/knowledge.py` (DeepSeek dedup, working `_ask_llm_is_duplicate`) | ✅ 207 lines | Real — has a usable DeepSeek client |
| `semantic_merge.py`, `cli.py`, `templates/local_claude_md.py`, `adapters/` | ✅ all present | Real |
| Hooks installed & firing | ✅ settings.json has PostToolUse + Stop live; Stop already calls `coworker state-update` | Real |
| FTS5 + memory_store | ❌ greenfield | Matches PRD's ~1,840-line estimate |

---

## 1. Cannot Work (as written)

### 1.1 Impl-plan is a non-functional stub skeleton
Every function that does real work is a stub:
- `_call_llm` / `_llm_filter` → `NotImplementedError`
- `scan_dimension` (7-dim discovery) → `return []`
- `execute_fix` → dummy `FixResult`
- `dynamic_check` (Layer 3) → `return None`
- orchestrator `run()` → breaks after 1 iteration, **never calls** gap-check/discovery/fix
- `qa_hook_push` → two `echo` calls (no-op)

Tests are written to pass on the stubs (assert only that events yield), so "green" ≠ working. Additional defects: no MEMORY.md is ever written (`memory_ref` → `#pending`); no FTS5 virtual table (yet defines `QA_E004_FTS5Corrupted`); LLM filter silently disabled (catches `NotImplementedError` → `relevant: true`); `git add ~/.coworker/skills/qa-*/` fails (paths outside repo); AST scanner is Python-only but the spec's example project is TypeScript.

The impl-plan also builds `src/coworker/qa/`, **not** the PRD's `src/coworker/memory/` or `skills/` (neither exists).

### 1.2 PRD hook architecture — 5 technical errors
Verified against 2026 Claude Code docs:

| # | PRD says | Reality | Impact |
|---|---|---|---|
| 1 | "SessionStop" hook for session-end summary | No such hook. `Stop` = per-turn; `SessionEnd` = per-session | Wrong granularity or never fires |
| 2 | Stop as PostToolUse fallback | `Stop` is per-turn, can block, 8-iteration cap | Wrong granularity |
| 3 | SessionStop covers subagent blind spot | Dedicated `SubagentStop` hook exists; PRD never mentions it | Subagent work (richest content) stays invisible |
| 4 | `--session-id $SESSION_ID` in hook command | session_id arrives via stdin JSON, not a `$SESSION_ID` env var | Command gets empty session id |
| 5 | (no `async` specified) | Hooks are synchronous by default, 600s timeout | Every PostToolUse blocks on a DeepSeek call → terrible UX |

Good news: PRD §3.3 wrongly claims PostToolUse misses MCP + Skill tools — it actually fires for both. Only Agent/subagent is missed (use `SubagentStop`).

### 1.3 Broken document cross-references (6)
| # | Location | Break | Fix |
|---|---|---|---|
| 1 | spec §7.1; impl-plan :19, :133 | cites fabricated `PRD §5.7` (Autonomous Job Guardrail) — no §5.7 in en or zh PRD | source is global `CLAUDE.md §0.5` |
| 2 | design :236 | `PRD §2.1.2` | → `§2.2.2` |
| 3 | design :29 | Core Loop `extends §2.1` (implicit loop) | → `§2.2` (SDK mode) |
| 4 | spec :80 | MEMORY.md format `extends PRD §3.2` overclaim | §3.2 defines only the § delimiter, not this 4-field shape |
| 5 | `docs/initiatives/self-evolving-agent/{plan,spec}.md` | empty orphan templates, violate PRD placement convention | delete |
| 6 | en PRD :84 | duplicate `§1.4 Knowledge Taxonomy` (zh correctly has §1.6) | → `§1.6` |

> Fixes 1–6 are applied in this session (path-independent). See commits.

---

## 2. Hard to Use

- **"One-time setup" is oversold:** needs DeepSeek key + Gemini/Claude fallback keys + hook config + 3 cron jobs.
- **Behind-the-back behavior:** implicit evolution auto-modifies `CLAUDE.local.md`, auto-creates skills. Surprising; review mode helps but creates a pending queue to manage.
- **No budget guardrail:** v3 **removed** cost controls ("provider-managed recharge is the control"). A daily background LLM with no spend cap is a cost risk (prior review flagged this; v3 made it worse).
- **Context bloat:** MEMORY.md grows → injected snapshot grows → context pollution. Curator cleans stale but pins high-use → accumulation.
- **Cross-IDE unproven:** OpenCode hook reliability is "unassessed" per the PRD itself.
- **Transcript parsing is fragile:** Claude Code warns transcript JSONL format "changes between versions" — post-session summarization depends on it.
- **Subagent content loss:** modern Claude Code leans on subagents; they are structurally invisible to memory.

---

## 3. Hidden Risks

1. **Safety (PRD's own cited data):** auto-created tools are 65.5% unsafe (Shanghai AI Lab). Sandbox check is shallow (no `rm -rf`/creds/network — catches gross, not subtle). Circuit breaker is 3 skills/24h — but one subtly-wrong skill used 100× does more damage.
2. **Memory poisoning / prompt injection:** accumulated MEMORY.md + auto-skills are a persistent cross-session/cross-project attack surface. AgentWorm: 63% attack success. Extracted lessons have no input sanitization.
3. **Self-reinforcing errors:** wrong lesson → MEMORY.md → next session → agent acts on it → "confirms" it → reinforced. Contradiction detection relies on keyword FTS5 + an LLM filter that is currently a stub.
4. **Cost runaway:** no cap + per-turn + per-session LLM + DeepSeek 2× peak pricing.
5. **CLAUDE.local.md corruption:** auto-injection into the file the whole session depends on. `semantic_merge.py` protects PROTECTED blocks but the MEMORY snapshot block is agent-managed.
6. **"Smarter" is unmeasured:** no metric confirms the agent actually improves. Could accumulate cruft. Tracks popularity (use_count) and per-skill error_rate, not system-level competence. No regression gate (cf. Pioneer).

---

## 4. Prior Review (2026-07-24) Blockers — Status Check

| Blocker | v3 resolved? | Substance |
|---|---|---|
| Zero safety guardrails | On paper, shallow | Defaults flipped to review ✓, circuit breaker ✓, sandbox ✓ (shallow), rollback ✓. No system-level competence metric. |
| Loop termination undefined | SDK only ✓ | Primary (implicit) experience has no convergence concept — "each session is a cycle" means endless accumulation (see risk 3/6). |
| Hook reliability | Right direction, wrong details | Dual-trigger concept ok, but uses non-existent hook name, missing SubagentStop, missing `async`, `$SESSION_ID` bug (§1.2 above). |

---

## Recommendations

1. **Decide scope:** the goal is the **platform** (engine), not the QA skill. Don't let the impl-plan drag effort into the QA shell.
2. **Fix the hook architecture before code:** real hook names (`PostToolUse` + `SubagentStop` + `SessionEnd`), `async: true`, read session_id from stdin JSON (copy existing `common.sh`), use `SubagentStop` for the subagent blind spot.
3. **Reuse what exists:** don't rewrite `_call_llm` (use `analytics/knowledge.py._ask_llm_is_duplicate`); don't build parallel `qa/knowledge.db` (extend `analytics.db`'s existing `knowledge` table).
4. **Restore a budget cap** (v3 removed it).
5. **Add a competence regression gate** (benchmark tasks run periodically, or user-correction-rate trending down).
6. **Treat accumulated memory as untrusted input** — sanitize/validate extracted lessons; make contradiction detection actually work.
7. **See `dependency-and-sequencing.md`** for the build-path decision (self-contained QA skill vs engine-first).

---

## Bottom Line

The PRD's conceptual architecture survived scrutiny. The foundation (hooks, analytics DB, reuse infra) is real and working for built-in tools. But **the current spec + impl-plan are a hollow QA-skill skeleton that depends on an unbuilt platform**, and the PRD's hook design has fixable but currently-wrong technical details. To get a self-evolving agent, build the platform's greenfield modules for real — that is where "smarter" actually comes from.
