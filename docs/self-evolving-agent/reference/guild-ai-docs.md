# Guild.ai — Reference Documentation

> Source: https://www.guild.ai/platform, https://github.com/mathomhaus/guild
> Commercial: guild.ai | Open Source: github.com/mathomhaus/guild
> Founded by James Everingham (ex-VP Eng at Meta) | $44M Series A

## Positioning

"The control plane for AI agents" — centralized infrastructure layer for managing full lifecycle of AI agents in production. "Think Kubernetes, but for AI agents."

## Architecture

### Managed Agent Hub
Centralized inventory: ownership, version history, access controls, reusable components.

### Mediated Gateway / Proxy Layer
All agent → LLM traffic routed through `https://gateway.guild.ai`. Agents never see raw API keys. Gateway intercepts calls, verifies identity, applies token tracking, injects scoped credentials.

### Credential Vault
Hardware-isolated, encrypted vault. Short-lived, scoped, ephemeral credentials per agent. Central rotation with zero downtime. Each agent gets unique identity principal with per-endpoint permissions.

### Identity & Auth (KYA — "Know Your Agent")
Zero-trust: every agent is an independent security principal. Cryptographically signed token handshakes, mTLS, centralized OAuth. Agent identities decoupled from human employee accounts.

### Gateway-Level Traffic Management
Automated failover across providers, concurrent request distribution, token throttling.

## Capabilities

### Governance
- Scoped credential management with per-endpoint permissions
- Full audit trails (every version, change, author)
- Git-backed versioning
- Access controls and ownership tracking

### Observability
- Real-time token usage and session traces
- Dashboards: tokens consumed, cost per agent/model, top users
- Incident tracking with session traces

### Deployment
- Model-agnostic (OpenAI, Anthropic, Google, OpenAI-compatible)
- Framework-agnostic (LangChain, CrewAI, etc.)
- BYOK — no vendor lock-in
- Cost-aware routing

### Build
- Open-source TypeScript SDK
- Sandboxed runtime
- Agent sharing and reusable components
- Integrations: GitHub, Jira, Slack, Confluence, Linear

## Open Source: mathomhaus/guild

A separate open-source project (314 stars):
- Single Go binary + embedded MCP server + local SQLite
- Four primitives: Quests (tasks with atomic claiming), Lore (knowledge archive), Oaths (project principles), Briefs (session handoff notes)
- Hybrid search: BM25 keyword + vector semantic via reciprocal-rank fusion
- Works with any MCP client (Claude Code, Cursor, Codex, etc.)
- Install: `brew install mathomhaus/tap/guild` or `go install`
