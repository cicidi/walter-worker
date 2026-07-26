---
date: 2026-07-25
session_id: 3a3b321b
severity: critical
category: tool-use
tags: [edit-tool, insertion-error, dashboard, blank-page, silent-failure]
---

# Dashboard INIT call overwritten during Edit insertion

**What happened:** When using Edit tool to insert new loader functions before `// INIT` at the end of dashboard.js, the original initialization call (`renderSidebar();loadOverview();startAR('overview',15000);`) was replaced with just `// INIT` — no code after it. This caused the dashboard to show a completely blank page because the sidebar never rendered and loadOverview() was never called. No JS errors in console — the page was syntactically valid but logically dead.

**Root cause:** The Edit tool matched on `old_string` that included the init call, and the `new_string` was the new loader functions followed by `// INIT` — but the init call was accidentally omitted from `new_string`. The auto-worker's JS function-count check detected function definitions were present, but didn't check that the initialization CALL was present.

**How it was discovered:** User reported "dashboard 现在什么都不显示了" after multiple rounds of CSS/JS fixes. Manual inspection of `tail -5 dashboard.js` revealed the missing init call.

**Impact:** Dashboard completely non-functional for ~1 hour. Required manual inspection to find and fix.

**Fix:** Appended `renderSidebar();loadOverview();startAR('overview',15000);` after `// INIT` on the last line.

**Prevention rule:** When using Edit tool to insert code at the end of a file, ALWAYS verify that the original last-line initialization/call is preserved. Check with `tail -3 <file>` after every edit.

**Related entries:** [[2026-07-25-dashboard-css-js-overwrite]] — same root cause category (tool-use error on dashboard files)
