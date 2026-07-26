# Wrong History — Index

> **Purpose:** Prevent repeating past mistakes.
> **Check before coding:** `grep -rl "<keyword>" docs/self-evolving-agent/wrong-history/entries/`

## Entries by Severity

### Critical
| Date | Entry | Category | Prevention Rule |
|------|-------|----------|-----------------|
| 2026-07-25 | [Dashboard CSS/JS overwritten by Write tool](entries/2026-07-25-dashboard-css-js-overwrite.md) | tool-use | Never use Write on existing files; always use Edit |
| 2026-07-25 | [Dashboard INIT call overwritten during Edit](entries/2026-07-25-dashboard-init-call-lost.md) | tool-use | Verify tail -3 after end-of-file edits |

## Stats

- **Total entries:** 2
- **Critical:** 2
