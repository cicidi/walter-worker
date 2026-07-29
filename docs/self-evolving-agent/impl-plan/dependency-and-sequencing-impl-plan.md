# Dependency & Sequencing — QA Skill vs Self-Evolution Engine

> Initiative: self-evolving-agent | Type: decision doc | Status: **pending user decision**
>
> Companion to: [advocate review](../raw/devil-advocate-reviews/2026-07-24-prd-spec-review/report.md)
>
> Question this answers: the QA-agent skill (design/spec/impl-plan) declares dependencies on PRD platform features that **do not exist yet**. How do we resolve this — build the engine first, or make the skill self-contained?

---

## The Core Problem

The QA-agent docs claim to be "built on" the self-evolution platform. Verified against the codebase on 2026-07-24:

| Platform feature the QA skill claims | Claimed in | Actually built? |
|---|---|---|
| MEMORY.md store (`memory_store.py`) | design:6, spec §2.2, impl-plan:5 | ❌ greenfield |
| FTS5 index (`fts5_index.py`) | design:6, design §1, impl-plan:31 | ❌ greenfield |
| State Engine (§4) | design:6, spec §4, impl-plan | ⚠️ partial — `coworker state-update` runs on Stop hook, but the state-file convention + recording criteria are not implemented |
| Self-Evolution Engine (§5: auto skill create/patch) | design:6, design §5 | ❌ greenfield |
| `coworker run --loop` SDK driver (§2.2) | design:29, impl-plan | ❌ greenfield |
| `SessionStop` hook | design:21,31 | ❌ **not a real hook name** (real: `SessionEnd`; see review §1.2) |
| `/memory-search`, `/memory-add` skills | design §1 | ❌ do not exist as skills |

**A skill cannot extend infrastructure that does not exist.** This is the central dependency conflict to resolve before writing more code.

### Additional inconsistency: impl-plan v2 silently switched backends
The impl-plan (`qa-autonomous-agent-impl-plan.md`, header "v2 — Guild OSS + Jam.dev MCP") diverges from BOTH the design and the spec:
- **design + spec** agree: two-tier `MEMORY.md` + SQLite `knowledge_index` (+ FTS5).
- **impl-plan v2** replaces FTS5 with **Guild OSS Lore** (BM25+vector), state files with **Guild Quests/Briefs**, and adds **Jam.dev MCP**.

**Note on Appendix A (corrected):** PRD Appendix A did **not** reject Guild wholesale. It rejected Guild only as a *wholesale replacement for the memory architecture* (R2/R7 + no self-evolution features), while explicitly endorsing Guild as a **complementary v2 candidate**, including "evaluating as an alternative to FTS5 for v2." The impl-plan v2's use of Guild (Lore for search, Quests/Briefs for task tracking) is therefore **aligned with Appendix A's v2 guidance**, not a contradiction — using Guild for the QA skill is a legitimate option.

The accurate concerns are: (a) **design ↔ impl-plan disagree** — the design doc still describes the no-Guild `MEMORY.md + SQLite + FTS5` architecture and was not updated when the impl-plan pivoted to Guild; (b) **R2/R7 are context-dependent** — they fail the PRD's *implicit auto-capture* requirement, but the QA skill runs in SDK mode (deliberate invocation), where a background MCP server and orchestrated writes are acceptable, so they likely don't block the QA skill; (c) **new external dependencies** — Guild Go binary + Jam.dev MCP add install/maintenance burden. Reconcile the design↔impl-plan substrate choice alongside the Path 1/2 decision.

---

## What DOES Exist (verified, reusable now)

| Asset | Location | Usable for QA skill? |
|---|---|---|
| Analytics DB | `analytics/db.py` — 8 tables incl. `knowledge` (title/type/session_id/project/skills/summary/evidence), `session_summaries`, `tool_calls` | ✅ extend the existing `knowledge` table instead of a parallel DB |
| Working DeepSeek client | `analytics/knowledge.py._ask_llm_is_duplicate` | ✅ reuse instead of a new `_call_llm` |
| Live hooks | `~/.claude/settings.json` — PostToolUse + Stop firing; Stop calls `coworker state-update` | ✅ extend hook commands |
| CLI / templates / adapters / semantic_merge | `cli.py`, `templates/local_claude_md.py`, `adapters/`, `semantic_merge.py` | ✅ |
| Existing skills | `session-memory`, `self-analyze`, `self-heal` (in `skills/` + `~/.claude/skills/`) | ✅ reference/adapt |

