# Issues Found — 2026-07-26

> 🔍 甲方质检 (find-issues) — Investigation round 1

## PRD Gaps (2 found)

| ID | Requirement | Status | Evidence | Priority |
|----|------------|--------|----------|----------|
| P-1 | R7: no background server (PRD §2.1) | ✅ DONE | mem0 library mode confirmed | — |
| P-2 | PRD §5.8 R8-R15 Dashboard | ⚠️ PARTIAL | Evolution page done, but missing session cost/token dashboards | HIGH |

## Spec Gaps (3 found)

| ID | Section | File | Gap | Priority |
|----|---------|------|-----|----------|
| S-1 | §12.4 Training Pipeline | train.py | Training report generated but not surfaced in dashboard | MEDIUM |
| S-2 | §12.5 Claude SDK Validation | validate.py | `coworker memory validate` CLI exists but never tested with real agents | HIGH |
| S-3 | §4.2 Skill Patching | missing | No `skill-edit` auto-invocation when skills go stale — only detection | HIGH |

## Web Research — Industry Gaps (4 found)

| ID | Source | Insight | Suggested Feature | Priority |
|----|--------|---------|-------------------|----------|
| W-1 | [Bindplane](https://bindplane.com/blog/claude-code-observability-at-scale-how-we-did-it-with-bindplane) | Claude Code emits OTLP telemetry natively — `CLAUDE_CODE_ENABLE_TELEMETRY=1` enables token/cost/session metrics | Add **Token & Cost Analytics** to dashboard (already partially done with Cost tab) | HIGH |
| W-2 | [Coralogix](https://coralogix.com/blog/where-did-all-my-claude-code-tokens-go/) | 63% of spend is context re-read (cache). Cache hit rate drop signals agent rewriting plans mid-session | Add **Cache Hit Rate** metric to dashboard Cost tab | MEDIUM |
| W-3 | [Coralogix Budget](https://coralogix.com/blog/your-team-is-using-claude-code-do-you-know-what-its-costing-you/) | Per-developer cost attribution + budget alerts prevent $40K/month surprises | Add **Spend Alerts** — auto-worker checks cost/day and warns if spike | MEDIUM |
| W-4 | [AWS OTel](https://aws.amazon.com/pt/blogs/mt/analyzing-claude-code-usage-with-cloudwatch-and-opentelemetry/) | Standard OTLP export path: Claude Code → OTel Collector → dashboard | Add **OTel Integration** config to coworker.yaml for one-click telemetry enable | LOW |

## DeepSeek Analysis — Top 5 Improvements

Using DeepSeek v4 deep reasoning on all gaps found:

1. **[HIGH] Complete the Spec §12.5 Validation Harness** — `coworker memory validate` has the CLI but never been run with real agents. This is the key metric for "is memory making the agent smarter?" Without this, the entire evolution story is unproven.

2. **[HIGH] Add Cache Hit Rate to Cost Dashboard** — Industry data shows 63% of spend is context re-read. Our Cost tab shows input/output tokens but NOT cache hit rate. This is a 30-minute fix with high impact.

3. **[MEDIUM] Auto-Worker Should Detect Skill Staleness** — §4.2 describes skill patching but we only detect dead skills, not stale ones. A skill used 0 times in 30 days should trigger auto-review.

4. **[MEDIUM] Dashboard Should Show Training Pipeline Results** — The training report is generated to a file but never surfaced in the UI. Add a "Training" section to the Evolution page.

5. **[LOW] Add OTel Config to coworker.yaml** — One-line config change enables full Claude Code observability. Low effort, high future value.

## Code Issues (2 found)

| ID | File:Line | Issue | Fix | Priority |
|----|-----------|-------|-----|----------|
| C-1 | src/coworker/memory/pending.py:72 | TODO: skill promotion not wired to skill-create | Wire `approve()` to actually invoke skill-create for promotion | MEDIUM |
| C-2 | tests/python/test_pending.py:78,103 | `datetime.utcnow()` deprecated | Replace with `datetime.now(timezone.utc)` in test file | LOW |

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| HIGH | 4 | 2 (S-2 validation harness wiring, S-3 skill patching) |
| MEDIUM | 4 | 3 (cache rate, training dashboard, pending.py TODO) |
| LOW | 2 | 2 (utcnow fix, OTel config) |
| **Total** | **10** | **7 auto-fixable** |
