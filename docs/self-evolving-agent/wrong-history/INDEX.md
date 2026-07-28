# Wrong History — Index

> **Purpose:** Prevent repeating past mistakes.
> **Check before coding:** `grep -rl "<keyword>" docs/self-evolving-agent/wrong-history/entries/`

## 🔴 Critical
| Date | Entry | Category | Prevention Rule |
|------|-------|----------|-----------------|
| 2026-07-27 | [Dashboard data was present but WRONG — never validated against source of truth](entries/2026-07-27-dashboard-data-not-verified.md) | testing | **Never claim dashboard data is "OK" just because API returns non-empty.** For E... |
| 2026-07-25 | [Dashboard INIT call overwritten during Edit insertion](entries/2026-07-25-dashboard-init-call-lost.md) | tool-use | When using Edit tool to insert code at the end of a file, ALWAYS verify that the... |
| 2026-07-25 | [Dashboard CSS/JS silently overwritten by Write tool](entries/2026-07-25-dashboard-css-js-overwrite.md) | tool-use | **NEVER use Write tool on files that already exist in the repository.** Always u... |

## Stats
- **Total entries:** 3
- **🔴 Critical:** 3
