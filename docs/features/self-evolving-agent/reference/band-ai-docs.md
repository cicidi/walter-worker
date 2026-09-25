# BAND AI — Reference Documentation

> Source: https://venturebeat.com/ai/talking-to-ai-agents-is-one-thing-what-about-when-they-talk-to-each-other-new-startup-band-debuts-universal-orchestrator
> Company: Thenvoi AI Ltd. | $17M Seed (Sierra Ventures, Hetz Ventures, Team8)
> Founded: Mid-2025 | HQ: Tzur Yigal, Israel
> Co-Founders: Arick Goomanovsky (CEO, ex-Sygnia/Ermetic), Vlad Luzin (CTO, ex-Samsung multi-agent systems)

## Positioning

"Slack for AI agents" — enterprise communication and interaction infrastructure for distributed AI agents. The "internet of agents."

## Architecture: Two-Layer System

### Interaction Layer ("Agentic Mesh")
- Agent discovery across internal and external environments
- Structured delegation between agents
- Full-duplex multi-peer communication
- Cross-framework, cross-cloud interoperability
- Shared "rooms" with synchronized context
- Deterministic routing (NOT LLM-based routing — patented multi-layer architecture)
- Built on same stack as WhatsApp and Discord (billions of messages)

### Control Plane
- Runtime governance with authority boundaries
- Credential traversal (delegated agents only access data the original human is permitted)
- Full observability with audit trails
- Human-in-the-loop oversight for inspection, approval, intervention

## Key Capabilities
- Framework-agnostic + cloud-agnostic
- Works with: LangChain, CrewAI, Salesforce, Workday, ServiceNow, Claude Code, Codex, OpenClaw
- Edge deployment: lightweight enough for drones (UAVs) and satellites

## Enterprise Use Cases
- Multi-agent coding workflows (planning → coding → review agents)
- Cross-boundary automation (Workday onboarding → ServiceNow ticketing → purchasing)
- Telecommunications, financial services, cybersecurity

## Deployment Options
- SaaS
- Private Cloud / On-Premise (within customer VPC)
- Edge

## Pricing
| Tier | Price | Details |
|------|-------|---------|
| Free | $0/mo | 10 remote agents, 50 chat rooms, 24hr retention |
| Pro | $17.99/mo | 40 agents, 250 chat rooms |
| Enterprise | Custom | Unlimited agents, custom retention, Memory APIs |

## Market Context
Gartner predicts 90% of enterprises deploying multiple agents will need a "Universal Orchestrator" by 2029.
