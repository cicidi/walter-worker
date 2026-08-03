# Auto-Worker — Design

> Initiative: self-evolving-agent | Type: design | Status: **draft v1**
>
> Builds on: [PRD v6](../prd/self-evolving-agent-prd.md) (requirements), [Spec v1.1](../spec/self-evolving-agent-spec.md) (technical detail), [Memory Platform Design](memory-platform-design.md) (infrastructure)
>
> The auto-worker is a self-looping QA agent that reads PRD/spec/design docs, audits project state, finds gaps and inconsistencies, and self-executes improvements. It runs on the memory platform but has its own decision-making logic — what to check, how to judge, when to act, when to stop and ask.

---

## 1. What the Auto-Worker Does

The auto-worker is NOT a test runner. It's a **QA reviewer that also fixes things**. It reads the project's declared intent (PRD, spec, design) and compares it to reality (code, data, runtime behavior). When it finds a gap, it doesn't just report — it fixes. When it's unsure, it asks. When no one answers, it moves on and comes back later.

```
┌──────────────────────────────────────────────────────────┐
│                    AUTO-WORKER LOOP                        │
│                                                            │
│  1. Load Context                                           │
│     ├─ PRD / Spec / Design docs                            │
│     ├─ Prior run state (what was checked, what was fixed)  │
│     ├─ Memory snapshot (past lessons, conventions)          │
│     └─ Open Questions from prior runs                       │
│                                                            │
│  2. Gap Detection Loop                                      │
│     ├─ Numerical sanity checks                              │
│     ├─ Dead code / dead skill detection                     │
│     ├─ PRD/spec requirement vs implementation audit         │
│     └─ Discovery dimensions (perf, security, consistency)   │
│                                                            │
│  3. For each finding:                                       │
│     ├─ Check Working Notes → already handled? → skip        │
│     ├─ Investigate: why was it done this way?               │
│     ├─ Classify: not-done / done-wrong / done-right         │
│     ├─ Vision Check: does fixing this move us closer?       │
│     ├─ Decide: fix / ask-user / skip / note-for-later       │
│     └─ Act: research → advocate review → execute → note     │
│                                                            │
│  4. End of round:                                           │
│     ├─ Update state file with findings + verdicts            │
│     ├─ Surface unanswered Open Questions                     │
│     └─ Loop again (or stop if nothing left to check)        │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Core Rules

These rules govern every decision the auto-worker makes. They are binding — not guidelines.

### Rule 1: Validate Against Raw Data

Trust nothing derived. Every number, every claim, every metric must be traceable to raw source data.

```
skill usage count → verify against raw session transcripts
"X was implemented" → grep the code, don't trust a state file
"test passes" → run the test, don't trust a previous run's output
```

**Source of truth hierarchy:**
1. Raw session transcripts (analytics.db raw data)
2. Git history (commits, diffs)
3. Live code (filesystem)
4. Test output (run fresh)
5. State files / derived data (read with skepticism)
6. LLM summaries (read with more skepticism)

### Rule 2: Dead Code Detection

Scan for things that exist but are never used:

| Check | Method |
|-------|--------|
| Skills never invoked | Scan analytics.db: any session invoke this skill? |
| Sessions with zero file reads | Session used only chat, no tool calls touching code |
| Config keys never referenced | grep codebase for each config key name |
| State files for completed initiatives | Initiative is done → state file should be archived |
| Imported but unused modules | Static analysis |

### Rule 3: Three-Layer Attribution

For every requirement (PRD item, spec section, design decision), determine:

```
Layer 1 — Exists?
  grep/code search → found / not_found
  → "not_found" → classification: NOT DONE

Layer 2 — Works?
  Run tests, check behavior → pass / fail
  → "found but fails" → classification: DONE WRONG

Layer 3 — Correct?
  Compare implementation intent with requirement intent
  → "found and passes" → classification: DONE RIGHT
  → "found, passes, but wrong approach" → DONE WRONG (design-level)
