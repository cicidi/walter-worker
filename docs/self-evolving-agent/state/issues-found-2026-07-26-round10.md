# Issues Found — 2026-07-26 (Round 10)

> 🔍 甲方质检 (find-issues) — Documentation + Integration Gaps

## Documentation (3 found)

| ID | Issue | Evidence | Priority |
|----|-------|----------|----------|
| DOC-3 | README doesn't mention new features | `README.md` lists 4 features (auto-scan, inject, initiatives, track projects). None of the new work documented: memory platform, auto-worker, dashboard, find-issues, wrong-history | HIGH |
| DOC-4 | No onboarding doc for new developers | 105 files changed vs master, 22,772 new lines. No guide for how to use the new features. | MEDIUM |
| DOC-5 | Spec §8 OpenCode plugin not updated | `.opencode/coworker-analytics/` exists but `tool.execute.after` doesn't call `coworker memory sync` as spec requires | MEDIUM |

## Integration (2 found)

| ID | Issue | Evidence | Priority |
|----|-------|----------|----------|
| I-1 | 60+ untracked design/HTML files | `git status` shows html/, devil-advocate/, design/ files not committed. These are project artifacts but have no home in the repo structure. | LOW |
| I-2 | Massive PR (22,772 lines) has no PR description template | The original PR was created but lacks the standard sections. 105 files in one PR is hard to review. | LOW |

## Summary

| Priority | Count | Auto-Fixable |
|----------|-------|-------------|
| HIGH | 1 | 1 (DOC-3: README update) |
| MEDIUM | 2 | 1 (DOC-5: OpenCode plugin update) |
| LOW | 2 | 0 |
| **Total (new)** | **5** | **2 auto-fixable** |
| **Grand Total** | **71** | |
