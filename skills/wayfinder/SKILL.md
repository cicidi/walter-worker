---
name: wayfinder
description: |
  Use when planning work too large for one agent session. Charts a shared map
  of decision briefs on the issue tracker, resolves them one at a time until
  the route to the destination is clear.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - wayfinder
    - chart map
    - decision mapping
    - plan large work
  when_to_use: |
    When work is too big for one session and the path from here to the
    destination isn't visible. When decisions need shared, persistent tracking
    across multiple sessions.
  when_not_to_use: |
    When the work fits in one session. When requirements are already fully
    specified with tickets ready to implement. When you just need a quick
    spec — use to-spec instead.
  audience:
    - developers
    - architects
    - tech leads
  source_author: mattpocock
  source_url: https://github.com/mattpocock/skills/blob/main/skills/engineering/wayfinder/SKILL.md
---

A loose idea has arrived — too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet. Wayfinding is about finding that way, not charging at the destination. This skill charts the way as a **shared map** on the repo's issue tracker, then works its **decision briefs** — questions whose resolution is a decision, not slices of a build to execute — one at a time until the route is clear.

The destination varies per effort, and naming it is the first act of charting — it shapes every brief. It might be a spec to hand off and iterate on, a decision to lock before planning starts, or a change made in place like a data-structure migration. The map is domain-agnostic — engineering work, course content, whatever fits the shape.

## Plan, don't do

Wayfinder is **planning** by default: each brief resolves a decision, and the map is done when the way is clear — nothing left to decide before someone goes and does the thing. The pull to just do the work is usually the signal you've reached the edge of the map and it's time to hand off. An effort can override this in its **Notes** — carrying execution into the map itself — but absent that, produce decisions, not deliverables.

## Refer by name

Every map and brief is an issue, so it has a **name** — its title. In everything the human reads — narration, the map's Decisions-so-far — refer to it by that name, never by a bare id, number, or slug. A wall of `#42, #43, #44` is illegible; names read at a glance. The id and URL don't vanish — a name wraps its link — but they ride *inside* the name, never stand in for it.

## The Map

The map is a single issue on this repo's issue tracker, labelled `wayfinder:map` — the canonical artifact. Its briefs are child issues of the map.

The map is an **index**, not a store. It lists the decisions made and points at the briefs that hold their detail; a decision lives in exactly one place — its brief — so the map never restates it, only gists it and links.

**Where the map, its child briefs, blocking, and frontier queries physically live is tracker-specific.** The issue tracker configuration should have been provided via the project's init flow. If no tracker has been configured, default to the local-markdown tracker (issues as files under `.scratch/`). Consult the tracker doc's "Wayfinding operations" section for how _this_ repo expresses them.

### The map body

The whole map at low resolution, loaded once per session. Open briefs are **not** listed — they are open child issues, found by query.

```markdown
## Destination

<what reaching the end of this map looks like — the spec, decision, or change this effort is finding its way to. One or two lines; every session orients to it before choosing a brief.>

## Notes

<domain; skills every session should consult; standing preferences for this effort>

## Decisions so far

<!-- the index — one line per closed brief: enough to judge relevance, then zoom the link for the detail the brief holds -->

- [<closed brief title>](link) — <one-line gist of the answer>

## Not yet specified

<!-- see "Fog of war": in-scope fog you can't brief yet; graduates as the frontier advances -->

## Out of scope

<!-- see "Out of scope": work ruled beyond the destination; closed, never graduates -->
```

### Briefs

Each brief is a **child issue** of the map; the tracker's issue id is its identity. Its body is the question, sized to one 100K token agent session:

```markdown
## Question

<the decision or investigation this brief resolves>
```

