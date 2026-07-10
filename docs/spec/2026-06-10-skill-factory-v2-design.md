# skill-factory v2: skill-create Design Spec

**Date:** 2026-06-10
**Status:** Draft (awaiting user review)
**Author:** Brainstorm session with user (cicidi)
**Target project:** `~/project/skill-factory/`
**Target file:** `~/project/skill-factory/skills/skill-create/SKILL.md`

---

## 1. Context & Background

This design is the v2 of a "skill creation" skill, based on a quality audit of v1 (`coworker-meta-skill-create.md` in the ai-coworker project, 590 lines, v1.0.0).

### Audit findings (v1)

The v1 audit surfaced **43 issues** in 4 severity tiers:

| Severity | Count | Examples |
|----------|-------|----------|
| 🔴 Critical | 4 | References to non-existent `scripts/`, `schemas/`, `/project/skill-repo/` paths, and missing skill dependencies (`counter-research`, `deep-research`, `security-review`, `counter-main-skill-train`) |
| 🟠 High | 17 | OCR text artifacts (`>**Phase 0.3<**` style markers), truncated sentences (`"must be reph..."`), nonsense words (`"tete-o-tee"`, `"Cherut"`, `"skill-orateur"`), self-contradictions (500-line rule but file is 590 lines) |
| 🟡 Medium | 16 | Non-standard frontmatter fields, anti-pattern violation in own example (`slack-team.slack.com` real domain), `2024-04-32` invalid date, chock-full of inconsistencies between YAML and JSON evals |
| 🟢 Low | 6 | Verbose, decorative emoji, inconsistent quoting |

**Root cause** (per v1 changelog): "Initial skill extracted from handwritten screen photos" — OCR-derived first version, never systematically reviewed.

### Why a v2

- v1 promises a 4-phase "skill factory" pipeline (Search → Interview → Build → Verify → Publish) with provenance, quality gates, and evals — but **all supporting infrastructure is missing**. The skill is a spec for a system that was never built.
- User's goal: build a new project (`~/project/skill-factory/`) that **does** have this infrastructure, with v2 as the foundation.

---

## 2. Goals & Non-Goals

### Goals

