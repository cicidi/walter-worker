# Wrong History — Index

> **Purpose:** Prevent repeating past mistakes.
> **Check before coding:** `grep -rl "<keyword>" docs/self-evolving-agent/wrong-history/entries/`

## 🔴 Critical
| Date | Entry | Category | Prevention Rule |
|------|-------|----------|-----------------|
| 2026-07-28 | [file_ops table accumulated 47,933 duplicates (96%) due to missing UNIQUE constraint](entries/2026-07-28-file_ops-table-accumulated-47,933-duplicates-(96%)-due-to-mi.md) | code-quality | Every table that uses INSERT OR IGNORE MUST have a UNIQUE constraint. Never assu... |
| 2026-07-27 | [Dashboard data was present but WRONG — never validated against source of truth](entries/2026-07-27-dashboard-data-not-verified.md) | testing | **Never claim dashboard data is "OK" just because API returns non-empty.** For E... |
| 2026-07-25 | [Dashboard INIT call overwritten during Edit insertion](entries/2026-07-25-dashboard-init-call-lost.md) | tool-use | When using Edit tool to insert code at the end of a file, ALWAYS verify that the... |
| 2026-07-25 | [Dashboard CSS/JS silently overwritten by Write tool](entries/2026-07-25-dashboard-css-js-overwrite.md) | tool-use | **NEVER use Write tool on files that already exist in the repository.** Always u... |

## 🟡 High
| Date | Entry | Category | Prevention Rule |
|------|-------|----------|-----------------|
| 2026-07-28 | [find-issues command always fails on code phase due to 120s test timeout](entries/2026-07-28-find-issues-command-always-fails-on-code-phase-due-to-120s-t.md) | code-quality | When running subprocess for full test suite, timeout must be >= 600s (tests take... |
| 2026-07-27 | [Adversarial review PRO agent surrendered 12/12 — missed a HIGH bug](entries/2026-07-27-adversarial-review-pro-agent-must-not-surrender.md) | process | In con/pro/judge review, PRO MUST search counter-evidence & attempt to REFUTE each... |

## Stats
- **Total entries:** 6
- **🔴 Critical:** 4
- **🟡 High:** 2
