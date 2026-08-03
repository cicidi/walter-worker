---
name: dashboard
description: |
  Use when viewing analytics, starting the web dashboard, importing session
  data, or managing the analytics daemon. Use when the user asks for
  dashboard, analytics, session stats, or data import.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - dashboard
    - analytics
    - session stats
    - import sessions
    - analytics dashboard
    - show dashboard
    - data import
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
| `start [--daemon]` | Launch dashboard on http://localhost:8080. With `--daemon`, also start background auto-import every 30 min |
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

The dashboard shows: session counts by project/initiative, tool usage,
model costs, skill evolution, and knowledge cards. Open http://localhost:8080
in a browser after starting.

### import

```bash
coworker analytics import  # full scan
# or for specific files:
coworker analytics import --files ~/.claude/projects/-home-cicidi-project-skill-factory/*.jsonl
```

Imports Claude Code sessions from `~/.claude/projects/` and OpenCode sessions
from `~/.local/share/opencode/opencode.db`. Only imports sessions not already
in analytics.db. Auto-detects the initiative name from CLAUDE.local.md or
branch name.

### stop

```bash
pkill -f "coworker analytics daemon"
```
