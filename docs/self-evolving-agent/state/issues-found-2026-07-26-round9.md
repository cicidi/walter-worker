# Issues Found — 2026-07-26 (Round 9)

> 🔍 甲方质检 (find-issues) — PRD Safety & Privacy Compliance

## Safety Gaps (4 found)

| ID | PRD Ref | Requirement | Our Status | Priority |
|----|---------|-------------|------------|----------|
| S-7 | §5.6 Sandbox Testing | "Before a pending skill is promoted, dry-run it in a sandboxed session." Approve() copies files with zero testing. A malicious/broken skill gets promoted blindly. | MISSING | **CRITICAL** |
| S-8 | §5.6 Rollback | "Every auto-created/patched skill supports rollback to last known-good version. Automatically if post-patch error rate exceeds pre-patch by 50%+. Version history retains last 5 versions." Approve is one-way, no undo. | MISSING | HIGH |
| S-9 | §5.6 Safety Monitoring | "Track refusal_rate, unsafe_output_rate, skill_error_rate, circuit_breaker_trips per session." Metrics.py tracks circuit_breaker_trips only. Missing 3 of 4 safety metrics. | PARTIAL | HIGH |
| S-10 | §5.4 Privacy Model | "Summarization sends session content to the configured remote background LLM. Local-only opt-in for sensitive sessions." No privacy toggle exists. All extraction calls go to DeepSeek without user awareness. | MISSING | MEDIUM |

## Implementation Gaps (1 found)

| ID | Issue | Evidence | Priority |
|----|-------|----------|----------|
| G-1 | 8 HIGH priority issues from previous rounds remain unfixed | grep "HIGH" across 7 issue files shows accumulating debt. Some (W-1 Token dashboard, S-2 Validate harness) have been partially addressed but marked HIGH for weeks. | MEDIUM |

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| CRITICAL | 1 | 0 (sandbox infra required) |
| HIGH | 2 | 0 (design work) |
| MEDIUM | 2 | 0 |
| **Total (new)** | **5** | **0 auto-fixable** |
| **Grand Total** | **66** | |
