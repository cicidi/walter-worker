# Dashboard PRD

<!-- PROTECTED -->
Project: ai-coworker
Owner: cicidi
Last Updated: 2026-06-11
Status: PLANNED
<!-- END PROTECTED -->

## Overview

A local-first web monitoring dashboard for AI coding CLI sessions (Claude Code, OpenCode, Gemini CLI). Visualizes what existing LLM observability tools (Langfuse, Helicone, Opik) cannot: the real-time and historical behavior of black-box CLI AI coding agents.

## Architecture

| Layer | Responsibility |
|-------|---------------|
| **Middleware** | Intercept CLI processes, capture raw events → SQLite |
| **Dashboard** | Read SQLite, serve FastAPI Web UI (read-only visualization) |
| **Knowledge Skill** | LLM-driven offline analysis → writes insights to SQLite |

## Goals

1. Real-time visibility into agent behavior — skills used, tools called, files touched
2. Historical session review, comparison, and replay
3. Multi-worktree monitoring with conflict detection
4. Display LLM-generated insights from Knowledge Skill

## Dashboard Views

### Keep (MVP)

| # | View | Description |
|---|------|-------------|
| 1 | Dashboard Overview | Active session card, stats, live tool feed |
| 2 | Real-time Session Stream | Think/Tool/File timeline + stats sidebar |
| 7 | Trace Waterfall | Nested operation waterfall with latency bars |
| 10 | Session Compare + Search + Notifications | Side-by-side diff, FTS, alert center, per-session summary |
| 12 | Session Replay + Settings | Step playback with session summary, config panel |

### Simplify (Display-Only from Knowledge Skill)

| # | View | What's Simplified |
|---|------|-------------------|
| 4 | Skills + Tools | Drop knowledge cards. Keep skill tree + tool perf |
| 6 | File Heatmap + Timeline | Drop dependency impact. Keep frequency + calendar |
| 8 | Multi-Worktree | Drop cost/tokens. Keep worktree status + conflict detection |
| 11 | Knowledge Base | Display only — knowledge cards, self-healing rules, efficiency scores, ROI, session summaries from Knowledge Skill |

### Deleted

| # | View | Reason |
|---|------|--------|
| 3 | 8-Stage Workflow | CLI doesn't emit stage labels |
| 5 | Agent Behavior Insights | Requires impossible data or LLM analysis |
| 9 | Prompt Version + Evaluation | Quality scores need automated test attribution |

## Non-Goals

- No insight generation — all semantic analysis in Knowledge Skill
- No SaaS, no multi-user, no auth
- No real-time token counting (CLI tools don't expose this)
- No automated workflow stage detection

## Tech

- Backend: FastAPI + WebSocket
- Frontend: Vanilla JS + HTML/CSS
- Database: SQLite (shared with middleware)

## Spec

This PRD.
UI mockup: `docs/prd/dashboard-mockup.html` / `docs/prd/dashboard.js`

## Plan

TBD
