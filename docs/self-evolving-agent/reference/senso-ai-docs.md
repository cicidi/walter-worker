# Senso.ai — Reference Documentation

> Source: https://www.senso.ai/about, https://www.senso.ai/internal-agents
> YC-backed (Winter 2024) | Toronto/SF/NYC

## Positioning

"The Context Layer for AI Agents" — infrastructure for the "agentic web" where AI agents are primary consumers of organizational information.

## Architecture: Four-Stage Pipeline

1. **Ingest** — Raw sources (PDFs, documents, URLs, knowledge bases, SOPs)
2. **Compile** — Parse, chunk, embed, index into verified knowledge base
3. **Query** — AI agents search compiled knowledge base for grounded answers with source citations
4. **Generate** — Verified content grounded in sources; stays in sync as sources change

## Continuous Improvement Loop
1. **Evaluate** — Assess LLM accuracy (ChatGPT, Claude, Gemini, Perplexity) for your org
2. **Remediate & Verify** — Produce agent-ready context with human-in-the-loop approval
3. **Publish** — Deploy verified context to your domain, machine-consumable + human-readable

## Knowledge Files Structure
- **agents.md** — Agent capabilities & permitted actions
- **soul.md** — Brand voice, values & tone
- **heartbeat.md** — Live data sync & refresh cycles
- **security.md** — Compliance rules & access controls

## Consumption Paths
| Audience | Action |
|----------|--------|
| Teams | Free audit at geo.senso.ai/industries |
| Developers | docs.senso.ai |
| Agents | `npm install -g @senso-ai/cli` |

## Performance
93% response quality with Senso Verified Context