```

### Rule 4: Working Notes — Don't Repeat

Every check, every test, every fix → write a note. Before starting any work, read prior notes.

```
State file section:
  ## Checked (this round)
  | ID | What | Verdict | Date |
  |----|------|---------|------|
  | C-1 | PRD §3.2 R3 semantic search | DONE RIGHT | 2026-07-25 |
  | C-2 | skill "session-memory" usage count | NEEDS FIX | 2026-07-25 |

  ## Fixed (this round)
  | ID | What | Action | Date |
  |----|------|--------|------|

  ## Skipped (this round)
  | ID | What | Reason | Date |
  |----|------|--------|------|
```

**Re-check policy:**
- Within same round: skip checked items while unchecked items remain
- New round (all items checked at least once): full re-check allowed
- Fixes applied: re-check the fixed area only

### Rule 5: Vision Check

Before any change, answer:

> "Self-evolving agent 的愿景是让 agent 通过使用越来越聪明。这个改动是让 agent 更聪明，还是仅仅修了一个无关紧要的东西？"

**Tie-breaker questions:**
- Does this change make future sessions smarter?
- Does this remove friction that blocks learning?
- Does this improve the quality of extracted lessons?
- Does this expose a pattern that should be captured as a skill?

If the answer to ALL is "no" → deprioritize. The auto-worker has limited time and should focus on changes that compound.

### Rule 6: Research → Advocate → Act

Before making any change:

```
1. Research
   ├─ Search web: how do other projects solve this?
   ├─ Search codebase: has this been attempted before?
   ├─ Search memory: any past lessons about this?
   └─ Read git history: what was the original intent?

2. Adversarial Review
   ├─ Run contrarian-review on the proposed change
   ├─ Challenge: is there a better approach?
   ├─ Challenge: what breaks if we do this?
   └─ Output: confirmed / refuted / amended

3. Act
   └─ Only after both steps pass
