---
feature: analytics-listener
type: design
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Analytics Listener — Design

Requirements are in the [PRD](../prd/analytics-listener-prd.md). Decisions are in the [decision history](../decision-history/analytics-listener-decision-history.md). Behavior below was read from the code at commit `a0f4ce0`, and every `file:line` citation refers to that commit. Files named without a folder are under `src/coworker/analytics/hooks/`, `src/coworker/analytics/`, or `src/coworker/memory/`. Where the code does not meet a requirement, the gap is an Open Question.

## Problem Statement

walter-worker wants to answer questions such as "which tools do I use most", "how long do sessions last", and "what did I work on last week", and its [memory platform](../../../../memory-platform/design/memory-platform-design.md) wants the raw material of past sessions. Claude Code keeps transcripts, but not in a form that is easy to query across sessions, and it does not record tool timings or which files a session touched.

## Solution

Small shell hooks append one JSON line per event to plain files, which is cheap enough to run on every prompt and tool call and cannot corrupt a database if interrupted. Importers, run on demand or by a background loop, turn those files and Claude Code's own transcripts into rows in one SQLite database, which every reader queries.

## User Stories

The user stories are in the [PRD](../prd/analytics-listener-prd.md#user-stories).

## Implementation Decisions

Hooks are bash scripts with small inline Python for JSON parsing, so they start fast and need no installed package (ARD-B). Claude Code transcripts are the preferred source of message text, because they contain the assistant's replies, which the hooks never see (ARD-C). The database schema is created and migrated on every connection, so a missing or old database is never an error.

## Design

### DSGN-A — Hooks and the files they write

The installer copies the hook scripts to `~/.coworker/analytics/hooks/` and registers them in `~/.claude/settings.json` with no timeout set (`setup/install.sh:652-662` at `a0f4ce0`). Without a timeout of its own, a hook gets Claude Code's default limit of 60 seconds ([Claude Code hooks reference](https://docs.claude.com/en/docs/claude-code/hooks)).

| Hook | Claude Code event | Writes |
|---|---|---|
| `on-user-prompt.sh` | `UserPromptSubmit` (prompt submitted) | One line in `sessions/<id>/messages.jsonl` with the time, the type `user`, the sequence number, and the full prompt |
| `on-pre-tool.sh` | `PreToolUse` (before a tool runs) | One line in `sessions/<id>/tools.jsonl` with the phase `before`, the tool name, the call id, the sequence number, and the full tool input |
| `on-post-tool.sh` | `PostToolUse` (after a tool runs) | One line in `tools.jsonl` with the phase `after`, the tool name, the call id, the result, and the duration |
| `on-stop.sh` | `Stop` (the assistant finished a turn) | Sets or refreshes a `closed` time in `sessions/<id>/session.yaml`, runs `coworker memory curate --if-due`, and, after the first turn only, appends one line for the session to `~/.coworker/analytics/index.jsonl` |
| `on-correction.py` | `UserPromptSubmit` (prompt submitted) | A draft trace, when the prompt reads as a correction (DSGN-D) |

All paths above are under `~/.coworker/analytics/`. The first hook of a session creates `sessions/<id>/session.yaml` with the session id, creation time, the tool name `claude-code`, and the working folder. Sequence numbers come from a per-session counter file, `.seq`. The hooks write local times with a UTC offset. These rules implement PRD-A.

The after-record's result is Python's `str()` of the tool response, cut to 10,000 characters and then quoted as a JSON string (`on-post-tool.sh:17`). A response that is a dictionary is therefore stored as Python text such as `{'a': 'b'}`, not as JSON (QUES-O).

Claude Code fires `Stop` each time the assistant finishes a turn, not only when the session ends ([Claude Code hooks reference](https://docs.claude.com/en/docs/claude-code/hooks)); the hook's own comment says so (`on-stop.sh:24`). Two things follow. The `closed` time is the time of the last finished turn, not a session end. The `index.jsonl` line is written once, after the first turn, so its message and tool counts describe the first turn and never change (`on-stop.sh:30-49`).

The same installer step registers two more `Stop` hooks, `coworker memory capture` and `coworker memory close` (`setup/install.sh:678,684`). They belong to the [memory platform](../../../../memory-platform/design/memory-platform-design.md) feature (its DSGN-A and DSGN-B), not to this one.

### DSGN-B — Failure behavior

Claude Code treats a hook's exit status as follows: 0 is success, 2 blocks the event, and any other non-zero status is reported but does not block the session. For a `UserPromptSubmit` hook that exits 0, Claude Code adds what the hook prints on standard output to the model's context ([Claude Code hooks reference](https://docs.claude.com/en/docs/claude-code/hooks)). No hook here exits 2 on purpose.

Every write in the prompt and tool hooks ends in a step that ignores failure (`common.sh:52`), so those hooks exit successfully even when the disk is full. This implements the "exits successfully" part of PRD-B for those hooks. Two exceptions break it today: the last write in `on-stop.sh` is not guarded (`on-stop.sh:48-49`), and `on-correction.py` has no error handling around its file write (`on-correction.py:85-102`) (QUES-B). The counter file is read and incremented without a lock (`common.sh:39-45`), so two hooks firing together can produce the same sequence number (QUES-C).

Exiting successfully does not mean the record is valid. The tool hooks have Python print each payload field on its own line and read the fields back one line at a time (`on-pre-tool.sh:9-15`, `on-post-tool.sh:10-19`). A field that contains a newline, such as a tool call id, shifts every later field by one line, and the hook writes a line that is not valid JSON. When the payload is not JSON at all, `read` clears the default value, so `on-user-prompt.sh` writes `"content":}` (`on-user-prompt.sh:13-21`). When `duration_ms` is `null`, `on-post-tool.sh` writes the Python word `None` (`on-post-tool.sh:18`). The hook-file importer, which both `import` and `once` use, skips a line it cannot parse without any warning (`import_data.py:162,175`), so these records are lost silently. The 2026-11-24 review counted, read-only on the owner's machine, 1,596 of 8,171 before-records, 1,541 of 7,943 after-records, and 54 of 486 message lines that do not parse (`../raw/review/2026-11-24-spec-review-analytics-listener-gaps.md`). PRD-A is not met for these records (QUES-J).

Each shell hook starts two Python interpreters, not one: one in `common.sh:12` reads the session id, and one reads the other fields. `on-stop.sh` also runs `coworker memory curate --if-due` synchronously on every turn (`on-stop.sh:28`). When the curator is not due, that command only reads a stamp file. When it is due, the stamp is written only after a run without errors (`cli_memory.py:462-484`). So while mem0 (the memory library, see Terms) is unavailable or a run keeps failing, every turn either loads the mem0 library, which happens before the API key is checked (`mem0_client.py:73`), or reruns the whole curator. Nothing bounds this below Claude Code's 60-second default, so PRD-B's "finishes quickly" is not guaranteed (QUES-M).

With `HOME` unset, the shell hooks build their paths from an empty `$HOME`, so they try to write under `/.coworker`, which an ordinary user cannot create. The prompt and tool hooks print errors on standard error and exit 0, and `on-stop.sh` exits 1 because its last write is unguarded. `on-correction.py` uses Python's `Path.home()`, which falls back to the home directory in the system's user database, so it still writes its trace into the real home directory. These results were observed by the 2026-11-24 review (`../raw/review/2026-11-24-spec-review-analytics-listener-gaps.md`, finding I5).

A prompt or tool record whose payload has no session id goes to `sessions/_unattributed/`, and those hooks write no `session.yaml` there (`common.sh:31-35`). The quarantine is not complete. When `on-stop.sh` gets no session id, it appends a `closed:` line to `_unattributed/session.yaml` and so creates that file (`on-stop.sh:13-19`), and it adds an `index.jsonl` line for the id `_unattributed`. `once` skips directory names that start with `_` (`auto_import.py:335`), but `import` skips only names that start with a dot (`import_data.py:294-299`). So `import` stores `_unattributed` as an ordinary session, and once that id is in the database the curator may delete the directory (`curator.py:103-109`). PRD-C is met by `once` but not by `import` (QUES-L).

### DSGN-C — Import into the database

The database is `$COWORKER_ANALYTICS_DB` if set, else `~/.coworker/analytics/analytics.db`. Every connection creates the parent folder, turns on write-ahead logging and foreign keys, creates any missing table, and runs the migrations, including renaming the old `initiative` column to `feature`. This implements PRD-E. The main tables are `sessions`, `messages`, `tool_calls`, `file_ops`, `session_stats`, `skills`, `knowledge`, and `session_summaries`.

The `coworker analytics` commands run the importers; none takes options.

| Command | Behavior |
|---|---|
| `create-db` | Creates the database with its schema |
| `import` | Re-imports every hook session directory that has a `session.yaml`, skipping only names that start with a dot, so `_unattributed` is included (DSGN-B) |
| `once` | One pass: Claude Code transcripts under `~/.claude/projects/`, then hook directories, then OpenCode session metadata; skips any session id already in the database, so a hook directory whose id was just imported from a transcript is skipped (`auto_import.py:310-345`) |
| `daemon` | Runs `once` every 30 minutes, forever; nothing starts it automatically |

Importing a hook session (the path `import` uses, and `once` uses for hook directories) infers the project from the working folder, the git branch, and the active feature from the project's `CLAUDE.local.md` or the branch prefix. It takes message text from the matching Claude Code transcript when one exists, keeping the user's typed prompts and the assistant's text, cut to 10,000 characters, and falls back to the hook's `messages.jsonl` otherwise. It pairs before and after tool records by call id and records which files Read, Write, Edit, and Glob touched. OpenCode (another AI coding tool, see Terms) sessions contribute only their id, model, and creation time, and sessions with an empty title are skipped (`auto_import.py:273`).

The transcript importer, which `once` runs first, stores less. It keeps message text only when a message's content is a list of blocks (`auto_import.py:127-134`), but Claude Code stores a typed prompt as a plain string, so the user's typed prompts are never stored. It sets the project to the transcript's encoded folder name, such as `-home-x-project-foo`, leaves the branch, feature, and closed time empty, and stores tool calls with no result and no duration (`auto_import.py:143-147,180-184`). Because `once` then skips the hook directory with the same id, the hook copy of each prompt never arrives either. On the default path (`once` and `daemon`), PRD-D and the PRD's first success metric, "every prompt appears in the database", are therefore not met (QUES-I). Transcript times are UTC with a `Z` suffix, unlike the hooks' local times.

A re-import does not refresh everything. `import` replaces the session row (`import_data.py:80`), but it inserts tool calls and file operations only when they are new (`import_data.py:206,227`). A tool call first imported with only its before-record keeps an empty result and a zero duration after later imports. Skill counts also differ by importer. The hook importer adds 1 to `skills.total_calls` for each distinct skill in a session on every import (`import_data.py:232-253`), while the transcript importer adds 1 for each call (`auto_import.py:149-154`). So `total_calls` means different things depending on which importer ran (QUES-E).

This implements PRD-D, with these gaps: typed prompts are lost on the transcript path (QUES-I); `once` never refreshes a session it imported while the session was still running, and skips the hook directory whenever a transcript with the same id exists (QUES-D); re-imports are not repeatable and leave stale tool calls (QUES-E); and OpenCode token and cost figures are read but not stored (QUES-H).

### DSGN-D — Correction detector

The detector skips empty prompts, slash commands, and one-word prompts. It gives the lowercased prompt a score from a fixed list of weighted correction phrases. An explicit correction phrase, such as "you should have" or "I told you", is enough on its own to write a trace, and a weak word such as "no" or "stop" is not. A trace is written when the score is at least 0.8, or at least 0.9 for prompts longer than 300 characters. The phrase list and its weights are an internal detail of `on-correction.py:26-37` and may change without changing this contract.

The trace is `~/.coworker/analytics/traces/correction-<timestamp>.md`, with a draft status, the score, the first 200 characters of the prompt, and empty sections for what was wrong, the expected behavior, and the fix. Two corrections in the same second overwrite each other, and nothing in this repository reads the traces yet. After writing, the detector prints `correction trace written: <path>` on standard output (`on-correction.py:103`). Because Claude Code adds a `UserPromptSubmit` hook's standard output to the model's context (DSGN-B), the model sees that line (QUES-N). The detector finds the home directory with `Path.home()`, so with `HOME` unset it writes into the real home directory (DSGN-B).

This implements PRD-F. The detector's positive case is not tested, and its tests run a file path that does not exist (QUES-G).

### DSGN-E — Privacy and retention

Prompts, tool inputs, tool results up to 10,000 characters, assistant text, working folders, file paths, and branch names are stored in plain text. Nothing is redacted, which does not meet PRD-G (QUES-A). Nothing is sent off the machine.

Raw session directories are deleted by the curator of the [memory platform](../../../../memory-platform/design/memory-platform-design.md) feature (its DSGN-D). It deletes a directory when the directory's session id is in the database, the directory is older than 30 days, the weekly curator run is due, and mem0 is available (`curator.py:95-109`, `cli_memory.py:462-479`). An id in the database does not mean this directory was imported. `once` puts the id there from the transcript and skips the hook directory (`auto_import.py:319-345`), so the tool results and durations in `tools.jsonl` are deleted after 30 days without ever reaching the database (QUES-K).

The database, `index.jsonl`, and the traces are never pruned. `_unattributed/` is not pruned unless `import` has stored it as a session (DSGN-B, QUES-L). There is no delete command, and uninstall keeps `~/.coworker/analytics/`. This implements PRD-H, except for the data loss in QUES-K.

### Sub-problem ownership (子问题归属)

| 子问题 | 归属 | 依据 |
|---|---|---|
| How Claude Code treats a hook that exits non-zero or prints output | AI 查 | Answered in DSGN-B: exit 2 blocks, other non-zero codes do not, and `UserPromptSubmit` output reaches the model; https://docs.claude.com/en/docs/claude-code/hooks |
| Whether `index.jsonl` is still needed | 人决定 | QUES-F; nothing reads it |
| What to redact, and whether redaction belongs in the hooks or the importer | 人决定 | QUES-A |
| How to make every hook record valid JSON, and whether to merge transcript and hook data | 人决定 | QUES-I, QUES-J, QUES-D |
| Whether the detector's output line should reach the model | 人决定 | QUES-N |

## Testing Decisions

Hooks are tested by running them with a sample payload against a temporary home directory; importers and migrations are tested against temporary databases. The cases are in the [test plan](../test-plan/analytics-listener-test-plan.md).

## Out of Scope

The dashboard, session summaries, knowledge cards, and hook registration are specified elsewhere, as listed in the [PRD](../prd/analytics-listener-prd.md#out-of-scope).

## Further Notes

The installer also registers an OpenCode analytics plugin when the directory `.opencode/coworker-analytics` exists in the checkout and the file `~/.config/opencode/config.json` exists (`setup/install.sh:697`). That directory is ignored by git and its source is no longer in the repository, so on a fresh clone no plugin is registered and OpenCode sessions are known only through their metadata (DSGN-C).

## Alternatives Considered

Writing hook events straight into SQLite was rejected: a hook interrupted mid-write could leave a locked or damaged database, and every hook would need the Python package. Relying only on Claude Code transcripts was rejected because they carry no tool durations (ARD-C).

## Drawbacks

Data is duplicated: once in the session files, once in the database. Imports must be run, by hand or by the daemon, before the dashboard shows recent sessions.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| A hook slows or breaks the session | Writes ignore failure; gaps in QUES-B |
| The Stop hook's curator check is slow on every turn while mem0 is unavailable or a run fails | Not mitigated today; Claude Code's 60-second default is the only bound (QUES-M) |
| Records are lost silently: invalid JSON lines, typed prompts on the transcript path, and pruned hook data that was never imported | Not mitigated today (QUES-J, QUES-I, QUES-K) |
| Secrets end up in the database | Not mitigated today (QUES-A) |
| The disk fills with old sessions | Directories whose session id is in the database and that are older than 30 days are pruned (DSGN-E); the database grows without limit |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | Prompts and tool inputs, which can contain API keys and passwords, are stored unredacted. Should the hooks or the importer redact known secret patterns, as PRD-G requires? | No redaction exists; see `on-user-prompt.sh:14-17` and `on-pre-tool.sh:14` at `a0f4ce0`. | cicidi | yes |
| **QUES-B** | `on-stop.sh`'s last write and `on-correction.py`'s file write are unguarded, so a write failure makes the hook exit non-zero. Guard them? | `on-stop.sh:48-49` and `on-correction.py:85-102` at `a0f4ce0`. | cicidi | no |
| **QUES-C** | The sequence counter has no lock, so concurrent hooks can share a number. Lock it, or accept? | `common.sh:39-45` at `a0f4ce0`. | cicidi | no |
| **QUES-D** | `once` skips sessions already imported, so a session imported mid-run is never completed, and hook data is ignored when a transcript exists. Re-import open sessions and merge both sources? | `auto_import.py:310-345` at `a0f4ce0`. A fix is in walter-worker PR #22 (open, `ede4fd2`): the Stop hook re-imports the session's transcript after every reply. | cicidi | no |
| **QUES-E** | `import` adds to `skills.total_calls` again on each run, keeps a tool call's empty result and zero duration once stored, and counts skills per session while the transcript importer counts per call. Make re-imports repeatable and give `total_calls` one meaning? | `import_data.py:206-211,232-253` and `auto_import.py:149-154` at `a0f4ce0`. PR #22 (open, `ede4fd2`) has the transcript importer count each skill call once across re-imports; the hook importer is unchanged. | cicidi | no |
| **QUES-F** | Nothing reads `index.jsonl`, and its counts describe only the first turn. Remove it? | `on-stop.sh:30-49` at `a0f4ce0`. | cicidi | no |
| **QUES-G** | The only positive test for the correction detector is marked expected-to-fail and sends a differently shaped payload. All four detector tests also run a hook path that does not exist (`parents[3]` points one folder above the checkout), so the three negative tests pass without running the detector. Fix the tests? | `tests/python/test_correction_detector.py:10,16,29` at `a0f4ce0`. | cicidi | no |
| **QUES-H** | OpenCode token and cost figures are selected but not stored, and no importer fills the token columns for Claude Code sessions. Store them? | `auto_import.py:272-294` at `a0f4ce0`. | cicidi | no |
| **QUES-I** | The transcript importer drops the user's typed prompts, because it keeps only list-shaped content and Claude Code stores a typed prompt as a string; it also leaves branch, feature, closed time, tool results, and durations empty. `once` and `daemon` then skip the hook copy. Read string content, and merge the hook data? | `auto_import.py:127-134,143-147,180-184,310-345` at `a0f4ce0`; reproduced in the `../raw/review/2026-11-24-spec-review-analytics-listener-gaps.md`, finding C1. PR #22 (open, `ede4fd2`) stores string-content typed prompts; the other gaps stay. | cicidi | yes |
| **QUES-J** | The hooks write lines that are not valid JSON when a field contains a newline, the payload is not JSON, or `duration_ms` is null, and the importer skips them silently; about 19% of tool records on the owner's machine do not parse. Emit each whole record from one `json.dumps` call? | `on-pre-tool.sh:9-15`, `on-post-tool.sh:10-19`, `on-user-prompt.sh:13-21` at `a0f4ce0`; counts in the `../raw/review/2026-11-24-spec-review-analytics-listener-gaps.md`, finding C2. PR #22 (open) does not change these hooks; the line-by-line field reading is the same at `f917bbf`. | cicidi | yes |
| **QUES-K** | The curator deletes a hook directory when its session id is in the database, even when only the transcript was imported, so tool results and durations that never reached the database are deleted after 30 days. Prune only directories that were imported? | `curator.py:95-109` with `auto_import.py:319-345` at `a0f4ce0`. | cicidi | yes |
| **QUES-L** | `on-stop.sh` creates `_unattributed/session.yaml`, and `import` then stores `_unattributed` as a session, after which the curator may delete it. Skip `_` names in `import` and stop creating the file? | `on-stop.sh:13-19`, `import_data.py:294-299`, `curator.py:103-109` at `a0f4ce0`. | cicidi | no |
| **QUES-M** | The Stop hook runs the curator check synchronously on every turn, and while mem0 is unavailable or a run has errors the stamp is never written, so each turn loads mem0 or reruns the curator. Bound or background it? | `on-stop.sh:28`, `cli_memory.py:462-484`, `mem0_client.py:73` at `a0f4ce0`. | cicidi | no |
| **QUES-N** | The correction detector prints `correction trace written: <path>`, which Claude Code adds to the model's context. Should that line reach the model? | `on-correction.py:103` at `a0f4ce0`. | cicidi | no |
| **QUES-O** | The after-record stores the tool response as Python `str()` text, not JSON. Store JSON instead? | `on-post-tool.sh:17` at `a0f4ce0`. | cicidi | no |

## Reversibility

Removing the hook entries from `~/.claude/settings.json`, or running the uninstaller, stops recording. Recorded data stays until the user deletes `~/.coworker/analytics/`. The database can be rebuilt from the session files and transcripts that still exist.

## Terms

| Term | Meaning |
|---|---|
| Hook | A command Claude Code runs on an event, registered in `~/.claude/settings.json` |
| JSONL | A text file with one JSON object per line, appended to and never rewritten |
| Transcript | The file Claude Code itself keeps for each session under `~/.claude/projects/` |
| Turn | One user prompt and the assistant's full response to it; Claude Code fires the `Stop` event at the end of each turn |
| Curator | The weekly maintenance job of the [memory platform](../../../../memory-platform/design/memory-platform-design.md) feature, which among other steps prunes old session directories |
| mem0 | The library the memory platform uses to store and search short lessons; the curator does not run without it |
| OpenCode | Another AI coding tool in the terminal; walter-worker reads only its session metadata |
| Python `str()` text | The way Python prints a value, for example `{'a': 'b'}` for a dictionary; it is not JSON |
| Write-ahead logging | A SQLite mode that lets readers and a writer work at the same time |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0` with the 13 required sections; gaps recorded as QUES-A to QUES-H (ARD-A, ARD-D) |
| 0.3 | 2026-11-24 | Review fixes: Stop fires per turn; DSGN-B fallback and quarantine claims corrected; transcript importer, re-import, and pruning gaps stated; DSGN-D reduced to its contract; memory platform linked; `file:line` evidence added; QUES-I to QUES-O added (ARD-D, ARD-E) |
| 0.4 | 2026-11-24 | QUES-D, QUES-E, QUES-I, and QUES-J note what open PR #22 changes; master behavior unchanged |
