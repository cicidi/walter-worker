# Dashboard UI — PRD

> Initiative: self-evolving-agent | Type: PRD | Status: draft v1.0 | Date: 2026-07-28

## 1. Overview

Analytics dashboard for ai-coworker. Displays session data, skill usage, tool metrics,
cost analytics, memory health, and self-evolution metrics.

**Current state:** v2 redesign deployed (3-tab nav), partially complete.

---

## 2. Requirements

### R1: Information Architecture — 3-Tab Top Nav

| Tab | Sub-nav items |
|-----|--------------|
| Activity | Summary, Sessions, Files (with Hotspots toggle) |
| Insights | Usage (Skills+Tools+Models), Cost, Quality, Knowledge |
| System | Health, Errors, Evolution (lazy load) |

**Status:**
- [x] 3-tab bar renders
- [x] Sub-nav switches per tab
- [x] "FilesHotspots" display bug — fixed (shows "📁 Files ↻" with toggle hint)
- [x] Tab bar visual distinction — fixed (gap 8px, border-bottom, larger padding)
- [ ] Evolution lazy loading (mem0 dependency isolation)

### R2: Info Tooltips — Every Number Explained

Every stat card value and table header must have a clickable ℹ icon.
Clicking shows a tooltip card with:
- **Name**: What is this metric?
- **Description**: What does it mean?
- **Source**: Which API endpoint / DB table / SQL query produces it?
- **Purpose**: Why is this shown? What action should the user take?

**Status:**
- [x] ℹ icons render on Summary stat cards
- [x] INFO_MAP dictionary exists
- [x] INFO_MAP expanded to cover summary, sessions, projects, health, errors, cost, quality
- [x] Table headers have ℹ icons (via enrichContent)
- [x] Tooltip fallback shows human-readable text instead of raw keys
- [ ] Tooltip positioning: below-right preferred, flip to above-left near viewport edge
- [ ] Click-away dismissal
- [ ] Some pages still use fallback (add more entries to INFO_MAP)

### R3: Skill Detail Page — Content + Review

When clicking a skill in Evolution, show:
- Skill metadata (source, status, calls, sessions, reuse rate)
- Full SKILL.md content rendered as **markdown preview** (not monospace)
- Description and When-to-Use extracted from frontmatter
- If status is "pending": Approve / Reject buttons
- Session IDs where skill was invoked

**Status:**
- [x] SKILL.md content displayed
- [x] Markdown preview renderer (renderMd)
- [x] Approve/Reject buttons for pending skills
- [ ] Description and When-to-Use sometimes empty (frontmatter key format mismatch: `when_to_use` vs `when-to-use`)
- [ ] Approve/Reject buttons don't show for pending skills that were auto-promoted (state was "active" not "pending" before fix)

### R4: Data Correctness — No Broken Pages

All pages must display correct data. Zero tolerance for field name mismatches.

**Bugs found and fixed:**
- [x] Projects page: 6 field name mismatches (project→project_name, sessions→session_count, etc.)
- [x] Errors page: API returned flat array, JS expected `d.tool_errors`
- [x] Memory page: JS expected mem0 fields, API returned skills/knowledge/summaries counts
- [x] Hotspots page: File column empty (f.file_path→f.path), missing columns added
- [x] Sessions count: hardcoded limit 500, DB had 569 (→2000)

**Ongoing concerns:**
- [ ] Models page uses `model_group` but Cost page uses `model` — same concept, different field name
- [ ] Skills page `last_invoked` vs Evolution page `last_used` — same concept
- [ ] `total_sessions` vs `session_count` vs `sessions` — three names for same concept across APIs
- [ ] `active_sessions` means different things in `/api/overview` vs `/api/activity`

### R5: No Duplicate Data Display

**Duplications to eliminate:**
- [ ] Skills stats appear on both Skills page and Evolution page → single source in Insights > Usage
- [ ] File operations appear on both Files page and Hotspots page → merge as Files page with Hotspots toggle
- [ ] Project coverage on Overview + Data Quality → move coverage to Data Quality only
- [ ] `/api/tools` + `/api/tool-detail` → `/api/tool-detail` is superset, merge