```

**Exception:** Trivial fixes (typo, obvious broken config) skip advocate review but still do step 1 research.

### Rule 7: Context-Aware Input

Every run reads more than just the PRD. Gather all relevant discussion:

- PRD items, spec sections, design decisions
- Open Questions from the PRD (§8)
- Devil's advocate review findings
- Dependency-and-sequencing decisions
- Prior state files for this initiative
- CLAUDE.local.md active initiative context

Cross-reference them: does the spec contradict the PRD? Does the design say one thing but the impl-plan another?

### Rule 8: Ask, Don't Block

```
Need human input?
  ├─ Send question (Telegram / terminal notification)
  ├─ Write to State File → Open Questions
  ├─ Continue working on OTHER tasks (don't block)
  └─ Next loop: check Open Questions first
       ├─ Answered → process
       └─ Still unanswered → skip again
```

**Before asking:** exhaust Rule 6 first (research + advocate). Only ask when:
- The original intent is genuinely unknowable (missing commit, undocumented decision)
- Two valid approaches are equally good and the choice is subjective
- The change is destructive (deleting code, changing API)

---

## 3. Decision Tree

The auto-worker's decision logic for every finding:

```
┌─────────────────────────────────────────────────────────────────┐
│                      FINDING DISCOVERED                          │
│                             │                                    │
│                             ▼                                    │
│                   ┌─────────────────┐                            │
│                   │ Check Notes:     │                            │
│                   │ already handled? │──Yes──→ SKIP               │
│                   └────────┬────────┘                            │
│                            │No                                   │
│                            ▼                                     │
│                   ┌─────────────────┐                            │
│                   │ Investigate:     │                            │
│                   │ why was it done  │                            │
│                   │ this way?        │                            │
│                   │                  │                            │
│                   │ Check: PRD, spec,│                            │
│                   │ git commit,      │                            │
│                   │ state files      │                            │
│                   └────────┬────────┘                            │
│                            │                                     │
│              ┌─────────────┼─────────────┐                       │
│              ▼             ▼             ▼                       │
│         DELIBERATE    MISTAKE /      UNKNOWN                     │
│         CHOICE        HISTORICAL     ORIGIN                      │
│              │             │             │                       │
│              ▼             ▼             ▼                       │
│         ┌────────┐   ┌─────────┐   ┌─────────┐                  │
│         │ ASK    │   │ Better  │   │ ASK     │                  │
│         │ USER   │   │ approach│   │ USER    │                  │
│         │ before │   │ exists? │   │         │                  │
│         │ changing│  │         │   │         │                  │
│         └────────┘   └────┬────┘   └─────────┘                  │
│                           │                                      │
│              ┌────────────┼────────────┐                         │
│              ▼            ▼            ▼                         │
│            YES          NO, BUT      NO                          │
│            (better      IMPROVEMENT  (works,                     │
│            approach)    POSSIBLE     no better                    │
│              │            │          way)                         │
│              ▼            ▼            ▼                         │
│         ┌────────┐   ┌─────────┐   ┌──────┐                      │
│         │ RESEARCH│  │ Note it │   │ NOTE │                      │
│         │ → ADV.  │  │ + skip  │   │ +    │                      │
│         │ → FIX   │  │ (not    │   │ SKIP │                      │
│         │         │  │  worth  │   │      │                      │
│         └────────┘  │  it)    │   └──────┘                      │
│                     └─────────┘                                   │
│                            │                                     │
│              ┌─────────────┼─────────────┐                       │
│              ▼                           ▼                       │
│         User answered              User didn't answer            │
│         → follow answer            → write Open Question         │
│                                    → continue loop               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Gap Detection Dimensions

### 4.1 Numerical Sanity

Compare claimed numbers against raw data:

| Check | Method |
|-------|--------|
| Skill usage count | Raw session transcripts vs `usage.json` |
| Session count | analytics.db `sessions` table |
| Tool call count | analytics.db `tool_calls` table |
| Cost estimates | Actual API usage vs claimed cost per session |
| Metrics (PRD §5.7) | Calculated from raw data, not read from derived tables |

### 4.2 Requirement Audit

For every requirement in PRD §3–§5, every spec section, every design decision:

| Requirement | Implementation | Verdict |
|-------------|---------------|---------|
| R1 IDE-agnostic | mem0 at `~/.coworker/memory/` | DONE RIGHT |
| R2 Per-turn persistence | PostToolUse hook → `coworker memory sync` | DONE RIGHT |
| R3 Cross-session search | mem0 hybrid retrieval | NOT DONE (mem0 not yet integrated) |
| ... | ... | ... |

### 4.3 Document Consistency

Cross-reference documents for contradictions:

- Spec says X, PRD says Y → flag
- Design decision differs from spec detail → flag
- Impl-plan references a module that doesn't exist → flag
- Open Questions in PRD have no corresponding work item → flag

### 4.4 Discovery Dimensions (from deferred QA design)

| Dimension | Check | Method |
|-----------|-------|--------|
| Test Coverage | Which branches/edge cases untested? | pytest --cov |
| Dependency Debt | Outdated/vulnerable deps? | pip list --outdated |
| Error Handling | Missing error handlers? | Static analysis |
| Code Pattern Consistency | Same thing done different ways? | grep + pattern matching |
| Config Drift | Config says X, code does Y? | Cross-reference config keys with code |

---

## 5. Loop Mechanics

### 5.1 SDK Mode

The auto-worker runs via `coworker run --loop` (SDK mode — PRD §2.2). One cycle = one complete pass through the gap detection loop.

### 5.2 Termination

Default max time: 12 hours. The loop stops when ANY of:

| Condition | Detection |
|-----------|-----------|
| All checks passed | Nothing left unchecked, no new findings |
| Stagnation | 3 consecutive cycles produce no new findings AND no fixes applied |
| Time expired | 12h elapsed → graceful stop, save state, write summary |
| Human halt | "stop" signal received |

### 5.3 State Continuity

```
Run N                     Run N+1
┌──────────────┐         ┌──────────────┐
│ Read state   │         │ Read state   │
│ Check A: done│         │ Check A: skip │
│ Check B: todo│────────▶│ Check B: run  │
│ Check C: todo│         │ Check C: skip │
│ Fix 1: done  │         │ (fixed in N)  │
│ Fix 2: todo  │         │ Fix 2: run    │
└──────────────┘         └──────────────┘
```

State file is the continuity mechanism. Every run reads the previous run's state before doing anything.

---

## 6. Integration with Memory Platform

The auto-worker is a consumer of the memory platform:

```
Memory Platform                    Auto-Worker
──────────────                     ────────────
analytics.db raw sessions ──────▶ training data for analysis
mem0 search()            ──────▶ past lessons when investigating
CLAUDE.local.md snapshot ──────▶ project conventions
memory.add()             ◀────── new lessons discovered
state files              ◀────── check results + working notes
pending queue            ◀────── skills auto-created from patterns
```

### 6.1 Training Pipeline (Phase 1 of Validation)

Before the auto-worker runs its loop, it needs initial knowledge. **All** historical sessions are used — no subset, no sampling:

```
ALL historical session data (analytics.db)
         │
         ▼
┌─────────────────────────┐
│ Batch extraction         │
│ For EVERY past session:  │
│   Read full transcript   │
│   → DeepSeek Flash       │
│   → Extract lessons      │
│   → Identify patterns    │
│   → Assess skill-worthiness │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ Output:                  │
│ • Top 10 Skills (SOPs)   │
│ • Top 10 Experiences     │
│ • Written to mem0        │
│ • Skills staged to       │
│   pending queue          │
│ • Training report        │
│   (total sessions,       │
│    lessons extracted,    │
│    skills identified)    │
└──────────────────────────┘
```

---

## 7. Validation Harness (Phase 2)

After training, validate that the knowledge is useful:

### 7.1 Task Design

The validation task is designed by the auto-worker based on available skills and experiences. Example approach:

1. Scan the 10 auto-trained skills → pick one that involves code modification
2. Scan the 10 auto-trained experiences → identify conventions the agent should follow
3. Design a task that requires BOTH skill usage AND convention knowledge

Example task: "Add a `coworker stats` CLI command that prints session statistics"

Expected behavior WITH memory:
- Agent searches memory → finds conventions (ruff E501 ignored, Click CLI pattern)
- Agent searches memory → finds the analytics.db schema (no need to re-discover)
- Agent may invoke an auto-trained skill for "add CLI command"

### 7.2 Comparison Metrics

| Metric | Without Memory | With Memory |
|--------|---------------|-------------|
| Tool calls to completion | baseline | expected lower |
| Incorrect assumptions | baseline | expected lower |
| Convention violations | baseline | expected zero |
| Auto-train skill invoked | 0 | ≥1 |
| Auto-train experience retrieved | 0 | ≥1 |

### 7.3 Claude SDK Integration

The validation harness uses Claude SDK to spawn two agents:
- **Agent A (no memory):** Fresh Claude SDK session, no context injection
- **Agent B (with memory):** Same task, but session starts with CLAUDE.local.md snapshot (injected memory + skill references)

Both agents get the same task. Their transcripts are compared against the metrics above.

---

## 8. Model Routing

| Task | Model | Why |
|------|-------|-----|
| Gap detection (per-item comparison) | DeepSeek Flash | Decomposed to yes/no per item |
| Numerical sanity validation | No model (SQL queries) | Deterministic |
| Dead code detection | No model (grep + analytics.db queries) | Deterministic |
| Investigation (why was it done this way) | DeepSeek Pro | Needs git history + multi-source synthesis |
| Vision Check | DeepSeek Pro | Subjective, needs judgment |
| Research (web search) | WebSearch (no model) | Retrieval only |
| Advocate review | Claude (stronger model) | Safety-critical, needs adversarial thinking |
| Code fixes | DeepSeek Flash | Mechanical, cheap |
| Report generation | DeepSeek Pro | Narrative quality |
| User communication | Telegram / terminal | Direct, no model needed |

---

## 9. Error Handling

| Failure | Behavior |
|---------|----------|
| LLM extraction fails | Retry 3× with backoff → skip this check → log → continue |
| analytics.db unreadable | Degrade: work from filesystem + git only. Flag to user. |
| mem0 search fails | Degrade: grep-based search. Log. |
| Git history unavailable | Degrade: work from current state only. Note reduced confidence. |
| Web search fails (Rule 6 research) | Skip external research. Note "no external reference available." |
| Advocate review fails (LLM down) | Skip advocate review. Flag "skipped safety check." |
| User unreachable (Rule 8) | Write Open Question → continue. Never block. |

---

## 10. Out of Scope (v1)

- Adversarial multi-agent review within the auto-worker (delegated to contrarian-review skill)
- Cross-project gap detection (single-project scope)
- Automatic PR creation and merge
- GEPA/DSPy prompt evolution

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-25 | Initial creation |
