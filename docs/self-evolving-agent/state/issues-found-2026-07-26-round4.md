# Issues Found — 2026-07-26 (Round 4)

> 🔍 甲方质检 (find-issues) — Reliability + Silent Failure Audit

## Industry Research — Claude Code Quality Issues (3 found)

Based on r/ClaudeAI community reports and official postmortems (March–June 2026):

| ID | Source | Issue | Our Risk | Priority |
|----|--------|-------|----------|----------|
| R-1 | [InfoQ](https://www.infoq.cn/article/YxxhwlcTWclI5ErKROKv) — Claude ignores CLAUDE.md rules | Claude Code frequently ignores `CLAUDE.md` instructions. Our memory platform relies on `inject_into_local_md()` to write context. If agent ignores it, all memory is useless. | **CRITICAL: No verification that injection actually worked.** `inject_into_local_md()` writes but never reads back to confirm. | **CRITICAL** |
| R-2 | [Reddit](https://aiweekly.co/node/2915) — "Done" declared while 500 errors continued for 2 days | Auto-worker declares fixes "complete" without mandatory verification gate. Same failure pattern: agent claims victory but code still broken. | **HIGH: No mandatory test-run after auto-worker fixes.** Run `pytest` after each fix as a gate. | HIGH |
| R-3 | [VentureBeat](https://venturebeat.com/technology/is-anthropic-nerfing-claude-users-increasingly-report-performance) — Model silently downgraded | Anthropic changed reasoning effort from high→medium without disclosure. Our `LLMClient` uses `deepseek-v4-flash` but has no quality gate to detect if model quality drops. | **MEDIUM: Add periodic model quality check** — test known-good prompt and verify output quality. | MEDIUM |

## Code Deep-Dive — Silent Failures (3 found)

| ID | File:Line | Issue | Fix | Priority |
|----|-----------|-------|-----|----------|
| C-8 | src/coworker/memory/mem0_client.py:154 | `continue` after exception in add retry loop — exceptions swallowed silently | Log each failed attempt with the actual error message | MEDIUM |
| C-9 | src/coworker/memory/mem0_client.py:235 | `pass` in delete() catches ALL exceptions including SystemExit/KeyboardInterrupt | Only catch `(KeyError, Exception)` as intended | LOW |
| C-10 | src/coworker/memory/inject.py | `inject_into_local_md()` has no return value verification — writes file but never reads back to confirm | Add verification read after write | HIGH |

## New Spec Gaps (1 found)

| ID | Section | Issue | Priority |
|----|---------|-------|----------|
| S-6 | §9 Error Handling | "Rebuild from raw session transcripts" mentioned but `rebuild_index()` in audit.py never called by any automation | MEDIUM |

## DeepSeek Analysis — Top 5 This Round

1. **[CRITICAL] CLAUDE.md Compliance Is Unverified** — Industry data shows Claude Code frequently ignores CLAUDE.md. Our memory platform's value proposition is "agent gets smarter via injected context." If the injection is silently ignored, the entire product is vaporware. Need injection verification.

2. **[HIGH] No Mandatory Verification Gate** — Auto-worker fixes things but never runs tests afterward. Every fix should trigger `pytest` on the affected module before being declared "done."

3. **[HIGH] Injection Write-Only** — `inject_into_local_md()` writes to file but never verifies the write succeeded or that the content is readable.

4. **[MEDIUM] Silent Exception Swallowing** — 3 places in mem0_client.py where exceptions are caught and silently discarded.

5. **[MEDIUM] Model Quality Not Monitored** — If DeepSeek degrades model quality (as Anthropic did), we have no detection mechanism.

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| CRITICAL | 1 | 1 (injection verification) |
| HIGH | 2 | 2 (verification gate, C-10) |
| MEDIUM | 3 | 2 (C-8 logging, R-3 model quality check stub) |
| LOW | 1 | 1 (C-9 exception narrowing) |
| **Total (new)** | **7** | **6 auto-fixable** |
| **Grand Total** | **39** | |
