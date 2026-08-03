---
date: 2026-07-27
session_id: 3a3b321b
severity: critical
category: testing
tags: [data-validation, dashboard, source-of-truth, verification-methodology]
---

# Dashboard data was present but WRONG — never validated against source of truth

**What happened:** The auto-worker checked 37 dashboard API endpoints and reported "all OK" because every endpoint returned non-empty data. But the Initiatives tab showed 5 initiatives, and **`self-evolving-agent` was NOT among them** — despite this entire session running on the `feat/self-evolving-agent` branch. 0 sessions in analytics.db had `initiative='self-evolving-agent'` because the session import pipeline doesn't auto-detect initiative from git branch names.

**Root cause:** I verified data **quantity** ("API returns 5 items ✅") but never verified data **correctness** ("should it be 6? is the data accurate?"). The verification methodology was:
1. Call API endpoint
2. Check response is non-empty
3. Claim "OK"

What it should have been:
1. Call API endpoint
2. Identify the **ultimate source of truth** for each data point
3. Trace from display → API → DB → raw source
4. Verify data matches expectations derived from the source
5. Only then claim "OK"

**How it was discovered:** User manually inspected dashboard and noticed the initiative for the current branch was missing.

**Impact:** Dashboard displayed incomplete initiative data for 56+ hours of autonomous operation. The auto-worker's health checks were systematically blind to data quality issues. This is the same pattern as DQ-1 (28% project coverage flagged as "healthy").

**Fix:** 
1. Added `initiative` auto-detection from git branch to session import
2. Created `skills/data-validation/SKILL.md` — systematic methodology for tracing data from source to display
3. Updated auto-worker health check to include data correctness verification, not just data presence

**Prevention rule:** **Never claim dashboard data is "OK" just because API returns non-empty.** For EVERY dashboard metric, trace back to the ultimate source of truth and verify against it. Quantity ≠ quality. Presence ≠ correctness.

**The methodology:**
1. **Metadata**: Identify what the data is, where it's displayed (page/tab/position), what API endpoint serves it, what DB table/column stores it, what the RAW source is (session files, git config, env vars)
2. **Trace**: Calculate expected value from raw source. Extract from raw source. Compare against DB intermediate. Verify they match.
3. **Display**: Verify the displayed value matches the DB value. Screenshot or text-capture the rendered output.
4. **Evidence**: Record every step with actual values. Never fabricate.

**Related entries:** [[2026-07-25-dashboard-css-js-overwrite]] — same root category (dashboard verification failure), [[2026-07-25-dashboard-init-call-lost]] — same pattern of "looks OK but isn't"
