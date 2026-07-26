# Issues Found — 2026-07-26 (Round 2)

> 🔍 甲方质检 (find-issues) — Second investigation

## Web Research — Competitor Gap Analysis (5 found)

Compared our mem0-based memory platform against 9 OSS projects (OmniMem, total-agent-memory, ClawMem, Co-Engram, A-MEM, YesMem, deep-memory, komi-learn, Evolver).

| ID | Source | Our Gap | Suggested Feature | Priority |
|----|--------|---------|-------------------|----------|
| W-5 | [OmniMem](https://github.com/richarvey/OmniMem) — experience scoring + graveyard | No experience scoring; no tracking of failed approaches | Add `use_count` auto-increment + `effectiveness_score` to memory metadata | HIGH |
| W-6 | [total-agent-memory](https://github.com/vbcherepanov/total-agent-memory) — LongMemEval benchmark | No retrieval quality benchmark | Add `coworker memory benchmark` using a standardized test set | HIGH |
| W-7 | [ClawMem](https://github.com/yoloshii/ClawMem) — self-cleaning stale embeddings | No automatic deduplication of near-duplicate memories | Add semantic dedup in curator: `_merge_similar()` finds cosine-similar entries | MEDIUM |
| W-8 | [YesMem](https://github.com/carsteneu/yesmem) — Ebbinghaus decay + auto-quarantine | No decay curve; stale just sits there | Add recency-weighted scoring: recent+used > old+unused | MEDIUM |
| W-9 | [Co-Engram](https://www.npmjs.com/package/@co-engram/core) — 3-stage maintenance (light/deep/REM) | Only one curator mode (manual trigger) | Add `coworker curator --mode light|deep|rem` with escalating depth | LOW |

## Spec Gaps — Re-check (2 found)

| ID | Section | File | Gap | Priority |
|----|---------|------|-----|----------|
| S-4 | §2.3 PRD taxonomy | mem0 schema | Spec defines `agent_id` field — never populated in our `memory.add()` calls | MEDIUM |
| S-5 | §9 Error Handling | capture.py | Spec says "CLAUDE.local.md lock → fcntl; queue 3× w/ backoff" — not implemented, just writes directly | MEDIUM |

## Code Deep-Dive (3 found)

| ID | File:Line | Issue | Fix | Priority |
|----|-----------|-------|-----|----------|
| C-3 | src/coworker/memory/curator.py:69 | `query=""` passed to mem0.search — mem0 v2 rejects empty queries (we patched search() but not _mark_stale) | Use `query="."` instead of `""` | HIGH |
| C-4 | src/coworker/memory/audit.py:40 | `datetime.utcnow()` deprecated (same as C-2 from round 1) — but audit.py wasn't fixed yet! | Replace with `datetime.now(timezone.utc)` | LOW |
| C-5 | src/coworker/memory/capture.py:169 | `metadata` includes `use_count: 0` and `last_used` timestamp but these are NEVER updated when the memory is actually retrieved | Add `use_count++` and `last_used` update in `mem0_client.search()` | HIGH |

## DeepSeek Analysis — Top 5 This Round

1. **[HIGH] Memory Retrieval Quality Is Unmeasured** — All 9 competitors have benchmarks (LongMemEval, LoCoMo). We have zero metrics. Without this, "is the agent getting smarter?" is unanswerable.

2. **[HIGH] Memories Are Write-Only** — We store lessons with `use_count: 0` and `last_used` but these fields are NEVER updated on retrieval. The curator can't distinguish "frequently used" from "never used" memories.

3. **[HIGH] Curator Uses Empty Query** — `_mark_stale` and `_archive_old` pass `query=""` to mem0.search, which mem0 v2 rejects. These functions silently fail.

4. **[MEDIUM] No Deduplication** — Similar memories accumulate. OmniMem and ClawMem both do semantic dedup at write time. We don't.

5. **[MEDIUM] Spec §9 File Lock Not Implemented** — CLAUDE.local.md concurrent-write protection is specified but not coded.

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| HIGH | 4 | 3 (C-3 empty query, C-5 use_count update, W-5 scoring) |
| MEDIUM | 4 | 3 (S-4 agent_id, W-7 dedup, S-5 lock) |
| LOW | 2 | 2 (C-4 utcnow, W-9 curator modes) |
| **Total (new)** | **10** | **8 auto-fixable** |
| **Total (cumulative)** | **20** | **12 auto-fixable (6 already fixed)** |
