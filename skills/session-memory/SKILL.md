---
name: session-memory
version: 0.1.0
description: Use when summarizing past opencode sessions into structured memory cards for both AI context reuse and personal
  knowledge management. Use when the user asks to "summarize sessions", "extract memory", "scan session history", or "build
  knowledge graph from conversations". Periodically runs batch extraction from opencode.db, feeds session content through
  a local LLM, and writes Markdown memory cards to the Obsidian vault.
triggers:
- summarize sessions
- extract memory
- scan session history
- build knowledge graph
- session memory
- organize memory
- archive sessions
when-to-use: Periodic batch summarization of completed opencode sessions. Building a searchable knowledge base from agent
  conversation history. Extracting reusable patterns, decisions, and lessons from past work. Feeding AI context into future
  sessions.
license: MIT
compatibility: opencode
user-invocable: true
---
# ai-coworker-session-memory

Extracts structured memory cards from opencode session history using a local LLM. Each memory card captures the essence of a session for both AI retrieval and human review in Obsidian.

## Philosophy

Agent sessions generate valuable context that is lost after the terminal closes. This skill recovers that context: what was decided, what went wrong, what patterns emerged, and what projects were touched. The resulting memory cards form a knowledge graph in Obsidian, linkable via `[[wikilinks]]`, searchable by both human and AI.

## Model Requirement (MANDATORY)

All summarization MUST use a local model via Ollama. Never send session content to remote APIs.

**Required model:** `qwen3:30b` (or fallback to `qwen3:14b` if 30b unavailable).

```bash
# Ensure model is pulled
ollama pull qwen3:30b
```

**Verification before starting:**
```bash
ollama list | grep qwen3:30b || ollama pull qwen3:30b
curl -s http://localhost:11434/api/generate -d '{"model":"qwen3:30b","prompt":"test","stream":false}' | jq -r .response | head -1
```

## When to Use

- After accumulating 5+ completed sessions since last run
- Weekly or daily batch processing
- User explicitly asks to summarize or extract knowledge
- Building cross-session knowledge graph in Obsidian

## When NOT to Use

- Sessions still in progress (active conversation)
- Sessions with fewer than 3 messages
- Pure system-internal sessions (tool test, config check)
- Real-time streaming summarization (use self-healing-trace)

## Process

### Step 1: Connect and Discover

Read the opencode database and identify sessions to process.

```python
import sqlite3, json, time

DB_PATH = os.environ.get("COWORKER_ANALYTICS_DB",
                         os.path.expanduser("~/.coworker/analytics/analytics.db"))
VAULT_PATH = os.environ.get("COWORKER_VAULT_PATH",
                            os.path.expanduser("~/obsidian/coworker-brain"))
MEMORY_DIR = f"{VAULT_PATH}/session-memory"

db = sqlite3.connect(DB_PATH)

# Find sessions not yet summarized (check memory dir for existing files)
import os
existing = set()
if os.path.exists(MEMORY_DIR):
    for f in os.listdir(MEMORY_DIR):
        if f.endswith(".md"):
            existing.add(f.replace(".md", ""))

# Get sessions ordered by time
sessions = db.execute("""
    SELECT id, title, time_created, model, cost, tokens_input, tokens_output
    FROM session
    WHERE title IS NOT NULL AND title != ''
    ORDER BY time_created ASC
""").fetchall()

# Filter unprocessed
to_process = [(s[0], s[1], s[2], s[3], s[4], s[5], s[6]) for s in sessions if s[0] not in existing]
```

**Fallback:** If DB is locked, copy it first: `cp opencode.db /tmp/opencode_copy.db`

### Step 2: Extract Session Content

For each unprocessed session, extract messages and parts.

```python
import json

def extract_session_content(db, session_id):
    """Extract all user and assistant messages for a session."""
    messages = db.execute("""
        SELECT m.role, m.data, m.time_created
        FROM message m
        WHERE m.session_id = ?
        ORDER BY m.time_created ASC
    """, (session_id,)).fetchall()

    parts = []
    for role, data, ts in messages:
        if data:
            try:
                obj = json.loads(data)
                text = json.dumps(obj, ensure_ascii=False)
                parts.append({"role": role, "text": text, "time": ts})
            except:
                parts.append({"role": role, "text": str(data), "time": ts})

    return parts
```

