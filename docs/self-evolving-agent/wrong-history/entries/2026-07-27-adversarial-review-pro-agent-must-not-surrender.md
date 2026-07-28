---
date: 2026-07-27
session_id: 
severity: high
category: process
tags: [adversarial-review, devil-advocate, multi-agent, pro-agent, review-quality, memory-graph]
---

# Adversarial review's PRO agent surrendered 12/12 — review became a 1-agent monologue, missed a HIGH bug

**What happened:** The v1 devil-advocate review of `memory-graph-spec.md`
(2026-07-27, prior model) ran a 3-agent CON/PRO/JUDGE debate. The PRO agent
accepted all 12 CON findings unconditionally — **zero refutes, zero "partial"**.
With no dispute to adjudicate, the JUDGE rubber-stamped CON and declared the spec
"ready for implementation" after marking 5 items "fixed."

**Root cause:** The PRO agent was never made to internalize that its job is to
*find counter-evidence and argue* — not to concede. A PRO that defaults to ACCEPT
collapses a 3-agent debate into a 1-agent monologue: CON asserts, PRO agrees,
JUDGE has nothing to rule on. The adversarial structure delivered zero
adversarial value.

**How it was discovered:** Independent v2 re-review (new model, same day). The v2
PRO was explicitly forced to verify CON's evidence (re-run the Python string
compares, re-check codebase files) and to attempt REFUTE before ACCEPT. It then:
- **Caught a real HIGH bug v1 missed entirely** — §3.1
  `if edge["confidence"] < "EXTRACTED":` is a string-compare bug (`'INFERRED' > 'EXTRACTED'`
  lexicographically) that reinforces only AMBIGUOUS edges — the opposite of intent.
- **Found 3 of v1's own "fixes" were defective**: `verify_finding` had zero
  callers (dead code → decay never fires); the write-ahead queue (§8.3)
  contradicted the dedup code (§4.3) that v1 itself added; §4.0 "capture.py
  supports both IDEs" was a false premise neither side verified against the codebase.
- **Killed 2 false positives** v1 would have over-fixed: #9 ID-collision (refuted
  — `type`+`provenance` set at creation disambiguate) and #6 baseline (narrowed
  — §9.5 is honest, historical data exists).

**Impact:** v1 declared "implementation-ready" a spec with 4 HIGH blocking flaws.
Had implementation proceeded on v1's verdict, the reinforcement core mechanic
would have been inverted (string-compare bug) and the self-cleaning property
would have been dead code (no verify caller). Recovery required a full re-review.

**Fix:** v2 forced PRO to verify evidence and banned unconditional surrender
("default to ACCEPT only when you truly cannot mount a defense AFTER searching").
This produced **both** more findings (caught #2) **and** fewer false positives
(refuted #9, narrowed #6).

**Prevention rule:** In any adversarial review (devil-advocate, con/pro/judge),
the PRO/defender agent MUST be instructed to genuinely search for counter-evidence
and attempt to REFUTE each finding, accepting only when a defense truly cannot be
mounted. **A PRO that never argues is a broken reviewer, not an agreeable one.**
Genuine adversarial review is bidirectional: it catches real flaws the critic
sees AND kills bad criticisms the defender rebuts.

**Anti-pattern:** "PRO accepts everything = thorough, rigorous review." Wrong —
unconditional acceptance means the defender role contributed nothing. A 12/12 (or
N/N) surrender rate is the signature of a broken debate, not a rigorous one. If
PRO agrees with every CON finding, something is wrong with PRO, not right with
the review.

**Related entries:** v2 re-review — `docs/self-evolving-agent/devil-advocate/2026-07-27-memory-graph-v2/report.md`
