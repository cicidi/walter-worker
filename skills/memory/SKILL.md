---
name: memory
version: 0.1.0
description: |
  Use when searching past session memories, knowledge cards, or the code
  knowledge graph. Use when the user asks to search memory, recall past work,
  find related sessions, or query what was learned. Wraps `coworker memory query`.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - search memory
    - memory search
    - recall
    - what did we learn
    - find past session
    - knowledge graph
    - memory query
---

# memory

Search the memory graph and session memories via `coworker memory query`.

## When to Use

- Searching past session summaries for what was learned or decided
- Finding knowledge cards related to a topic or initiative
- Querying the code knowledge graph for relevant files or functions
- Recalling past work before starting a related task

## When NOT to Use

- Extracting new memories from sessions → use /knowledge
- Searching git history → use git log directly
- Searching the web → use web search

## Process

### Step 1: If no query given

Ask the user what they want to search for. Be specific — a few keywords
or a short question works best.

### Step 2: Run the query

```bash
coworker memory query "<user's question>" --mode both --top-k 30
```

**Mode options:**
- `--mode both` (default) — search both the code graph AND session memories
- `--mode graph` — code structure only (functions, files, modules)
- `--mode vector` — session memories only (summaries, knowledge cards)

**Tuning:**
- `--top-k 20` — fewer results, faster
- `--top-k 50` — more results, for thorough searches
- `--min-score 0.5` — stricter relevance filter
- `--budget 4000` — more context per result

### Step 3: Interpret results

The command outputs two tables:
- 🔗 Knowledge Graph — code nodes (functions, files, modules) with
  labels, types, source files, and path weights
- 🧠 Session Memory — memory cards from past sessions with content,
  type, and relevance score

Synthesize what was found and present it clearly to the user.

### stats — Memory graph overview

When the user asks about memory stats or health:

```bash
coworker memory stats
```

Shows: node count by type, edge count by relation, provenance, and edge
health (normal/stale/suppressed).
