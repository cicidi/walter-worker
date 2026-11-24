---
feature: memory-platform
type: design
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Memory Platform — Design

Requirements are in the [PRD](../prd/memory-platform-prd.md). Decisions are in the [decision history](../decision-history/memory-platform-decision-history.md). Behavior below was read from the code at commit `a0f4ce0`; where it does not meet a requirement, the gap is an Open Question.

## Problem Statement

Each Claude Code session starts from nothing. Corrections, conventions, and hard-won fixes from earlier sessions are lost unless someone writes them down, and a pile of notes nobody prunes becomes noise.

## Solution

Two stores with different strengths. The vector store, mem0 over a local Qdrant database with local embeddings, holds short lessons and finds them by meaning. The knowledge graph, one JSON file, holds typed nodes (code, documents, sessions, decision points, concepts) and typed edges, which can answer "what is connected to this file". Capture writes to both at session end; the graph side goes through a pending dump that a separate merge step folds in, so a slow or failed merge never delays the session. A curator ages the vector store weekly; graph edges fade with time when read.

## User Stories

The user stories are in the [PRD](../prd/memory-platform-prd.md#user-stories).

## Implementation Decisions

Language-model calls go to DeepSeek first and fall back to Gemini; embeddings are computed locally, so stored vectors never leave the machine (ARD-B). Graph writes are atomic (temporary file, then rename) (ARD-C). Capture and merge are two Stop hooks rather than one, so capture can return quickly.

## Design

### DSGN-A — Capture at session end

The installer registers `coworker memory capture` as a Stop hook with no timeout. It reads the hook payload from standard input and needs a session id and a transcript path; empty or malformed input, or a missing field, is an error with exit status 1. It then sets up the vector store. If mem0 is not installed, that is an error with exit status 1, even when no key is set (QUES-E). If `DEEPSEEK_API_KEY` is missing, capture returns quietly with status 0.

Capture reads the last 50,000 characters of the transcript and makes one language-model call that asks for lessons, candidate skills, and graph facts as JSON. Each lesson is stored in the vector store, tagged with the project (the transcript's working folder name). Each candidate skill reported with at least ten tool calls (`COWORKER_SKILL_THRESHOLD` changes the number) is staged for approval, subject to DSGN-F. The graph facts are written atomically to `~/.coworker/memory/pending/<session id>.json`. One line goes to `~/.coworker/memory/audit.log`. A failed lesson write, skill staging, or dump write is logged and capture continues. These rules implement PRD-A, except for the mem0-not-installed case.

### DSGN-B — Merging into the graph

`coworker memory close [SESSION_ID]` is also a Stop hook, run with no id, so every stop merges every pending dump. For each dump it marks new nodes and edges as captured now, folds a new node into an existing one of the same type (and same related file, when both have one) whose label is more than 70% similar, gives each new edge a starting weight from its confidence (0.9 extracted, 0.7 inferred, 0.5 ambiguous, 0.2 weak), drops edges whose target node does not exist, appends the rest, saves the graph atomically, and deletes the dump. Edges are never folded together, so repeated facts add duplicate edges (QUES-H). An unknown session id is an error with exit status 1.

Two gaps break PRD-B. A dump with a node type, relation, or confidence value outside the allowed lists raises an error that nothing catches; the dump is never deleted, and because dumps are processed in sorted order, every later `close` fails on it (QUES-A). There is no lock around reading, changing, and saving the graph, so two merges at once can lose updates (QUES-B). A damaged `graph.json` makes every graph command fail with a traceback (QUES-C).

### DSGN-C — Edge decay and queries

An edge's effective weight is its starting weight for the first 20 days after it was last traversed, then shrinks by 1% per day; weights of 0.5 and above are normal, 0.3 to 0.5 stale, and below 0.3 suppressed. The weight is computed when read and never stored, and queries never update the traversal time, so decay counts from when the edge was merged.

`memory query QUESTION [--top-k 50] [--budget 2000] [--min-score 0.3] [--mode graph|vector|both]` picks up to five starting nodes (with Graphify's scorer when installed, otherwise by label substring), walks outgoing edges up to six steps, skipping suppressed ones, and ranks by depth and path weight. It also searches the vector store. Each side is cut to the budget at about three characters per token, and both are printed as tables. `memory search QUERY [--project] [--limit 10]` searches the vector store only and is an error with exit status 1 when mem0 is unavailable. Searching updates each hit's use count. These rules implement PRD-C.

### DSGN-D — Curator

`on-stop.sh` runs `coworker memory curate --if-due`, discarding its output. It is due when the stamp file `~/.coworker/memory/.curator_last_run` is missing, unreadable, or at least seven days old; the stamp is written only when every step succeeded. Each step catches its own errors:

| Step | Effect |
|---|---|
| Mark stale | Active memories unused for 30 days become stale |
| Archive | Stale memories unused for 90 days become archived; there is no command to undo this |
| Prune sessions | Raw folders under `~/.coworker/analytics/sessions/` are deleted when the session is in the analytics database and the folder is older than 30 days |
| Export | Active memories, grouped by project and type, are written to `~/.coworker/memory/MEMORY.md` |
| Expire pending | Staged skills older than 30 days are marked expired |
| Score | Each memory gets a score from its use count and recency |

With `--if-due` and mem0 unavailable, the curator prints a short note and exits 0 without stamping; run by hand, the same case exits 1. Its documentation mentions merging duplicates and a two-hour idle condition; neither is implemented. These rules implement PRD-D.

### DSGN-E — Snapshot and wrong-history in `CLAUDE.local.md`

`coworker memory refresh` searches the vector store for the current project's active memories (up to ten) and writes them between `<!-- MEMORY:<project> START -->` and `<!-- MEMORY:<project> END -->` in `~/CLAUDE.local.md` in the home folder, creating the file or the block as needed. It also writes the critical and high-severity wrong-history rules between `<!-- WRONG-HISTORY START -->` and `<!-- WRONG-HISTORY END -->`. It always exits 0. Text outside the markers is unchanged. This implements PRD-E. The wrong-history entries are read from a path relative to the current folder, so running the command elsewhere replaces the block with "No wrong-history entries yet" (QUES-F). Nothing runs `refresh` at session start; the dashboard and the auto-worker can also write these blocks.

### DSGN-F — Skill staging limit

Staging a skill writes `~/.coworker/pending/skills/<name>.json` with status `pending`, replacing an earlier file of the same name. A circuit breaker, a counter in `~/.coworker/safety/circuit_state.json`, allows three stagings per fixed 24-hour window; when it trips, staging fails and the caller logs it. A damaged counter file counts as allowed. Only the dashboard can reset the counter. Promotion happens only through `coworker skill approve`. This implements PRD-F.

### DSGN-G — Knowledge commands

`coworker knowledge summarize SESSION_ID` summarizes one session from the analytics database with a language-model call and writes a summary row, plus knowledge cards when the model returns them; an unknown session or a model failure exits 1. `knowledge analyze [--since yesterday|today|N days ago|ISO date|all] [--all]` summarizes every session in the window, continues past a failed session, and exits 1 only when none succeeded; an unrecognized `--since` exits 1. The prompt never asks for cards, so cards appear only when the model adds them unasked (QUES-G). This implements PRD-G.

### DSGN-H — Privacy and keys

| Content | Sent to |
|---|---|
| The last 50,000 characters of each transcript (capture, and `memory train`) | DeepSeek, or Gemini if DeepSeek fails |
| Each lesson's text, when stored | DeepSeek, through mem0's own extraction |
| Session excerpts up to 12,000 characters (`knowledge`) | DeepSeek or Gemini; card titles also to DeepSeek for duplicate checks |

Embeddings, the vector store, the graph, dumps, staged skills, the audit log, `MEMORY.md`, and `CLAUDE.local.md` stay local. mem0 telemetry is off. Keys come only from the process environment; no code reads `~/.coworker/.env`, although the installer tells users to put keys there (QUES-D). There is no command to delete a memory (QUES-D). PRD-H is not met.

### DSGN-I — Graph from Graphify, and wrong-history entries

`memory init [--graphify-dir] [--force]` builds the graph from Graphify's output; it refuses, with exit status 0, when the graph already has nodes, unless `--force` is given, in which case the old graph is first copied under `~/.coworker/backups/<timestamp>-memory-init/`. `memory sync` merges Graphify's nodes and edges into the existing graph, keeping existing edges as they are; without Graphify output it prints a note and exits 0. These implement PRD-I. `memory wrong-history record --summary --rule [...]` writes an entry and rebuilds `INDEX.md`; `index` only rebuilds; a missing summary or rule prints an error and exits 0. These implement PRD-J.

### Sub-problem ownership (子问题归属)

| 子问题 | 归属 | 依据 |
|---|---|---|
| Whether Claude Code runs `capture` before `close` at a stop | AI 查 | UNKNOWN; set by Claude Code, outside this repository |
| What to do with a dump that cannot be merged | 人决定 | QUES-A |
| Whether transcripts may be sent to an outside provider at all, and which | 人决定 | QUES-D; the current behavior is in DSGN-H |
| Whether mem0's metadata update replaces or merges fields | AI 查 | UNKNOWN; mem0 library behavior |

## Testing Decisions

The graph core is tested directly with temporary files; capture, the curator, and the CLI are tested with the language model and mem0 replaced. The cases are in the [test plan](../test-plan/memory-platform-test-plan.md).

## Out of Scope

Session recording, skill approval, `memory validate`, and `memory train` are outside this design, as listed in the [PRD](../prd/memory-platform-prd.md#out-of-scope). The memory MCP server (`python -m coworker.memory.mcp_server`), which exposes graph query and vector search to AI tools, is not specified here.

## Further Notes

The language-model client's documentation still names a Claude Haiku fallback that no longer exists, and the installer advertises an Anthropic key fallback that no code reads.

## Alternatives Considered

A single store was rejected: the vector store cannot answer "what touches this file", and the graph cannot match a lesson by meaning. Merging the graph inside the capture hook was rejected so that a slow merge never lengthens the session's end (ARD-C).

## Drawbacks

Capture costs one language-model call per session and sends transcript text off the machine. The graph only grows: edges are never folded or deleted except by rebuilding.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| A bad dump blocks every later merge | Not mitigated today (QUES-A) |
| Concurrent merges lose updates | Atomic writes prevent damaged files but not lost updates (QUES-B) |
| Secrets in transcripts reach a provider | Not mitigated; documented in DSGN-H (QUES-D) |
| Capture slows a session's end | No timeout is set; the model client retries three times with a 30-second limit per provider |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | A pending dump with a value outside the allowed types makes `close` fail, is never deleted, and blocks every later merge. Move such dumps aside and continue? | Found in the code at `a0f4ce0`; no test covers it. | cicidi | yes |
| **QUES-B** | Graph read, change, and save have no lock, so two merges at once lose updates. Add a lock? | Found in the code at `a0f4ce0`. | cicidi | yes |
| **QUES-C** | A damaged `graph.json` makes every graph command fail with a traceback. Report it, and keep a backup? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-D** | Keys are read only from the environment, not from `~/.coworker/.env` as PRD-H and the installer say, and there is no command to delete a memory. Add both? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-E** | Capture exits 1 when mem0 is not installed, even with no key set, so an unconfigured machine reports a failing Stop hook. Check the key first? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-F** | `memory refresh` reads wrong-history from a path relative to the current folder, so it erases the block when run elsewhere. Resolve the path from the project? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-G** | The knowledge prompt never asks for cards, so cards appear only by chance. Ask for them? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-H** | Repeated facts add duplicate edges, so the graph grows without bound. Fold duplicate edges? | Found in the code at `a0f4ce0`. | cicidi | no |

## Reversibility

`memory init --force` keeps a backup of the old graph, restorable with `coworker restore memory-init`. Archived memories cannot be unarchived, and there is no command to delete a memory. The blocks in `~/CLAUDE.local.md` can be removed by hand or rewritten by `memory refresh`. Staged skills can be rejected with `coworker skill reject`.

## Terms

| Term | Meaning |
|---|---|
| Vector store | A database that finds text by meaning, using numeric embeddings of the text |
| Embedding | A list of numbers representing a text's meaning, computed here by a local model |
| mem0 | The library that manages the vector store and extracts memories from text |
| Knowledge graph | `graph.json`: nodes for code, documents, sessions, decisions, and concepts, joined by typed edges |
| Pending dump | The graph facts from one session, waiting in `~/.coworker/memory/pending/` to be merged |
| Graphify | A tool that maps a codebase and its documents into a graph |
| Circuit breaker | The counter that limits skill staging to three per day |
| Wrong-history | Recorded past mistakes and the rules learned from them |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0` with the 13 required sections; gaps recorded as QUES-A to QUES-H (ARD-A, ARD-D) |
