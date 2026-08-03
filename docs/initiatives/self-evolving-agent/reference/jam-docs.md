# Jam.dev MCP — Reference Documentation

> Source: https://jam.dev/blog/meet-the-new-jam-mcp/
> MCP Server: https://mcp.jam.dev/mcp

## Overview

Jam MCP server allows coding agents (Claude Code, Cursor, Codex) to pull debugging context from Jam bug recordings.

## MCP Tools (6 tools)

1. **analyzeVideo** — Full recorded video with automatic transcription
2. **getConsoleLogs** — Browser console output during bug recording
3. **getNetworkRequests** — Network activity during reproduction
4. **getUserEvents** — Step-by-step user action replay
5. **getScreenshots** — Screenshots captured during the bug
6. **getDetails** — Bug metadata and context

## Workflow
1. User opens saved Jam recording → clicks MCP button
2. Follow tool-specific setup prompt or create personal access token
3. Paste Jam link into coding agent
4. Agent pulls all debugging context and implements fixes

## Vision
"AI agents that ship bug fixes while they sleep" — structured context for autonomous debugging.

## Related: Dag7/jam (OSS Agent Orchestrator)
> Source: https://github.com/Dag7/jam

An open-source desktop app (Electron + React) that orchestrates multiple AI coding agents:
- 4 agent runtimes: Claude Code, Cursor, OpenCode, Codex CLI
- Voice control via Whisper + ElevenLabs/OpenAI TTS
- Living personalities (SOUL.md) — evolves over time
- Conversation memory via JSONL history
- Dynamic skills — agents auto-generate reusable skill files
- Sandbox isolation: Docker, Seatbelt/Bubblewrap, Git worktree
- Computer use: each agent has virtual desktop (Xvfb + Playwright)
- Team coordination: task scheduling, smart assignment, trust scoring
- Yarn 4 monorepo, 10 packages
- Latest: v0.4.1 (April 2026)
