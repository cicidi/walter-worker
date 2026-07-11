# CLAUDE.md Design — Three-Layer Architecture

<!-- PROTECTED -->
Project: ai-coworker
Last Updated: 2026-07-01
Initiative: claude-md-design
<!-- END PROTECTED -->

## Overview

Redesign how CLAUDE.md works across ai-coworker — separating concerns into three distinct layers: Global (programming philosophy), Project (meta-controller), Skill (workflow execution). All configuration MUST be compatible with both Claude Code and OpenCode. No tool-specific features (e.g., `.claude/rules/`) unless they have an OpenCode equivalent.

**Evidence base**: [CLAUDE.md Engineering: Best Practices and Anti-Patterns](./2026-07-01-claude-md-best-practices-paper.md) — systematic literature review of 22 sources including Anthropic Applied AI, Chroma context-rot experiments, Superpowers (244k stars), and Andrej Karpathy's behavioral principles. This design was validated against 6 best practices and 5 anti-patterns identified in the review.

### Core Decision

**Cross-tool compatibility first.** Every feature in this design must work in both Claude Code and OpenCode without translation. OpenCode reads `CLAUDE.md` as a fallback when `AGENTS.md` doesn't exist — so `CLAUDE.md` is the shared format.

## Architecture

```
┌────────────────────────────────────────────────┐
│  Global CLAUDE.md (~/.claude/CLAUDE.md)         │
│  Karpathy 8 Programming Principles | <100 lines │
│  Shared across all projects, rarely updated      │
├────────────────────────────────────────────────┤
│  Project CLAUDE.md (<project>/CLAUDE.md)         │
│  Lean Meta-Controller, committed to git          │
│  - Project Context (non-discoverable only)        │
│  - Project Relationships (upstream/downstream)   │
│  - Knowledge Repo (docs/ structure)              │
│  - Context Management Framework                  │
│  - Workflow Decision Heuristics (auto + confirm)  │
│  - Skill References (descriptions not catalog)    │
│  - Auto Memory + Compaction Survival             │
│  - Local Override → read CLAUDE.local.md         │
├────────────────────────────────────────────────┤
│  CLAUDE.local.md (<project>/CLAUDE.local.md)     │
│  Personal, NOT committed to git                  │
│  - Config Paths (~/.coworker/project.yaml)       │
│  - Initiative Context (injected by coworker)      │
│  - Reference Docs (paths to relevant documents)   │
│  - Current Task State (→ docs/state-{task}.md)   │
│  - Personal Workflow Preferences                 │
├────────────────────────────────────────────────┤
│  Skills (SKILL.md × N from skill-factory)        │
│  Auto-matched by task description                │
│  TDD | Loop Engineering | Context Management     │
└────────────────────────────────────────────────┘
```

## 1. Global CLAUDE.md

### Source
Karpathy's 8 principles from [andrej-karpathy-skills/CLAUDE.md](https://github.com/cicidi/andrej-karpathy-skills/blob/main/CLAUDE.md). No additions unless cross-tool verified.

### Content (exact mapping)

| # | Principle | Essence |
|---|-----------|---------|
| 1 | Ask and Confirm Before Coding | Surface tradeoffs, don't hide confusion |
| 2 | Evidence and Reasoning | Ground decisions in docs/code, not assumptions |
| 3 | Simplicity First | Minimum code to solve, no speculation |
| 4 | Surgical Changes | Touch only what you must, match existing style |
| 5 | Goal-Driven Execution | Define success criteria, loop until verified |
| 6 | Decompose Complex Tasks | Split before starting, re-prioritize as you learn |
| 7 | Plan and Track Progress | TodoWrite, visible plans, parallelize independent subtasks |
| 8 | Recommend Model Upgrade | Flag when a task needs stronger model |

### Location
`~/.claude/CLAUDE.md` (Claude Code) — OpenCode reads this as fallback when `~/.config/opencode/AGENTS.md` doesn't exist.

### Update mechanism
`ai-worker-update` Phase 2 — semantic merge against canonical template. Protect user additions, `<!-- PROTECTED -->` blocks, and initiative context.

### Size target
**< 100 lines.** Keep it lean. Philosophy only. No tool references, no project-specific rules.

