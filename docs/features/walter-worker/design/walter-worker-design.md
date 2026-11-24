---
feature: walter-worker
type: design
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# walter-worker — Design

Requirements are in the [parent PRD](../prd/walter-worker-prd.md). Decisions that span sub-features are in the [parent decision history](../decision-history/walter-worker-decision-history.md). Each area's behavior is in its own design, linked below; this page holds the module map, the rules that apply to every area, and the [glossary](#glossary). The older system design is kept as a part of this design until it is folded in: [ai-coworker design](ai-coworker-design.md); where it disagrees with a sub-feature design, the sub-feature wins.

## Problem Statement

AI coding tools each keep their own configuration, skills, and history in their own formats and places. Without one owner, configurations drift, skills duplicate, past sessions are forgotten, and a tool that writes another tool's files can destroy the user's own settings.

## Solution

One package owns the machine-side setup. Each area is a sub-feature with its own specification, so a change can be checked against a small contract. The areas share three rules (DSGN-B), and share the user's home folder layout under `~/.coworker/`.

## User Stories

The user stories are in the [parent PRD](../prd/walter-worker-prd.md#user-stories) and in each sub-feature's PRD.

## Implementation Decisions

The specifications were backfilled on 2026-11-24 from the code at `a0f4ce0`, so each sub-feature describes what the code does today and records every gap against its requirements as an Open Question rather than hiding it (ARD-B).

## Design

### DSGN-A — Module map

| Area | Code | Specification | Parent requirement |
|---|---|---|---|
| Install, update, uninstall | `setup/*.sh` | [setup-deploy design](../features/setup-deploy/design/setup-deploy-design.md) | PRD-A |
| Configuration commands and sync | `src/coworker/cli.py`, `config.py`, `adapters/`, `semantic_merge.py`, `backup.py` | [core-cli design](../features/core-cli/design/core-cli-design.md) | PRD-B |
| Features | `src/coworker/features/` | [feature-system design](../features/feature-system/design/feature-system-design.md) | PRD-C |
| Session capture and import | `src/coworker/analytics/` | [analytics-listener design](../features/analytics-listener/design/analytics-listener-design.md) | PRD-D |
| Dashboard | `src/coworker/dashboard/` | [analytics-dashboard design](../features/analytics-dashboard/design/analytics-dashboard-design.md) | PRD-D |
| Memory and knowledge | `src/coworker/memory/`, `analytics/knowledge.py` | [memory-platform design](../../memory-platform/design/memory-platform-design.md) | PRD-E |
| Review loop | `src/coworker/autoworker/`, `cli_autoworker.py` | [autoworker design](../../autoworker/design/autoworker-design.md) | PRD-F |

### DSGN-B — Rules every area follows

Three rules span the areas. First, a component that runs inside an AI tool's session (a hook) ignores its own failures, so the session continues; each area lists where it does not yet meet this, which implements PRD-G. Second, a command that overwrites a user-visible file copies it first under `~/.coworker/backups/<timestamp>-<label>/`, restorable with `coworker restore <label>`. Third, every place session content is sent to an outside service is listed in the area's design; today that is the memory platform's language-model calls and the review loop's `claude` sessions, which implements PRD-H.

### DSGN-C — Shared home layout

| Path | Owner |
|---|---|
| `~/.coworker/coworker.yaml`, `project.yaml`, `features/` | core-cli, feature-system |
| `~/.coworker/analytics/` (hooks, session files, database, traces) | analytics-listener |
| `~/.coworker/memory/`, `pending/`, `safety/` | memory-platform |
| `~/.coworker/backups/` | every area that overwrites files |
| `~/.coworker/install-manifest.json` | setup-deploy |

### Sub-problem ownership (子问题归属)

This is an orchestration design: each sub-feature design carries its own ownership table, so the table does not apply here.

## Testing Decisions

Each area's test plan lists its cases; the [parent test plan](../test-plan/walter-worker-test-plan.md) lists how to run them all.

## Out of Scope

Tmux presentation, the self-evolving-agent tree, and skill authoring are outside this feature, as stated in the [parent PRD](../prd/walter-worker-prd.md#out-of-scope).

## Further Notes

The legacy documents in this feature's `prd/`, `design/`, `decision-history/`, `plan/`, `spec/`, `state/`, and `work-review/` folders predate the current spec standard and fail its path and frontmatter checks. They are kept and linked as parts until the owner decides how to fold or retire them (QUES-A).

## Alternatives Considered

One large specification for the whole package was rejected: it would exceed the size limit, and a reader checking one change would have to load all of it.

## Drawbacks

Facts that span areas, such as the home folder layout, live here and must be kept in step with the sub-features.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| A sub-feature and a legacy document disagree | The sub-feature wins; legacy documents are marked as parts to fold in |
| The specifications drift from the code again | Each sub-feature cites the commit it was checked against |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | Should the legacy documents in `prd/`, `design/`, `decision-history/`, `plan/`, `spec/`, `state/`, and `work-review/` be folded into the sub-features and removed, renamed to the current standard, or kept as they are? | Kept and linked as parts on 2026-11-24; restructuring needs the owner's decision. | cicidi | no |
| **QUES-B** | The sub-features record blocking code gaps: setup-deploy QUES-C to QUES-F, core-cli QUES-A, QUES-B, QUES-L, QUES-M, QUES-O, QUES-S, QUES-T, analytics-listener QUES-A, memory-platform QUES-A and QUES-B, autoworker QUES-A. Which are fixed first? | Listed in each sub-feature design; setup-deploy QUES-C to QUES-E have a fix in walter-worker PR #17. | cicidi | no |

## Reversibility

This page and the sub-feature specifications are documents; any of them can be reverted through version control. The behaviors they describe are reversed as each sub-feature's Reversibility section states.

## Glossary

Terms used across walter-worker's specifications. Sub-feature designs may add their own Terms tables; a term defined here means the same everywhere.

| Term | Meaning |
|---|---|
| Skill | An instruction file (`SKILL.md`, plus files beside it) an AI coding tool loads when a task matches its description |
| Command | A Claude Code slash command: one markdown file under `.claude/commands/` |
| Hook | A command Claude Code runs on an event, registered in `~/.claude/settings.json` |
| MCP | Model Context Protocol, the way AI tools connect to external tool servers |
| Feature | A named piece of work that may span projects, recorded under `~/.coworker/features/` |
| `CLAUDE.local.md` | A personal, uncommitted instruction file Claude Code reads at the start of every session |
| Manifest | `~/.coworker/install-manifest.json`, the installer's record of what it wrote |
| Backup label | The word at the end of a backup folder's name, naming the command that took it |
| Transcript | The file Claude Code keeps for each session under `~/.claude/projects/` |
| Vector store | A database that finds text by meaning |
| Knowledge graph | `~/.coworker/memory/graph.json`, typed nodes joined by typed edges |
| Headless session | A Claude Code run started with `-p`, which runs one prompt and exits |
| Wrong-history | Recorded past mistakes and the rules learned from them |
| Open Question | A tracked gap or undecided point, with an owner and a blocking flag, in a design's Open Questions table |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft by another agent (never committed) |
| 0.2 | 2026-11-24 | Written as the parent entry with the module map, shared rules, home layout, and glossary; the legacy design linked as a part (ARD-A, ARD-B) |
