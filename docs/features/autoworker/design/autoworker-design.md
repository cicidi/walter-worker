---
feature: autoworker
type: design
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Auto-worker — Design

Requirements are in the [PRD](../prd/autoworker-prd.md). Decisions are in the [decision history](../decision-history/autoworker-decision-history.md). Behavior below was read from the code at commit `a0f4ce0`; where it does not meet a requirement, the gap is an Open Question.

## Problem Statement

Specifications and code drift apart faster than a maintainer can audit them by hand. An AI agent can do the audit, but an unattended agent loop that hides its failures, runs forever, or reports success it did not have is worse than no loop.

## Solution

The Python side is a thin supervisor. It builds a prompt, starts a headless Claude Code session per round with a time limit, appends the session's output to a dated state file, and stops on a time budget or a round cap. The audit itself (reading specifications, comparing them with code, fixing, and classifying findings) is done by the agent following the prompt.

## User Stories

The user stories are in the [PRD](../prd/autoworker-prd.md#user-stories).

## Implementation Decisions

The agent runs as `claude -p <prompt> --output-format json` so the supervisor can read a structured result (ARD-B). A missing `claude` command is a failed round, never a silent fallback to a tool-less mode (ARD-C). There is no `coworker autoworker` command; the two commands are `coworker run` and `coworker find-issues run`.

## Design

### DSGN-A — `coworker run`

`coworker run [--loop] [--max-hours 12] [--project walter-worker]` prints a hint and exits 0 without `--loop`, which implements PRD-A. With `--loop` it first tries to set up the memory client, the language-model client, and the analytics database; if any of them fails it prints "Running in reduced mode" and continues. None of the three is used by the loop, but setting them up creates the analytics database and the memory vector folder.

### DSGN-B — Rounds and stopping

Before the first round, the supervisor reads the wrong-history entries under `docs/features/self-evolving-agent/wrong-history/`; when any is marked critical, it writes them as a delimited block into `~/CLAUDE.local.md` in the home folder. This implements PRD-F.

Each round starts `claude -p` in the current folder with a 600-second limit plus 30 seconds of grace. The first round's prompt asks the agent to audit the project against its specifications, fix real problems, follow eight working rules, report with the labels DONE_RIGHT, DONE_WRONG, NOT_DONE, and MISMATCH, and record a wrong-history entry after each fix. Later rounds get a short follow-up prompt. The prior state passed to a round is only the number of finding rows and question rows in today's state file and the file's path; no specification is loaded by the supervisor. `--project` appears only as text in the prompt.

The loop checks the time budget at the top of each round, so a round can overrun it by up to 630 seconds. It stops after 50 rounds at most and sleeps 60 seconds between rounds when time remains. There is no stop on repeated failures. These rules implement PRD-B; PRD-C is met only partly, because the specifications reach the agent through the prompt's instructions rather than as loaded context (QUES-C).

### DSGN-C — State file and result

A successful round appends `## Round N Agent Output` with the first 5,000 characters of the agent's result to `docs/features/self-evolving-agent/state/auto-worker-<YYYY-MM-DD>-state.md` in the current folder, using the UTC date, whatever `--project` says. A round counts as a fix when its output contains "fixed" or "DONE_RIGHT", at most one per round. At the end the supervisor marks the file completed and appends the rounds, fixes, asked count (always 0), and elapsed time, then prints a one-line summary. A failed round is kept only in memory: it is not written to the state file, not printed, and the command still exits 0. This does not meet PRD-D (QUES-A). The state folder is not ignored by git (QUES-D).

### DSGN-D — `coworker find-issues run`

`find-issues run [--project walter-worker] [--phases all] [--output PATH]` writes its report to `--output`, or by default to `docs/features/self-evolving-agent/state/issues-found-<YYYY-MM-DD>-auto.md`, overwriting it. An unknown phase name is an error with exit status 1.

| Phase | What it does |
|---|---|
| `prd` | Counts requirement lines in `docs/features/<project>/prd/*.md` |
| `spec` | Counts section lines starting `## §` in `docs/features/<project>/spec/*.md` |
| `web` | Writes a fixed note to search the web interactively |
| `code` | Runs `python3 -m pytest tests/python/ -q --tb=no` with a 600-second limit and counts modified files from `git status` |

Failing tests make the command write the report and then exit 1; otherwise it exits 0, including when the requirement or specification folders are missing. A test run that exceeds the limit ends the command with an uncaught error before the report is written (QUES-B). The `spec` phase looks for a `spec/` folder, which the spec standard now calls `design/` (QUES-E). These rules implement PRD-E. No phase calls a language model.

### Sub-problem ownership (子问题归属)

| 子问题 | 归属 | 依据 |
|---|---|---|
| What the agent may change in the repository | 人决定 | UNKNOWN; set by the user's Claude Code permissions, which this repository does not control |
| Whether the unused rule classes should be wired in or removed | 人决定 | QUES-F |
| Which project's state folder the loop should write to | AI 查完人决定 | QUES-D |

## Testing Decisions

The supervisor's agent start is tested with the subprocess replaced; `find-issues` is tested through the command line. The cases are in the [test plan](../test-plan/autoworker-test-plan.md), which notes that the loop itself has no test.

## Out of Scope

The memory platform's wrong-history commands, and the self-evolving-agent feature's documents, are specified elsewhere.

## Further Notes

`src/coworker/autoworker/rules.py` and `state.py` define gap checks, a requirement auditor, a dead-code detector, and state helpers that have unit tests but no caller in either command. One of them still reads the documentation path from before the move to `docs/features/`.

## Alternatives Considered

Doing the audit in Python with the rule classes was the earlier direction; the shipped commands delegate it to the agent instead, which can read any document and edit code. Running the agent through an API client without tools was rejected, because an audit that cannot read files or run tests reports nothing real (ARD-C).

## Drawbacks

Because the audit lives in a prompt, its quality cannot be tested, and the supervisor's "fixed" count is a guess from words in the output. Every round costs a full agent session.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| The loop runs far longer than intended | Time budget, 50-round cap, and per-round limit (DSGN-B) |
| Failures look like success | Not mitigated in the loop today (QUES-A) |
| The agent makes unwanted changes | Delegated to the user's Claude Code permissions; no dry run exists |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | Failed rounds are not recorded or printed, and the run exits 0 even when every round failed, for example when `claude` is not installed. Record failures and exit non-zero, as PRD-D requires? | Found in the code at `a0f4ce0`. | cicidi | yes |
| **QUES-B** | A test run longer than 600 seconds ends `find-issues` with an uncaught error and no report. Catch it and report a timeout? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-C** | The supervisor loads no specification; the agent is only told to read them. Load the project's specifications as context, as PRD-C asks, or relax PRD-C? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-D** | State always goes to the self-evolving-agent folder in the current directory, whatever `--project` says, and that folder is not ignored by git. Write per project, and ignore it? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-E** | `find-issues` looks for `spec/` and `## §` headings, which the current spec standard does not use, so it finds nothing in documents written to that standard. Update it? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-F** | The rule classes and state helpers are tested but never called. Wire them in, or remove them? | Found in the code at `a0f4ce0`. | cicidi | no |

## Reversibility

Stopping the process ends a loop. The state and report files can be deleted. Changes the agent made are ordinary repository changes, reversible through version control; the block written to `~/CLAUDE.local.md` must be removed by hand.

## Terms

| Term | Meaning |
|---|---|
| Headless session | A Claude Code run started with `-p`, which executes one prompt and exits without an interactive window |
| Round | One headless session and the recording of its output |
| Wrong-history | A folder of recorded past mistakes and the rules learned from them |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten from the code at `a0f4ce0` with the 13 required sections; gaps recorded as QUES-A to QUES-F (ARD-A, ARD-D) |