## 2. Project CLAUDE.md

### Purpose
A **lean meta-controller** that teaches the AI to self-evaluate each task and determine the right workflow. It does NOT duplicate skill instructions — it provides the decision framework.

### Sections

#### 2.1 Project Identity

**Do NOT list auto-discoverable information.** Language, framework, package manager, test/lint commands — the AI can discover these by reading `pyproject.toml`/`package.json`/`go.mod`. Listing them wastes limited context budget (Hong et al., 2025; Rajasekaran et al., 2025).

Include only fundamental, slow-changing project identity:
- Repo URL (defines the project)
- Local path (if non-obvious)

Architecture quirks and project-specific conventions can be added by the team during `ai-coworker-setup-in-project` interview.

#### 2.1.1 Project Relationships
List upstream / downstream / peer projects:

```markdown
## Project Relationships
| Project | Role | Description |
|---------|------|-------------|
| auth-service | upstream | Authentication API consumed by this project |
| user-service | peer | Shared user data model |
| frontend-app | downstream | Consumes this project's API |
```

The actual project catalog config file path is personal — listed in `CLAUDE.local.md`.

#### 2.1.2 Knowledge Repo
Shared project documentation:

```markdown
## Knowledge Repo
- Specs: `docs/specs/`
- Discussions: `docs/discussion/`
```

#### 2.1.3 Team Links
Shared external references for the team:

```markdown
## Team Links
- Wiki: https://wiki.internal/team
- Slack: #team-channel
- API Docs: https://api.internal.docs
```

#### 2.2 Document Map
All doc locations relative to project root:
```
docs/
  specs/         → design documents, spec/prd conclusions (committed, shared)
  discussion/    → discussion records, decision logs (committed, shared)
  state-{task}.md → per-task progress state (gitignored, personal)
```

Initiative reference docs are listed in `CLAUDE.local.md` (personal, not committed).

#### 2.3 Context Management Framework

**Rule**: Before any non-trivial task, evaluate whether external context is needed. Skip for trivial fixes.

**Five categories of information**:

| Category | Source | Storage | Priority |
|----------|--------|---------|----------|
| 1. What to build | PRD, spec, conversation, issue | `docs/specs/` | Read first |
| 2. Discussion & decisions | Slack, wiki, GitHub comments | `docs/discussion/` | Read when unclear |
| 3. Implementation plan | Derived from category 1 & 2 | `docs/specs/` | Use as guide |
| 4. Verification plan | Tests, acceptance criteria | `docs/specs/` | Loop until pass |
| 5. Historical archive | Prior sessions, state files | `docs/state-{task}.md` | Resume context |

**Information channels**: Slack, wiki, PRD, GitHub issues/PRs, external links. Only pull from channels actively configured for the project.

**AI self-assessment checklist** before starting work:
1. Is the goal clear? If not → need clarification from user
2. Is there a PRD/spec? If yes → read it first
3. Were there prior discussions? If yes → read docs/discussion/
4. Was this task started before? If yes → read docs/state-{task}.md
5. Are all referenced files actually read? If not → read them NOW

#### 2.4 Workflow Decision Heuristics

**Two-tier decision rule**: At the start of every new task, analyze characteristics. Route to auto or confirm.

**Low-risk → auto-execute, no confirmation**:
| Task characteristics | Action |
|---------------------|--------|
| Clear requirements, simple change, low risk | Direct implementation, skip workflow prompt |
| Bug fix with clear reproduction, small scope | bug-hunt → fix → verify, no confirmation |
| Minor refactoring with existing tests passing | Edit → verify tests pass, no confirmation |

**Medium/high risk → suggest workflow, confirm first**:
| Task characteristics | Suggested workflow |
|---------------------|--------------------|
| Unclear requirements, large scope | brainstorming → spec → discuss |
| Clear requirements, complex code, high bug risk | TDD + loop engineering |
| Large project, lots of discussion AND code | brainstorming + TDD + loop |
| Writing/updating documentation | doc conventions skill |

**Decision logic** (applied per task):
```
if clarity == clear AND scope == small AND risk == low:
    → auto-execute, no prompt
else:
    → analyze → suggest workflow → ask user to confirm
```