**Fallback:** If message parsing fails, skip that message and continue with remaining content.

### Step 3: Summarize with Local Model

Send extracted content to Ollama for structured summarization.

**System prompt (MUST use):**

```
You are a session memory extractor. Analyze the following AI agent conversation and extract structured knowledge as JSON.

The output MUST be valid JSON with these fields:
{
  "title": "concise title capturing the session's purpose (max 80 chars)",
  "summary": "2-3 sentence summary of what was accomplished",
  "key_decisions": ["decision 1", "decision 2", ...],
  "lessons_learned": ["lesson 1", "lesson 2", ...],
  "projects": ["project-name-1", "project-name-2"],
  "skills_used": ["skill-1", "skill-2"],
  "tags": ["tag1", "tag2"],
  "confidence": 0.0-1.0
}

Rules:
1. Use Chinese or English based on the session's dominant language
2. If content is too thin to extract meaningful memory, set confidence < 0.3
3. Project names should use kebab-case matching directory names (e.g., ai-coworker, skill-factory)
4. Tags should be lowercase, useful for Obsidian graph connections
5. Only respond with the JSON, no explanation
```

**API call:**

```python
import requests

def summarize_session(content_text, model="qwen3:30b"):
    # Truncate to fit 32K context (model limit)
    max_chars = 24000
    if len(content_text) > max_chars:
        content_text = content_text[:max_chars]

    system_prompt = """You are a session memory extractor..."""  # full prompt above

    resp = requests.post("http://localhost:11434/api/generate", json={
        "model": model,
        "system": system_prompt,
        "prompt": content_text,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 1024
        }
    }, timeout=120)

    result = resp.json()["response"]
    # Extract JSON from response
    import re
    json_match = re.search(r'\{[\s\S]*\}', result)
    if json_match:
        return json.loads(json_match.group())
    return None
```

**Retry logic:** If model returns invalid JSON, retry once with `temperature: 0.1`. If still invalid, mark session with confidence=0 and store raw output for manual review.

**Fallback model:** If `qwen3:30b` is unavailable, fall back to `qwen3:14b` (smaller but faster).

### Step 4: Write Memory Card

Generate a Markdown file with Obsidian wikilinks for the vault.

```python
import os
from datetime import datetime

def write_memory_card(session_id, title, memory, db):
    """Write a memory card to Obsidian vault."""
    # Parse session metadata
    session = db.execute("""
        SELECT time_created, model, cost, tokens_input, tokens_output
        FROM session WHERE id = ?
    """, (session_id,)).fetchone()

    ts = datetime.fromtimestamp(session[0] / 1000)
    date_str = ts.strftime("%Y-%m-%d %H:%M")

    # Build tags with # prefix for Obsidian
    tags = memory.get("tags", [])
    tag_str = " ".join([f"#{t}" for t in tags])

    # Build project links
    projects = memory.get("projects", [])
    project_links = ", ".join([f"[[projects/{p}]]" for p in projects])

    # Build skill links
    skills = memory.get("skills_used", [])
    skill_links = ", ".join([f"[[skills/{s}]]" for s in skills])

    card = f"""---
date: {date_str}
tags: {tag_str}
projects: [{", ".join(projects)}]
confidence: {memory.get("confidence", 0.5)}
model: {session[1]}
cost: ${session[2]:.4f}
tokens: {session[3]} in / {session[4]} out
---

# {memory.get("title", title)}

**Date:** {date_str}
**Confidence:** {"high" if memory.get("confidence", 0) >= 0.7 else "medium" if memory.get("confidence", 0) >= 0.3 else "low"}

## Summary

{memory.get("summary", "No summary available.")}

## Key Decisions

{chr(10).join([f"- {d}" for d in memory.get("key_decisions", ["None recorded"])])}

## Lessons Learned

{chr(10).join([f"- {l}" for l in memory.get("lessons_learned", ["None recorded"])])}

## Connections

- **Projects:** {project_links if project_links else "none"}
- **Skills:** {skill_links if skill_links else "none"}

## Metrics

| Metric | Value |
|--------|-------|
| Model | {session[1]} |
| Cost | ${session[2]:.4f} |
| Input Tokens | {session[3]} |
| Output Tokens | {session[4]} |

---
*Generated by ai-coworker-session-memory using qwen3:30b*
"""

    os.makedirs(MEMORY_DIR, exist_ok=True)
    filename = f"{MEMORY_DIR}/{session_id}.md"
    with open(filename, "w") as f:
        f.write(card)

    return filename
```

