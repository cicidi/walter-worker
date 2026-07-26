# Issues Found — 2026-07-26 (Round 8)

> 🔍 甲方质检 (find-issues) — PRD Deep-Dive + Fresh Install

## PRD Compliance (3 found)

| ID | PRD Ref | Requirement | Status | Priority |
|----|---------|-------------|--------|----------|
| PRD-2 | §5.2 Quality Metrics | `error_rate`, `patch_frequency`, `user_override_rate`, regression detection required by PRD. Curator only tracks use/view/patch counts. | PARTIAL — missing 3 of 4 quality metrics | HIGH |
| PRD-3 | §5.6 Safety Architecture | "Sandbox dry-run before promotion" and "rollback" mechanism required. We have circuit breaker (stop) but no sandbox (test before promote) or rollback (undo after bad promote). | PARTIAL — safety is stop-only, no test/recover | HIGH |
| PRD-4 | §5.2 Zero-use visibility | R10: "Zero-use skills must be visible — they are candidates for archival." Evolution page shows all skills but doesn't highlight zero-use ones. | MISSING — zero-use filter/indicator | MEDIUM |

## Operational (1 found)

| ID | Issue | Evidence | Priority |
|----|-------|----------|----------|
| OPS-3 | `coworker` CLI help doesn't list new commands | `coworker --help` shows 8 groups but find-issues, memory sub-commands aren't obvious | LOW |

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| HIGH | 2 | 0 (design work) |
| MEDIUM | 1 | 1 (PRD-4: zero-use filter) |
| LOW | 1 | 0 |
| **Total (new)** | **4** | **1 auto-fixable** |
| **Grand Total** | **61** | |
