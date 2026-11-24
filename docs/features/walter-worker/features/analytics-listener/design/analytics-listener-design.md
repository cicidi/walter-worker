---
feature: analytics-listener
type: design
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Listener — Design

Requirements are in the [PRD](../prd/analytics-listener-prd.md). Decisions are in the [decision history](../decision-history/analytics-listener-decision-history.md). Behavior below was read from the code at commit `a0f4ce0`; where it does not meet a requirement, the gap is an Open Question.

## Problem Statement

walter-worker wants to answer questions such as "which tools do I use most", "how long do sessions last", and "what did I work on last week", and its memory features want the raw material of past sessions. Claude Code keeps transcripts, but not in a form that is easy to query across sessions, and it does not record tool timings or which files a session touched.

## Solution

Small shell hooks append one JSON line per event to plain files, which is cheap enough to run on every prompt and tool call and cannot corrupt a database if interrupted. Importers, run on demand or by a background loop, turn those files and Claude Code's own transcripts into rows in one SQLite database, which every reader queries.

## User Stories

The user stories are in the [PRD](../prd/analytics-listener-prd.md#user-stories).

## Implementation Decisions

Hooks are bash scripts with small inline Python for JSON parsing, so they start fast and need no installed package (ARD-B). Claude Code transcripts are the preferred source of message text, because they contain the assistant's replies, which the hooks never see (ARD-C). The database schema is created and migrated on every connection, so a missing or old database is never an error.

## Design

### DSGN-A — Hooks and the files they write

The installer copies the hook scripts to `~/.coworker/analytics/hooks/` and registers them in `~/.claude/settings.json` with no timeout set.

| Hook | Claude Code event | Writes |
|---|---|---|
| `on-user-prompt.sh` | prompt submitted | One line in `sessions/<id>/messages.jsonl` with the time, the type `user`, the sequence number, and the full prompt |
| `on-pre-tool.sh` | before a tool runs | One line in `sessions/<id>/tools.jsonl` with the phase `before`, the tool name, the call id, the sequence number, and the full tool input |
| `on-post-tool.sh` | after a tool runs | One line in `tools.jsonl` with the phase `after`, the call id, the result cut to 10,000 characters, and the duration |
| `on-stop.sh` | session stop | Sets a `closed` time in `sessions/<id>/session.yaml`, runs `coworker memory curate --if-due`, and appends one line per session to `~/.coworker/analytics/index.jsonl` |
| `on-correction.py` | prompt submitted | A draft trace, when the prompt reads as a correction (DSGN-D) |

All paths above are under `~/.coworker/analytics/`. The first hook of a session creates `sessions/<id>/session.yaml` with the session id, creation time, the tool name `claude-code`, and the working folder. Sequence numbers come from a per-session counter file, `.seq`. Times are local with a UTC offset. These rules implement PRD-A.

### DSGN-B — Failure behavior

Every write in the prompt and tool hooks ends in a step that ignores failure, so those hooks exit successfully even when the disk is full or the payload cannot be parsed; unparseable fields fall back to empty values. This implements PRD-B for those hooks. Two exceptions break it today: the last write in `on-stop.sh` is not guarded, and `on-correction.py` has no error handling around its file write (QUES-B). The counter file is read and incremented without a lock, so two hooks firing together can produce the same sequence number (QUES-C). Behavior with `HOME` unset is UNKNOWN.

A record whose payload has no session id goes to `sessions/_unattributed/`, with no `session.yaml`. This implements PRD-C.

### DSGN-C — Import into the database

The database is `$COWORKER_ANALYTICS_DB` if set, else `~/.coworker/analytics/analytics.db`. Every connection creates the parent folder, turns on write-ahead logging and foreign keys, creates any missing table, and runs the migrations, including renaming the old `initiative` column to `feature`. This implements PRD-E. The main tables are `sessions`, `messages`, `tool_calls`, `file_ops`, `session_stats`, `skills`, `knowledge`, and `session_summaries`.

The `coworker analytics` commands run the importers; none takes options.

| Command | Behavior |
|---|---|
| `create-db` | Creates the database with its schema |
| `import` | Re-imports every hook session directory that has a `session.yaml` |
| `once` | One pass: Claude Code transcripts under `~/.claude/projects/`, then hook directories, then OpenCode session metadata; skips any session id already in the database |
| `daemon` | Runs `once` every 30 minutes, forever; nothing starts it automatically |

Importing a hook session infers the project from the working folder, the git branch, and the active feature from the project's `CLAUDE.local.md` or the branch prefix. It takes message text from the matching Claude Code transcript when one exists, including assistant text, cut to 10,000 characters, and falls back to the hook's `messages.jsonl` otherwise. It pairs before and after tool records by call id and records which files Read, Write, Edit, and Glob touched. OpenCode sessions contribute only their id, model, and creation time. This implements PRD-D, with three gaps: `once` never refreshes a session it imported while the session was still running, and skips the hook directory whenever a transcript with the same id exists (QUES-D); `import` adds to skill call counts again on every re-run, so it is not repeatable (QUES-E); and OpenCode token and cost figures are read but not stored (QUES-H).

### DSGN-D — Correction detector

The detector skips empty prompts, slash commands, and one-word prompts. It scores the lowercased prompt by summing the weights of matching phrases: strong ones such as "you should have", "why didn't you", and "I told you" weigh 1.0, "wrong" 0.5, "stop" 0.3, and "no" 0.2. A score of at least 0.8, or 0.9 for prompts longer than 300 characters, writes `~/.coworker/analytics/traces/correction-<timestamp>.md` with a draft status, the score, the first 200 characters of the prompt, and empty sections for what was wrong, the expected behavior, and the fix. Two corrections in the same second overwrite each other, and nothing in this repository reads the traces yet. This implements PRD-F; the detector's positive case is not tested (QUES-G).

### DSGN-E — Privacy and retention

Prompts, tool inputs, tool results up to 10,000 characters, assistant text, working folders, file paths, and branch names are stored in plain text. Nothing is redacted, which does not meet PRD-G (QUES-A). Nothing is sent off the machine.

Raw session directories are deleted by the memory curator when the session is already in the database, the directory is older than 30 days, the weekly curator run is due, and the memory backend is available. The database, `index.jsonl`, the traces, and `_unattributed/` are never pruned, and there is no delete command; uninstall keeps `~/.coworker/analytics/`. This implements PRD-H.

### Sub-problem ownership (子问题归属)

| 子问题 | 归属 | 依据 |
|---|---|---|
| How Claude Code treats a hook that exits non-zero or prints output | AI 查 | UNKNOWN; outside this repository |
| Whether `index.jsonl` is still needed | 人决定 | QUES-F; nothing reads it |
| What to redact, and whether redaction belongs in the hooks or the importer | 人决定 | QUES-A |

## Testing Decisions

Hooks are tested by running them with a sample payload against a temporary home directory; importers and migrations are tested against temporary databases. The cases are in the [test plan](../test-plan/analytics-listener-test-plan.md).

## Out of Scope

The dashboard, session summaries, knowledge cards, and hook registration are specified elsewhere, as listed in the [PRD](../prd/analytics-listener-prd.md#out-of-scope).

## Further Notes

The installer also registers an OpenCode analytics plugin when the directory `.opencode/coworker-analytics` exists in the checkout. That directory is ignored by git and its source is no longer in the repository, so on a fresh clone no plugin is registered and OpenCode sessions are known only through their metadata (DSGN-C).

## Alternatives Considered

Writing hook events straight into SQLite was rejected: a hook interrupted mid-write could leave a locked or damaged database, and every hook would need the Python package. Relying only on Claude Code transcripts was rejected because they carry no tool durations (ARD-C).

## Drawbacks

Data is duplicated: once in the session files, once in the database. Imports must be run, by hand or by the daemon, before the dashboard shows recent sessions.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| A hook slows or breaks the session | Writes ignore failure; gaps in QUES-B |
| Secrets end up in the database | Not mitigated today (QUES-A) |
| The disk fills with old sessions | Imported directories older than 30 days are pruned (DSGN-E); the database grows without limit |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | Prompts and tool inputs, which can contain API keys and passwords, are stored unredacted. Should the hooks or the importer redact known secret patterns, as PRD-G requires? | Found in the code at `a0f4ce0`; no redaction exists. | cicidi | yes |
| **QUES-B** | `on-stop.sh`'s last write and `on-correction.py`'s file write are unguarded, so a write failure makes the hook exit non-zero. Guard them? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-C** | The sequence counter has no lock, so concurrent hooks can share a number. Lock it, or accept? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-D** | `once` skips sessions already imported, so a session imported mid-run is never completed, and hook data is ignored when a transcript exists. Re-import open sessions and merge both sources? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-E** | `import` adds to `skills.total_calls` again on each run. Make it repeatable? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-F** | Nothing reads `index.jsonl`. Remove it? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-G** | The only positive test for the correction detector is marked expected-to-fail and sends a differently shaped payload, so the detector firing is untested. Fix the test? | Found in `tests/python/test_correction_detector.py` at `a0f4ce0`. | cicidi | no |
| **QUES-H** | OpenCode token and cost figures are selected but not stored, and no importer fills the token columns for Claude Code sessions. Store them? | Found in the code at `a0f4ce0`. | cicidi | no |

## Reversibility

Removing the hook entries from `~/.claude/settings.json`, or running the uninstaller, stops recording. Recorded data stays until the user deletes `~/.coworker/analytics/`. The database can be rebuilt from the session files and transcripts that still exist.

## Terms

| Term | Meaning |
|---|---|
| Hook | A command Claude Code runs on an event, registered in `~/.claude/settings.json` |
| JSONL | A text file with one JSON object per line, appended to and never rewritten |
| Transcript | The file Claude Code itself keeps for each session under `~/.claude/projects/` |
| Write-ahead logging | A SQLite mode that lets readers and a writer work at the same time |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0` with the 13 required sections; gaps recorded as QUES-A to QUES-H (ARD-A, ARD-D) |