1. **Preserve the 4-phase spirit** of v1 (Search, Interview, Build, Verify, Publish) as the core process.
2. **Drop all dead references** to non-existent scripts, schemas, paths, and skills.
3. **Use opencode-compatible format** (5 frontmatter fields, `SKILL.md` filename, `skills/<name>/` directory).
4. **Leverage obra/superpowers:writing-skills** (already installed) as optional enhancement, not as a replacement.
5. **Slim to ~200 lines** — fits in context, fast to read, no progressive disclosure needed yet.
6. **Single version, no deploy/** — user explicitly said "skill-factory 就保留一个版本就行".
7. **No `## Changelog` section** — git log is the source of truth for changes.
8. **Production-ready on day 1** — every MUST gate must be enforceable today, not tomorrow.

### Non-Goals (deferred)

- ❌ Automated provenance.json (claim-level traceability)
- ❌ `scripts/` for build/validate/compile
- ❌ `schemas/` for validation
- ❌ `deploy/` concept (single version only)
- ❌ Self-evolution log (skill-forge style) — defer until v3
- ❌ Cross-harness installation (Claude Code, Cursor, Gemini sync) — project scope is opencode only
- ❌ AI-coworker integration — v2 lives independently in skill-factory

---

## 3. Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Path:** `~/project/skill-factory/skills/skill-create/SKILL.md` | Opencode-native path; flat with one folder per skill |
| D2 | **Name:** `skill-create` (no `coworker-` prefix) | Project is skill-factory, not ai-coworker; prefix would tie it to wrong project |
| D3 | **Frontmatter:** opencode 5 fields + `metadata` for extensions | Only fields opencode recognizes: `name`, `description`, `license`, `compatibility`, `metadata` |
| D4 | **No `## Changelog` body section** | User preference; git log is canonical history |
| D5 | **No `## Convention Notes` body section** | Outdated, not actionable; replaced by project `CONVENTIONS.md` |
| D6 | **No `## Rules` body section** | Merged into Quality Gates (MUST/NICE) |
| D7 | **No `## Overview` body section** | Merged into intro paragraph after title |
| D8 | **Phase 0.2 = External research + obra delegation** | Merged v1's 0.2 (open-source search) and 0.3 (deep research); obra handles "deep" via reuse audit |
| D9 | **No provenance.json** | v1's claim-level traceability is replaced by markdown `## Sources` (segment-level) |
| D10 | **No evals.json** | Replaced by markdown `## Test Scenarios` (4 scenarios, manual) |
| D11 | **No bash scripts** | No `scripts/skill-health-checks.sh`, `run-evals.sh`, `compile.sh`, `validate.sh` — Quality Gates are inline checklists |
| D12 | **obra is OPTIONAL** | Body uses `> Optional enhancement:` markers; main flow works without obra |
| D13 | **MUST/NICE quality gates** (borrowed from skill-forge) | MUST = block publish; NICE = warn only |
| D14 | **4-phase process** preserved as: Phase 0 (Search) / 1 (Interview) / 2 (Build) / 3 (Verify) / 4 (Publish) | User's explicit choice |
| D15 | **Sources段** (markdown) replaces v1's `provenance.json` | Each major section lists source + confidence (high/med/low) |
| D16 | **Test Scenarios** (markdown) replaces v1's `evals.json` | 4 scenarios, manually run, no JSON schema |

---

## 4. Architecture

### 4.1 File structure (target)

```
~/project/skill-factory/                       (new project, ~50 lines initial)
├── README.md                                  (project intro, ~40 lines)
├── CONVENTIONS.md                             (project conventions, ~50 lines)
├── .gitignore                                 (standard)
├── skills/
│   └── skill-create/
│       └── SKILL.md                           (THE deliverable, ~215 lines)
└── (future: more skills as siblings)
```

### 4.2 Naming

- File: `SKILL.md` (uppercase, opencode requirement)
- Folder: `skill-create` (matches frontmatter `name`)
- Folder format: `skills/<name>/SKILL.md` (per opencode 6 scan paths)

### 4.3 Dependencies (obra, optional)

| obra skill | When invoked | Fallback if missing |
|------------|--------------|---------------------|
| `obra/superpowers:writing-skills` | Phase 2 (CSO for description, anti-rationalization for discipline skills) | Use inline CSO checklist; skip anti-rationalization |
| `obra/superpowers:brainstorming` | Phase 1 (interview rhythm: one question at a time) | Use default interview questions from body |
| `obra/superpowers:verification-before-completion` | Phase 3 (self-review checklist) | Use inline self-review in body |
| `obra/superpowers:requesting-code-review` | Phase 3 (user review) | Inline user review prompts |
| `obra/superpowers:test-driven-development` | Phase 3 (optional, for discipline skills) | Skip TDD-for-skills enhancement |

**No hard dependencies** — all are body references, not frontmatter `metadata.requires` enforcement.

### 4.4 Opencode config (already done in this session)

The `superpowers` plugin is already added to `~/.config/opencode/config.json`. After restart, opencode will:
- Scan `~/project/skill-factory/skills/skill-create/SKILL.md` and auto-discover the skill
- Auto-load `obra/superpowers:writing-skills` (and 13 others)
- No additional config needed for skill-factory project

---

## 5. Components

### 5.1 `skill-create` (main deliverable)

**Inputs:**
- User prompt (e.g., "create a new skill for X", "I need a skill that does Y")
- Optional: reference docs, links, tribal knowledge

**Outputs:**
- A new `skills/<new-skill-name>/SKILL.md` file
- A git commit (conventional format: `skill: add <name>`)
- (No PR by default — user decides)

**Behavior — 4 phases:**

| Phase | MUST (block) | NICE (warn) | Optional obra enhancement |
|-------|--------------|-------------|---------------------------|
| **0. Search & Reuse Audit** | List existing skills in `~/project/skill-factory/skills/`; if ≥70% similar found, stop and recommend `skill-edit` instead | Web search for similar skills on GitHub | n/a |
| **1. Interview** | One question at a time; capture intent + failure modes + factor weight; ask until clear | Use obra's `brainstorming` skill for interview rhythm | obra:brainstorming |
| **2. Build** | Write frontmatter (5 fields), body sections, Sources段; use `skill-create` body as template | Run CSO check on description (per obra) | obra:writing-skills (CSO + anti-rationalization) |
| **3. Verify** | Run inline Quality Gates (MUST list); present to user; wait for sign-off | Run Test Scenarios | obra:verification-before-completion, obra:requesting-code-review, obra:test-driven-development |
| **4. Publish** | git commit with conventional message; no auto-push | Create PR | n/a |

**Error handling:**
- Phase 0 finds ≥70% match → STOP, recommend `skill-edit`
- User refuses spec review in Phase 3 → iterate, don't proceed
- Quality Gate fails → block publish, fix, re-run

### 5.2 `skill-edit` (deferred)

User mentioned wanting this too. **Not part of v2 spec** — defer to a future brainstorming session. The skill-factory project can grow to have `skill-edit/SKILL.md` later.

---

## 6. Frontmatter Spec (exact YAML)

```yaml
---
name: skill-create
description: |
  Use when creating a new skill for the skill-factory project. Walks through
  search, interview, build, verify, and publish phases with reuse audit and
  quality gates. For editing existing skills, use a separate skill-edit
  workflow instead.
license: MIT
compatibility: opencode
metadata:
  triggers:
    - create a new skill
    - new skill
    - add skill
    - build a skill
    - design a skill
  when_to_use: |
    When the user wants to create a new skill file for any AI agent harness
    supported by the skill-factory project.
  when_not_to_use: |
    For editing an existing skill, use skill-edit. For one-off workflows
    that won't be reused, write inline instead of creating a skill.
  phase_count: 4
  requires:
    - obra/superpowers:writing-skills
    - obra/superpowers:brainstorming
  audience:
    - skill-authors
    - ai-coworker
---
```

**Field rules:**
- `name`: lowercase, kebab-case, matches folder name (opencode requirement)
- `description`: third person, "Use when..." format, ≤1024 chars, **no workflow summary** (per obra CSO)
- `license`: SPDX identifier, default MIT
- `compatibility`: harness name(s), comma-separated
- `metadata`: arbitrary string-to-string map (opencode ignored unknown fields at this level; here we use it for extensions)

---

## 7. Body Structure (line budget)

| Section | Lines | Notes |
|---------|-------|-------|
| `# skill-create` + overview paragraph | ~10 | Core principle in 1-2 sentences |
| `## When to Use` | ~10 | Bullets with symptoms |
| `## When NOT to Use` | ~5 | Bullets with anti-triggers |
| `## Skill Dependencies` | ~5 | Lists optional obra; explains fallback |
| `## Process` (with 4 phases) | ~100 | Each phase ~20-25 lines |
| `## Quality Gates` | ~30 | MUST + NICE checklists |
| `## Anti-Patterns` | ~50 | 4 sets, cleaned |
| `## Test Scenarios` | ~15 | 4 markdown bullets |
| **Total** | **~215** | (vs v1's 590) |

---

## 8. Phase Specifications (detailed)

### Phase 0: Search & Reuse Audit

**MUST:**
1. List existing skills: `ls ~/project/skill-factory/skills/`
2. Read each `SKILL.md` frontmatter (`name`, `description`, `metadata.triggers`)
3. If user-provided query matches any existing skill's triggers or description ≥70%:
   - STOP
   - Tell user: "Found existing skill `X` at path Y. Did you mean to edit it? Use skill-edit."
4. If no match, continue to Phase 1

**NICE:**
- Webfetch GitHub search for similar skills (optional, slow)
- Note promising patterns in `## Sources` for Phase 2 to reference

**Sources段 input (for Phase 2 to use):**
- "Phase 0: Search — local skills scanned, N matched, M similar"
- Confidence: high (if local scan was thorough)

### Phase 1: Interview

**MUST:**
1. Ask one question at a time (don't overwhelm)
2. Capture: intent (what), trigger (when), success criteria, target audience, failure modes
3. Ask about **factor weights** (Accuracy / Speed / Edge cases / Readability / Tool integration)
4. When user says "skip" or "default", use sensible defaults:
   - Accuracy: 0.4
   - Speed: 0.2
   - Edge cases: 0.2
   - Readability: 0.1
   - Tool Integration: 0.1

**NICE:**
- Use obra `brainstorming` skill for interview rhythm
- Use multiple-choice questions when possible (faster for user)

**Sources段 input:**
- "Phase 1: Interview — factor weights recorded: {dict}"
- Confidence: medium (user's stated needs may shift)

### Phase 2: Build

**MUST:**
1. Generate name: `kebab-case`, matches project conventions
2. Create folder: `skills/<name>/`
3. Write `SKILL.md` with:
   - Frontmatter (per Section 6)
   - Body sections (per Section 7)
4. Write `## Sources` segment (markdown, not JSON):
   ```markdown
   ## Sources
   - Phase 0 (Search): confidence high — local scan complete
   - Phase 1 (Interview): confidence medium — user-stated needs
   - Phase 2 (Build): confidence high — derived from interview
   ```

**NICE:**
- Run CSO check on description (third person, "Use when...", no workflow summary, ≤500 chars)
- For discipline skills (rules/requirements), add anti-rationalization section
- Use obra `writing-skills` for both above

### Phase 3: Verify

**MUST:**
1. Run inline Quality Gates (MUST list — all must pass)
2. Self-review the new skill:
   - Placeholder scan (TBD, TODO, vague?)
   - Internal consistency (sections agree?)
   - Scope check (focused enough?)
   - Ambiguity check (could be read 2 ways?)
3. Present complete new skill to user
4. Wait for user approval
5. If user requests changes, iterate

**NICE:**
- Run Test Scenarios (4 listed in body) — does the new skill work for these?
- For discipline skills, run TDD-for-skills (per obra) — RED baseline, GREEN write, REFACTOR
- Use obra `verification-before-completion` for systematic verify
- Use obra `requesting-code-review` for code-review style feedback

### Phase 4: Publish

**MUST:**
1. git status — verify only the new skill is staged
2. git add `skills/<name>/`
3. git commit with conventional message: `skill: add <name> — <one-line description>`
4. Tell user: "Created at <path>, committed as <hash>. Push? (y/n)"

**NICE:**
- If user says yes, git push
- If user wants a PR, use `gh pr create` (if gh CLI configured)

**Sources段 input:**
- "Phase 4: Publish — git commit: <hash>"
- Confidence: high (commit hash is ground truth)

---

## 9. Quality Gates

### MUST (block publish)

- [ ] Frontmatter 5 字段完整: `name`, `description`, `license`, `compatibility`, `metadata`
- [ ] `name` 与目录名 `skills/<name>/` 匹配
- [ ] `description` ≤ 1024 字符
- [ ] `description` 不用第一人称 ("I can..." ❌)
- [ ] `description` 不总结工作流 ("dispatches subagent, then does X" ❌)
- [ ] 不引用不存在的 `scripts/`、`schemas/`、其他本地 skill
- [ ] 不引用不存在的外部路径（除非用 webfetch 动态拉）
- [ ] body 无 `## Changelog` 段（用 git log 替代）
- [ ] body 无 `## Convention Notes` 段（用项目 CONVENTIONS.md）
- [ ] 无真实组织名 / 真实 Slack domain / 真实 GitHub org 泄漏
- [ ] 无 `2024-04-32` 等无效日期
- [ ] 无装饰 emoji (✅ ❌ 🚀 🔥 等)
- [ ] 4 阶段节标题齐全 (`### Phase 0/1/2/3/4`)
- [ ] 无截断句子（`"must be reph..."` 这种）
- [ ] 无 `**>...<**` 伪影

### NICE (warn only)

- [ ] `description` 以 "Use when..." 开头
- [ ] body < 500 行
- [ ] 引用 obra 时标注是 optional
- [ ] `## Sources` 段每条标注 confidence (high/med/low)
- [ ] `## Test Scenarios` 至少 4 条
- [ ] Markdown 表格列名清晰
- [ ] 无 `TODO` / `FIXME` 残留

---

## 10. Anti-Patterns (cleaned from v1, self-violations fixed)

### Set 1: Concrete-context leak

**Symptom:** Examples cite real org names, internal Slack/GitHub URLs, GHA quota, colleague handles.

**Why wrong:** Skills are reusable across tasks/teams/orgs. Concrete leaks travel and leak.

**Bad (from v1 itself — REMOVED):**
> `anti-agent-config is the source of truth. `{{Direction [Slack]/https://slack-team.slack.com/archives/C/_}}, Dev → 2024-04-32``

**Good:**
> `anti-agent-config  {source-system} / {section} / {doc} → {team.slack.com / example.com}`

**Detection:** scan body for `*.slack.com`, `*.enterprise.slack.com`, real-looking GitHub orgs, `@-mentionable` usernames length ≥12, real ticket IDs.

### Set 2: One-off notes masquerading as skills

**Symptom:** Description or body only makes sense for the one task that motivated creation.

**Why wrong:** Not reusable. Belongs in vault, not in skill library.

**Fix:** Either generalize to a class of tasks, or abandon (don't create a skill).

### Set 3: Decorative emoji in skill body

**Symptom:** ✅ ❌ 🚀 🔥 used for status emphasis.

**Why wrong:** Adds noise, breaks text-only readers, encoding fragility.

**Fix:** Plain text. `pass` / `fail` / `done` / `block` / `warn`.

### Set 4: Verbatim user prompt in Examples

**Symptom:** Example section pastes the actual user prompt with all specifics (file paths, project names, ticket IDs).

**Why wrong:** Same as Set 1 — visible, travels, leaks.

**Fix:** Rewrite each example with neutral placeholders. Keep structural shape; replace specifics.

---

## 11. Test Scenarios (markdown, manual)

These are NOT evals.json. They are markdown bullets to manually walk through.

### Scenario 1: Create a simple git helper

**Input:** "create a skill that helps me write good git commit messages"
**Expected:**
- Phase 0 finds 0 similar skills (low threshold met)
- Phase 1 captures: audience = developer, accuracy high, speed medium
- Phase 2 produces `skills/git-commit-helper/SKILL.md` with:
  - description "Use when writing git commit messages..."
  - body < 100 lines
  - 1 test scenario
- Phase 3: all MUST gates pass
- Phase 4: committed as `skill: add git-commit-helper`

### Scenario 2: Create an API caller

**Input:** "I need a skill to query the GitHub API for issue lists"
**Expected:**
- Phase 0 finds no exact match (probably)
- Phase 1 captures: tool integration weight high (0.4)
- Phase 2 includes actual `gh` CLI commands in body
- Phase 3 includes live test (run a `gh` command)

### Scenario 3: Create a PDF processor

**Input:** "skill for extracting text from PDF files"
**Expected:**
- Phase 0 finds no match
- Phase 1 captures: edge cases high (0.4) due to PDF format variety
- Phase 2 references Python `pypdf` or similar
- Phase 3 MUST pass

### Scenario 4: Create a conflicting skill

**Input:** "I want a new git helper, similar to my existing one"
**Expected:**
- Phase 0 finds ≥70% match
- **STOPS** with message "Found existing skill `git-commit-helper` at path Y. Did you mean to edit it? Use skill-edit."
- Does NOT proceed to Phase 1

---

## 12. Out of Scope (deferred to v3+)

| Item | Why deferred |
|------|--------------|
| `provenance.json` (claim-level) | High effort, low return for v2 |
| `scripts/` (health-checks, run-evals, compile, validate) | Inline checklists suffice for v2 |
| `schemas/` (provenance, evals JSON schema) | JSON schemas not needed without JSON files |
| `deploy/` (single vs full version) | User chose single version only |
| `## Changelog` body section | User chose git log instead |
| `## Convention Notes` body section | Replaced by `CONVENTIONS.md` at project root |
| `## Rules` body section | Merged into Quality Gates |
| `## Overview` body section | Merged into intro |
| `evals.json` (test corpus) | Replaced by markdown Test Scenarios |
| Self-evolution log | Defer to v3 (after real usage data) |
| Cross-harness install (Claude Code, Cursor, Gemini) | Opencode-only for v2 |
| `skill-edit` (separate skill) | Defer to next brainstorming |
| ai-coworker integration | v2 is independent |

---

## 13. Open Questions

| # | Question | Default until answered |
|---|----------|------------------------|
| Q1 | Should `metadata.requires` be enforced or advisory? | Advisory (body checks, doesn't block) |
| Q2 | Should Phase 4 auto-push? | No — user decides |
| Q3 | What license for skill-factory project? | MIT (placeholder, confirm later) |
| Q4 | Where does `CONVENTIONS.md` live vs `README.md`? | Separate (CONVENTIONS = rules, README = intro) |
| Q5 | Should new skills be added to a CHANGELOG.md at project root? | Not for v2 — git log only |

---

## 14. References

### GitHub repos compared (12 found, 6 methodologically relevant)

1. **obra/superpowers** (224k stars) — TDD-for-skills, CSO, anti-rationalization, pressure testing
2. **includewudi/skill-forge** (6 stars) — 6 phases, 6 design principles, MUST/NICE gates, self-evolution
3. **anthropic skill-creator** (official, referenced by skill-forge) — trigger rate scoring, quality scoring
4. **lirazgershon148/conversation-to-skill-generator** (4 stars) — progressive disclosure, 4 eval scenarios, SKILL.md < 500 lines
5. **victor-aguilars/persona-architect** (4 stars) — interview-first 4-5 questions
6. **crystian/skills** (23 stars) — skill-optimizer (post-create improvement), 3-layer progressive disclosure

Libraries reviewed (not methodology, but reference):
- haolange/RDC-Agent-Frameworks
- CodeAtCode/oss-ai-skills
- uxuiprinciples/agent-skills
- eterdis/strategy-skills
- maruakshay/mii-ai-security
- arturseo-geo/claude-code-skills

### Key files

- v1 (audited): `/home/cicidi/project/ai-coworker/skills/coworker-meta-skill-create.md` (590 lines)
- v1 sibling: `/home/cicidi/project/ai-coworker/skills/coworker-meta-create-skill.md` (86 lines, quick version)
- obra's `writing-skills`: `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.0.7/skills/writing-skills/SKILL.md`
- opencode config: `~/.config/opencode/config.json` (superpowers plugin added this session)

---

## 15. Success Criteria

This design is "done" when:

- [ ] User reviews and approves this spec
- [ ] `~/project/skill-factory/` directory created
- [ ] `~/project/skill-factory/README.md` written (40 lines)
- [ ] `~/project/skill-factory/CONVENTIONS.md` written (50 lines)
- [ ] `~/project/skill-factory/skills/skill-create/SKILL.md` written (~215 lines, per Section 7)
- [ ] All 15 MUST quality gates pass on the new SKILL.md
- [ ] Opencode TUI started, `> use skill tool to list skills` shows `skill-create` discovered
- [ ] One end-to-end test: create a new skill from scratch using `skill-create`, verify it lands in the right place

---

## Self-Review (per brainstorming skill)

1. **Placeholder scan:** No TBD / TODO / "to be determined". ✓
2. **Internal consistency:** Architecture (Section 4) matches Components (Section 5) matches Frontmatter (Section 6) matches Body (Section 7) matches Quality Gates (Section 9). ✓
3. **Scope check:** Focused on one deliverable (skill-create). Skill-edit deferred. ✓
4. **Ambiguity check:**
   - "≥70% match" in Phase 0 — left as-is (user can adjust threshold)
   - Factor weight defaults — explicit in Phase 1
   - Quality gate enforcement (block vs warn) — explicit per gate
   - "obra is optional" — explicit everywhere

No issues found. Ready for user review.