Each brief carries a `wayfinder:<type>` label — one of `research`, `prototype`, `grilling`, `task` (see [Brief Types](#brief-types)).

A session **claims** a brief by assigning it to the dev driving the map, **first**, before any work, so concurrent sessions skip it. That assignee _is_ the claim: an open, unassigned brief is unclaimed.

Blocking uses the tracker's **native** dependency relationship — essential because it renders the frontier _visually_ in the tracker's own UI, so the human sees what's takeable without opening the map. Only a tracker that lacks native blocking falls back to a body convention. A brief is **unblocked** when every brief blocking it is closed; the **frontier** is the open, unblocked, unclaimed children — the edge of the known.

The answer isn't part of the body — it's recorded on resolution (see [Work through the map](#work-through-the-map)). Assets created while resolving a brief are linked from the issue, not pasted in.

## Brief Types

Every brief is either **HITL** — human in the loop, worked *with* a human who speaks for themselves — or **AFK**, driven by the agent alone. A HITL brief only resolves through that live exchange; the agent never stands in for the human's side of it (a grilling agent that answers its own questions has broken this).

- **Research** (AFK): Reading documentation, third-party APIs, or local resources like knowledge bases to surface a fact a decision waits on. Resolved by a `/research` **subagent**. Use when knowledge outside the current working directory is required.
- **Prototype** (HITL): Raise the fidelity of the discussion by making a cheap, rough, concrete artifact to react to — an outline, a rough take, a stub, or UI/logic code via the /prototype skill. Links the prototype as an asset. Use when "how should it look" or "how should it behave" is the key question.
- **Grilling** (HITL): Conversation via the /grilling and /domain-modeling skills, one question at a time. The default case.
- **Task** (HITL or AFK): Manual work that must happen before a *decision* can be made — nothing to decide, prototype, or research, but the discussion is blocked until it's done. Signing up for a service so its API can be judged, provisioning access, moving data so its shape can be seen. This is the one type that *does* rather than decides — and it earns its place by unblocking a decision, not by delivering the destination. The agent drives it alone where it can (AFK); otherwise it hands the human a precise checklist (HITL). Resolved when the work is done; the answer records what was done and any resulting facts (credentials location, new URLs, row counts) later briefs depend on.

## Pluggable Skill Interfaces

Wayfinder depends on four capabilities. Each is an interface with a default
implementation; you can replace any of them with your own skill at install time.

| Interface | Purpose | Default | Your Replacement |
|---|---|---|---|
| **interview** | Grill user, one question at a time, write CONTEXT.md + ADRs | `grill-with-docs` + `domain-modeling` | (ask on install) |
| **investigate** | Read docs/APIs/source, produce cited markdown file | `research` (ai-coworker) | (ask on install) |
| **prototype** | Build throwaway artifact to answer a design question | `prototype` | (ask on install) |
| **tracker** | Issue CRUD — create, list, label, assign, close | `gh` CLI (GitHub Issues) | (ask on install) |

### Configuration

On first install, the user is asked one question per interface:

> For `<interface>` (`<purpose>`), default is `<default>`. Replace or keep?

Answers can be:
- **"keep" / "default"** — use the default implementation
- **"use <name>"** — use a named skill (must exist in the project)
- **"skip"** — that brief type is unavailable

Choices are recorded so the skill reads them on every invocation.

## Fog of war

The map is _deliberately_ incomplete: don't chart what you can't yet see. Beyond the live briefs lies the **fog of war** — the dim view of decisions and investigations you can tell are coming but can't yet pin down, because they hang on questions still open. Resolving a brief clears the fog ahead of it, graduating whatever's now specifiable into fresh briefs — one at a time, until the way to the destination is clear and no briefs remain.

The map's **Not yet specified** section is where that dim view is written down: the suspected question, the area to revisit later. It's the undiscovered frontier _toward_ the destination — everything here is in scope, just not sharp enough to brief. Write as loosely or as fully as the view allows; it doubles as a signpost for collaborators reading where the effort is headed.

**Fog or brief?** The test is whether you can state the question precisely now — _not_ whether you can answer it now.

- **Brief when** the question is already sharp — even if it's blocked and you can't act on it yet.
- **Not yet specified when** you can't yet phrase it that sharply. Don't pre-slice the fog into brief-sized pieces: it's coarser than a brief, and one patch may graduate into several briefs, or none, once the frontier reaches it.

**Not yet specified** excludes what's already decided (Decisions so far), what's already a live brief, and what's out of scope (the next section).

## Out of scope

Fog only ever gathers _toward_ the destination. The destination fixes the scope, so work beyond it is **out of scope** — it isn't fog, and it doesn't belong in **Not yet specified**. It gets its own **Out of scope** section on the map: work you've consciously ruled out of _this_ effort. Scope, not sharpness, lands it here.

Out-of-scope work never graduates — the frontier stops at the destination — so it returns only if the destination is redrawn, and then as a fresh effort, not a resumption.

Ruling something out of scope is a scoping act, not a step on the route. When a brief that already exists turns out to sit past the destination — mis-scoped in while charting, or exposed by a resolution — **close it** (a closed brief is unambiguously off the frontier) and leave one line in the **Out of scope** section: the gist plus why it's out of scope, linking the closed brief. It stays out of **Decisions so far**, which records the route actually walked — a scope boundary isn't a step on it.

## Doc-Organize: MkDocs-Ready

Every document created or moved during a Wayfinder session must be MkDocs-ready
— deployable as a GitHub Pages website without additional conversion.

`doc-organize` runs as an inline discipline, not a separate checkpoint:
- INDEX.md is maintained (new docs added, moved docs updated)
- File naming follows mkdocs conventions (kebab-case, no special chars)
- Directory structure matches mkdocs nav hierarchy
- `mkdocs.yml` nav is updated when new sections are added

This is a standing requirement for every document-producing step.

## Spec Creation & Doc-Review Checkpoint

After all briefs are resolved and the map is done, before handing off to
`to-tickets`:

```
Wayfinder map done
       |
       v
    to-spec
       |
       +-- Synthesizes all brief conclusions into a spec (PRD)
       +-- Creates a Jira ticket for the spec itself
       |
       v
    doc-review checkpoint
       |
       +-- Reviews: spec + all closed briefs + CONTEXT.md + ADRs
       +-- Checks: consistency, completeness, no contradictions
       +-- Verifies: mkdocs-ready (INDEX.md, nav, naming)
       |
       v
    Review passed?
       |
   YES +-- to-tickets -> creates Jira build tickets
   NO  +-- fix documents, re-review
```

The doc-review checkpoint is a gate — it must pass before `to-tickets` can run.
This ensures all documents are consistent, complete, and deployable before any
implementation begins.

### Entity Relationships

```
N briefs (decisions) -> 1 spec (PRD, a Jira ticket) -> M Jira tickets (build)

  Map:      1 issue, label wayfinder:map
  Brief:    N child issues, label wayfinder:<type>
            (research | grilling | prototype | task)
  Spec:     1 issue, label ready-for-agent (created by to-spec)
  Tickets:  M issues, label ready-for-agent (created by to-tickets)
```

## Pipeline

```
wayfinder -> to-spec -> doc-review -> to-tickets -> auto-tdd
 (decide)    (write)    (verify)      (ticket)     (build)
```

## Invocation

Two modes. Either way, **never resolve more than one brief per session** — with the exception of research briefs.

### Chart the map

User invokes with a loose idea.

1. **Name the destination.** Run a `/grilling` and `/domain-modeling` session to pin down what this map is finding its way to — the spec, decision, or change. The destination fixes the scope, so it's settled first.
2. **Map the frontier.** Grill again, **breadth-first** this time: fan out across the whole space rather than deep on any one thread, surfacing the open decisions and the first steps takeable now. **If this surfaces no fog** — the way to the destination is already clear, the whole journey small enough for one session — you don't need a map. Stop and ask the user how they'd like to proceed.
3. **Create the map** (label `wayfinder:map`): Destination and Notes filled in, Decisions-so-far empty, the fog sketched into **Not yet specified**.
4. **Create the briefs you can specify now** as child issues of the map — then wire blocking edges in a **second pass** (issues need ids before they can reference each other). Wiring sorts them into the frontier and the blocked; everything you can't yet specify stays in the fog — the **Not yet specified** section.
5. **Fire the research subagents.** For each `research` brief you just created, spin up a `/research` subagent to resolve it in parallel, capturing its findings on a throwaway `research/<name>` branch with a context pointer from the brief.
6. Stop — charting is one session's work; it hand-resolves nothing.

### Work through the map

User invokes with a map (URL or number). A brief is **optional** — without one, you pick the next decision, not the user.

1. Load the **map** — the low-res view, not every brief body.
2. Choose the brief. If the user named one, use it. Otherwise take the first frontier brief in order. **Claim it**: assign it to yourself before any work.
3. Resolve it — **zoom as needed**: fetch the full body of any related or closed brief on demand; invoke the skills the `## Notes` block names. If in doubt, use `/grilling` and `/domain-modeling`.
4. Record the resolution:
   4a. **Delivery Review Gate.** IF the brief type is `task` AND the task produced
       deliverables (files, code, documents):
       - Determine deliverable type:
         - `.md` files → invoke `doc-review` (ai-coworker)
         - code files → invoke `matt-code-review` (ai-coworker)
         - fallback (neither available) → Claude's default review
       - Review must pass before the brief can be closed.
       - If review fails → fix issues, re-review.
       
       Research, grilling, and prototype briefs skip this gate — their output
       is knowledge/decisions, not deliverables.
   
   Post the answer as a **resolution comment**, **close** the issue, and **append a context pointer** to the map's Decisions-so-far.
5. Add newly-surfaced briefs (create-then-wire); graduate any fog the answer has made specifiable, clearing each graduated patch from **Not yet specified** so it lives only as its new brief. If the answer reveals a brief — this one or another — sits beyond the destination, **rule it out of scope** rather than resolving it on the route. If the decision invalidates other parts of the map, update or delete those briefs.

The user may run unblocked briefs in parallel, so expect other sessions to be editing the tracker concurrently.
