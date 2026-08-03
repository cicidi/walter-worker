---
name: data-validation
version: 0.1.0
description: "Systematic dashboard data validation — trace every displayed metric from source to screen. Never trust quantity; verify correctness against the ultimate source of truth."
triggers:
  - "data validation"
  - "validate data"
  - "verify dashboard"
  - "data quality"
when-to-use: "Use when verifying dashboard data correctness or investigating data discrepancies."
---

# Data Validation — 数据溯源验证

> **"If you haven't traced it to the source, you haven't validated it."**

## The Problem

Dashboard health checks typically verify **presence** ("API returns data") but not **correctness** ("data matches reality"). This creates a dangerous false sense of security — the auto-worker reports all green while the dashboard shows incomplete or wrong data.

## The Methodology

For EVERY data point displayed in the dashboard, follow this 4-step validation:

### Step 1: Metadata — What is this data?

For each metric, document:

| Field | Example |
|-------|---------|
| **Display location** | Dashboard → Initiatives tab → table row 1 |
| **JSON path** | `$.initiative` in `/api/initiatives` response |
| **DB location** | `analytics.db` → `sessions` table → `initiative` column |
| **Raw source** | Git branch name `/home/cicidi/project/walter-worker/.git/HEAD` |
| **Expected value** | `self-evolving-agent` (current branch) |

### Step 2: Trace — Does the source match the DB?

```bash
# Source: git branch
SOURCE=$(git branch --show-current)
echo "Source: $SOURCE"

# DB: what initiatives are stored?
sqlite3 ~/.coworker/analytics/analytics.db \
  "SELECT DISTINCT initiative FROM sessions WHERE initiative != ''"

# Verify: does source appear in DB?
# If NOT → session import is NOT capturing initiative correctly → BUG
```

### Step 3: Display — Does the DB match the API?

```bash
# API: what does the dashboard show?
curl -s http://127.0.0.1:8083/api/initiatives | python3 -c "
import sys,json
data=json.load(sys.stdin)
for d in data:
    print(d['initiative'])
" | sort

# Verify: does SOURCE appear in API output?
# If NOT → query is filtering wrong → BUG
```

### Step 4: Evidence — Record everything

Never claim "verified" without recording:
- The actual source value
- The actual DB query result
- The actual API response
- The comparison that proves they match (or don't)

## Validation Checklist

Run this against EVERY dashboard tab:

| Tab | Data | Source | How to Verify |
|-----|------|--------|---------------|
| Overview | total_sessions | analytics.db COUNT(* ) | Compare with `git log --oneline --all | wc -l`? No — sessions come from IDE imports. Verify: count session files on disk. |
| Projects | project list | analytics.db sessions.project | `ls ~/project/` should roughly match. Missing projects = import bug. |
| Initiatives | initiative list | analytics.db sessions.initiative | `git branch --show-current` should appear if working on a feature branch. |
| Models | model distribution | analytics.db sessions.model | Spot-check: is the current model in the list? |
| Skills | skill list + call count | analytics.db skills + tool_calls | Compare with `~/.coworker/skills/` directory listing. |
| Cost | token/cost data | analytics.db session_stats | Check: is today's session showing cost? If not, import is broken. |
| Evolution | auto-trained skills | `~/.coworker/skills/` + usage.json | Count files with provenance=agent. Should match. |
| Memory | mem0 entry count | mem0.search() | Compare with `ls ~/.coworker/memory/vector/collection/` |
| Errors | tool error count | analytics.db tool_calls | `grep -c "error\|fail"` in recent session transcripts |
| Sessions | session list | analytics.db sessions | `ls ~/.claude/projects/*/` session count should roughly match |

## Anti-Patterns

- ❌ "API returned 5 items, must be OK" — 5 could be wrong if there should be 6
- ❌ "DB has data" — DB data is derived; verify against the raw source
- ❌ "The query looks correct" — run it and check the actual output
- ❌ "I verified this yesterday" — data changes; verify every time
- ✅ For each metric: source → DB → API → display, all must match

## Integration

Run as part of auto-worker health check or manually:

```bash
coworker find-issues --phases data  # includes data validation phase
```
