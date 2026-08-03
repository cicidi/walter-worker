---
name: multi-model-team
description: |
  Use when the user presents a large task (build a full feature, implement X
  system, refactor a module) that benefits from decomposition into subtasks
  executed by specialized workers. Use when the user says "orchestrate this",
  "dispatch to workers", "split this into subtasks", or "use the team".
  The architect (GLM 5.2) analyzes, splits, and dispatches; workers
  (DeepSeek v4 Pro) implement; the architect reviews and integrates.
license: MIT
compatibility: opencode
metadata:
  triggers:
    - build a full feature
    - implement X system
    - orchestrate this
    - dispatch to workers
    - split this into subtasks
    - break this down
    - use the team
  when_to_use: |
    Use when the task is complex enough to benefit from decomposition
    (touches 3+ files, spans multiple concerns, or requires independent
    parallel work). The architect model handles reasoning and judgment;
    worker models handle mechanical implementation.
  when_not_to_use: |
    Skip for single-file edits, trivial fixes, or tasks completable in
    under 3 trivial steps. Skip when the models are not configured.
---

# multi-model-team

Orchestrate a multi-model team where a reasoning-focused architect (GLM 5.2)
decomposes tasks and dispatches implementation to worker subagents (DeepSeek v4
Pro), then reviews and integrates results. Workers self-correct up to 3 times
before escalating to the architect.

## When to Use

- Task touches 3+ files or spans multiple concerns
- Work can be parallelized into independent subtasks
- Task requires both high-level design judgment and mechanical implementation
- User says "build a full feature", "implement X system", "use the team"

## When NOT to Use

- Single-file edit or trivial fix (under 3 steps)
- Task has no independent subtasks (everything depends on everything else)
- Architect or worker models are not configured

## Prerequisites

Before using this skill, configure the following in `opencode.json`:

```json
{
  "provider": {
    "zhipu": { "models": { "glm-5.2": {} } },
    "deepseek": { "models": { "deepseek-v4-pro": {} } }
  },
  "agent": {
    "architect": {
      "mode": "primary",
      "model": "zhipu/glm-5.2",
      "description": "Analyze tasks, decompose into subtasks, dispatch workers, review results",
      "temperature": 0.1
    },
    "worker": {
      "mode": "subagent",
      "model": "deepseek/deepseek-v4-pro",
      "description": "Implement assigned subtasks with self-correction",
      "temperature": 0.2
    }
  }
}
```

Model IDs are provider-specific. Run `opencode models` to confirm available
models and adjust the `model` values to match configured providers.

## Process

### Phase 1: Analyze

The architect (GLM 5.2) reads the user's task and analyzes it:

1. Identify the goal and acceptance criteria
2. Map dependencies: what must be done before what
3. Identify parallelizable work
4. Estimate subtask count (2-5 ideally, max 8)

If the task cannot be decomposed into independent subtasks, fall back to direct
implementation by the architect.

**Fallback:** If analysis is unclear, ask the user one clarifying question.

### Phase 2: Split

The architect produces a task breakdown. For each subtask:

- Clear, self-contained description
- Expected output (files changed, test coverage)
- Dependencies on other subtasks
- Priority (high/medium/low)

Present the breakdown to the user for approval. Do not proceed until approved.

**Fallback:** If user rejects the breakdown, iterate once with their feedback,
then proceed.

### Phase 3: Dispatch

The architect dispatches workers (DeepSeek v4 Pro) for independent subtasks in
parallel using the Task tool. Each worker prompt includes:

- The exact subtask description and expected output
- Relevant file paths and context
- Constraint: do not modify files outside the assigned scope
- Instruction: return a summary of changes made and any concerns

Sequential dependencies: dispatch dependent subtasks only after their
prerequisites complete successfully.

**Worker self-correction:** If a worker reports failure, it retries with the
same prompt up to 3 times. On the 3rd failure, escalate to the architect with
the failure context.

**Fallback:** If a worker is stuck after 3 retries, the architect re-analyzes
the subtask and either rewrites the prompt or absorbs the subtask into its own
execution.