---

## The Fork — Two Build Paths

### Path 1 — Self-contained QA skill (ship now)
Strip the 5 platform dependencies. The QA skill uses only existing ai-coworker infra:
- Knowledge storage → extend `analytics.db`'s `knowledge` table (not a parallel `qa/knowledge.db`).
- LLM calls → reuse `analytics/knowledge.py`'s DeepSeek client (not a new `_call_llm`).
- Hooks → wire into the existing PostToolUse/Stop commands (with correct `SessionEnd` + `async`).
- No MEMORY.md / FTS5 / State-Engine-convention / auto-evolution dependency.

**Tradeoffs**
- ➕ Buildable **today**; delivers a working QA tool; unblocked by the engine.
- ➕ Dogfooding a real skill produces the data that tells you what the engine actually needs.
- ➖ Does not participate in self-evolution (no shared memory/skill lifecycle with the platform).
- ➖ Later migration cost onto the engine when it exists.

### Path 2 — Engine-first (build the platform, then the skill)
Build the PRD's greenfield modules first: `memory_store.py`, `fts5_index.py`, `sync.py`, `curator.py`, `lifecycle.py`, `pending.py`, post-session summarization, the corrected hook layer, `coworker run --loop`. The QA skill then consumes them as originally designed.

**Tradeoffs**
- ➕ QA skill becomes part of the evolving system from day one (shared memory/skills).
- ➕ Directly serves the stated goal ("daily self-evolution, better over time").
- ➖ Much larger work (~1,840 greenfield lines + hook rebuild + safety hardening).
- ➖ QA tool delayed until the platform lands.
- ➖ The platform is where the hardest unsolved problems live (subagent capture, safety, competence metrics).

---

## Recommendation

**Path 1 for the QA skill now; run the self-evolution engine as a separate workstream.**

Rationale:
1. The user stated the QA agent is **"a supplement to ai-coworker."** A supplement should not block on the platform.
2. The impl-plan already exists as scaffolding; converting it to self-contained (reuse `analytics.db` + `knowledge.py`, drop the platform claims) is smaller than building the engine.
3. A working QA skill gives **real dogfooding signal** that de-risks the engine design.
4. The engine is the bigger, riskier bet and deserves its own focused initiative — including fixing the hook architecture (review §1.2) and adding safety/competence gates (review §3) **before** relying on it for autonomous self-modification.

When the engine exists, migrate the QA skill onto it (swap `analytics.db knowledge` reads for MEMORY.md+FTS5, swap manual skill calls for auto-evolution triggers).

---

## Fix Classification

### Path-independent fixes (APPLIED this session — correct regardless of path)
1. spec §7.1 + impl-plan :19,:133 — fabricated `PRD §5.7` → real source (global `CLAUDE.md §0.5`).
2. design :236 — `§2.1.2` → `§2.2.2`.
3. design :29 — Core Loop `extends §2.1` → `§2.2`.
4. spec :80 — MEMORY.md format overclaim corrected.
5. Deleted orphan empty templates `docs/initiatives/self-evolving-agent/{plan,spec}.md`.
6. en PRD :84 — duplicate `§1.4 Knowledge Taxonomy` → `§1.6` (matches zh).
7. design :6 — added ⚠️ marker flagging the platform features as unbuilt, pointing here.

### Path-dependent fixes (DECIDE PATH FIRST)
- design:6 "Infrastructure used: MEMORY.md + FTS5…" — reword to "target dependencies" (Path 2) or remove and list existing-infra replacements (Path 1).
- All references to `/memory-search`, `/memory-add`, `SessionStop`, State Engine §4 convention — rewrite per chosen path.
- MEMORY.md 4-field format (spec §2.2) — ratify into PRD §3.2 (Path 2) or mark as QA-local (Path 1).
- impl-plan's parallel `qa/knowledge.db` — switch to `analytics.db` extension (Path 1) or wait for engine (Path 2).

### Separate workstream (NOT in scope here — see review)
- Hook architecture correction (real hook names, `async`, stdin session_id, `SubagentStop`).
- Engine greenfield modules + safety + competence gate + budget cap.

---

## Decision Needed

**Pick Path 1 or Path 2.** Until then, treat the QA skill's platform dependencies as aspirational, not available.
