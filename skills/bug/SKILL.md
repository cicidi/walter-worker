---
name: bug
description: |
  Use when debugging, reporting bugs, or managing the self-healing loop.
  Use when the user encounters an error, wants to file a bug, needs
  systematic root cause investigation, or wants to record a correction
  pattern for future prevention.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - bug
    - debug
    - report bug
    - file issue
    - self heal
    - self analyze
    - fix this error
    - what's wrong
    - why is this failing
    - record correction
    - learn from mistakes
---

# bug

Three-branch skill covering the full bug lifecycle: hunt (find + fix root
cause), report (file a GitHub issue), and heal (record corrections and
analyze patterns for prevention).

## When to Use

- Encountering an error or unexpected behavior that needs investigation
- Wanting to file a bug report for the walter-worker system itself
- The AI keeps making the same mistake and needs pattern-based prevention
- User corrected the AI and wants that correction remembered

## When NOT to Use

- Feature requests or enhancement proposals → use /initiative
- Code review of working code → use /doc-review design
- General questions about how something works → just ask

## Process

### Step 0: Determine Branch

Ask the user ONE question:

> "What do you need?"
> - **Hunt** — find and fix a bug (systematic root cause investigation)
> - **Report** — file a GitHub issue for the walter-worker system
> - **Heal** — record a correction and analyze patterns to prevent future mistakes

---

## Branch A: Hunt — Scientific Debugging

Hypothesis-driven root cause investigation. No guessing, no workarounds.

### Phase 1: Gather Evidence

1. Read the error message or stack trace in full
2. Read the failing test or reproduction steps
3. Read code around the failure point (trace all callers and callees)
4. Check git log: when did this start failing?
5. Verify: does it pass on the main branch?

### Phase 2: Form Hypotheses

List 3-5 possible root causes, ranked by likelihood.
- H1 (most likely): ...
- H2: ...
- H3: ...

### Phase 3: Test Hypotheses

For each hypothesis (test in order, stop at first confirmed):
1. Define a minimal test that isolates this hypothesis
2. Run the test
3. Record expected vs actual → CONFIRMED or REJECTED

### Phase 4: Fix

Once a hypothesis is CONFIRMED:
1. Identify the exact root cause (file:line)
2. Apply a **minimal** fix — address only the root cause
3. Add a regression test that would have caught this
4. Run the full test suite — verify no regressions

### Phase 5: Document

- Commit with `fix:` conventional commit format
- If the pattern is generalizable, offer to run the heal branch

---

## Branch B: Report — File a GitHub Issue

For bugs in the walter-worker system itself (not project-specific bugs).

### Steps

1. **Describe:** what the AI did wrong, what was expected, which skill/rule was involved
2. **Draft the issue:** use title prefix `[coworker]`, sections for what happened,
   expected behavior, affected component, reproduction steps, suggested fix
3. **Create:** target repo `cicidi/walter-worker`, labels `coworker-bug` or `coworker-improvement`
4. **Link:** if this was an AI mistake, also run the heal branch to log a trace

---

## Branch C: Heal — Self-Healing Loop

Record corrections and generate prevention rules.

### Phase C1: Record Correction

When the user corrects the AI:
1. Detect the correction (trigger keywords: no, don't, stop, wrong, never, "not like that", "I told you")
2. Write a trace to `.self-healing/traces/YYYY-MM-DD.yaml`:
   ```yaml
   - id: <uuid>
     timestamp: <ISO8601>
     context: <what the AI did wrong>
     correction: <what the user said>
     category: code-conventions | workflow | security | architecture | tool-use
   ```
3. Confirm: "Logged. You can run self-analyze to generate prevention rules."

### Phase C2: Analyze Patterns

When the user wants to generate prevention rules from accumulated traces:
1. Read all `traces/*.yaml` files, group by category, count frequency
2. Find patterns: same correction occurring 2+ times
3. Generate a markdown block with the rules
4. Inject into the project's CLAUDE.md (replace existing SELF-ANALYZE block or append)
5. Report: traces analyzed, patterns found, rules injected

A single correction does NOT trigger a rule — only repeated patterns (2+ occurrences).

## Quality Gates

### MUST (block)

- Hunt: hypotheses formed before any fix attempted
- Hunt: regression test added
- Hunt: fix is minimal (only root cause, no refactoring)
- Report: reproduction steps included in issue
- Report: affected skill/component identified
- Heal: trace written with valid category
- Heal: only 2+ occurrence patterns generate rules

### NICE (warn)

- Hunt: git log checked for when the failure started
- Report: suggested fix included
- Heal: suggestion to run analyze after accumulating traces