**Escape hatch**: These heuristics bias toward caution. For trivial, reversible operations (reading files, running `ls`/`grep`, simple logging), use judgment and proceed without overthinking. The goal is to avoid wasted time on "confirm before git status" — not to create a bureaucracy.

**Confirmation prompt** (only when needed):
```
Task analysis:
  - Goal: [what to achieve]
  - Clarity: somewhat clear / unclear
  - Scope: medium / large
  - Code risk: medium / high
  - Related docs found: [files]

Recommended workflow: [name]
Reason: [why]

Proceed? [y / n / suggest alternative]
```

#### 2.5 Local Override

**Rule**: If `CLAUDE.local.md` exists in the project root, read it immediately after reading CLAUDE.md. It contains personal working context that is NOT committed to git.

```markdown
## Local Override

If `CLAUDE.local.md` exists in this project root, read it now.
- Claude Code natively auto-loads this file
- OpenCode: use Read tool to load it on startup

It contains:
- Active initiative context (injected by coworker `initiative activate`)
- Current task state reference (→ docs/state-{taskname}.md)
- Personal workflow preferences for this project
```

**Content of CLAUDE.local.md**:

1. **Initiative Context** (injected by coworker):
```markdown
<!-- INITIATIVE:<name> -->
## Active Initiative: <name>
> <description>
### Projects in scope
### Links
### Reference Docs
<!-- END INITIATIVE -->
```

2. **Config File Paths** (personal, installation-specific):
```markdown
## Config Paths
- Project Catalog: ~/.coworker/project.yaml
- Local Config: .local_config.yaml
```

3. **Current Task State**: Reference to active `docs/state-{task}.md`

4. **Personal Preferences**: Override any project-level defaults

**Cross-tool**: Claude Code natively loads `CLAUDE.local.md`. OpenCode does not — but the explicit instruction in project CLAUDE.md ensures it reads it via Read tool.

#### 2.6 Skill References

**Not a catalog — descriptions that enable auto-match.**

```
When a task matches a skill's domain, invoke that skill:
- TDD / auto-tdd: test-first development, red-green-refactor cycles
- bug-hunt: systematic debugging with hypothesis-test-confirm loop
- brainstorming: creative work, feature design, exploration
- commit: git commits following conventional commits format
- doc-*: documentation workflows (create, merge, protect)
- self-heal / self-analyze: logging corrections, pattern analysis
```

**Auto-match principle**: Skill descriptions should be specific enough that the AI can unambiguously determine when to use them. If a human can't tell which skill applies, the AI can't either.

#### 2.7 Auto Memory

**Auto memory** is a complementary system to CLAUDE.md:
- **CLAUDE.md** = upfront, explicit rules written by the user
- **Auto memory** = learned rules written by the AI during sessions

Both Claude Code and OpenCode support auto-memory mechanisms where the AI writes its own learnings to persistent storage. The project CLAUDE.md should acknowledge this:

```markdown
## Auto Memory
- CLAUDE.md contains upfront rules — read these first
- Auto memory (if enabled) contains learnings from prior sessions
- When auto memory exists, read it after CLAUDE.md but before starting work
- Conflict resolution: upfront rules (CLAUDE.md) override learned rules (auto memory)
```

**Cross-tool note**: Auto-memory storage locations differ by tool. CLAUDE.md guidance should be tool-agnostic ("read your persistent memory") rather than tool-specific paths.

**Memory safety**: Auto-memory is separate from CLAUDE.md. Never let auto-memory inject back into CLAUDE.md without human review. Store auto-memories in a separate location (e.g., tool-managed memory storage). Periodically audit and prune stale memories. Bad agents writing bad memories into persistent instructions → context pollution over time.

#### 2.8 Compaction Survival

After `/compact` (Claude Code) or session truncation (OpenCode), only the project-root CLAUDE.md is guaranteed to be re-injected. All prior context, nested rule files, and conversation history are lost.

**Survival rules** for CLAUDE.md guidance:

```markdown
## Compaction Survival
After context compaction or session truncation:
1. Project CLAUDE.md is always re-injected — use it as your reset anchor
2. docs/state-{task}.md survives on disk → re-read it to resume progress
3. Initiative context is re-injected if active → re-read reference docs
4. Previous conversation is lost → rely on state files, not memory
5. Re-run the context self-assessment checklist from start
```

