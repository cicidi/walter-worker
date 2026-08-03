---
name: initiative-deactivate
version: 0.2.0
description: Deactivate the current active initiative
triggers:
- initiative-deactivate
when-to-use: When user needs to deactivate the current active initiative
license: MIT
compatibility: claude-code,opencode,gemini
---

# initiative-deactivate

Deactivate the current active initiative.

## Usage

```bash
coworker initiative deactivate
```

## What it does

When the user invokes this skill:

1. **Read current `CLAUDE.local.md`** — find the active initiative block
2. **Remove the initiative block** — delete everything from `<!-- INITIATIVE:<name> START -->` through the initiative section
3. **Preserve the rest** — keep `## Reference Docs`, `## Current Task State`, `## Current Workflow`, `## Personal Preferences` sections, resetting them to empty state
4. **Confirm** — tell user the status bar will no longer show the initiative

## Change Log

| Date | Change |
|------|--------|
| 2026-07-08 | Initial creation |
| 2026-08-01 | Added status bar tag removal logic |
