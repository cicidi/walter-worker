# Hermes Agent — Reference Documentation

> Source: https://github.com/NousResearch/hermes-agent
> Tagline: "The agent that grows with you"
> Latest: v0.18.2 (July 2026) | MIT License | Nous Research

## Overview

Hermes Agent is an open-source, multi-platform autonomous agent with a built-in **closed learning loop** — it creates skills from experience, improves them during use, persists knowledge across sessions, and builds a deepening model of users over time. Accessible from 22+ messaging platforms, supports 25+ LLM providers.

## Core Self-Evolving Learning Loop

### 1. Autonomous Skill Creation
After completing a complex task involving **5+ tool calls**, the agent automatically creates a reusable `SKILL.md` file (agentskills.io standard). Ships with 166+ tracked skills (87 bundled + 79 optional) across 26+ categories.

### 2. Skill Self-Improvement (Patch/Edit)
When a skill becomes outdated or wrong during use, the agent **autonomously patches** it. `patch` action: surgical edits via old_string/new_string. `edit` action: major rewrites. `patch_count` telemetry feeds the Curator.

### 3. The Autonomous Curator
Background process every 7 days (after 2+ hours idle):
- Tracks view_count, use_count, patch_count per skill
- Moves unused skills: active → stale (30d) → archived (90d)
- Consolidates overlapping skills, generates REPORT.md
- Never touches bundled or hub-installed skills

### 4. GEPA-Driven Self-Evolution
Pairs DSPy with GEPA (Genetic-Pareto prompt evolution). Reads execution traces, proposes targeted mutations. Evolved variants must pass test suite + size limits + caching checks + PR review. ~$2-10 per optimization run, no GPU training needed.

### 5. Procedural Memory (Three-Layer)
- **Context compression**: configurable first-turn protection + recent-message floor (default: 20)
- **SQLite FTS5 session search** with LLM summarization for cross-session recall
- **Persistent MEMORY.md**: agent-curated facts with periodic nudges

## Architecture
- **Single agent core** (`AIAgent`): one implementation serves CLI, gateway, ACP, cron, API
- **Transport abstraction**: `ProviderTransport` ABC separates provider-specific format from agent orchestration
- **Concurrent tool execution**: ThreadPoolExecutor (max 8), interactive tools force sequential
- **Six terminal backends**: Local, Docker, SSH, Daytona, Singularity, Modal
- **Plugin architecture**: drop Python files into `~/.hermes/plugins/` for custom tools, commands, hooks, dashboards, platforms
- **Lifecycle hooks**: pre_llm_call, post_llm_call, on_session_start, on_session_end
- **Profile system**: run multiple isolated Hermes instances from same installation

## Key Design Patterns
1. Single-agent-core consistency across all surfaces
2. Self-improving loop: create → use → patch → curator cycle
3. Plugin-first extensibility without forking
4. Progressive disclosure: autonomous by default, checkpoints on critical actions
5. Serverless-friendly: hibernate when idle, near-zero cost
6. Research-to-production pipeline: export ShareGPT traces for SFT/RL training
7. Smart approval system that learns safe commands over time

## Install
```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```