**Implications for design**:
- `docs/state-{task}.md` is the primary mechanism for surviving compaction — write progress frequently
- CLAUDE.md must be self-contained enough to bootstrap without prior context
- Skills loaded before compaction must be re-loaded after
- Auto memory (if enabled) may or may not survive compaction (tool-dependent)
- **Compaction timing**: Compact or write state at 50-70% of context window. Don't wait until 95% — the agent may be operating from a degraded state by then (Chroma research showed model performance degrades sharply at longer contexts). Write state BEFORE compaction, not during.

### Size target
**< 200 lines total.** Following Anthropic's guidance: longer files consume more context and reduce adherence. Push details to skills, not CLAUDE.md.

### Priority Ordering
**Critical rules must be at the top.** Agents scan, they don't read deeply. Superpowers found a 94% PR rejection rate from agents not reading their own CLAUDE.md. Structure sections by importance:
1. Most critical behavioral rules first (guardrails, enforcement rules)
2. Context/identity second
3. Heuristics and guidelines third
4. Reference material last (paths, URLs)

### Generation
`coworker init` scans the project and generates sections 2.1, 2.2, 2.4. Sections 2.3, 2.5, 2.6, 2.7, 2.8 are merged from canonical templates maintained in ai-coworker.

### Update mechanism
`ai-worker-update` Phase 3 — per-project semantic merge. Sections 2.1, 2.2 (project-specific) are KEPT by default. Sections 2.3, 2.4, 2.6, 2.7, 2.8 (canonical templates) can be OVERWRITTEN or MERGE_ADDed from updated templates.

## 3. Docs Directory Structure

```
<project-root>/
  docs/
    specs/                    ← Design docs, spec conclusions, PRDs
      2026-07-01-feature-x-design.md
      2026-06-15-api-spec.md
      prd-core-v2.md
    discussion/               ← Discussion records, decision logs
      2026-07-01-architecture-decisions.md
      slack-excerpts-auth-flow.md
    state-feature-x.md        ← Per-task progress state
    state-auth-migration.md
    rules/                    ← Optional, shared rule files (referenced via @path)
      testing-conventions.md
```

CLAUDE.md references these paths so the AI knows where to look.

### Paths in CLAUDE.md

```markdown
## Document Map
- Specs: `docs/specs/` — design documents, spec conclusions
- Discussions: `docs/discussion/` — discussion records, decision logs
- State files: `docs/state-{taskname}.md` — per-task progress
```

## 4. Skill-Level Workflows

Skills are the execution layer. Each skill defines ONE workflow. Project CLAUDE.md teaches the AI WHEN to use them, not HOW.

### Skill structure (existing `SKILL.md` format maintained)
```yaml
---
name: tdd
description: Test-first development with red-green-refactor cycles
compatibility: claude-code,opencode
triggers: test coverage, bug fix, feature implementation
---
```

### Key design constraints for skills
1. **Auto-match over manual invoke**: Write descriptions so the AI naturally determines relevance. No `must invoke skill` wrappers unless truly universal.
2. **Rigid vs Flexible**: TDD, bug-hunt = rigid (follow exactly). Brainstorming, commit = flexible (adapt to context).
3. **Cross-tool in SKILL.md**: Skills work in both Claude Code and OpenCode. Tool-specific references use `references/` for equivalents.
4. **Size awareness**: Skills loaded into context cost tokens. Keep focused.

## 5. Initiative Context Integration

### Initiative = task context

An initiative is more than just links and project references. It carries the **task goal, approach, and testing method** — the things that change per task and belong in CLAUDE.local.md, not in the committed project CLAUDE.md.

### InitiativeConfig fields

| Field | Injected into local.md as | Purpose |
|-------|--------------------------|---------|
| `goal` | Current Task State > Goal | What this task is trying to achieve |
| `approach` | Current Workflow > Approach | How to tackle it (TDD, brainstorming→spec, etc.) |
| `testing` | Current Workflow > Testing | How to verify correctness |
| `projects` | Projects in scope | Which projects are involved |
| `links` | Links | External references (wikis, PRDs) |
| `decisions` | Key Decisions | What was decided and why |
| `reference_docs` | Reference Docs | Local files the AI must read before starting |

