---
date: 2026-07-28
session_id: 
severity: critical
category: code-quality
tags: []
---

# file_ops table accumulated 47,933 duplicates (96%) due to missing UNIQUE constraint

**What happened:** Analytics daemon re-imports sessions every 30min. file_ops had INSERT OR IGNORE but no UNIQUE constraint. Each import added duplicates. Session a3d923aa had 890 rows for 17 actual reads (53x inflation). Total DB had 50,012 rows, only 2,079 were real.

**Root cause:** No UNIQUE constraint on file_ops(session_id, call_id, op, path). INSERT OR IGNORE is a no-op without a constraint. Same pattern as wrong-history entries #1 and #2: checking API returns OK ≠ data is correct.

**How it was discovered:** auto-worker health check

**Impact:** Unknown — auto-detected

**Fix:** Added UNIQUE index on (session_id, call_id, op, path). Import now DELETEs old file_ops before re-import. Cleaned up 47,933 duplicate rows.

**Prevention rule:** Every table that uses INSERT OR IGNORE MUST have a UNIQUE constraint. Never assume INSERT OR IGNORE prevents duplicates — check the schema first.

**Anti-pattern:** Not following the prevention rule above

**Related entries:** [[2026-07-27-dashboard-data-not-verified]] — same pattern: trusting API 200 without verifying data correctness. [[2026-07-25-dashboard-css-js-overwrite]] — same category: INSERT/Write without verifying constraints.
