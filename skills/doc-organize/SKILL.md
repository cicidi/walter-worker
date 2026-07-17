---
name: doc-organize
version: 0.1.0
description: Document organization skill — determines where to place docs, what to name them, and maintains INDEX.md. Covers 9 document types + evidence suffix with naming conventions and folder hierarchy. Use when creating, moving, or reorganizing documentation files.
triggers:
- organize docs
- where to put this doc
- create a doc
- move doc
- doc structure
- file naming
- what type of doc
- document type
- index docs
when-to-use: When writing a new document and need to know where to place it and what to name it. When reorganizing existing docs. When user asks about document structure or naming conventions. This skill is about doc PLACEMENT and NAMING — write-doc handles content (Change Log).
license: MIT
compatibility: claude-code,opencode
user-invocable: true
---
# Doc Organize

Determine the correct **location**, **file name**, and **document type** for any documentation.  
Works alongside `write-doc` — this skill handles placement, write-doc handles Change Log.

---

## Document Types (9 + evidence suffix)

| Type | Purpose | Write When |
|------|---------|------------|
| `prd` | Product Requirements Document | Project kickoff |
| `research` | Investigation + comparison of options | Before making a decision |
| `design` | Technical design — one type, two optional suffixes (`.hld.md` for architecture, `.lld.md` for module detail) | Choosing architecture, before implementation |
| `spec` | Detailed technical specification | Formalizing interfaces |
| `impl-plan` | Implementation plan with milestones | Breaking down tasks |
| `test-plan` | Testing strategy and cases | Before QA phase |
| `decision-history` | Architecture Decision Record (ADR). Covers Context → Options → Decision → Why this option → Consequences | Making key decisions, defending a choice |
| `retro` | Retrospective / post-mortem | End of phase/milestone |
| `how-to` | Operational guide / runbook | Documenting repeatable processes |

### Suffixes (not standalone types)

**Evidence** — attach to any doc to provide supporting data:

```
docs/dashboard-v2/research/2026-07-02-competitor-analysis.md
docs/dashboard-v2/research/2026-07-02-competitor-analysis.evidence.md   ← benchmarks/screenshots
```

**Design detail** — attach to a design doc for HLD or LLD view:

```
docs/dashboard-v2/design/2026-07-05-caching-strategy.md                 ← main design doc
docs/dashboard-v2/design/2026-07-05-caching-strategy.hld.md             ← architecture overview
docs/dashboard-v2/design/2026-07-05-caching-strategy.lld.md             ← component detail
```

Rules for both:
- Same name prefix, same folder as parent
- INDEX.md only lists the parent doc
- Suffix files are optional — simple designs don't need them
- `.hld.md` = system topology, service boundaries, data flow
- `.lld.md` = class diagrams, API contracts, DB schema, module internals

---

## Directory Structure

```
project/
├── docs/
│   ├── INDEX.md                     ← Auto-generated directory + move log
│   ├── <initiative>/
│   │   └── <type>/
│   │       └── YYYY-MM-DD-<specific-topic>.md
│   └── shared/                      ← Cross-initiative docs
│       ├── glossary.md
│       └── conventions.md
│
└── knowledge-repo/  (optional, separate git repo)
    └── (same structure)
```

---

## File Naming Convention

```
docs/<initiative>/<type>/YYYY-MM-DD-<specific-topic>.md
```

Rules:
- Date: `YYYY-MM-DD` (creation date)
- Topic: kebab-case, describes the specific problem/subject — NOT the initiative name
- An initiative can be a product feature, env setup, team oncall, or anything
- Multiple files of same type in one initiative are normal

Examples:

```
# Product feature
docs/user-profile-v2/
├── prd/2026-07-01-user-profile-v2-requirements.md
├── research/2026-07-02-competitor-profile-pages.md
├── design/2026-07-05-profile-service-architecture.md
│   ├── design/2026-07-05-profile-service-architecture.hld.md
│   └── design/2026-07-05-profile-service-architecture.lld.md
├── design/2026-07-08-profile-api-and-db-schema.md
├── spec/2026-07-10-profile-endpoint-contracts.md
├── impl-plan/2026-07-12-profile-migration-steps.md
├── test-plan/2026-07-14-profile-integration-tests.md
└── retro/2026-08-01-profile-v2-launch-review.md

# Environment / Setup
docs/dev-env-setup/
├── prd/2026-06-01-dockerize-all-services.md
├── research/2026-06-02-podman-vs-docker-compose.md
├── research/2026-06-03-devcontainer-vs-vagrant.md
├── decision-history/2026-06-03-why-docker-compose-not-k8s.md
├── design/2026-06-05-container-orchestration-plan.md
├── impl-plan/2026-06-10-onboarding-scripts-and-docs.md
└── how-to/2026-06-15-new-hire-setup-checklist.md

# Team Oncall
docs/team-oncall/
├── prd/2026-07-01-oncall-rotation-redesign.md
├── how-to/2026-07-05-pagerduty-escalation-flow.md
├── how-to/2026-07-06-database-incident-runbook.md
├── decision-history/2026-07-08-why-pagerduty-over-opsgenie.md
├── research/2026-07-10-q2-incident-stats-before-after.md
│   └── research/2026-07-10-q2-incident-stats-before-after.evidence.md
└── retro/2026-07-15-july-oncall-handoff.md

# Refactoring / Migration
docs/payment-refactor/
├── research/2026-07-01-stripe-vs-adyen-2026.md
├── design/2026-07-05-new-payment-provider-interface.md
├── research/2026-07-06-migration-vs-big-bang-cutover.md
├── impl-plan/2026-07-10-gradual-migration-phases.md
└── impl-plan/2026-07-20-migration-performance-benchmarks.md
│   └── impl-plan/2026-07-20-migration-performance-benchmarks.evidence.md
```

