---
name: doc-review
description: |
  Use when the user wants a design/spec review (adversarial stress-test before
  implementation) or a work completion review (verify finished work against
  acceptance criteria). Use when the user asks for review, sign-off, devil's
  advocate, adversarial check, or acceptance verification.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - review
    - design review
    - spec review
    - adversarial review
    - devil advocate
    - 杠精
    - work review
    - acceptance review
    - sign off
    - verify work
    - check work
    - accept work
    - challenge this
---

# doc-review

Two-branch review skill. Design review stress-tests a spec/design/proposal
before implementation. Work completion review verifies finished work against
acceptance criteria. Every finding in design review gets a severity rating;
only level 3+ issues are discussed — nitpicks and minor preferences are skipped
to avoid over-engineering.

## When to Use

- Spec, design doc, or proposal needs adversarial scrutiny before implementation
- Finished feature needs formal acceptance check against PRD/design
- User asks for review, sign-off, devil's advocate, or 杠精

## When NOT to Use

- Code-level PR review (line-by-line diff review)
- Trivial one-line changes with no architectural impact
- No concrete document or acceptance criteria to review against
- Purely conversational brainstorming without formal output

## Process

### Step 0: Determine Review Type

Ask the user ONE question:

> "Design review (stress-test a spec/design before building) or work
> completion review (verify finished work against acceptance criteria)?"

If the user chooses design review, let them know upfront: "After I collect
findings, you can choose quick scan (a single gap report) or full adversarial
review (two independent reviewers + debate on disagreements)."

Then ask which documents to review. Present candidates from `docs/` if the
user hasn't specified.

---

## Branch A: Design Review

Stress-test a spec, design doc, or proposal. Find hidden assumptions,
missing edge cases, risks, and better alternatives before implementation.

### Severity Gate

Rate every finding on a 5-point scale:

| Level | Meaning | Action |
|-------|---------|--------|
| 5 — Critical | Would break the system or require major rework | Must fix |
| 4 — Important | Significant design flaw or missing requirement | Should fix |
| 3 — Worth discussing | Real concern but not blocking | Discuss, decide |
| 2 — Minor | Nice-to-have, stylistic preference | Skip |
| 1 — Nitpick | Typo, formatting, wording preference | Skip |

**Only discuss and act on findings rated 3+.** Level 1 and 2 findings are
noted in the report as "skipped" but are NOT debated or acted upon. This
prevents bikeshedding and keeps the design from becoming over-complicated.

### Choose Intensity

After collecting findings, if ALL are level 2 or below → the doc passes,
no changes needed. If any level 3+ findings exist, ask:

> "Quick scan or full adversarial review?"
>
> - Quick scan — I'll produce a gap report (GAPS.md) with all 3+ findings.
> - Full review — two independent reviewers + debate on disagreements.

### Quick Scan

1. Read the target document.
2. Challenge every claim: is this assumption valid? Is this edge case covered?
   Are there industry alternatives the doc ignores?
3. Search the web for conflicting evidence or better patterns (at least one
   search per major claim).
4. Rate every finding 1-5 using the severity scale.
5. Write `docs/discussion/YYYY-MM-DD-<topic>-gaps.md`:

```markdown
# Gap Report — {document}

## Summary
- {N} findings: {critical} critical, {important} important, {discuss} worth discussing
- {skipped} skipped (level 1-2)
- Verdict: PASS / NEEDS WORK

## Critical (5)
| # | Finding | Section | Evidence | Fix |
|---|---------|---------|----------|-----|

## Important (4)
...

## Worth Discussing (3)
...

## Skipped (1-2)
{N} minor items skipped — see appendix.
```

### Full Adversarial Review

For important documents where the cost of being wrong is high.

#### Phase 1: Independent Critique

Launch two reviewers in parallel:

**Reviewer A — Scrutiny + Web Search:**
1. Read the target document.
2. For each section, challenge: assumptions, feasibility, risks, edge cases.
3. Search the web for each major claim or decision. Find industry patterns,
   conflicting evidence, or superior alternatives. Cite URLs.
4. Output structured findings: `section`, `concern`, `evidence` (with URLs),
   `severity` (1-5), `proposed_fix`.

