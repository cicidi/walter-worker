---
name: analytics-once
version: 0.1.0
description: Import new sessions once — scans for unimported Claude Code and OpenCode sessions
triggers:
- analytics-once
- import sessions once
- check for new sessions
when-to-use: When user wants to import sessions without running the daemon
license: MIT
compatibility: claude-code,opencode,gemini
user-invocable: true
---
# analytics-once

Import new sessions from Claude Code and OpenCode into the analytics database.

## Usage

```bash
coworker analytics once
```

Scan for new sessions and import only those not yet in analytics.db.
Write checkpoint so the same sessions are not imported again.
