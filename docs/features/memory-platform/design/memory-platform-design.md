---
feature: memory-platform
type: design
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Memory Platform — Design

Requirements are in the [PRD](../prd/memory-platform-prd.md). Decisions are in the [decision history](../decision-history/memory-platform-decision-history.md). Behavior below was read from the code at commit `a0f4ce0`, and capture's trigger from `634adf1`, after walter-worker PR #22. Each `file:line` citation names its commit. Where it does not meet a requirement, the gap is an Open Question (ARD-D). This design is the authority for the memory code's current behavior; the older memory documents under `self-evolving-agent` are design history (ARD-G).

This feature implements PRD-E of the [parent walter-worker PRD](../../walter-worker/prd/walter-worker-prd.md), the rule that lessons are kept across sessions and curated. It also follows the parent's PRD-G, which says no component blocks a session through its own failure, and PRD-H, which says session content leaves the machine only where a design documents it. The rules shared by every area are in the [parent design](../../walter-worker/design/walter-worker-design.md). Terms such as turn, Stop hook, mem0, Qdrant, and Graphify are defined in its [glossary](../../walter-worker/design/walter-worker-design.md#glossary).

## Problem Statement

Each Claude Code session starts from nothing. Corrections, conventions, and hard-won fixes from earlier sessions are lost unless someone writes them down, and a pile of notes nobody prunes becomes noise.

## Solution

Two stores with different strengths. The vector store, mem0 over a local Qdrant database with local embeddings, holds short lessons and finds them by meaning. The knowledge graph, one JSON file, holds typed nodes (code, documents, sessions, decision points, concepts) and typed edges, which can answer "what is connected to this file". Capture writes to both stores. It runs once per session, after the session ends, from a SessionEnd hook that detaches it (ARD-H). The graph side goes through a pending dump that a separate merge step folds in, so a slow or failed merge never delays capture. A curator ages the vector store weekly. Graph edges added by capture fade with time, but edges imported from Graphify never fade (DSGN-C).

## User Stories