**Fallback:** If vault directory doesn't exist, create it. If write fails, save to `/tmp/memory/` and notify.

### Step 5: Generate Index

After processing all sessions, update the master index file in Obsidian.

```python
def update_index():
    """Generate or update the index of all memory cards."""
    files = sorted(os.listdir(MEMORY_DIR))
    cards = []
    for f in files:
        if not f.endswith(".md"):
            continue
        card_path = f"{MEMORY_DIR}/{f}"
        with open(card_path) as cf:
            content = cf.read()
            # Extract title from first # heading
            title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else f
            cards.append((f, title))

    index = f"""# Session Memory Index

> Auto-generated index of all session memory cards. Updated by ai-coworker-session-memory.

**Total sessions indexed:** {len(cards)}

| Date | Title | Confidence |
|------|-------|-------------|
"""
    for fname, title in cards:
        date = "unknown"
        with open(f"{MEMORY_DIR}/{fname}") as cf:
            for line in cf:
                if line.startswith("date:"):
                    date = line.split(":", 1)[1].strip()
                    break
        index += f"| {date} | [[session-memory/{fname.replace('.md', '')}\\|{title}]] | - |\n"

    index += f"\n*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"

    with open(f"{VAULT_PATH}/Session Memory Index.md", "w") as f:
        f.write(index)
```

### Step 6: Report Summary

Print a summary to the user:

```
Processed: 15 sessions
Skipped (already exist): 178 sessions
High confidence (≥0.7): 12
Medium confidence (0.3-0.7): 2
Low confidence (<0.3): 1 (manual review recommended)
Written to: ~/obsidian/coworker-brain/session-memory/
Index: ~/obsidian/coworker-brain/Session Memory Index.md
```

## Quality Gates

### MUST (block completion)

- [ ] `qwen3:30b` model verified available via `ollama list`
- [ ] opencode.db path exists and is readable
- [ ] Obsidian vault path exists
- [ ] All processed sessions have a valid JSON summary from model
- [ ] No session content sent to remote API
- [ ] Memory cards use valid Markdown format
- [ ] Index file updated with all cards

### NICE (warn but don't block)

- [ ] At least 80% of sessions have confidence ≥ 0.3
- [ ] Zero sessions had invalid JSON on first attempt
- [ ] Project tags match actual directory names
- [ ] Skills referenced actually exist in skill-factory

## Anti-Patterns

| Symptom | Why Wrong | Fix |
|---------|-----------|-----|
| Sending to remote model API | Session content is private, violates local-only requirement | Always use `http://localhost:11434` |
| Summarizing active sessions | In-progress sessions have incomplete context | Check `time_archived` or only process sessions older than 24h |
| One huge prompt for all sessions | Exceeds model context window, loses detail | Process one session per API call |
| Skipping low-confidence sessions | Even thin sessions may contain useful breadcrumbs | Generate card with confidence flag, don't skip |

## Sources

- opencode.db schema: confidence high — reverse-engineered from actual database with 193 sessions
- Ollama API: confidence high — official documentation for `/api/generate` endpoint
- Obsidian wikilink format: confidence high — `[[path/note|display]]` syntax
- Phase 1 interview: confidence high — user-specified requirements for memory card fields and output format
- Model selection (qwen3:30b): confidence high — 32K context, strong Chinese summarization, fits within 12GB VRAM + partial offload