---

## Knowledge Repo vs Project Docs

| Scenario | Where |
|----------|-------|
| Small team, docs tightly coupled with code | `docs/` in project repo |
| Large team, docs merge independently of code | Separate `knowledge-repo/` |
| Cross-project shared knowledge | `knowledge-repo/` |
| Single project, active development | Project `docs/` |

**Default advice**: start with project `docs/`. Split to knowledge-repo when you notice doc PRs conflicting with code PRs frequently.

---

## INDEX.md

Auto-maintained at `docs/INDEX.md`:

```markdown
# Document Index

Last updated: YYYY-MM-DD

## By Initiative

### <initiative-name>
| St | Type | File | Created |
|----|------|------|---------|
| ✅ | prd | [description](./initiative/prd/date-name.md) | 2026-07-14 |
| 🚧 | spec | [description](./initiative/spec/date-name.md) | 2026-07-15 |
| 🔲 | tbd | (placeholder for future doc) | — |

## Move Log

| Date | File | From | To | Reason |
|------|------|------|----|--------|
| 2026-07-17 | dashboard-prd.md | analytics-listener/prd/ | analytics-v2/prd/ | Initiative rename |
```

Rules:
- Append on every doc creation or move
- Never delete entries — log moves instead

---

## Document Lifecycle

6 stages. Tracked in INDEX.md only — NOT in filename.

| Stage | Icon | Meaning | When to advance |
|-------|------|---------|-----------------|
| `tbd` | 🔲 | Placeholder, not started | → draft: start writing |
| `draft` | 📝 | Rough outline, structure ready | → wip: serious writing begins |
| `wip` | 🚧 | Active development, content iterating | → review: author thinks it's done |
| `review` | 👀 | Awaiting peer/team review | → final: approved, OR → wip: changes requested |
| `final` | ✅ | Approved, no further changes expected | → archived: no longer relevant |
| `archived` | 📦 | Outdated, kept for reference | — end of life |

Rules:
- New docs start at `draft` by default. Use `tbd` for intentionally empty placeholders.
- Change stage in INDEX.md only — never rename the `.md` file.
- `review → wip` is the only allowed "backward" transition (rework after feedback).

---

## Workflow

### When user asks to create a doc

1. **Identify initiative** — Ask if unclear. Check existing initiatives in `docs/`.
2. **Determine type** — Match user's intent to one of the 9 types. Ask if ambiguous.
3. **Generate path** — `docs/<initiative>/<type>/YYYY-MM-DD-<specific-topic>.md`
4. **Create file** — Use `write-doc` conventions for content.
5. **Update INDEX.md** — Append new entry.

### When user asks to reorganize docs

1. Scan `docs/` for misplaced files (wrong type dir, wrong naming).
2. Propose moves before executing.
3. After each move: update INDEX.md Move Log.

### When user asks where to put something

1. Identify or ask initiative and doc type.
2. Output the exact path.
3. Offer to create it.

---

## Initiative Raw Context Folder

Each initiative has a `raw/` folder for unrefined, high-volume AI context:

```
docs/<initiative>/
├── raw/                        ← Temporary, unrefined dumps
│   ├── agent-discussion.md     ← Advocate agent transcripts
│   ├── error-logs.md           ← Raw error output
│   └── brainstorming.md        ← Unsorted ideas
├── prd/
├── design/
└── ...
```

Rules:
- `raw/` content is NOT indexed by type/stage — it's ephemeral context
- These files are for AI consumption, not human readers
- Never refine raw content in-place — extract to a typed doc when ready
- Can be deleted once the typed docs are written

---

## Integration with write-doc

CRITICAL: `write-doc` MUST invoke `doc-organize` before creating any file in `docs/`.

1. **write-doc** handles: Change Log entries in file content
2. **doc-organize** handles: where the file goes, what it's named, INDEX.md

When user says "write a PRD":
1. → doc-organize determines path + filename
2. → write-doc creates the file with proper Change Log header
