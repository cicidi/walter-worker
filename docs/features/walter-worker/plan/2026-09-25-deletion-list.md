# Deletion List — 2026-09-25

> `[DelList]` — over-engineered subsystems, rarely-used features, and code with
> no path from any entry point. Nothing here is deleted yet; this is the list to
> rule on.

**Goal:** a small, sharp, publishable coworker. Every entry below was found by
tracing callers, not by reading and guessing.

**Decision rule** (the one already set for this cleanup):

- Dead **and** unrelated to the self-evolving-agent vision → **delete**
- Dead **but** vision-relevant → **fix**, do not delete
- Duplicate / superseded → **merge**, keep the live one

"Dead" here means: no import, no CLI registration, no hook, no config entry.
Each entry names the evidence that established it.

---

## A. Delete — dead and not on the loop

### A1. `src/coworker/memory/errors.py` — 61 lines — **DONE** (`0172480`)

Error-code registry ("spec §9"). Referenced by nothing: no import, no config, no
hook. The only file naming it was the generated `SOURCES.txt`. `tests/python/
test_errors.py` covered the registry and nothing else, and went with it.

*Confidence: high.* Vision relevance: none — it is scaffolding for a spec, not a
stage of the loop.

**One thing found after this entry was written, worth recording rather than
burying:** spec §9 does call for an error-code registry ("reuse the QA `E0xx`
style registry, namespaced `MEM_E0xx`… Exact table → impl"). So the module was
not invented — it implemented that line. It was deleted anyway, on the grounds
that a vocabulary nobody raises is not error handling, and that the spec's own
"Exact table → impl" leaves the table to the implementation. That does leave
§9's sentence unmatched. The spec was not edited: it is the authoritative
statement of intent, and per the doc standard a human rules on code/spec
conflicts. Reverse with `git revert` if the registry was meant to be adopted
rather than dropped.

### A2. `build/` and `src/walter_worker.egg-info/` — **DONE**

Both were local build artifacts, already gitignored — working-copy cleanup
rather than a repo change. 768 KB removed. Verified afterwards that
`import coworker` and `coworker --help` still work: the editable install keeps
its metadata in site-packages (`walter_worker-0.1.0.dist-info`), so the
`egg-info` in the source tree was a leftover, not what the install reads.

One caveat on the diagnosis, because the obvious reading is wrong: running
`python -m build` inside the checkout fails with `No module named
build.__main__; 'build' is a package`, which looks like `build/` shadowing the
PyPI tool. It is not. `build/` has no `__init__.py`, so it resolves only as a
namespace package, and `import build` in that interpreter reports
`__file__ = None` — the `build` tool is simply not installed in that venv
(CI installs it explicitly before its wheel step). The local directory only
makes the error message point somewhere misleading.

So: delete it for tidiness, not because it breaks anything.

*Confidence: high — corrected after checking; the first reading of this was wrong.*

---

## B. Fix — dead but vision-central

These are the ones the standing rule says to repair rather than remove. They are
listed first in priority because they are the difference between a memory that
evolves and a memory that only accumulates.

### B1. `coworker/autoworker/` + `cli_autoworker.py` — the loop's driver

~35 KB: `engine.py` (spawns Claude SDK agents that "autonomously investigate and
fix"), `rules.py`, `state.py`, plus a complete CLI registering `find-issues run`
and `run --loop`.

**It is commented out.** `cli.py:37` and `cli.py:1265` both carry
`# ... TODO: not yet implemented`, which is stale — it *is* implemented.

The known blocker was a 120 s pytest timeout inside `find-issues`, which the
wrong-history entry of 2026-07-28 records as fixed. The fix is present
(`cli_autoworker.py:96`, `timeout=600`), and the command is still disabled — so
whatever held it back has since been resolved, or was something else that was
never written down.

This is the highest-value entry on the list: it is the self-evolving loop's
actual executor. Re-enabling it is a **runtime behaviour change that spends
money** (it spawns agents in a loop for up to `--max-hours`), so it needs a
decision, not a silent re-enable.

*Confidence: high on the facts, medium on intent.*

### B2. `memory/capture.py` — the loop's first stage — **DONE**

`process_session_end` is callable as `coworker memory capture`, reading the same
flat stdin payload the hooks get, and **setup/install.sh registers it on the
Stop hook**. Verified end to end: a transcript in, a lesson stored in mem0 out,
and `coworker sync` preserves the hook entry rather than dropping it.

Two guards came out of running it under a hook that fires every session:

- Without an API key it exits 0 silently. An unconfigured machine is a state,
  not an error, and repeating that at the user after every session is noise.
  A genuine failure still exits non-zero and says why.
- `process_turn`, the per-PostToolUse half, stays unwired. It costs an LLM call
  per *tool call*, which is a different order of magnitude; it should wait until
  session-end capture has been watched working.

Cost, now accepted rather than assumed: one LLM call per session.

The rest of this entry stands as the reason it was unreachable:

`process_turn` (per PostToolUse) and `process_session_end` (per Stop) are
complete and tested. **Zero production callers.** Neither hook calls them.

The design doc is explicit about the intended wiring
(`design/memory-platform-design.md:89`):

> `coworker memory sync` | PostToolUse / SubagentStop → LLM extraction → `mem0.add`

…and line 320 puts reconciliation on Stop. But `coworker memory sync` already
exists and means something else entirely — "re-sync Graphify skeleton into the
memory graph". The name the design reserved was taken by an unrelated command,
which is the likeliest reason the wiring never happened.

*Confidence: high.* Note the cost: PostToolUse fires on **every tool call**, so
wiring `process_turn` there means an LLM call per tool call. That is a design
decision about spend, not a bug fix.

### B3. `engine.reconcile()` — a stub standing where the real code should be

`engine.py:164` returns `0` unconditionally, with the comment *"For now, just
note the gap — full re-extraction needs LLM"*. Meanwhile
`capture.process_session_end` **is** the full re-extraction, implemented and
unused. So the stub and the real thing coexist, neither called.

Per the merge rule: keep `capture.process_session_end`, and either delete the
stub or have it delegate.

*Confidence: high.*

### B4. `memory/metrics.py` — 118 lines, the "is it actually improving?" gauge

"Collects effectiveness and safety metrics to track whether the agent is
actually getting 'smarter over time.'" Exposes `record_session_metrics`,
`compute_evolution_score`, `get_metrics_report`. Nothing calls any of them; the
single mention in `cli_memory.py` is a comment explaining a removed command.

An evolution loop with no instrument cannot tell whether it is evolving. But it
is also the piece most likely to be premature — measuring before the loop runs
produces numbers nobody acts on.

*Confidence: high on deadness; the sequencing call is a judgement.*

---

## C. Over-engineered or rarely used — candidates, not conclusions

### C1. `_sync_mcp` is union-only — outdated MCP servers can never be removed

`adapters/claude.py:97` merges by name and never removes. The comment makes the
intent explicit: refusing to delete entries the user may have added is the safe
direction. That is correct as a default and wrong as a permanent limit — a
server that has been retired from `coworker.yaml` lives in `~/.claude.json`
forever, which is the `[MCPPrune]` gap.

Not a bug. Wants a deliberate `--prune-mcp` (or a managed-vs-user distinction),
not a change to the default.

*Confidence: high on the behaviour, medium on the fix shape.*

### C2. Two evolution scores, disagreeing — needs a ruling, not a patch

`evolution_score` and `skill_reuse_rate` are each computed twice, differently,
from different sources. Both surfaces are live, so the dashboard and
`coworker memory metrics` report different numbers under the same names.

| | Dashboard (`dashboard/queries_evolution.py:56`) | `memory/metrics.py:65` |
|---|---|---|
| Inputs | analytics.db: distinct sessions that called the `Skill` tool ÷ all sessions; count of `active` skills | mean of the last 10 recorded `skill_reuse_rate` values |
| Formula | `reuse*40 + active_skills*5 + 30` | `reuse*30 + first_pass*25 + memory_hit*25 + (1-correction)*15 + no_trips*5` |
| Floor | **30** — an agent that has done nothing scores 30/100 | 0 |

Three consequences worth separating:

1. `skill_reuse_rate` means *any* `Skill` tool call in the dashboard, but the
   spec (§7, line 365) defines it as the fraction of sessions invoking an
   **auto-created** skill. The dashboard overstates it, and cannot compute the
   spec's version from `tool_calls` alone — that needs the provenance the
   skills table already carries.
2. `+ active_skills * 5` rewards *how many* skills exist, not whether the agent
   got better; ten unused skills raise the score by 50.
3. The +30 base means the dashboard can never show 0, so a fresh install reads
   as 30% evolved.

Not patched here: which score is authoritative is a product decision, and the
spec's own signature — `compute_evolution_score(skills, experiences,
total_sessions)` — matches neither implementation exactly, so the spec needs a
ruling too. `memory/metrics.py` additionally reads a store that nothing writes
(see B4), so until capture lands it will report 0 while the dashboard reports
30-plus.

*Confidence: high on the divergence; the resolution is a design call.*

### C3. Documented-but-absent commands

`coworker knowledge` was the last one and is now implemented (see D). The scan
that found it — fenced code blocks only, comments skipped — now runs as
`test_all_skill_code_refs_resolve_in_cli` and reports nothing else across every
shipped skill.

*Confidence: high; this class is now guarded.*

---

## D. Fixed during this cleanup (for the record)

| Commit | What |
|---|---|
| `99c6442` | `docs/features/*/raw/` untracked — 166 files, 4.2 MB, incl. a vendored third-party toolkit with no licence |
| `663d189` | mem0 tests skip on a missing `[memory]` extra instead of erroring (3 failures + 47 errors) |
| `3fed5ef` | `on-correction.py` registered on install — the correction detector ran on one machine only |
| `640d173` | `/home/cicidi` removed from three shipped files |
| `056a912` | install works without `md5sum` — it exited 127 on macOS, which it claims to support |
| `170f530` | the two skills the global template invokes are shipped again |
| `072b4a4` | install no longer registers a gitignored OpenCode plugin path; template no longer ships the author's project names |
| `9ad28ac` | `coworker knowledge summarize`/`analyze` implemented (+ 3 defects in the module behind them) |
| `6da17ab` | guard: skill code blocks can no longer reference a nonexistent command |
| `f90a35b` | this list |
| `be50f63` | `state-update` wrote state files into the cwd, not the project root |
| `172bde3` | `record_session_metrics` docstring named keys that do not exist; `engine.reconcile` stub now delegates to the real implementation; `coworker memory metrics` added |
| `0172480` | A1 + A2 of this list |

---

## Suggested order

1. ~~**A2** — delete the build artifacts~~ — **done**
2. ~~**B3** — the stub delegates to the real implementation~~ — **done**
3. ~~**B4** — expose the evolution metrics~~ — **done** (`coworker memory metrics`)
4. ~~**A1** — delete the unused error registry~~ — **done**
5. ~~**B2** — capture, then the agent loop~~ — **done**, wired to Stop with the
   spend explicitly accepted.
6. **B1** — re-enable the autoworker CLI.
7. **C1** — decide `[MCPPrune]`'s shape.
8. **C2** — rule on which evolution score is authoritative.

B1 spawns agents in a loop for up to `--max-hours`, so it is the one remaining
entry that spends real money per invocation. C1 and C2 are product decisions —
neither is a defect to fix, and both need a ruling rather than a patch.
