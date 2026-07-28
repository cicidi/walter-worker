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

Search long-term memory. Two sources:

| Source | Command | What it finds |
|--------|---------|--------------|
| **Mem0** (vector) | `/memory-search <query>` | Past session lessons, patterns, conventions |
| **Graph** (structure) | `coworker memory query "<query>"` | Code structure, file relationships, knowledge graph nodes |

The graph maps your project's code + docs into 2,595 nodes × 5,126 edges.
Use it to find: which files relate to a feature, what calls what, architecture patterns.

**Always try both** when researching a problem — graph gives structure, mem0 gives experience.

## Usage

```
/memory-search <query>
coworker memory query "<query>"
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
