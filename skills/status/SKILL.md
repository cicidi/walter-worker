---
name: status
version: 0.2.0
description: Show current coworker config status and active initiative progress
triggers:
  - status
  - show me status
  - what's the status
  - how is the initiative going
when-to-use: When user needs to show current coworker config status or initiative progress
license: MIT
compatibility: claude-code,opencode,gemini
user-invocable: true
---

# status

Show current coworker config status. When an initiative is active, also shows
initiative-specific progress: work artifacts (docs), session/commit counts,
memory references, and remaining work.

## Usage

```bash
coworker status
```

## Output Sections

### 1. Config Status
Global and project-level config paths, MCP count, skill count.

### 2. Initiative Overview (if active)
Name, status, created date, goal, approach.

### 3. Work Artifacts
Auto-scanned from `docs/<initiative>/`:
- ✅ PRD, Spec/Design, Implementation Plan, Test Plan, Research, Decision History
- ⬜ indicates expected but missing artifact types

### 4. Sessions & Commits
- **Sessions** — count from `analytics.db` where `initiative` column matches
- **Commits** — `git log --grep <initiative-name>` count since initiative creation
- **Memory References** — count of graph.json nodes referencing the initiative

### 5. Remaining Work
- If `remaining` field is populated in initiative YAML: shows the list
- If empty, auto-derives suggestions based on missing artifacts/activity
