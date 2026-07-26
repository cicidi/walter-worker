# Issues Found — 2026-07-26 (Round 11)

> 🔍 甲方质检 (find-issues) — Process Audit + PRD §5.3

## Process Gaps (2 found)

| ID | Issue | Evidence | Priority |
|----|-------|----------|----------|
| P-1 | Wrong-history not auto-invoked on test failures | R32 detected 4 skill frontmatter test failures. R33 auto-fixed them. But no wrong-history entry was created documenting the mistake (missing frontmatter fields on 4 skills). The auto-worker fixed the symptom but didn't record the root cause. | HIGH |
| P-2 | Auto-worker doesn't run full test suite by default | For 31 rounds, auto-worker ran 119 core tests. It took until R32 to discover that `tests/python/test_skill_frontmatter.py` existed and had failures. The health check was testing a subset, missing the full picture. | HIGH |

## PRD §5.3: Auto Skill Patching (1 found)

| ID | PRD Ref | Issue | Priority |
|----|---------|-------|----------|
| PRD-5 | §5.3 | "Invoke skill-edit (surgical: old_string → new_string) when skill is found outdated." Zero implementation. No code detects outdated skills or proposes patches. This was flagged as S-3 in Round 1 but never progressed. | HIGH |

## Code Quality (1 found)

| ID | File | Issue | Priority |
|----|------|-------|----------|
| C-13 | `tests/python/test_skill_frontmatter.py` | This test file existed all along but was excluded from auto-worker's test suite. 35 tests were never run in 31 rounds because the pytest command hardcoded a specific file list. | LOW |

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| HIGH | 3 | 2 (P-1, P-2: fix test suite coverage) |
| LOW | 1 | 1 (C-13: expand test list) |
| **Total (new)** | **4** | **3 auto-fixable** |
| **Grand Total** | **75** | |
