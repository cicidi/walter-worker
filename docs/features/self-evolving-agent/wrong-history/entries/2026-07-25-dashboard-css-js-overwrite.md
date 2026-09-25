---
date: 2026-07-25
session_id: 3a3b321b
severity: critical
category: tool-use
tags: [write-tool, file-overwrite, dashboard, frontend-regression, silent-failure]
---

# Dashboard CSS/JS silently overwritten by Write tool

**What happened:** In commit `6d3a3dc`, the dashboard CSS was reduced from 420 to 177 lines and JS from 531 to ~199 lines. The Write tool was used to create "new" files instead of Edit tool to surgically modify existing files. This silently removed: `.lexpand`/`.lexpand.open` expandable row CSS, `.tab-bar`/`.tbtn` tab styles, `expRow()`/`toggleExp()` expand functions, `goBack()` navigation, `startAR()` auto-refresh, full `viewSession()` detail view, and helper functions (`fmtNum`, `fmtTime`, `trunc`, `escHtml`, `shortId`, `ideIconHtml`). The dashboard still loaded (no JS errors), but all advanced functionality was gone.

**Root cause:** Using Write tool on existing files replaces ALL content. The mental model was "add new feature" but the tool action was "replace entire file." The `6d3a3dc` commit was focused on adding Evolution page features; the CSS/JS changes were treated as "create new styles" rather than "append to existing styles."

**How it was discovered:** User report — "dashboard 之前我是有expand ，每一都能expand一个扩展页面，展示细节 ，怎么现在全没了"

**Impact:** All expandable row functionality, session detail view richness, and auto-refresh were broken for ~3 commits. Required full file restoration from git history and surgical re-application of new features. Approx 30 min to diagnose and fix.

**Fix:** Restored original CSS from `e86741d` (420 lines) and JS from `e86741d` (531 lines). Then used Edit tool to surgically add new loader functions (`loadEvolution`, `loadHotspots`, `loadErrors`, `loadMemory`, `loadCost`, `loadEfficiency`, `loadQuality`) and new CSS classes (`.tag-auto`, `.tag-manual`, `.btn`, `.btn-primary`, `.btn-warning`). Final: CSS 442 lines, JS 560 lines.

**Prevention rule:** **NEVER use Write tool on files that already exist in the repository.** Always use Edit tool with `old_string`/`new_string` for modifications to existing files. Write tool is ONLY for creating brand-new files that have never been committed.

**Anti-pattern:** "I'm adding new functionality, so I'll write a new version of this file" — this treats the file as a greenfield even though it has accumulated value. Think of existing files as "append/modify only" territory.

**Related entries:** _(none yet — this is the first entry)_

**Auto-worker lesson:** The auto-worker's backend-only checks (API responses, test results) are blind to frontend regressions. Added to auto-worker: `git diff --stat` check for files with >50% line reduction, and JS function count check (`grep -c "function "`).
