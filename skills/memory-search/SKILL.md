---
name: memory-search
version: 0.1.0
description: Search the agent's cross-session memory for past lessons, patterns, and conventions stored in mem0
triggers:
  - "memory search"
  - "search memory"
  - recall
when-to-use: "Use when searching for past lessons or checking if a pattern was encountered before."
---

# Memory Search

Search the agent's long-term memory for past lessons, patterns, and conventions.

## Usage

```
/memory-search <query>
```

Or:

```
coworker memory search "<query>" --project ai-coworker --limit 10
```

## Implementation

Runs `coworker memory search --query "<query>"` and returns results from the mem0 vector store. Results include the memory text, type (lesson/convention/preference), topic, and state (active/stale/archived).

## Related

- `coworker memory refresh` — Refresh the CLAUDE.local.md memory snapshot
- `coworker memory train` — Batch-train mem0 from past sessions
- `coworker memory sync` — Per-turn capture (called automatically by hooks)
- `coworker memory close` — Session-end reconciliation (called automatically by hooks)
