---
name: wrong-history
version: 0.1.0
description: Use when you made a mistake that you want to record so it never happens again. Also use BEFORE starting any significant code change to check past mistakes.
triggers:
  - "wrong history"
  - mistake
  - "record this"
when-to-use: "Use after making a mistake or before starting a significant code change."
---

# Wrong History

> **"Those who cannot remember the past are condemned to repeat it."** — George Santayana

Records development mistakes so the agent learns from them across sessions.

## When to Use

1. **AFTER** discovering a bug caused by your own action → record it
2. **AFTER** a user correction that reveals a pattern worth preventing → record it  
3. **AFTER** noticing you repeated a past mistake → record it AND link to prior entry
4. **BEFORE** starting any significant code change → check for relevant past mistakes

## How to Record

Write a new entry to `docs/self-evolving-agent/wrong-history/entries/{date}-{slug}.md`:

```markdown
---
date: YYYY-MM-DD
session_id: <current-session-id>
severity: critical | high | medium | low
category: tool-use | code-quality | process | communication | design
tags: [tag1, tag2]
---

# <one-line summary>

**What happened:** <what went wrong — concrete, specific>

**Root cause:** <why it happened — the thinking error, not just the action>

**How it was discovered:** <user report | test failure | visual inspection | etc.>

**Impact:** <what was broken, how long to fix>

**Fix:** <what was done to resolve it>

**Prevention rule:** <ONE clear, actionable rule that would have prevented this>

**Anti-pattern:** <the thinking pattern to avoid>

**Related entries:** <links to similar past mistakes if any>
```

## How to Check

Before starting any code change that modifies existing files:

1. Run: `ls docs/self-evolving-agent/wrong-history/entries/ | tail -20`
2. Grep for relevant keywords: `grep -rl "<keyword>" docs/self-evolving-agent/wrong-history/entries/`
3. If any entry matches your current situation → read it and apply the prevention rule

## Automation

The auto-worker checks `docs/self-evolving-agent/wrong-history/entries/` for:
- Entries with severity=critical → enforce as hard rules
- Entries with category matching current task → warn before action
- Recurring tags → escalate to skill update

## Index

See `docs/self-evolving-agent/wrong-history/INDEX.md` for the full list.