### Injection target: CLAUDE.local.md

Initiative context is personal working context — it changes as you switch tasks. Injecting into `CLAUDE.local.md` keeps it out of the committed project CLAUDE.md.

### During initiative creation
The `initiative-create` skill interviews the user for goal, approach, testing, projects, links, decisions, and reference docs. These are saved to the initiative YAML.

### During initiative activation
When `initiative activate` is called, the initiative context block is injected into `<project>/CLAUDE.local.md`. The block includes all fields above, filling the "Current Task State" and "Current Workflow" sections.

### Deactivation
When `initiative deactivate` is called, remove the initiative block from `CLAUDE.local.md`.

### AI behavior (from project CLAUDE.md's Local Override section)
When project CLAUDE.md is loaded, the AI reads `CLAUDE.local.md`. If initiative context is present:
1. Read every file listed under Reference Docs
2. Read project CLAUDE.md files for in-scope projects
3. Fetch external links if needed for understanding
4. Report back: "Read X files, Y links. Ready to proceed."
5. Use the goal, approach, and testing fields to guide task execution

## 6. Install / Update / Init Flow

### Global CLAUDE.md

- On install: copy canonical template (Karpathy 8 principles) to `~/.claude/CLAUDE.md`
- If already exists: **do NOT override**. Show warning: "Global CLAUDE.md exists. Compare with latest template and merge manually if needed."
- On update (`ai-worker-update`): semantic merge, preserving user additions

### Project CLAUDE.md — Interactive Setup

The `ai-coworker-setup-in-project` skill handles project-level setup via interview:

1. **Scan project**: detect language, framework, deps (for context, not for inclusion in CLAUDE.md)
2. **Interview** (one question at a time):
   - Project relationships: any upstream/downstream/peer projects?
   - Knowledge repo: where are PRDs, specs, wiki, external docs?
   - Architecture quirks: anything not obvious from scanning?
   - Testing conventions: any project-specific test patterns?
   - Team guardrails: any additional team rules beyond defaults?
3. **Generate Project CLAUDE.md** with:
   - Mandatory Guardrails (always included)
   - Critical rules (Local Override, Auto Memory, Compaction)
   - Interview answers (relationships, knowledge, quirks)
   - Canonical sections (Context Management, Workflow Heuristics)
4. **Generate CLAUDE.local.md** with:
   - Auto-detected available skills (from `~/.claude/commands/` etc.)
   - Config paths, task state template, personal preferences placeholder
5. **Create docs/ structure**: `docs/specs/`, `docs/discussion/`
6. **Add to .gitignore**: `CLAUDE.local.md`, `docs/state-*.md`
7. **Configure hooks**:
   - Claude Code: `coworker state-update` hook on Stop event
   - OpenCode: `coworker *` allow permission in opencode.json

### Update (`ai-worker-update`)
1. Pull latest ai-coworker and skill-factory
2. Semantic merge Global CLAUDE.md (canonical template vs current)
3. Per-project:
   - Semantic merge canonical sections (Guardrails, Context Management, Workflow Heuristics, Compaction)
   - Keep project-specific sections (relationships, knowledge repo, user customizations)
4. Regenerate CLAUDE.local.md skills section (re-scan for new/removed skills)
5. Re-run install for analytics hooks, MCP config
6. Sync to all IDEs

### Init (`coworker init`)
Quick non-interactive mode — generates minimal CLAUDE.md with all canonical sections, no interview:
1. Auto-detect project context (scan)
2. Generate Project CLAUDE.md with default sections
3. Generate CLAUDE.local.md with auto-detected skills
4. Create docs/ structure
5. User can then run `ai-coworker-setup-in-project` skill for full interactive interview

## 7. Cross-Tool Compatibility Rules

### Mandatory
| Rule | Reason |
|------|--------|
| `CLAUDE.md` as shared format | OpenCode reads it as AGENTS.md fallback |
| No `.claude/rules/` unless `opencode.json` `instructions` also configured | Feature mismatch between tools |
| Use each tool's enforcement mechanism separately | Claude Code: hooks in `~/.claude/settings.json`. OpenCode: permissions in `opencode.json`. Same intent, different configs. |
| Skill SKILL.md must declare `compatibility` field | `claude-code,opencode` or single tool |

