# Knowledge Skill PRD

<!-- PROTECTED -->
Project: ai-coworker
Owner: cicidi
Last Updated: 2026-06-11
Status: PLANNED
<!-- END PROTECTED -->

## Overview

An LLM-driven offline analysis skill that reads session data from SQLite and produces structured insights. Runs periodically (per-session or daily batch), writes results back to SQLite. Dashboard reads and displays — Knowledge Skill is the brain, Dashboard is the eyes.

## Architecture

```
Session DB (SQLite) → Knowledge Skill (LLM) → Insights DB (SQLite) → Dashboard
```

Knowledge Skill reads raw session events, feeds them to an LLM with structured prompts, and writes back structured results.

## Goals

1. Extract reusable knowledge from session traces (traps, best practices, patterns)
2. Detect recurring failure modes and generate self-healing rules
3. Evaluate per-session efficiency and surface improvement areas
4. Identify useful vs useless actions within each session
5. Estimate ROI via surviving-lines-per-cost analysis

## Outputs

### 1. Session Summary (per-session)

For each completed session, produce a structured summary stored in the session data.

**What to capture:**
- **SOP / Workflows:** Reusable step sequences discovered or validated in this session (e.g. "创建 worktree → 安装依赖 → 运行测试 → 开始开发")
- **Context to remember:** Project state, branch status, unfinished work, decisions pending — things the next session needs to know
- **Effective operations:** Specific tool invocations or approaches that worked well
- **Command line:** Useful CLI commands, flags, or patterns discovered or validated
- **Documentation insights:** Which docs were useful, what they helped solve, gaps identified
- **Pitfalls & fixes:** Things that failed repeatedly, what was tried, and the final working solution — the "折腾了半天最后怎么解决的" story
- **Wasted actions:** Loops, unnecessary reads, dead-end explorations that led nowhere
- **Bottlenecks:** Longest think times, most repetitive tool calls, user wait time
- **Efficiency tip:** One actionable suggestion for next similar session

**Dashboard display:** Per-session panel in Session Compare / Session Replay views.

### 2. Knowledge Cards (cross-session)

Extracted patterns recurring across multiple sessions.

| Category | Example |
|----------|---------|
| ⚠️ Trap | "pytest not found in worktree — use python3 instead" |
| ✅ Best Practice | "Always brainstorm before new features — 95% doc completion rate" |
| 📋 Pattern | "brainstorming → writing-plans → executing-plans is optimal path" |
| 📝 Decision | "Dashboard uses FastAPI + vanilla JS — deliberate simplicity" |
| 🔧 Constraint | "OpenCode --workdir more reliable than cd" |
| ⚡ Command | "pytest --co -q to collect tests before full run" |

**Dashboard display:** Knowledge Base view (View 9).

### 3. Self-Healing Rules (cross-session)

When the same user correction pattern appears ≥2 times, generate a rule.

**Format:**
- Trigger: user correction text
- Action: behavioral change to apply
- Source sessions: which sessions triggered this
- Impact: measured improvement after rule applied

**Dashboard display:** Self-Healing section in Knowledge Base view.

### 4. Session Efficiency Score (per-session)

| Metric | Calculation |
|--------|-------------|
| think/action ratio | think time / tool call time |
| edit redundancy | average edits per file |
| unnecessary reads | files read but never written |
| loop count | repeated identical tool calls |
| user wait time | time spent waiting for question answers |
| vs. similar sessions | compare to past sessions on same feature |

**Dashboard display:** Efficiency panel in Session Compare view.

### 5. ROI Estimate (per-session, TODO)

- surviving_lines per session via git blame
- estimated cost per session
- roi = surviving_lines / cost
- decay over time as later sessions overwrite lines

**Dashboard display:** ROI panel in Knowledge Base view.

## Non-Goals

- No real-time analysis — runs offline, not during active sessions
- No automated code quality scoring — requires test integration that doesn't exist
- No workflow stage detection — CLI doesn't emit stage labels

## Implementation

### Runtime: OpenCode SDK

OpenCode provides full programmatic control via `@opencode-ai/sdk`:

```js
import { createOpencode } from "@opencode-ai/sdk"

// Create headless OpenCode instance
const { client } = await createOpencode({ port: 4096 })

// Create a session for analysis
const session = await client.session.create({
  body: { title: "Knowledge Skill — Session Summary" }
})

// Feed session data + prompt for structured analysis
const result = await client.session.prompt({
  path: { id: session.id },
  body: {
    parts: [{
      type: "text",
      text: `Analyze this session data and return a structured summary:
      <session_data>${JSON.stringify(sessionEvents)}</session_data>`
    }],
    format: {
      type: "json_schema",
      schema: {
        type: "object",
        properties: {
          sop_workflows: { type: "array", items: { type: "string" } },
          context_to_remember: { type: "string" },
          effective_operations: { type: "array", items: { type: "string" } },
          command_line: { type: "array", items: { type: "string" } },
          documentation_insights: { type: "string" },
          pitfalls_and_fixes: { type: "array", items: { type: "object", properties: { problem: { type: "string" }, attempts: { type: "array", items: { type: "string" } }, solution: { type: "string" } } } },
          wasted_actions: { type: "array", items: { type: "string" } },
          bottlenecks: { type: "array", items: { type: "string" } },
          efficiency_tip: { type: "string" }
        }
      }
    }
  }
})

// Write result back to SQLite
const summary = result.data.info.structured_output
writeToSessionDB(sessionId, summary)
```

Alternatively, use CLI non-interactive mode:

```bash
opencode run --format json "Analyze this session data from ~/.coworker/sessions/session-123.jsonl ..."
```

### Skill Definition

Knowledge Skill is a standard `.opencode/skills/knowledge-skill/SKILL.md` file with triggers like:
- "analyze this session"
- "summarize what I did"
- "generate knowledge cards from today's sessions"

The skill reads session data from SQLite, calls the LLM for analysis, and writes structured results back.

