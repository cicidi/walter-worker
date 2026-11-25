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

`coworker run [--loop] [--max-hours 12] [--project walter-worker]` prints a hint and exits 0 without `--loop`, which implements PRD-A. `--max-hours` accepts whole hours only. `--max-hours 0` runs no round, still writes a completed summary, and exits 0.

With `--loop`, the command first imports the memory client, the language-model client, and the analytics database module. The language-model module imports the `openai` package at load time, and `openai` is installed only with the `memory` optional extra in `pyproject.toml`. Without that extra, the command stops with `ModuleNotFoundError: No module named 'openai'` and exit status 1 before any round runs (QUES-G). When the imports succeed, the command tries to set the three up. If any setup step fails, it prints "Running in reduced mode" and continues. None of the three is used by the loop. Setup creates `~/.coworker/memory/vector` and the analytics database (by default `~/.coworker/analytics/analytics.db`) only when the `mem0` package is installed and `DEEPSEEK_API_KEY` is set. Otherwise the first setup step fails and the later steps are skipped.

### DSGN-B — Rounds and stopping

Before the first round, the supervisor reads the wrong-history entries in `docs/features/self-evolving-agent/wrong-history/entries/` under the current folder. It keeps only entries whose severity is critical or high and that state a prevention rule. If at least one kept entry is critical, the supervisor writes every kept rule, critical and high alike, as a delimited block into `~/CLAUDE.local.md` in the home folder, replacing any earlier block. If no kept entry is critical, nothing is written, even when high entries exist. The lessons that the prompt tells the agent to record use severity high, so they never trigger an injection by themselves.

This is how PRD-F is implemented, with two limits. Claude Code reads `CLAUDE.local.md` files from the working folder and its parent folders, so the block reaches the agent only when the working folder is inside the home folder. An injection error is caught and logged as a warning, and the run continues without the rules (QUES-H).

Each round starts `claude -p` in the current folder with a 600-second limit plus 30 seconds of grace. The command passes no permission-mode flag, so the session can use only the tools that the user's Claude Code settings already allow (see Risks and Mitigations). The first round's prompt asks the agent to audit the project against its specifications, fix real problems, follow eight working rules, and report with the labels DONE_RIGHT, DONE_WRONG, NOT_DONE, and MISMATCH. Every round's prompt, not only the first, asks the agent to record a wrong-history entry after each fix.

Rounds 2 and later start a fresh session whose prompt is only a short follow-up. That prompt carries no mission, no report labels, and no project name. The prior state passed to a round is the state file's path plus counts of lines containing `| C-` (checked items) and `| Q-` (questions). Neither the supervisor nor the requested report labels produce such lines, so the counts are normally 0. No specification is loaded by the supervisor. `--project` appears only as text in the first round's prompt.

The loop checks the time budget at the top of each round, so a round can overrun it by up to 630 seconds. It stops after 50 rounds at most and sleeps 60 seconds between rounds when time remains. There is no stop on repeated failures. These rules implement PRD-B. PRD-C is met only partly. The specifications reach the agent only through the first round's instructions, not as loaded context, and later rounds receive neither the specifications nor those instructions (QUES-C).

### DSGN-C — State file and result

A successful round appends `## Round N Agent Output` with the first 5,000 characters of the agent's result to `docs/features/self-evolving-agent/state/auto-worker-<YYYY-MM-DD>-state.md` in the current folder, whatever `--project` says. A round is successful when `claude` exits 0. If its output is not JSON, the raw output is recorded as the result. A round counts as a fix when its output contains "fixed" in any letter case or "DONE_RIGHT", at most one per round. At the end the supervisor replaces every occurrence of the text `in_progress` in the file with `completed`, including any in the agent's own output. It then appends the rounds, fixes, asked count (always 0), and elapsed time, and prints a one-line summary. A failed round is kept only in memory: it is not written to the state file, not printed, and the command still exits 0. This does not meet PRD-D (QUES-A). The state folder is not ignored by git (QUES-D).

The date in the file name is the UTC date at the moment of each write, not the date the run started. A run that crosses UTC midnight therefore splits across two files, and the default 12-hour budget makes this likely. Rounds after midnight and the final summary go to a new file with a fresh header and the status completed. The first file keeps the status `in_progress` and has no summary. The prior state read by later rounds also switches to the new file (QUES-I).

### DSGN-D — `coworker find-issues run`

`find-issues run [--project walter-worker] [--phases all] [--output PATH]` writes its report to `--output`, or by default to `docs/features/self-evolving-agent/state/issues-found-<YYYY-MM-DD>-auto.md`, overwriting it. An unknown phase name is an error with exit status 1.

| Phase | What it does |
|---|---|
| `prd` | Counts lines in `docs/features/<project>/prd/*.md` that start with `- R` or contain `R1` or `R2` anywhere |
| `spec` | Counts section lines starting `## §` in `docs/features/<project>/spec/*.md` |
| `web` | Writes a fixed note to search the web interactively |
| `code` | Runs `python3 -m pytest tests/python/ -q --tb=no` with a 600-second limit and counts modified files from `git status` |

Failing tests make the command write the report and then exit 1; otherwise it exits 0, including when the requirement or specification folders are missing. A test run that exceeds the limit ends the command with an uncaught error before the report is written (QUES-B). An empty `--phases` value, such as `--phases ""` or only commas, is accepted. No phase runs, the report holds only its title line, and the command exits 0 (QUES-J).

