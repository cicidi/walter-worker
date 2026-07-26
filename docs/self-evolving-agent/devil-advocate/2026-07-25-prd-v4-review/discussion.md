# Devil's Advocate Review — Self-Evolving Agent PRD v4

**Document reviewed:** `docs/self-evolving-agent/prd/self-evolving-agent-prd.md`
**Date:** 2026-07-25
**Method:** 3-agent debate (Con / Pro / Judge), max 5 rounds
**Status:** Round 1 — awaiting JUDGE ruling

## Round 1 — Full Document Review

### CON Agent — 16 Findings

| # | Claim | Impact |
|---|-------|--------|
| 1 | `Stop` hook fires per-turn, not session-end — primary evolution mechanism miswired | HIGH |
| 2 | Hook config missing `async: true` — per-turn sync blocks sessions | HIGH |
| 3 | `SubagentStop` acknowledged but not wired into config | HIGH |
| 4 | Engine 0% built — 12 greenfield modules don't exist | HIGH |
| 5 | No budget cap — prior review fix unaddressed | HIGH |
| 6 | Safety metrics defined but unmeasurable — no mechanism | HIGH |
| 7 | No contradiction detection — self-reinforcing errors | HIGH |
| 8 | Snapshot injection code doesn't exist in templates | MED |
| 9 | No system-level competence metric | HIGH |
| 10 | Session ID mechanism unclear in hook examples | MED |
| 11 | Curator false-negatives for rare critical knowledge | MED |
| 12 | No snapshot size limit — context bloat | MED |
| 13 | R7 "no background server" contradicted by cron + daemon | MED |
| 14 | Guild evaluation only considers all-or-nothing, not hybrid | LOW |
| 15 | Sandbox testing superficial — catches gross, misses subtle | MED |
| 16 | `coworker state-update` writes empty progress entries | MED |

### PRO Agent — 20+ Defense Claims

| # | Claim | Dimension |
|---|-------|-----------|
| 1.1 | Three-tier solves real separation-of-concerns problem | Architecture |
| 1.2 | Frozen snapshot prevents stale context bugs | Architecture |
| 1.3 | Snapshot more robust than live injection | Architecture |
| 2.1 | R1-R7 falsifiable — Appendix A discriminates alternatives | Requirements |
| 2.2 | R3 dual search well-specified and necessary | Requirements |
| 2.3 | R5 prevents context consistency bugs | Requirements |
| 3.1 | Error handling thorough — 9 scenarios with concrete behavior | Completeness |
| 3.2 | Subagent gap documented honestly with 3 mitigation layers | Completeness |
| 3.3 | Safety architecture addresses all 3 prior review blockers | Completeness |
| 4.1 | Infrastructure reuse substantial and code-verified | Feasibility |
| 4.2 | Cost model negligible with 3-provider fallback | Feasibility |
| 4.3 | Greenfield components small, single-responsibility | Feasibility |
| 5.1 | Hook-embedded implicit evolution genuinely novel | Innovation |
| 5.2 | Knowledge taxonomy maps storage to knowledge type | Innovation |
| 5.3 | "Earn your way up" prevents shared repository spam | Innovation |
| 6.1 | v4 correctly separates PRD vs Spec vs Impl Plan | Improvement |
| 6.2 | Post-session trigger catches cross-task patterns | Improvement |
| 6.3 | CLAUDE.local.md vs CLAUDE.md scope documented | Improvement |

### Awaiting JUDGE ruling...
