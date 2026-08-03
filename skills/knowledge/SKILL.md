---
name: knowledge
description: |
  Use when extracting structured knowledge from past sessions — summarizes
  conversations into memory cards (Obsidian vault) or knowledge cards
  (SQLite analytics). Use when the user asks to summarize sessions, extract
  patterns, or build a searchable knowledge base from agent history.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - knowledge
    - summarize sessions
    - extract memory
    - scan session history
    - build knowledge graph from conversations
    - session memory
    - knowledge card
    - analyze sessions
    - what did we learn
---

# knowledge

Two-branch skill for extracting structured knowledge from past sessions.
One writes Markdown memory cards to an Obsidian vault. The other writes
structured summaries and cross-session knowledge cards to SQLite analytics.

## When to Use

- Summarizing completed sessions into reusable memory cards
- Building a searchable knowledge base from agent conversation history
- Extracting patterns, decisions, and lessons across multiple sessions
- Generating knowledge cards for patterns that recur across 2+ sessions

## When NOT to Use

- Searching existing memories → use /memory
- Recording a single correction → use /bug heal
- Real-time session tracking → analytics daemon handles that

## Process

### Step 0: Determine Branch

Ask the user ONE question:

> "Where should the knowledge go?"
> - **Obsidian vault** — Markdown memory cards in `~/obsidian/coworker-brain/` (local, private)
> - **SQLite analytics** — structured summaries + knowledge cards in `analytics.db` (cross-session patterns)

---

## Branch A: Obsidian Vault — Memory Cards

Extract conversation content and write markdown cards to the Obsidian vault.
ALL processing runs locally via Ollama — no session content leaves the machine.

### Steps

1. **Connect** — open `~/.coworker/analytics/analytics.db`, identify sessions not yet summarized
2. **Extract** — for each unprocessed session, pull messages from the `message` table ordered by time
3. **Summarize** — send extracted content to a local Ollama model with a structured JSON prompt:
   - Fields: title, summary, key_decisions, lessons_learned, projects, skills_used, tags, confidence
4. **Write Card** — generate Obsidian Markdown with frontmatter, `[[wikilinks]]`, and a metrics table. Skip thin sessions (< 3 messages) and active sessions
5. **Update Index** — regenerate `Session Memory Index.md`
6. **Report** — count processed, skipped, confidence distribution

**Hard requirement:** NEVER send session content to remote APIs. Local Ollama only.

---

## Branch B: SQLite Analytics — Knowledge Cards

Read session data, feed to LLM for structured analysis, write back to
`session_summaries` and `knowledge` tables. Supports batch mode.

### Single Session

```bash
coworker knowledge summarize <session_id>
```

Reads messages + tool_calls from analytics.db → LLM analysis → writes to:
- `session_summaries`: SOP workflows, context to remember, effective ops,
  pitfalls, wasted actions, bottlenecks, efficiency tip, memory keywords
- `knowledge`: only when patterns recur across 2+ sessions — type
  (trap/best_practice/pattern/decision/constraint), title, summary, evidence

### Batch Mode

```bash
coworker knowledge analyze --since yesterday
coworker knowledge analyze --since "2026-07-01"
coworker knowledge analyze --all
```

Processes all matching sessions. Cross-session pattern detection generates
knowledge cards only when a pattern appears in 2+ sessions.
