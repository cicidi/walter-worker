---
name: dashboard
version: 0.1.0
description: |
  Use when viewing analytics, starting the web dashboard, importing session
  data, or managing the analytics daemon. Use when the user asks for
  dashboard, analytics, session stats, or data import.
triggers:
  - dashboard
  - analytics
  - session stats
  - import sessions
  - analytics dashboard
  - show dashboard
  - data import
when-to-use: >
  Use when starting the web analytics dashboard, importing session data
  one-shot or continuously, or checking analytics status and managing
  background daemons.
license: MIT
compatibility: claude-code,opencode
---

# dashboard

Manage the analytics dashboard and session data pipeline. DB is auto-created
on first use — no separate init step needed.

## When to Use

- Starting the web analytics dashboard
- Importing session data (one-shot or continuous)
- Checking analytics status or stopping background daemons

## When NOT to Use

- Searching past session content → use /memory
- Extracting knowledge from sessions → use /knowledge
- Git history or code stats → use git commands directly

## Process

### No subcommand given

Ask the user what they want to do. Present the three options:
1. `start` — launch the web dashboard (optionally with `--daemon` for background auto-import)
2. `import` — one-shot session data import (optionally with `--files` for specific files)
3. `stop` — stop the background daemon

### Subcommands

| Subcommand | Behavior |
|------------|----------|
| `start [--daemon]` | Launch dashboard on http://localhost:8099. With `--daemon`, also start background auto-import every 30 min |
| `import [--files <paths>]` | One-shot scan and import. Without `--files`, scans all unimported sessions across all projects |
| `stop` | Stop the background daemon if running |

### start

```bash
# Dashboard only
coworker analytics dashboard

# Dashboard + background auto-import daemon
coworker analytics dashboard &
coworker analytics daemon
```

Open http://localhost:8099 in a browser after starting. Pages:

- **Overview** — when you work (weekday × hour), totals, and what stands out.
- **Insights** — where tools fail and why, which capabilities you use, how you
  prompt, session shape, tokens and cache.
- **Memory** — whether capture, storage and recall are paying off, plus a
  browser for stored lessons.
- **Sessions**, **Tools and skills**, **Files**, **Projects** — explorers with
  expandable rows.
- **Evolution** — agent-written skills and drafts awaiting review.
- **Data health** — how much of each field is actually recorded.

One filter bar (agent, model, project, time range) drives every page except
Memory, Evolution and Data health.

If the `coworker-dashboard` systemd user service is installed
(`setup/dashboard/`), it already serves 8099 — check with
`systemctl --user is-active coworker-dashboard` and open the URL instead of
starting a second copy, which would fail with "address already in use".

### import

```bash
coworker analytics import  # full scan
# or for specific files — one directory per project, named after its cwd
# with the slashes turned into dashes:
coworker analytics import --files ~/.claude/projects/-home-you-project-myapp/*.jsonl
```

Imports Claude Code sessions from `~/.claude/projects/` and OpenCode sessions
from `~/.local/share/opencode/opencode.db`. Only imports sessions not already
in analytics.db. Auto-detects the feature name from CLAUDE.local.md or
branch name.

### stop

```bash
pkill -f "coworker analytics daemon"
```