### Enforcement Layer (per tool)

Purpose: Hard rules that must be enforced (never commit secrets, never push to main, never delete without confirmation). CLAUDE.md provides guidance, enforcement provides guarantees.

**Claude Code — Hooks** (`~/.claude/settings.json`):
```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash(git push*)", "hooks": [{"type": "command", "command": "deny-git-push.sh"}]},
      {"matcher": "Bash(rm *)", "hooks": [{"type": "command", "command": "confirm-delete.sh"}]}
    ],
    "Stop": [
      {"matcher": "", "hooks": [{"type": "command", "command": "log-session.sh"}]}
    ]
  }
}
```

**OpenCode — Permissions** (`opencode.json`):
```json
{
  "permission": {
    "bash": {
      "*": "ask",
      "git *": "allow",
      "git push *": "deny",
      "rm *": "ask",
      "grep *": "allow",
      "ls *": "allow"
    }
  }
}
```

**Design rule**: Enforcement configs generated by `coworker sync` to each tool's config file. Same set of rules, different configuration formats. CLAUDE.md only provides guidance, never enforcement.

### When differences exist
If a feature only works in one tool:
- **Claude Code only** → put in `.claude/` directory, document in CLAUDE.md that it's CC-only
- **OpenCode only** → put in `opencode.json`, same documentation approach
- **Both** → put in `CLAUDE.md` and optionally duplicate in `AGENTS.md`

### Cross-tool degradation strategy
Don't design for the lowest common denominator. Use each tool's strengths where possible:
- If OpenCode lacks compact → rely only on `docs/state-{task}.md` and periodic user-initiated session restarts
- If Claude Code lacks auto-mode permissions → use hooks for enforcement
- Design gracefully degrades: if a tool lacks a feature, the agent still functions via the lower-common-denominator path in CLAUDE.md

### Preference
OpenCode's `AGENTS.md` can be a symlink to `CLAUDE.md` for single-source-of-truth:
```bash
ln -sf CLAUDE.md AGENTS.md
```
This is the current ai-coworker install behavior (Step 12 of install.sh).

## 8. Size Budget

| File | Target | Purpose |
|------|--------|---------|
| Global CLAUDE.md | < 100 lines | Karpathy 8 principles |
| Project CLAUDE.md | < 200 lines | Meta-controller + project context |
| SKILL.md (per skill) | < 300 lines | One workflow, self-contained |
| docs/specs/*.md | No limit | Design documents (not in context by default) |
| docs/state-{task}.md | < 100 lines | Progress tracking, loaded on demand |

Token budget is finite. Every line in CLAUDE.md costs context in every session. Be ruthless about what goes in.

## 9. Migration Path

### From current project CLAUDE.md (81 lines, mixed structure)

Current sections and their new locations:

| Current section | New location | Action |
|----------------|-------------|--------|
| Identity | Project CLAUDE.md §2.1 | Keep, enhance with init scan |
| Core Philosophy | Dropped from project | Covered by Global CLAUDE.md (Karpathy 1, 2, 3, 6) and skills |
| Guardrails (OWASP) | `docs/rules/security.md` or skill | Extract to dedicated security skill/rules |
| Git Conventions | Skill: `commit` skill | Covered by commit skill |
| Code Quality | `docs/rules/code-quality.md` or skill | Extract to rules or skill |
| Self-Healing | Skill: `self-heal` / `self-analyze` | Already skills, remove from CLAUDE.md |
| Issue-Driven Development | Skill or dropped | Covered by bug-hunt and general workflow heuristics |
| MCP Usage | Skill: MCP config skill (if needed) | Remove from CLAUDE.md, tools tell themselves |
| Project Context | Project CLAUDE.md §2.1 | Keep, enhance |

### Phase 1: Template
Create canonical Project CLAUDE.md template in ai-coworker.

### Phase 2: Init integration
Update `coworker init` to generate the new structure.

### Phase 3: Update integration  
Update `ai-worker-update` semantic merge logic for new sections.

### Phase 4: Migration tool
`coworker migrate-claude-md` to convert existing projects to new format.