The `prd` and `spec` phases follow conventions older than the current spec standard (QUES-E). The `prd` phase reports 0 for a PRD that uses `PRD-A`-style ids, including this feature's own PRD. The `spec` phase looks for a `spec/` folder, which the spec standard now calls `design/`. These rules implement PRD-E. No phase calls a language model.

### Sub-problem ownership (子问题归属)

| 子问题 | 归属 | 依据 |
|---|---|---|
| What the agent may change in the repository | 人决定 | UNKNOWN; set by the user's Claude Code permissions, which this repository does not control |
| Whether the unused rule classes should be wired in or removed | 人决定 | QUES-F |
| Which project's state folder the loop should write to | AI 查完人决定 | QUES-D |

## Testing Decisions

The supervisor's agent start is tested with the subprocess replaced; `find-issues` is tested through the command line. The cases are in the [test plan](../test-plan/autoworker-test-plan.md), which notes that the loop itself has no test.

## Out of Scope

The wrong-history commands are specified in the [memory-platform design](../../memory-platform/design/memory-platform-design.md). The self-evolving-agent feature's documents are specified in that feature.

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
| Failures look like success | Not mitigated in the loop today (QUES-A). In `find-issues`, an empty `--phases` value also exits 0 (QUES-J). |
| The agent makes unwanted changes | Delegated to the user's Claude Code permissions; no dry run exists |
| The agent cannot do the work it is asked to do | Not mitigated. A headless session cannot ask for permission, so any edit or shell command that the user's settings do not already allow is refused, and the round may change nothing while still counting as successful. |

## Open Questions

| ID | Question | Answer so far | Owner | Blocking |
|---|---|---|---|---|
| **QUES-A** | Failed rounds are not recorded or printed, and the run exits 0 even when every round failed, for example when `claude` is not installed. Record failures and exit non-zero, as PRD-D requires? | Found in the code at `a0f4ce0`. | cicidi | yes |
| **QUES-B** | A test run longer than 600 seconds ends `find-issues` with an uncaught error and no report. Catch it and report a timeout? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-C** | The supervisor loads no specification; the agent is only told to read them. Rounds 2 and later also get no mission and no report labels. Load the project's specifications as context in every round, as PRD-C asks, or relax PRD-C? | Found in the code at `a0f4ce0`. The later-round part was added by the 2026-11-24 review. | cicidi | no |
| **QUES-D** | State always goes to the self-evolving-agent folder in the current directory, whatever `--project` says, and that folder is not ignored by git. Write per project, and ignore it? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-E** | The `prd` phase of `find-issues` counts lines starting `- R` or containing `R1` or `R2`, and the `spec` phase looks for `spec/` and `## §` headings. The current spec standard uses none of these, so both phases find nothing in documents written to it. Update both phases? | Found in the code at `a0f4ce0`. The `prd` part was added by the 2026-11-24 review. | cicidi | no |
| **QUES-F** | The rule classes and state helpers are tested but never called. Wire them in, or remove them? | Found in the code at `a0f4ce0`. | cicidi | no |
| **QUES-G** | `run --loop` imports the `openai` package before its reduced-mode error handling, so an install without the `memory` extra stops with `ModuleNotFoundError` before any round. Move the imports inside the error handling, or declare the extra required? | Found by the 2026-11-24 review. The crash is visible, not silent. The PRD lists the extra under Resources Needed. | cicidi | no |
| **QUES-H** | Wrong-history injection needs one critical entry but then writes critical and high rules. It writes to `~/CLAUDE.local.md`, which reaches the agent only when the working folder is inside the home folder, and an error is only logged. Change the trigger, the content, or the target so PRD-F holds for every project? | Found by the 2026-11-24 review. The agent's own lessons are recorded as high, so they never trigger an injection. | cicidi | no |
| **QUES-I** | The state file name uses the UTC date at each write, so a run that crosses UTC midnight splits across two files and leaves the first one `in_progress` without a summary. Fix the date when the run starts? | Found by the 2026-11-24 review. No round output is lost. | cicidi | no |
| **QUES-J** | `find-issues run --phases ""` runs no phase, writes a report with only its title, and exits 0. Treat an empty phase list as an error, as PRD-E requires for an unknown phase name? | Found by the 2026-11-24 review. A scheduled job with this value reports success while inspecting nothing. | cicidi | no |

## Reversibility

Stopping the process ends a loop. An interrupt such as Ctrl-C skips the final summary, so the state file keeps the status `in_progress` and has no summary. The state and report files can be deleted. Changes the agent made are ordinary repository changes, reversible through version control. The block written to `~/CLAUDE.local.md` must be removed by hand. Setup may also create `~/.coworker/memory/vector` and the analytics database outside the repository (DSGN-A). The memory and analytics commands share them, so deleting them affects those commands too.

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
| 0.3 | 2026-11-24 | Review fixes: the `openai` crash, the injection rule and its limits, the `prd` phase rule, the UTC-midnight split, later-round prompts, empty `--phases`, Ctrl-C, headless permissions; QUES-G to QUES-J added, QUES-C and QUES-E widened (ARD-D, ARD-E) |
