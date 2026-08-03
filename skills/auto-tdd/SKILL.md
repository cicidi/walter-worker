---
name: auto-tdd
description: |
  Use when developing features or fixing bugs with test-driven methodology.
  Use when the user wants TDD, test-first development, or a self-correcting
  multi-agent TDD loop. Two modes: basic red-green-refactor and full
  multi-agent continuous loop.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - tdd
    - auto tdd
    - test driven
    - test first
    - red green refactor
    - write tests first
---

# auto-tdd

Two-mode test-driven development. Basic mode is classic red-green-refactor
through public interfaces. Auto mode is a continuous multi-agent TDD loop
with arbitration judge and quality judge — never stops until all tiers pass.

## When to Use

- Building features or fixing bugs where correctness matters
- Wanting test-first discipline enforced by process
- Complex work needing multi-agent quality assurance (auto mode)

## When NOT to Use

- Trivial one-line changes with no behavioral impact
- Pure configuration or documentation changes
- Prototyping where tests would be thrown away

## Process

### Step 0: Determine Mode

Ask the user ONE question:

> "Basic TDD (red-green-refactor, one test at a time) or auto TDD
> (multi-agent continuous loop with quality judge)?"

---

## Branch A: Basic TDD — Red-Green-Refactor

Classic test-driven development. Tests verify behavior through public
interfaces, not implementation details.

### Phase 1: Plan

1. Confirm interface changes needed
2. Prioritize behaviors to test
3. Design interfaces for testability
4. Get user approval

### Phase 2: Tracer Bullet

1. Write ONE test for ONE behavior → RED (it fails)
2. Write minimal code to pass → GREEN
3. This proves the end-to-end path works

### Phase 3: Incremental Loop

For each remaining behavior:
1. RED — write the next test, confirm it fails
2. GREEN — write minimal code to pass, one test at a time
3. Never anticipate future tests
4. Keep tests focused on observable behavior

### Phase 4: Refactor

After ALL tests pass:
1. Extract duplication
2. Deepen modules (SOLID)
3. Run tests after each refactor step
4. Never refactor while RED

**Anti-pattern:** Horizontal slicing (writing all tests first, then all code).
Always vertical slicing — one test, one implementation, repeat.

---

## Branch B: Auto TDD — Multi-Agent Continuous Loop

Four specialized agents in a self-sustaining loop. The loop continues until
all todos are done, all three test tiers pass, and quality judge signs off.

### Agent A — Implementation

Writes or refines code. Follows framework conventions, max 1000 lines/file,
max 50 lines/method. Anti-stall: pre-existing bugs become tasks immediately.

### Agent B — Three-Tier Testing

**Tier 1 — Deterministic:** Fixed-scenario tests with MockGateway. For every
test, write 2-3 variant tests by changing one dimension.

**Tier 2 — Simulated LLM:** An actual LLM role-plays as the user. At least
2 different models. Same variant protocol.

**Tier 3 — Quality Judge:** Turn-by-turn analysis of response quality,
error detection, multi-turn coherence. Score 1-10.

### Agent C — Arbitration Judge

When A and B disagree on root cause: reads failing test, implementation, spec.
Priority: spec > framework conventions > style. Rulings must cite spec sections.

### Agent D — Quality Judge

Runs after every test pass. Produces a quality report with score and specific
recommendations. Sign-off required for completion.

### Completion Criteria

ALL of: todo list empty, three tiers pass, Agent-D quality judge signs off,
contrarian review produces zero CRITICAL + HIGH gaps. Closed-loop rule:
when fixing code, also fix specs and skills that allowed the bug.

## Quality Gates

### Basic TDD MUST
- [ ] Test describes behavior, not implementation
- [ ] Test uses public interface only
- [ ] Code is minimal for this test
- [ ] Never refactor while RED

### Auto TDD MUST
- [ ] Never stop before complete
- [ ] Tiers run strictly 1 → 2 → 3
- [ ] Agent-C rulings cite spec sections
- [ ] Every failure becomes a tracked task
- [ ] Agent-D runs after every test pass