### Phase 4: Review

The architect (GLM 5.2) reviews all worker outputs:

1. Verify each subtask output matches the expected description
2. Check for integration conflicts between parallel workers
3. Run the project's test suite
4. Run the project's lint/typecheck commands

For each issue found, decide:
- Minor fix: architect fixes directly
- Moderate issue: re-dispatch the worker with specific feedback (one retry)
- Major issue: escalate to user with findings

**Fallback:** If review uncovers systemic issues (3+ subtasks have problems),
the architect re-analyzes from Phase 1 with updated context.

### Phase 5: Integrate

The architect integrates all worker outputs:

1. Verify all changed files are consistent (imports, naming, patterns)
2. Run the full test suite one final time
3. Report to the user: what was done, by which worker, and any concerns

## Anti-Patterns

| Pattern | Why Wrong | Fix |
|---------|-----------|-----|
| Dispatching all subtasks at once | Misses dependencies; workers collide on shared files | Respect dependency graph; stagger dependent tasks |
| Architect implementing everything itself | Defeats the purpose; architect model is suboptimal for implementation | Trust workers for implementation; architect only handles design and review |
| Skipping review after dispatch | Integration bugs from parallel workers go undetected | Always run Phase 4 review with full test suite |
| Dispatching a single trivial subtask | Overhead of dispatch > benefit of parallelism | Fall back to direct implementation |

## Quality Gates

### MUST (block completion)

- [ ] Task breakdown produced and approved before dispatch
- [ ] Worker prompts are self-contained with expected outputs
- [ ] Each worker returns a summary of changes
- [ ] Architect runs full test suite after all workers complete
- [ ] Architect reports final results to user

### NICE (warn but don't block)

- [ ] All worker outputs integrate without merge conflicts
- [ ] Test coverage does not decrease
- [ ] Lint and typecheck pass on first integration attempt

## Test Scenarios

### Scenario 1: Full feature build
**Input:** "Build a user authentication system with login, signup, password reset, and email verification"
**Expected:** Architect decomposes into 4 subtasks (login, signup, password-reset, email-verify). Subtasks dispatched in parallel where independent (login + signup first, then password-reset and email-verify). Workers implement; architect reviews, runs tests, reports results.

### Scenario 2: Single trivial task
**Input:** "Fix the typo in src/utils.ts line 42"
**Expected:** Architect recognizes this as a trivial single-file fix. Does not dispatch workers. Falls back to direct implementation.

### Scenario 3: Worker failure with self-correction
**Input:** "Add Redis caching to the API layer" (worker encounters an issue with Redis connection)
**Expected:** Worker retries up to 3 times with progressively adjusted approaches. On 3rd failure, escalates to architect with failure context. Architect re-analyzes and either rewrites the prompt or implements directly.

### Scenario 4: Integration conflict
**Input:** Two parallel workers both modify the same config file
**Expected:** Architect detects the conflict during Phase 4 review (test suite fails or lint catches issue). Architect resolves the conflict and re-runs tests.

### Scenario 5: Missing models configuration
**Input:** User says "use the team to build X" but architect/worker agents are not in opencode.json
**Expected:** Skill detects missing config. Reports to user: "Architect and worker agents need to be configured. Here's the required config block..." with the prerequisites JSON.

## Sources

- Phase 1-2 (Analyze/Split): confidence high — standard decomposition patterns
  from subagent-driven-development skill
- Phase 3 (Dispatch): confidence high — OpenCode Task tool with per-agent model
  config (docs/agents); worker self-correction from user interview (3 retries)
- Phase 4 (Review): confidence high — integration testing patterns from
  verification-before-completion skill
- Phase 5 (Integrate): confidence high — audit pattern from code review workflows
- Factor weights: Accuracy 0.50, Speed 0.15, Edge cases 0.20, Readability 0.05,
  Tool integration 0.10 — user-specified quality-first weighting
- Model selection: GLM 5.2 architect + DeepSeek v4 Pro workers — user-specified
  from interview
