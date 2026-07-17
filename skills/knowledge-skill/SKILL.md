---
name: knowledge-skill
version: 0.1.0
description: Reads session data from analytics.db, feeds to LLM for structured analysis, writes session summaries and knowledge
  cards back to SQLite.
triggers:
- analyze this session
- summarize what i did
- generate knowledge cards
- summarize session
- analyze today sessions
- run knowledge skill
when-to-use: 'After completing a session to extract insights.

  Periodic batch analysis of recent sessions.'
license: MIT
compatibility: claude-code,opencode
user-invocable: true
---
# knowledge-skill

Reads session data from analytics.db, sends to LLM for structured analysis,
writes back session_summaries and knowledge cards.

## Process

### Step 1: Load session data

Run `coworker knowledge summarize <session_id>` which:
1. Reads messages + tool_calls from analytics.db
2. Formats as structured prompt
3. Sends to LLM (uses current model)
4. Writes result to session_summaries + knowledge tables

### Step 2: Generate session summary

Prompt template instructs LLM to produce:
- SOP workflows discovered
- Context to remember for next session
- Effective operations that worked well
- Pitfalls and fixes (what failed, what solved it)
- Wasted actions (loops, dead ends)
- Bottlenecks (longest think times, repetitive calls)
- One efficiency tip
- Memory keywords for Obsidian graph

### Step 3: Generate knowledge cards

For patterns recurring across >=2 sessions, generate knowledge cards:
- Type: trap, best_practice, pattern, decision, constraint
- Title, summary, evidence, related skills
- Write to knowledge table

### Step 4: Batch mode

`coworker knowledge analyze --since yesterday`
`coworker knowledge analyze --all`