The user stories are in the [PRD](../prd/memory-platform-prd.md#user-stories).

## Implementation Decisions

Language-model calls go to DeepSeek first and fall back to Gemini; embeddings are computed locally, so stored vectors never leave the machine (ARD-B). Graph writes are atomic (temporary file, then rename) (ARD-C). Capture and merge are two commands. One detached shell runs capture and then merge, so the merge folds in the dump that capture just wrote (DSGN-B, ARD-H).

## Design

<a id="dsgn-a-capture-after-every-turn"></a>

### DSGN-A — Capture once per session

The installer registers `on-session-end.sh` as a SessionEnd hook, and removes each Stop hook made only of the old capture and close steps; a mixed hook is kept (`setup/install.sh:687-700` at `634adf1`, setup-deploy QUES-K). The hook saves its payload to a temporary file, starts capture and then close as a detached run, and exits 0 at once (`on-session-end.sh:13-21` at `634adf1`). It uses `setsid`, or `nohup` where `setsid` is missing, so the run is meant to outlive the hook and `claude` (`on-session-end.sh:9-12`); no test checks this, and on the `nohup` path it is UNKNOWN. Capture therefore runs once per SessionEnd event, and no time limit applies to it (ARD-H). Its exit status and output go nowhere.

Capture reads the hook payload from standard input. It needs a session id and a transcript path. Empty or malformed input, or a missing field, is an error with exit status 1. Capture then sets up the vector store. If mem0 is not installed, that is an error with exit status 1, even when no key is set (QUES-E). Every other setup failure makes capture return quietly with status 0 and write nothing, not even an audit line. A missing `DEEPSEEK_API_KEY` is one such failure. A local Qdrant store that another process holds open is another, and it happens when two sessions end at once, or when a curator run opens the store at the same time (QUES-K).

Capture reads the last 50,000 characters of the transcript. It makes one language-model call that asks for lessons, candidate skills, and graph facts as JSON. Each lesson is stored in the vector store, tagged with the project, which is the name of the transcript's working folder. Each candidate skill reported with at least ten tool calls is staged for approval, subject to DSGN-F; `COWORKER_SKILL_THRESHOLD` changes the number. The graph facts are written atomically to `~/.coworker/memory/pending/<session id>.json`. One line goes to `~/.coworker/memory/audit.log`. A failed lesson write, skill staging, or dump write goes to standard error, which the detached run discards, and capture continues.

Capture runs once per SessionEnd event (ARD-H). Whether a resumed session fires SessionEnd again, and so sends its transcript again, is UNKNOWN. Each run stores its lessons and stages its skill candidates once. Every staging counts against the limit of three per day (DSGN-F). `close` then merges the session's pending dump once (DSGN-B). This answers QUES-I.

Three more failures make capture exit with status 1. They are an unreadable transcript, a provider failure, and a reply that is not valid JSON. The last one includes the case where DeepSeek returns only its reasoning text, which the client passes on with the prefix `[reasoning]`. Provider and JSON failures write an audit line marked `error`; an unreadable transcript writes none. The hook exits 0 whatever capture returns, so the parent design's first shared rule, that a hook ignores its own failures, now holds. A failure shows only in the audit log. The owner reported on 2026-11-24 that about 40% of capture runs log an error; the cause is UNKNOWN (QUES-O).

The model client gives each request a 30-second limit. It tries each provider up to three times and waits 1 and then 2 seconds between tries. If every try times out, one provider takes 93 seconds. When the Gemini fallback is configured and also times out, the call takes 186 seconds. The OpenAI library that sends the requests adds its own retries to each try (two by default in the installed version 2.48.0), so the real worst case is longer. Each stored lesson adds a mem0 write with up to three tries, and each try makes mem0's own DeepSeek call, whose time limit is UNKNOWN. Nothing outside capture limits its run time, so a slow provider now delays only the summary (QUES-L).

These rules implement PRD-A, except for the silent setup failures (QUES-K) and the runs that end in an error (QUES-O).

### DSGN-B — Merging into the graph

`coworker memory close [SESSION_ID]` runs right after capture, in the same detached shell (DSGN-A). It runs with no id, so it merges every pending dump. That includes the dump capture just wrote, because the shell starts `close` after capture has returned (`on-session-end.sh:15` at `634adf1`). An unknown session id is an error with exit status 1.

For each dump, the merge takes these steps in order:

- It marks the new nodes and edges as captured now.
- It folds each new node into an existing node when both have the same type, the same related file (when both have one), and labels more than 70% alike. Folding means the new node is dropped and the existing node's session count goes up by one.
- It gives each new edge a starting weight from its confidence: 0.9 for extracted, 0.7 for inferred, 0.5 for ambiguous, and 0.2 for weak.
- It drops each edge whose target node does not exist.
- It appends the remaining nodes and edges, saves the graph atomically, and deletes the dump.

Folding does not redirect the dump's edges to the surviving node. An edge that points at a folded node is dropped as a miss. An edge that starts from a folded node is appended with a source id that no node has, so no query can reach it. This loses graph facts and breaks PRD-B's folding rule (QUES-J). Edges are never folded together, so repeated facts add duplicate edges (QUES-H). Since `close` runs once per session, a session's facts are merged once (ARD-H).

Two more gaps break PRD-B. A dump with a node type, relation, or confidence value outside the allowed lists raises an error that nothing catches; the dump is never deleted, and because dumps are processed in sorted order, every later `close` fails on it (QUES-A). There is no lock around reading, changing, and saving the graph, so two merges at once can lose updates (QUES-B). A damaged `graph.json` makes every graph command fail with a traceback (QUES-C).

### DSGN-C — Edge decay and queries

An edge's effective weight is its starting weight for the first 20 days after its traversal time, and then it shrinks by 1% per day. Weights of 0.5 and above are normal, 0.3 to 0.5 are stale, and below 0.3 are suppressed. The weight is computed when read and never stored. A merge sets an edge's traversal time to the moment of the merge, and queries never update it. So for an edge added by capture, decay counts from when the edge was merged. Edges imported from Graphify have no traversal time, so they never decay.

`memory query QUESTION [--top-k 50] [--budget 2000] [--min-score 0.3] [--mode graph|vector|both]` first picks up to five starting nodes. It uses Graphify's scorer when Graphify is installed, and otherwise matches label substrings. It then walks outgoing edges up to six steps, skipping suppressed ones. It ranks results by depth first and then by path weight, the product of the effective weights of the edges on the path. It also searches the vector store. Each side is cut to the budget at about three characters per token, and both are printed as tables. `memory search QUERY [--project] [--limit 10]` searches the vector store only and is an error with exit status 1 when mem0 is unavailable. Searching updates each hit's use count. These rules implement PRD-C.

### DSGN-D — Curator

`on-stop.sh` runs `coworker memory curate --if-due` at every stop, discarding its output. The curator is due when the stamp file `~/.coworker/memory/.curator_last_run` is missing, unreadable, or at least seven days old. Each step catches its own errors:

| Step | Effect |
|---|---|
| Mark stale | Active memories unused for 30 days become stale |
| Archive | Stale memories unused for 90 days become archived; there is no command to undo this |
| Prune sessions | Raw folders under `~/.coworker/analytics/sessions/` are deleted when the session is in the analytics database and the folder is older than 30 days |
| Export | Active memories, grouped by project and type, are written to `~/.coworker/memory/MEMORY.md` |
| Expire pending | Staged skills older than 30 days are marked expired |
| Score | Each memory gets a score from its use count and recency |

After a run, the stamp is written only when no step reported an error. Only three steps can report one: pruning session folders, writing the export, and expiring pending skills. The steps that use mem0 (mark stale, archive, and score) catch mem0 errors themselves, and listing memories returns an empty list on an error. So a mem0 failure during a run never blocks the stamp, and the next run comes seven days later. In that case the export also overwrites `MEMORY.md` with a file that lists no memories (QUES-M).

With `--if-due` and mem0 unavailable, the curator prints a short note and exits 0 without stamping; run by hand, the same case exits 1. Its documentation mentions merging duplicates and a two-hour idle condition; neither is implemented. These rules implement PRD-D.

### DSGN-E — Snapshot and wrong-history in `CLAUDE.local.md`

`coworker memory refresh` searches the vector store for the current project's active memories (up to ten) and writes them between `<!-- MEMORY:<project> START -->` and `<!-- MEMORY:<project> END -->` in `~/CLAUDE.local.md` in the home folder, creating the file or the block as needed. It also writes the critical and high-severity wrong-history rules between `<!-- WRONG-HISTORY START -->` and `<!-- WRONG-HISTORY END -->`. It always exits 0. Text outside the markers is unchanged. This implements PRD-E. The wrong-history entries are read from a path relative to the current folder, so running the command elsewhere replaces the block with "No wrong-history entries yet" (QUES-F). `refresh` rewrites `~/CLAUDE.local.md` in place without first copying it under `~/.coworker/backups/`, which the parent design's second shared rule requires; the curator overwrites `MEMORY.md` the same way (QUES-P). Nothing runs `refresh` at session start; the dashboard and the auto-worker can also write these blocks.

### DSGN-F — Skill staging limit

Staging a skill writes `~/.coworker/pending/skills/<name>.json` with status `pending`, replacing an earlier file of the same name. A circuit breaker, a counter in `~/.coworker/safety/circuit_state.json`, allows three stagings per fixed 24-hour window. The window is fixed, not sliding: it starts when the counter is created or reset, and the first check more than 24 hours later sets the count back to zero and starts a new window. When the breaker trips, staging fails and the caller logs it. A damaged counter file counts as allowed. Capture runs once per session, so a session stages each candidate once (ARD-H). Only the dashboard can reset the counter. Promotion happens only through `coworker skill approve`. This implements PRD-F.

### DSGN-G — Knowledge commands

`coworker knowledge summarize SESSION_ID` summarizes one session from the analytics database with a language-model call and writes a summary row, plus knowledge cards when the model returns them; an unknown session or a model failure exits 1. `knowledge analyze [--since yesterday|today|N days ago|ISO date|all] [--all]` summarizes every session in the window, continues past a failed session, and exits 1 only when none succeeded; an unrecognized `--since` exits 1. The prompt never asks for cards, so cards appear only when the model adds them unasked (QUES-G). This implements PRD-G.

### DSGN-H — Privacy and keys

| Content | Sent to |
|---|---|
| The last 50,000 characters of the transcript, sent at each SessionEnd event (capture, ARD-H) | DeepSeek, or Gemini if DeepSeek fails |
| The last 50,000 characters of each past session's transcript (`memory train`) | DeepSeek, or Gemini if DeepSeek fails |
| Each lesson's text, when it is stored | DeepSeek, through mem0's own extraction |
| Session excerpts up to 12,000 characters (`knowledge`) | DeepSeek, or Gemini if DeepSeek fails |
| The title, type, and summary of up to five existing knowledge cards and of the new card, for the duplicate check in `knowledge` | DeepSeek |
| The task text given to `memory validate`, sent twice through the Claude Code command line (`claude -p`); the second run is told to search stored memories, so what it finds goes too | Anthropic |

Embeddings, the vector store, the graph, dumps, staged skills, the audit log, `MEMORY.md`, and `CLAUDE.local.md` stay local. mem0 telemetry is off. Keys come only from the process environment; no code reads `~/.coworker/.env`, although the installer tells users to put keys there (QUES-D). There is no command to delete a memory (QUES-D). PRD-H is not met.

### DSGN-I — Graph from Graphify, and wrong-history entries

`memory init [--graphify-dir] [--force]` builds the graph from Graphify's output. Without `--graphify-dir`, it reads `graphify-out/graph.json` under the current folder. It refuses, with exit status 0, when the graph already has nodes, unless `--force` is given. With `--force`, the old graph is first copied under `~/.coworker/backups/<timestamp>-memory-init/`. When no Graphify output is found, `init` saves an empty graph and prints success. With `--force` on a populated graph, that replaces the graph with an empty one after the backup (QUES-N). `memory sync` merges Graphify's nodes and edges into the existing graph and keeps existing edges as they are. Without Graphify output, it prints a note and exits 0. Edges imported by either command never decay (DSGN-C). These rules implement PRD-I.

`memory wrong-history record --summary --rule [...]` writes an entry and rebuilds `INDEX.md`, and `index` only rebuilds. A missing summary or rule prints an error and exits 0. Recording the same summary twice on one day keeps the first entry file unchanged and still prints "Created". Both commands use the folder `docs/features/self-evolving-agent/wrong-history/` relative to the current folder. Run in any other folder, they create that folder tree there (QUES-F). These rules implement PRD-J.

### Sub-problem ownership (子问题归属)

| 子问题 | 归属 | 依据 |
|---|---|---|
| Whether `capture` runs before `close` | AI 查 | Answered: one shell runs `capture`, then `close` (`on-session-end.sh:15` at `634adf1`) |
| What to do with a dump that cannot be merged | 人决定 | QUES-A |
| Whether transcripts may be sent to an outside provider at all, and which | 人决定 | QUES-D; the current behavior is in DSGN-H |
| Whether mem0's metadata update replaces or merges fields | AI 查 | Answered for the installed mem0 2.0.14, which merges new fields into the old ones (`mem0/memory/main.py`, update path); `pyproject.toml` at `a0f4ce0` allows any `mem0ai>=0.1`, so other versions are UNKNOWN |
| Whether capture and merge should run once per session instead of every turn | 人决定 | Decided: once per session (ARD-H) |
| What should happen to the edges of a folded node | 人决定 | QUES-J |

## Testing Decisions

The graph core is tested directly with temporary files; capture, the curator, and the CLI are tested with the language model and mem0 replaced. Some test files also hold tests that call DeepSeek or the real mem0 store; they are skipped when no key is set. The cases are in the [test plan](../test-plan/memory-platform-test-plan.md).

## Out of Scope

Session recording, skill approval, `memory validate`, and `memory train` are outside this design, as listed in the [PRD](../prd/memory-platform-prd.md#out-of-scope). The memory MCP server (`python -m coworker.memory.mcp_server`), which exposes graph query and vector search to AI tools, is not specified here.

## Further Notes

The language-model client's documentation still names a Claude Haiku fallback that no longer exists, and the installer advertises an Anthropic key fallback that no code reads.

## Alternatives Considered

A single store was rejected: the vector store cannot answer "what touches this file", and the graph cannot match a lesson by meaning. Merging the graph inside the capture hook was rejected so that a slow merge never lengthens the session's end (ARD-C).

## Drawbacks

Capture costs one language-model call per session and sends the transcript tail off the machine once per session (ARD-H). A session's lessons arrive only after it ends. The graph only grows: edges are never folded or deleted except by rebuilding.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| A bad dump blocks every later merge | Not mitigated today (QUES-A) |
| Concurrent merges lose updates | Atomic writes prevent damaged files but not lost updates (QUES-B) |
| Secrets in transcripts reach a provider | Not mitigated; documented in DSGN-H (QUES-D) |
| A capture run lasts minutes after the session ends | Not bounded; the detached run has no time limit, and one model call can take 93 seconds per provider before giving up (DSGN-A, QUES-L) |
| Capture fails and no one sees it | Only the audit log records a failure; about 40% of runs log an error, for an UNKNOWN cause (QUES-O) |
| A session ends without a SessionEnd event and gets no summary | Not mitigated; which endings fire SessionEnd is UNKNOWN |
| Two processes open the local Qdrant store at once | Not mitigated; capture then exits 0 and saves nothing (QUES-K) |
| A folded node leaves edges dropped or pointing at no node | Not mitigated (QUES-J) |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | A pending dump with a value outside the allowed types makes `close` fail, is never deleted, and blocks every later merge. Move such dumps aside and continue? | Found in the code at `a0f4ce0`; no test covers it. | cicidi | yes |
| **QUES-B** | Graph read, change, and save have no lock, so two merges at once lose updates. Add a lock? | Found in the code at `a0f4ce0`. | cicidi | yes |
| **QUES-C** | A damaged `graph.json` makes every graph command fail with a traceback. Report it, and keep a backup? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-D** | Keys are read only from the environment, not from `~/.coworker/.env` as PRD-H and the installer say, and there is no command to delete a memory. Add both? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-E** | Capture exits 1 when mem0 is not installed, even with no key set. Check the key first? | Found in the code at `a0f4ce0`. Since PR #22 (`a91ebbd`) the SessionEnd hook discards that status, so no failing hook is reported. | cicidi | no |
| **QUES-F** | `memory refresh`, `memory wrong-history record`, and `memory wrong-history index` use a wrong-history path relative to the current folder. Run elsewhere, `refresh` erases the block, and `record` and `index` create the folder tree there. Resolve the path from the project? | Found in the code at `a0f4ce0`; widened from `refresh` to all three commands on 2026-11-24. | cicidi | no |
| **QUES-G** | The knowledge prompt never asks for cards, so cards appear only by chance. Ask for them? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-H** | Repeated facts add duplicate edges, so the graph grows without bound. Fold duplicate edges? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-I** | Capture and `close` ran as Stop hooks, so they ran after every turn, not once per session. Each turn repeated the model call with the transcript, stored lessons again, used up the daily staging limit, and merged the same facts again. Move them to the session-end event, or run them once per session? | Found in the code at `a0f4ce0` (`setup/install.sh` registers both on `Stop`). Fixed by walter-worker PR #22, merged as `a91ebbd`: one detached run per session from a SessionEnd hook, and install takes both off `Stop` (ARD-H). | cicidi | no |
| **QUES-J** | When the merge folds a new node into an existing one, it does not redirect the dump's edges. Edges into the folded node are dropped, and edges out of it point at a node that does not exist. Redirect them to the surviving node? | Found in the code at `a0f4ce0` and reproduced with a temporary home folder on 2026-11-24; no test covers it. | cicidi | yes |
| **QUES-K** | Every mem0 setup failure, not only a missing key, makes capture exit 0 with nothing saved and no audit line. That includes a Qdrant store held open by another process. Report real failures, or retry? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-L** | Capture runs detached with no time limit, and one model call can take 93 seconds per provider. Set a time limit, or shorten the client's retries? | Found in the code at `a0f4ce0`. Since PR #22 (`a91ebbd`) Claude Code no longer stops capture; a slow run only delays the summary. | cicidi | no |
| **QUES-M** | A mem0 failure during a curator run is caught inside the steps, so the stamp is written anyway and `MEMORY.md` is overwritten with no memories. Count these failures as errors? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-N** | `memory init` with no Graphify output saves an empty graph and prints success, and with `--force` it replaces a populated graph with an empty one. Refuse when no output is found? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-O** | Capture exits 1 when the transcript cannot be read, the provider fails, or the reply is not JSON. These failures show only in the audit log, with no cause, and an unreadable transcript writes no line. Log each failure's cause? | Found in the code at `a0f4ce0`. Since PR #22 (`a91ebbd`) the hook exits 0, so the parent rule that hooks ignore their own failures holds. The owner reported on 2026-11-24 that about 40% of runs log an error, cause UNKNOWN; logging the exception text is in progress, not merged. | cicidi | no |
| **QUES-P** | `memory refresh` overwrites `~/CLAUDE.local.md`, and the curator overwrites `MEMORY.md`, without the backup the parent's second shared rule requires. Add the backup? | Found in the code at `a0f4ce0`. | cicidi | no |

## Reversibility

`memory init --force` keeps a backup of the old graph, restorable with `coworker restore memory-init`. This matters because `init` replaces the graph even when it finds no Graphify output (QUES-N). Archived memories cannot be unarchived, and there is no command to delete a memory. The blocks in `~/CLAUDE.local.md` can be removed by hand or rewritten by `memory refresh`. Staged skills can be rejected with `coworker skill reject`.

## Terms

Terms used across walter-worker are in the [parent glossary](../../walter-worker/design/walter-worker-design.md#glossary). They include turn, Stop hook, SessionEnd hook, vector store, embedding, mem0, Qdrant, fastembed, knowledge graph, Graphify, language-model provider, and wrong-history. The terms below are used only in this feature.

| Term | Meaning |
|---|---|
| Detached run | A process started apart from the hook (`setsid`, or `nohup` where `setsid` is missing) so that it can keep running after the hook exits |
| Pending dump | The graph facts from one session, waiting in `~/.coworker/memory/pending/` to be merged; capture writes it once per session |
| Fold | To merge a new node into an existing, similar node: the new node is dropped and the existing node's session count rises |
| Starting weight | The weight an edge gets when it is merged, taken from its confidence |
| Traversal time | The time stored on an edge from which decay is counted; a merge sets it, and Graphify edges have none |
| Effective weight | An edge's starting weight after decay, computed each time it is read |
| Path weight | The product of the effective weights of the edges on a query path |
| Circuit breaker | The counter that limits skill staging to three per fixed 24-hour window |
| Fixed 24-hour window | A 24-hour period that starts when the counter is created or reset and does not slide with each staging |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0` with the 13 required sections; gaps recorded as QUES-A to QUES-H (ARD-A, ARD-D) |
| 0.3 | 2026-11-24 | Review fixes: capture and merge run every turn; fold, timeout, curator stamp, Graphify decay, init, exit-1, and privacy facts corrected; QUES-I to QUES-P added; QUES-F widened; parent links and glossary moved (ARD-D, ARD-F, ARD-G) |
| 0.4 | 2026-11-24 | QUES-I notes the fix in open PR #22; master behavior unchanged |
| 0.5 | 2026-11-24 | PR #22 merged: capture and close run once per session from SessionEnd (ARD-H); QUES-I answered; QUES-E, QUES-L, QUES-O re-read |
| 0.6 | 2026-11-24 | Review fixes: per-hook Stop removal, once per SessionEnd event, detached-run limits stated as UNKNOWN, stderr discarded, Detached run term |
