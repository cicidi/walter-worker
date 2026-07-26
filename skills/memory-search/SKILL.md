---
name: memory-search
description: Search the agent's cross-session memory for past lessons, patterns, and conventions stored in mem0
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
