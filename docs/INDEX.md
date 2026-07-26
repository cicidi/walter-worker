# Document Index

Last updated: 2026-07-25

## By Initiative

### self-evolving-agent

| St | Type | File | What It Contains |
|----|------|------|-----------------|
| 🚧 | prd | [self-evolving-agent-prd.md](./self-evolving-agent/prd/self-evolving-agent-prd.md) | PRD v7 — requirements-only (what/why). Three-tier memory, hook-embedded implicit evolution, SDK mode, auto skill create/patch, safety architecture, evolution observability (R1–R15) |
| 🚧 | prd | [self-evolving-agent-prd-zh.md](./self-evolving-agent/prd/self-evolving-agent-prd-zh.md) | PRD v3 — Chinese translation (older version, kept for reference) |
| 🚧 | spec | [self-evolving-agent-spec.md](./self-evolving-agent/spec/self-evolving-agent-spec.md) | Spec v1.2 — technical "how". mem0 substrate, dual-IDE capture layer, evolution engine, dashboard API, auto-worker loop, training pipeline |
| 📝 | spec | [qa-autonomous-agent-spec.md](./self-evolving-agent/spec/qa-autonomous-agent-spec.md) | QA autonomous agent spec — DEFERRED. Kept as reference for auto-worker redesign. |
| 🚧 | design | [memory-platform-design.md](./self-evolving-agent/design/memory-platform-design.md) | Memory platform architecture — component interfaces, data flow, mem0 schema, context injection, curator, pending queue, safety |
| 🚧 | design | [auto-worker-design.md](./self-evolving-agent/design/auto-worker-design.md) | Auto-worker design — 8 core rules, decision tree, gap detection, loop mechanics, training pipeline, Claude SDK validation harness |
| 🚧 | design | [dashboard-design.md](./self-evolving-agent/design/dashboard-design.md) | Dashboard Evolution page — layout, stat cards, skills table, experiences table, filters, API endpoints |
| 📝 | design | [qa-autonomous-agent-design.md](./self-evolving-agent/design/qa-autonomous-agent-design.md) | QA autonomous agent design — DEFERRED. Kept as reference. |
| 🚧 | impl-plan | [self-evolving-agent-impl-plan.md](./self-evolving-agent/impl-plan/self-evolving-agent-impl-plan.md) | Implementation plan — 7 waves, 17 tasks, all real infrastructure (mem0, SQLite, DeepSeek Flash, Claude SDK) |
| 📝 | impl-plan | [qa-autonomous-agent-impl-plan.md](./self-evolving-agent/impl-plan/qa-autonomous-agent-impl-plan.md) | QA impl plan — DEFERRED. Kept as reference. |
| 🚧 | test-plan | [self-evolving-agent-test-plan.md](./self-evolving-agent/test-plan/self-evolving-agent-test-plan.md) | Test plan v3 — no mocks, all real infrastructure. 100+ test cases, E2E Claude SDK A/B validation, 95% coverage target |
| 📝 | decision | [dependency-and-sequencing.md](./self-evolving-agent/dependency-and-sequencing.md) | QA skill vs self-evolution engine — dependency analysis and build path decision |
| 📝 | reference | [hermes-agent-docs.md](./self-evolving-agent/reference/hermes-agent-docs.md) | Hermes Agent reference |
| 📝 | reference | [guild-ai-docs.md](./self-evolving-agent/reference/guild-ai-docs.md) | Guild AI reference |
| 📝 | reference | [jam-docs.md](./self-evolving-agent/reference/jam-docs.md) | Jam MCP reference |
| 📝 | reference | [band-ai-docs.md](./self-evolving-agent/reference/band-ai-docs.md) | BAND AI reference |
| 📝 | reference | [pioneer-docs.md](./self-evolving-agent/reference/pioneer-docs.md) | Pioneer Agent reference |
| 📝 | reference | [actian-vectordb-docs.md](./self-evolving-agent/reference/actian-vectordb-docs.md) | Actian VectorDB reference |
| 📝 | reference | [senso-ai-docs.md](./self-evolving-agent/reference/senso-ai-docs.md) | Senso AI reference |
| 🚧 | state | [2026-07-24-state.md](./self-evolving-agent/state/2026-07-24-state.md) | Design phase progress snapshot |
| 🚧 | html | [evolution-dashboard-mockup.html](./self-evolving-agent/html/evolution-dashboard-mockup.html) | Dashboard Evolution page — standalone HTML mockup matching existing dashboard style |

### Other Initiatives

| St | Type | File | What It Contains |
|----|------|------|-----------------|
| — | — | _(see subdirectories)_ | — |

## Move Log

| Date | File | From | To | Reason |
|------|------|------|----|--------|
| 2026-07-25 | self-evolving-agent-test-plan.md | tests/test-plans/ | docs/self-evolving-agent/test-plan/ | Follow doc-organize conventions — test plans belong in docs/ |
