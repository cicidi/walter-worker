---
name: status
version: 0.2.0
description: Show current coworker config status and active feature progress
triggers:
  - status
  - show me status
  - what's the status
  - how is the feature going
when-to-use: When user needs to show current coworker config status or feature progress
license: MIT
compatibility: claude-code,opencode,gemini
user-invocable: true
---

# status

Show current coworker config status. When an feature is active, also shows
feature-specific progress: work artifacts (docs), session/commit counts,
memory references, and remaining work.

## Usage

```bash
coworker status
```

## Output Sections

### 1. Config Status
Global and project-level config paths, MCP count, skill count.

### 2. Feature Overview (if active)
Name, status, created date, goal, approach.

### 3. Work Artifacts
Auto-scanned from `docs/<feature>/`:
- ✅ PRD, Spec/Design, Implementation Plan, Test Plan, Research, Decision History
- ⬜ indicates expected but missing artifact types

### 4. Sessions & Commits
- **Sessions** — count from `analytics.db` where `feature` column matches
- **Commits** — `git log --grep <feature-name>` count since feature creation
- **Memory References** — count of graph.json nodes referencing the feature

### 5. Remaining Work
- If `remaining` field is populated in feature YAML: shows the list
- If empty, auto-derives suggestions based on missing artifacts/activity
