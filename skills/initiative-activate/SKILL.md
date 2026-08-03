---
name: initiative-activate
version: 0.2.0
description: Activate an initiative and inject its context into IDE configs
triggers:
- initiative-activate
when-to-use: When user needs to activate an initiative and inject its context into ide configs
license: MIT
compatibility: claude-code,opencode,gemini
---

# initiative-activate

Activate an initiative and inject its context into IDE configs.

## Usage

```bash
coworker initiative activate
```
or `/initiative-activate <initiative-name / description>`

## What it does

When the user invokes this skill:

1. **Identify the initiative** — from project `docs/initiatives/<name>/` or user-provided description
2. **Read initiative files** — `*-spec.md` and `*-plan.md` in the initiative directory
3. **Update `CLAUDE.local.md`** in the project root with:
   - An `## Active Initiative: <name>` section
   - Project scope, key decisions, reference docs, task state
   - **CRITICAL**: Insert `<!-- INITIATIVE:<name> START -->` as the first line of the initiative block. This HTML comment tag is parsed by the Claude Code status bar script (`~/.claude/statusline-command.sh`) to display the active initiative name in the status line. Without this tag, the status bar will not show the initiative.
   - Format:
     ```
     <!-- INITIATIVE:<name> START -->
     ## Active Initiative: <name>
     > <one-line description>
     ...
     ```
4. **Update initiative spec/plan files** — fill in overview, requirements, design, tasks if they were empty templates
5. **Confirm** the user sees the updated status bar

## Status Bar Integration

The Claude Code status bar (line 1) displays the active initiative via `🎯 initiative: <name>`. This relies on the exact HTML comment tag:

```
<!-- INITIATIVE:<name> START -->
```

The status bar script (`~/.claude/statusline-command.sh`, line 281) uses:
```bash
sed -n 's/.*<!--\s*INITIATIVE:\([^ ]*\)\s*START\s*-->.*/\1/p' CLAUDE.local.md
```

If this tag is missing or malformed, the initiative will NOT appear in the status bar.

## Change Log

| Date | Change |
|------|--------|
| 2026-07-08 | Initial creation |
| 2026-08-01 | Added status bar tag requirement (`<!-- INITIATIVE:...START -->`) |