**API merges pending (from data audit):**
- [x] `/api/errors` + `/api/session-errors` → merged
- [ ] `/api/skills` + `/api/evolution/skills` → unify
- [ ] `/api/tools` + `/api/tool-detail` → unify
- [ ] `/api/hotspots` + `/api/top-files` + `/api/file-stats` → `/api/files/stats`
- [ ] `/api/cost-analytics` + `/api/models` + `/api/model-usage` → unified `/api/models`
- [ ] `/api/memory-stats` + `/api/data-quality` → `/api/quality`
- [ ] `/api/daily-sessions` merge into `/api/overview`

### R6: Panel-Level Resilience

Each panel loads independently. One panel failure must not break other panels.

**Status:**
- [ ] Panel Dispatcher not implemented — pages still use single try/catch
- [ ] Skeleton loading: ✅ renders on navigate, but not per-panel
- [ ] Per-panel retry button: ❌ not implemented
- [ ] Per-panel timeout (10s): ❌ not implemented

### R7: Database Integrity

Tables that use `INSERT OR IGNORE` must have UNIQUE constraints.

**Status:**
- [x] file_ops: UNIQUE on (session_id, call_id, op, path)
- [x] messages: UNIQUE on (session_id, seq)
- [x] tool_calls: UNIQUE on (session_id, call_id)
- [x] Duplicate data cleaned: 55,204 rows removed across 3 tables
- [x] file_ops import: DELETE before re-import
- [ ] messages/tool_calls import: still use INSERT OR IGNORE without cleanup (safer but needs monitoring)

### R8: Skill Installation

Project skills in `skills/` directory must be installed to `.claude/commands/`.

**Status:**
- [x] 30 missing skills installed to `.claude/commands/`
- [x] `coworker init` auto-discovers and installs project skills
- [x] `ai-coworker-upgrade` Phase 4 includes skill installation step
- [x] `_promote_to_active()` installs to `~/.claude/commands/`

### R9: Wrong-History Auto-Creation

Auto-worker must create wrong-history entries when fixing bugs.

**Status:**
- [x] `record_entry()` function in wrong_history.py
- [x] `coworker memory wrong-history record` CLI command
- [x] Engine agents instructed to record after fixes
- [x] INDEX.md auto-rebuilt after new entries
- [x] 5 total entries (2 auto-created this session)

### R10: Responsive Design

Dashboard must work at 1024px+.

**Status:**
- [ ] No responsive breakpoints implemented
- [ ] Sidebar doesn't collapse at smaller widths
- [ ] Tables don't have horizontal scroll at narrow widths
- [ ] Stat grid doesn't adapt column count

---

## 3. Current Issues (from Audit)

### Visual
1. **"FilesHotspots" mashed together** — sub-nav item needs separator or toggle indicator
2. **Tab bar visual** — "◉ Activity◎ Insights⚙ System" runs together, needs spacing/separators
3. **Tab bar uses radio-button style** — should look like tabs with bottom border indicator
4. **Stat card tooltips show raw keys** — e.g. "overview.total_sessions" instead of "Total Sessions"
5. **No page subtitle** on some pages — inconsistent metadata display

### Functional
6. **Evolution page hangs** when mem0 is unreachable (blocks entire page)
7. **No breadcrumb** — can't see where you are in drill-down hierarchy
8. **Session detail shows "0 events"** for sessions without timeline data — should show message count at minimum
9. **No search/filter** on Skills, Tools, Knowledge pages
10. **Auto-refresh only on Summary** — other pages don't auto-refresh

### Data Quality
11. **Skills: 35 disk vs 28 DB** — project-local skills not in DB (by design but unclear)
12. **Summaries: 9.3% coverage** — needs `coworker memory train` call-to-action
13. **Model names stored as raw JSON** from OpenCode — should normalize

---

## 4. Implementation Priority

| Priority | Item | Effort |
|----------|------|--------|
| P0 | Fix "FilesHotspots" display bug | S | ✅ done |
| P0 | Fix tab bar visual distinction | S | ✅ done |
| P0 | Fix tooltip raw key display | S | ✅ done |
| P1 | Evolution lazy load (mem0 isolation) | M |
| P1 | Panel Dispatcher with retry | M |
| P1 | Complete INFO_MAP for all metrics | M |
| P2 | Breadcrumb navigation | M |
| P2 | API field name standardization | L |
| P2 | API merges (M1-M8 from audit) | L |
| P3 | Responsive breakpoints | M |
| P3 | Session River visualization | L |
| P3 | Search/filter on list pages | M |

---

## 5. Non-Goals (for v2)

- Mobile support (< 768px)
- Real-time WebSocket updates
- Dark/light theme toggle
- Export to CSV/PDF
- User authentication / multi-tenant