**Reviewer B — Cross-Check:**
1. Read the target document independently (do NOT see Reviewer A's output).
2. Critique for: correctness (factual errors), completeness (missing content),
   clarity (ambiguous wording), consistency (internal conflicts).
3. Check every claimed constraint — is it real or assumed?
4. Output structured findings: `section`, `concern`, `evidence` (doc line
   numbers or code references), `severity` (1-5), `proposed_fix`.

#### Phase 2: Resolution

The coordinator (the driving agent):

1. **Filter by severity.** Drop all level 1-2 findings from both reviewers.
   Only 3+ proceeds.
2. **Compare findings.** If both reviewers independently flag the same issue →
   accept the finding and note the fix. If only one reviewer flags it → brief
   review: does the finding have concrete evidence? Yes → accept. No → skip.
3. **Conflicts.** If reviewers disagree on severity or fix approach, run a
   focused debate (max 3 rounds):
   - Round 1: Each side states their case in ≤3 sentences.
   - Round 2: Rebuttals with evidence (citations or code references).
   - Round 3: Final positions, ≤2 sentences each. No new evidence.
4. **Judge ruling.** After debate, rule: accept proposal / reject / compromise.
   Ruling is final. Tie → mark as "deferred" in report, do not re-debate.

#### Phase 3: Report

Write `docs/discussion/YYYY-MM-DD-<topic>-review.md`:

```markdown
# Review Report — {document}

## Summary
- Reviewed by: 2 independent reviewers
- Findings (3+): {N} — {critical}C, {important}I, {discuss}D
- Skipped (1-2): {N}
- Debated: {N} issues, {resolved} resolved, {deferred} deferred
- Verdict: APPROVED / NEEDS REVISION / BLOCKED

## Accepted Findings
| # | Level | Section | Finding | Fix |
|---|-------|---------|---------|-----|

## Deferred
| # | Issue | Why deferred |
|---|-------|-------------|

## Skipped (1-2)
{N} minor items — see appendix for full list.
```

---

## Branch B: Work Completion Review

Verify finished implementation against scope, design, and PRD. Produce a
signed acceptance report or a rejection with specific action items.

### Phase 1: Collector

Gather all work context:

1. Read the PRD, design doc, spec, and implementation plan provided by the user.
2. Search related GitHub issues (keyword-filtered by topic).
3. Read git log (commits since base branch).
4. Scan the test directory and existing test files.

Synthesize `docs/work-review/YYYY-MM-DD-<topic>/acceptance.md` with three sections:

**Acceptance Criteria** — derived from the source documents. Each criterion has
a source (doc + line), priority (MUST/SHOULD/NICE), and what "done" means.

**Test Plan** — concrete scenarios. Each has Type (E2E/unit/integration/manual),
Steps, and Expected Behavior. Describe WHAT to test, not HOW to implement.

**Regression Guard** — existing features that must not break. Each with the
test command that verifies it.

### Phase 2: Reviewer

Execute the test plan:

1. Run the existing test suite. Record pass/fail counts.
2. For E2E scenarios: write Playwright scripts from the test plan Steps,
   start the dev server, run tests, screenshot failures.
3. For API scenarios: use curl/httpie to hit endpoints, verify responses.
4. For manual scenarios: walk the code paths, verify logic.
5. Check git diff coverage against acceptance criteria — every changed file
   should trace to a criterion.
6. Scan for debug code, hardcoded secrets, stray console.log.

### Phase 3: Sign-Off

Produce `docs/work-review/YYYY-MM-DD-<topic>/report.md`:

**REJECTED** (any FAIL or MISSING criterion):
- Failed criteria table: #, criterion, status (FAIL/MISSING), reason, fix target
- Action items for the implementer

**ACCEPTED** (all MUST criteria pass):
- Signed criteria table: #, criterion, status (PASS), evidence (file:line + test result)
- Append `[SIGNED]` to each criterion in acceptance.md

## Quality Gates

### MUST (block)

- [ ] Review type determined before starting (design or work completion)
- [ ] All findings in design review rated 1-5
- [ ] Level 1-2 findings filtered out, not debated
- [ ] Web search performed for at least one major claim in full adversarial review
- [ ] Two independent reviewers used in full adversarial mode
- [ ] Debate capped at 3 rounds per issue
- [ ] All debate and ruling files written to docs/discussion/ or docs/work-review/
- [ ] Work completion: acceptance.md has all 3 sections (criteria, test plan, regression)
- [ ] Work completion: Reviewer actually executes tests, doesn't just read code
- [ ] Report always generated (GAPS.md for quick scan, review.md for full, report.md for work)

### NICE (warn)

- [ ] Reviewer citations include specific doc line numbers or URLs
- [ ] E2E test failures include screenshots
- [ ] Regression guard items have test commands
- [ ] Work completion criteria include source document and line number

## Anti-Patterns

- **Bikeshedding.** Debating level 2 findings. The severity gate exists to prevent this.
- **No evidence.** Arguments without citations or search results. Reject and re-run.
- **Reviewer reads code instead of testing.** Code-reading is not verification.
  Every test scenario must produce a pass/fail from actual execution.
- **Vague sign-off.** "Looks good" is not acceptance. SIGNED needs file:line and test result.
- **Judge defers too much.** Only defer when both sides have truly comparable evidence.
- **Endless debate.** 3 rounds max per issue. After that, judge rules on available evidence.

## Sources

- devil-advocate (skill-factory): 3-agent con/pro/judge debate pattern, max 5 rounds
- contrarian-review (skill-factory): 2-mode structure, web search mandate, cross-model review
- work-review (skill-factory): collector/reviewer gatekeeper pattern for work acceptance
- User requirement: severity gate (5-point scale, 1-2 skipped), "不要钻牛角尖"
- CONVENTIONS.md: SKILL.md structure and naming conventions
