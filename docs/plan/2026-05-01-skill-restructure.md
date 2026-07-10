# Skill Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure all 33 personal skills to follow the new `skill-create` format — new frontmatter schema (triggers, when_to_use, when_not_to_use, services/category, dependencies) AND rename all files/folders with `coworker-{category}-` prefix.

**Architecture:** Each skill gets a new frontmatter block + file renamed in both source (`personal/skills/`) and installed (`~/.claude/commands/`) locations. Body content is preserved; only frontmatter and filename change.

**Tech Stack:** Bash, markdown, Claude Code

---

## New Schema (target frontmatter for every skill)

```yaml
---
name: {kebab-case-name}
triggers:
  - {natural phrase that triggers this skill}
  - {another phrase}
description: |
  {What this skill does. Be "pushy" about when to trigger — err on
   the side of triggering too often rather than too rarely.}
services:
  category: coworker-{category}
when_to_use: |
  {1-3 sentences: exact trigger condition}
when_not_to_use: |
  {when to skip this skill, or "false" if always applicable}
dependencies:
  - {other-skill-name}   # omit section if none
version: 1.0.0
---
```

## Category Mapping

| Old prefix | New prefix | coworker category |
|-----------|------------|-------------------|
| `commit-` | `coworker-do-` | `coworker-do` |
| `design-` | `coworker-design-` | `coworker-design` |
| `dev-ai-tool-` | `coworker-meta-` | `coworker-meta` |
| `dev-feat-` | `coworker-do-` | `coworker-do` |
| `doc-` | `coworker-meta-` | `coworker-meta` |
| `issue-` | `coworker-debug-` | `coworker-debug` |
| `mcp-` | `coworker-tool-` | `coworker-tool` |
| `video-edit` | `coworker-tool-video-edit` | `coworker-tool` |
| `skill-create` | `coworker-meta-skill-create` | `coworker-meta` |

## Full Rename Table (33 skills)

| Old filename | New filename | New `name:` field |
|---|---|---|
| `commit-code-conventions.md` | `coworker-do-code-conventions.md` | `coworker-do-code-conventions` |
| `commit-code-review.md` | `coworker-do-code-review.md` | `coworker-do-code-review` |
| `commit-guardrails.md` | `coworker-do-guardrails.md` | `coworker-do-guardrails` |
| `commit-review-checkpoint.md` | `coworker-do-review-checkpoint.md` | `coworker-do-review-checkpoint` |
| `commit-unit-tests.md` | `coworker-do-unit-tests.md` | `coworker-do-unit-tests` |
| `commit-verify-plan.md` | `coworker-do-verify-plan.md` | `coworker-do-verify-plan` |
| `design-c2d.md` | `coworker-design-c2d.md` | `coworker-design-c2d` |
| `design-c2f.md` | `coworker-design-c2f.md` | `coworker-design-c2f` |
| `design-d2pl.md` | `coworker-design-d2pl.md` | `coworker-design-d2pl` |
| `design-f2d.md` | `coworker-design-f2d.md` | `coworker-design-f2d` |
| `design-p2f.md` | `coworker-design-p2f.md` | `coworker-design-p2f` |
| `dev-ai-tool-auto-patches.md` | `coworker-meta-auto-patches.md` | `coworker-meta-auto-patches` |
| `dev-ai-tool-report-issue.md` | `coworker-meta-report-issue.md` | `coworker-meta-report-issue` |
| `dev-ai-tool-self-analyze.md` | `coworker-meta-self-analyze.md` | `coworker-meta-self-analyze` |
| `dev-ai-tool-self-healing-trace.md` | `coworker-meta-self-healing-trace.md` | `coworker-meta-self-healing-trace` |
| `dev-ai-tool-setup-coworker.md` | `coworker-meta-setup-coworker.md` | `coworker-meta-setup-coworker` |
| `dev-ai-tool-strain-sites.md` | `coworker-meta-strain-sites.md` | `coworker-meta-strain-sites` |
| `dev-feat-plan-to-code.md` | `coworker-do-plan-to-code.md` | `coworker-do-plan-to-code` |
| `dev-feat-quick-task.md` | `coworker-do-quick-task.md` | `coworker-do-quick-task` |
| `doc-create-skill.md` | `coworker-meta-create-skill.md` | `coworker-meta-create-skill` |
| `doc-edit-skill.md` | `coworker-meta-edit-skill.md` | `coworker-meta-edit-skill` |
| `doc-merge-docs.md` | `coworker-meta-merge-docs.md` | `coworker-meta-merge-docs` |
| `doc-protection.md` | `coworker-meta-doc-protection.md` | `coworker-meta-doc-protection` |
| `doc-review-request.md` | `coworker-meta-review-request.md` | `coworker-meta-review-request` |
| `issue-create.md` | `coworker-debug-issue-create.md` | `coworker-debug-issue-create` |
| `issue-debug.md` | `coworker-debug-issue-debug.md` | `coworker-debug-issue-debug` |
| `issue-investigate.md` | `coworker-debug-issue-investigate.md` | `coworker-debug-issue-investigate` |
| `mcp-discord.md` | `coworker-tool-discord.md` | `coworker-tool-discord` |
| `mcp-github.md` | `coworker-tool-github.md` | `coworker-tool-github` |
| `mcp-google-drive.md` | `coworker-tool-google-drive.md` | `coworker-tool-google-drive` |
| `mcp-slack.md` | `coworker-tool-slack.md` | `coworker-tool-slack` |
| `mcp-telegram.md` | `coworker-tool-telegram.md` | `coworker-tool-telegram` |
| `video-edit.md` | `coworker-tool-video-edit.md` | `coworker-tool-video-edit` |
| `skill-create.md` | `coworker-meta-skill-create.md` | `coworker-meta-skill-create` |

---

## Wave 0 — Backup

### Task 0: Backup current commands

**Files:**
- Create: `/home/cicidi/.claude/commands-backup-2026-05-01/` (copy of current commands)
- Create: `/home/cicidi/project/ai-coworker/personal/skills-backup-2026-05-01/` (copy of personal skills)

- [ ] **Step 1: Backup installed commands**
```bash
cp -r ~/.claude/commands ~/.claude/commands-backup-2026-05-01
echo "Backed up $(ls ~/.claude/commands-backup-2026-05-01 | wc -l) files"
```
Expected: "Backed up 34 files"

- [ ] **Step 2: Backup personal skills source**
```bash
cp -r /home/cicidi/project/ai-coworker/personal/skills \
      /home/cicidi/project/ai-coworker/personal/skills-backup-2026-05-01
echo "done"
```

---

## Wave 1 — coworker-do (commit-* + dev-feat-*)

6 commit skills + 2 dev-feat skills = 8 skills

### Task 1: coworker-do-code-conventions

**Files:**
- Modify: `~/.claude/commands/commit-code-conventions.md` → rename + new frontmatter
- Modify: `personal/skills/` (source, if exists)

- [ ] **Step 1: Write new file with updated frontmatter + body**

Create `~/.claude/commands/coworker-do-code-conventions.md`:
```markdown
---
name: coworker-do-code-conventions
triggers:
  - check code conventions
  - enforce code style
  - run formatter
  - style check before commit
description: |
  Enforces team code style — runs language-specific formatters, checks naming
  conventions, and validates commit message format before every commit.
  Trigger whenever code is about to be committed or reviewed for style.
services:
  category: coworker-do
when_to_use: |
  Before committing code. When user asks to "check style", "run formatter",
  or "enforce conventions". Auto-applied pre-commit.
when_not_to_use: |
  Do not apply to generated files, vendor code, or auto-formatted migrations.
version: 1.0.0
---
```
Then append the existing body from `commit-code-conventions.md` (everything after the closing `---`).

- [ ] **Step 2: Copy body from old file**
```bash
OLD=~/.claude/commands/commit-code-conventions.md
NEW=~/.claude/commands/coworker-do-code-conventions.md
# Get body (everything after second ---)
BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
# Prepend new frontmatter
cat > "$NEW" << 'FRONTMATTER'
---
name: coworker-do-code-conventions
triggers:
  - check code conventions
  - enforce code style
  - run formatter
  - style check before commit
description: |
  Enforces team code style — runs language-specific formatters, checks naming
  conventions, and validates commit message format before every commit.
  Trigger whenever code is about to be committed or reviewed for style.
services:
  category: coworker-do
when_to_use: |
  Before committing code. When user asks to "check style", "run formatter",
  or "enforce conventions". Auto-applied pre-commit.
when_not_to_use: |
  Do not apply to generated files, vendor code, or auto-formatted migrations.
version: 1.0.0
---
FRONTMATTER
echo "$BODY" >> "$NEW"
echo "Created $NEW"
```

- [ ] **Step 3: Remove old file**
```bash
rm ~/.claude/commands/commit-code-conventions.md
ls ~/.claude/commands/ | grep convention
```
Expected: `coworker-do-code-conventions.md`

### Task 2: coworker-do-code-review

- [ ] **Step 1: Create new file**
```bash
OLD=~/.claude/commands/commit-code-review.md
NEW=~/.claude/commands/coworker-do-code-review.md
BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
cat > "$NEW" << 'FM'
---
name: coworker-do-code-review
triggers:
  - review my code
  - pre-commit review
  - check for anti-patterns
  - code review before push
description: |
  Auto pre-commit code review against known anti-patterns. Self-improving via
  self-healing traces. Trigger before every commit or when asking for a code review.
services:
  category: coworker-do
when_to_use: |
  Before committing code or when user asks "review this", "check my code",
  or "look for issues". Run after writing new code.
when_not_to_use: |
  Skip for auto-generated files, schema migrations with no logic, or pure config changes.
version: 1.0.0
---
FM
echo "$BODY" >> "$NEW"
rm "$OLD"
echo "done"
```

### Task 3: coworker-do-guardrails

- [ ] **Step 1: Create new file**
```bash
OLD=~/.claude/commands/commit-guardrails.md
NEW=~/.claude/commands/coworker-do-guardrails.md
BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
cat > "$NEW" << 'FM'
---
name: coworker-do-guardrails
triggers:
  - security check
  - owasp check
  - check for vulnerabilities
  - run guardrails
description: |
  Auto-applied pre-commit guardrails based on OWASP Top 10 and standard security
  practices. Triggers before every commit to catch injection, secrets, auth issues.
services:
  category: coworker-do
when_to_use: |
  Before every commit. When user asks for security review or mentions OWASP.
  Auto-applies to all code changes.
when_not_to_use: |
  false
version: 1.0.0
---
FM
echo "$BODY" >> "$NEW"
rm "$OLD"
echo "done"
```

### Task 4: coworker-do-review-checkpoint

- [ ] **Step 1: Create new file**
```bash
OLD=~/.claude/commands/commit-review-checkpoint.md
NEW=~/.claude/commands/coworker-do-review-checkpoint.md
BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
cat > "$NEW" << 'FM'
---
name: coworker-do-review-checkpoint
triggers:
  - review checkpoint
  - confirm with reviewer
  - who should review this
  - find reviewer for phase
description: |
  After each pipeline phase, prompts user to confirm with the right reviewer before
  proceeding. Use at the end of each design/code/test phase.
services:
  category: coworker-do
when_to_use: |
  At the end of each pipeline phase (design, code, test). When user says
  "who should review this" or "confirm before next step".
when_not_to_use: |
  Skip for quick tasks under 30 minutes with no external dependencies.
version: 1.0.0
---
FM
echo "$BODY" >> "$NEW"
rm "$OLD"
echo "done"
```

### Task 5: coworker-do-unit-tests

- [ ] **Step 1: Create new file**
```bash
OLD=~/.claude/commands/commit-unit-tests.md
NEW=~/.claude/commands/coworker-do-unit-tests.md
BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
cat > "$NEW" << 'FM'
---
name: coworker-do-unit-tests
triggers:
  - verify tests
  - check unit tests
  - run test verification
  - 3-level test check
description: |
  3-level test verification: structural/frontmatter → content quality → dry-run
  before commit. Ensures tests exist, are meaningful, and pass before pushing.
services:
  category: coworker-do
when_to_use: |
  Before every commit that includes new functions or classes. When user asks
  to "verify tests" or "make sure tests are good".
when_not_to_use: |
  Skip for documentation-only changes or config tweaks with no logic.
version: 1.0.0
---
FM
echo "$BODY" >> "$NEW"
rm "$OLD"
echo "done"
```

### Task 6: coworker-do-verify-plan

- [ ] **Step 1: Create new file**
```bash
OLD=~/.claude/commands/commit-verify-plan.md
NEW=~/.claude/commands/coworker-do-verify-plan.md
BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
cat > "$NEW" << 'FM'
---
name: coworker-do-verify-plan
triggers:
  - verify mac
  - check acceptance criteria
  - post-execution verification
  - confirm feature works
description: |
  Post-execution MAC (Minimum Acceptance Criteria) verification in a fresh session.
  Confirms the feature actually works before creating a PR.
services:
  category: coworker-do
when_to_use: |
  After implementing a feature, before opening a PR. When user says "check if
  it works" or "verify the plan was executed correctly".
when_not_to_use: |
  Skip for hotfixes where the bug fix is immediately verifiable by the user.
version: 1.0.0
---
FM
echo "$BODY" >> "$NEW"
rm "$OLD"
echo "done"
```

### Task 7: coworker-do-plan-to-code

- [ ] **Step 1: Create new file**
```bash
OLD=~/.claude/commands/dev-feat-plan-to-code.md
NEW=~/.claude/commands/coworker-do-plan-to-code.md
BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
cat > "$NEW" << 'FM'
---
name: coworker-do-plan-to-code
triggers:
  - execute plan
  - plan to code
  - run the plan
  - implement from plan file
description: |
  Execute a plan file via orchestrator + subagent model. One task = one subagent
  = one commit. Use when a written plan exists and needs to be implemented.
services:
  category: coworker-do
when_to_use: |
  When a plan file exists (docs/plans/*.md) and user says "execute the plan",
  "implement this", or "run pl2c". After design/plan phases are complete.
when_not_to_use: |
  Do not use without a written plan. Use coworker-do-quick-task for changes under 100 lines.
dependencies:
  - coworker-do-guardrails
  - coworker-do-code-review
version: 1.0.0
---
FM
echo "$BODY" >> "$NEW"
rm "$OLD"
echo "done"
```

### Task 8: coworker-do-quick-task

- [ ] **Step 1: Create new file**
```bash
OLD=~/.claude/commands/dev-feat-quick-task.md
NEW=~/.claude/commands/coworker-do-quick-task.md
BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
cat > "$NEW" << 'FM'
---
name: coworker-do-quick-task
triggers:
  - quick fix
  - small change
  - hotfix
  - minor tweak
  - bug fix under 100 lines
description: |
  Small change (under 100 lines) without the full PRD/Design/Plan pipeline.
  For bug fixes, config tweaks, and simple one-off tasks.
services:
  category: coworker-do
when_to_use: |
  When the change is under 100 lines, well-understood, and doesn't require
  design discussion. Bug fixes, typos, config changes, minor refactors.
when_not_to_use: |
  Do not use for new features, architectural changes, or anything needing
  design review. Use the full 8-stage pipeline instead.
version: 1.0.0
---
FM
echo "$BODY" >> "$NEW"
rm "$OLD"
echo "done"
```

---

## Wave 2 — coworker-design (design-*)

5 skills

### Task 9–13: All design-* skills

- [ ] **Step 1: Rename and update all design skills in one block**
```bash
declare -A DESIGNS
DESIGNS[design-c2d]="Sync code changes back to DESIGN.md to prevent doc rot. Triggers after code changes that affect APIs or data models."
DESIGNS[design-c2f]="Scan code to mark implemented features as COMPLETE in FEATURE.md. Triggers after implementing a feature from FEATURE.md."
DESIGNS[design-d2pl]="Break DESIGN.md features into tasks grouped in waves with MAC. Triggers when design is ready and needs a plan."
DESIGNS[design-f2d]="Create or update DESIGN.md from FEATURE.md. Triggers when features list is ready and needs architecture design."
DESIGNS[design-p2f]="Propagate PRD changes to FEATURE.md, classify new/changed/removed features. Triggers when PRD is updated."

for OLD_NAME in "${!DESIGNS[@]}"; do
  SUFFIX="${OLD_NAME#design-}"
  NEW_NAME="coworker-design-${SUFFIX}"
  OLD=~/.claude/commands/${OLD_NAME}.md
  NEW=~/.claude/commands/${NEW_NAME}.md
  BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
  DESC="${DESIGNS[$OLD_NAME]}"
  cat > "$NEW" << FM
---
name: ${NEW_NAME}
triggers:
  - ${SUFFIX}
description: |
  ${DESC}
services:
  category: coworker-design
when_to_use: |
  ${DESC}
when_not_to_use: |
  false
version: 1.0.0
---
FM
  echo "$BODY" >> "$NEW"
  rm "$OLD"
  echo "Renamed $OLD_NAME → $NEW_NAME"
done
```

---

## Wave 3 — coworker-meta (dev-ai-tool-* + doc-*)

6 dev-ai-tool + 5 doc + 1 skill-create = 12 skills

### Task 14–19: All dev-ai-tool-* skills

- [ ] **Step 1: Rename all coworker-meta skills**
```bash
declare -A META
META[dev-ai-tool-auto-patches]="auto-patches|Auto-correct minor English grammar errors in AI responses for non-native speakers.|When any AI response has grammar errors. When user asks to fix grammar or auto-correct responses."
META[dev-ai-tool-report-issue]="report-issue|Report a bug or problem with the AI coworker system itself to GitHub Issues.|When AI coworker behaves incorrectly, produces wrong output, or user says 'report this bug'."
META[dev-ai-tool-self-analyze]="self-analyze|Analyze correction traces (2+ occurrences) and generate new skills or rules.|When user asks to analyze correction patterns, after 5+ traces accumulate, or periodically for self-improvement."
META[dev-ai-tool-self-healing-trace]="self-healing-trace|Log a correction trace when AI makes a mistake. Stores in YAML for pattern analysis.|Every time the user corrects the AI or says 'you did X wrong'. Must log before proceeding."
META[dev-ai-tool-setup-coworker]="setup-coworker|5-step interactive setup — scan project, generate CLAUDE.md, detect identity, create local config, install hooks.|When starting on a new project or when user asks to set up the AI coworker system."
META[dev-ai-tool-strain-sites]="strain-sites|Train AI on specific patterns through self-iteration — extract failure patterns and update skills.|When user asks to train AI on a pattern, improve a skill, or after repeated correction traces on same issue."

for OLD_NAME in "${!META[@]}"; do
  IFS='|' read -r SUFFIX DESC WHEN <<< "${META[$OLD_NAME]}"
  NEW_NAME="coworker-meta-${SUFFIX}"
  OLD=~/.claude/commands/${OLD_NAME}.md
  NEW=~/.claude/commands/${NEW_NAME}.md
  BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
  cat > "$NEW" << FM
---
name: ${NEW_NAME}
triggers:
  - ${SUFFIX}
description: |
  ${DESC}
services:
  category: coworker-meta
when_to_use: |
  ${WHEN}
when_not_to_use: |
  false
version: 1.0.0
---
FM
  echo "$BODY" >> "$NEW"
  rm "$OLD"
  echo "Renamed $OLD_NAME → $NEW_NAME"
done
```

### Task 20–24: All doc-* skills

- [ ] **Step 1: Rename all doc skills**
```bash
declare -A DOCS
DOCS[doc-create-skill]="create-skill|Create a new skill file with enforced frontmatter, duplicate detection, and auto PR.|When user asks to create a new skill, add a new capability, or says 'new skill'."
DOCS[doc-edit-skill]="edit-skill|Edit an existing skill — update content, bump version, validate changelog, auto-commit.|When user asks to edit, update, or improve an existing skill."
DOCS[doc-merge-docs]="merge-docs|Merge two versions of a markdown document after upstream sync conflicts.|When user has a merge conflict in a markdown doc or needs to reconcile two doc versions."
DOCS[doc-protection]="doc-protection|Manage PROTECTED blocks in documents. AI must never modify content inside protected blocks.|When user wants to protect a section of a document from AI edits."
DOCS[doc-review-request]="review-request|Auto-find the right reviewer and draft a review request message.|When user asks 'who should review this', 'find a reviewer', or 'draft a review request'."

for OLD_NAME in "${!DOCS[@]}"; do
  IFS='|' read -r SUFFIX DESC WHEN <<< "${DOCS[$OLD_NAME]}"
  NEW_NAME="coworker-meta-${SUFFIX}"
  OLD=~/.claude/commands/${OLD_NAME}.md
  NEW=~/.claude/commands/${NEW_NAME}.md
  BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
  cat > "$NEW" << FM
---
name: ${NEW_NAME}
triggers:
  - ${SUFFIX}
description: |
  ${DESC}
services:
  category: coworker-meta
when_to_use: |
  ${WHEN}
when_not_to_use: |
  false
version: 1.0.0
---
FM
  echo "$BODY" >> "$NEW"
  rm "$OLD"
  echo "Renamed $OLD_NAME → $NEW_NAME"
done
```

### Task 25: skill-create → coworker-meta-skill-create

- [ ] **Step 1: Rename skill-create**
```bash
mv ~/.claude/commands/skill-create.md ~/.claude/commands/coworker-meta-skill-create.md
# Update name field in frontmatter
sed -i 's/^name: skill-create/name: coworker-meta-skill-create/' \
    ~/.claude/commands/coworker-meta-skill-create.md
echo "done"
```

- [ ] **Step 2: Also rename source file**
```bash
mv /home/cicidi/project/ai-coworker/personal/skills/skill-create.md \
   /home/cicidi/project/ai-coworker/personal/skills/coworker-meta-skill-create.md
sed -i 's/^name: skill-create/name: coworker-meta-skill-create/' \
    /home/cicidi/project/ai-coworker/personal/skills/coworker-meta-skill-create.md
echo "done"
```

---

## Wave 4 — coworker-debug (issue-*)

3 skills

### Task 26–28: All issue-* skills

- [ ] **Step 1: Rename all issue skills**
```bash
declare -A ISSUES
ISSUES[issue-create]="issue-create|Doc-driven change request via GitHub Issue — 6-step structured discussion before any code.|When user reports a bug, requests a feature, or wants to track any non-trivial change. Always before writing code."
ISSUES[issue-debug]="issue-debug|Scientific debugging — hypothesis → test → confirm → fix. Best with strongest model.|When a bug exists and the cause is unknown. Form hypothesis, test, confirm, fix. Do not guess."
ISSUES[issue-investigate]="issue-investigate|Deep investigation of tickets, logs, or on-call issues. Follows every lead autonomously.|When user is on-call, has an incident, or asks to deeply investigate a ticket or log file."

for OLD_NAME in "${!ISSUES[@]}"; do
  IFS='|' read -r SUFFIX DESC WHEN <<< "${ISSUES[$OLD_NAME]}"
  NEW_NAME="coworker-debug-${SUFFIX}"
  OLD=~/.claude/commands/${OLD_NAME}.md
  NEW=~/.claude/commands/${NEW_NAME}.md
  BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
  cat > "$NEW" << FM
---
name: ${NEW_NAME}
triggers:
  - ${SUFFIX}
description: |
  ${DESC}
services:
  category: coworker-debug
when_to_use: |
  ${WHEN}
when_not_to_use: |
  false
version: 1.0.0
---
FM
  echo "$BODY" >> "$NEW"
  rm "$OLD"
  echo "Renamed $OLD_NAME → $NEW_NAME"
done
```

---

## Wave 5 — coworker-tool (mcp-* + video-edit)

5 mcp + 1 video = 6 skills

### Task 29–34: All coworker-tool skills

- [ ] **Step 1: Rename all tool skills**
```bash
declare -A TOOLS
TOOLS[mcp-discord]="discord|Discord MCP — send messages, read channels, manage notifications via Discord bot.|When user wants to send a Discord message, read a channel, or get notified via Discord."
TOOLS[mcp-github]="github|GitHub MCP — create/search/comment on issues and PRs via official MCP server.|When user wants to interact with GitHub: create issues, PRs, search repos, add comments."
TOOLS[mcp-google-drive]="google-drive|Google Drive MCP — read/write Google Docs, Sheets, Slides via official MCP server.|When user wants to read or write Google Docs, Sheets, or Slides."
TOOLS[mcp-slack]="slack|Slack MCP — read/write messages, search channels, send notifications.|When user wants to send a Slack message, search channels, or post notifications."
TOOLS[mcp-telegram]="telegram|Telegram MCP — send messages and notifications via Telegram bot.|When user wants to send a Telegram message or notification."
TOOLS[video-edit]="video-edit|Edit videos and add background music from free music sources.|When user asks to edit a video, trim clips, or add background music."

for OLD_NAME in "${!TOOLS[@]}"; do
  IFS='|' read -r SUFFIX DESC WHEN <<< "${TOOLS[$OLD_NAME]}"
  NEW_NAME="coworker-tool-${SUFFIX}"
  OLD=~/.claude/commands/${OLD_NAME}.md
  NEW=~/.claude/commands/${NEW_NAME}.md
  BODY=$(awk '/^---/{n++} n==2{print}' "$OLD" | tail -n +2)
  cat > "$NEW" << FM
---
name: ${NEW_NAME}
triggers:
  - ${SUFFIX}
description: |
  ${DESC}
services:
  category: coworker-tool
when_to_use: |
  ${WHEN}
when_not_to_use: |
  false
version: 1.0.0
---
FM
  echo "$BODY" >> "$NEW"
  rm "$OLD"
  echo "Renamed $OLD_NAME → $NEW_NAME"
done
```

---

## Wave 6 — Sync Source Files

All above waves only updated `~/.claude/commands/`. Now sync changes back to the source `personal/skills/` directory.

### Task 35: Sync installed → source

- [ ] **Step 1: Copy all new coworker-* files to personal/skills/**
```bash
SKILLS_DIR=/home/cicidi/project/ai-coworker/personal/skills
for f in ~/.claude/commands/coworker-*.md; do
  name=$(basename "$f")
  cp "$f" "$SKILLS_DIR/$name"
  echo "synced $name"
done
ls "$SKILLS_DIR" | grep coworker | wc -l
```
Expected: 34 files

- [ ] **Step 2: Remove old-named files from personal/skills/ if any remain**
```bash
SKILLS_DIR=/home/cicidi/project/ai-coworker/personal/skills
for prefix in commit- design- dev-ai-tool- dev-feat- doc- issue- mcp- video-edit skill-create; do
  for f in "$SKILLS_DIR"/${prefix}*.md; do
    [ -f "$f" ] && echo "OLD FILE FOUND: $f"
  done
done
```
If any found, remove them:
```bash
# Only run if Step 2 shows old files
rm /home/cicidi/project/ai-coworker/personal/skills/commit-*.md 2>/dev/null
rm /home/cicidi/project/ai-coworker/personal/skills/design-*.md 2>/dev/null
rm /home/cicidi/project/ai-coworker/personal/skills/dev-*.md 2>/dev/null
rm /home/cicidi/project/ai-coworker/personal/skills/doc-*.md 2>/dev/null
rm /home/cicidi/project/ai-coworker/personal/skills/issue-*.md 2>/dev/null
rm /home/cicidi/project/ai-coworker/personal/skills/mcp-*.md 2>/dev/null
```

---

## Wave 7 — Verify

### Task 36: Final verification

- [ ] **Step 1: Count installed skills**
```bash
echo "=== Installed commands ===" && ls ~/.claude/commands/ | sort
echo "=== Total ===" && ls ~/.claude/commands/*.md | wc -l
```
Expected: All 34 files start with `coworker-`

- [ ] **Step 2: Check no old-prefix files remain**
```bash
ls ~/.claude/commands/ | grep -E "^(commit|design|dev-|doc-|issue|mcp|video|skill-create)" | wc -l
```
Expected: 0

- [ ] **Step 3: Spot-check frontmatter on 3 files**
```bash
head -15 ~/.claude/commands/coworker-do-guardrails.md
echo "---"
head -15 ~/.claude/commands/coworker-debug-issue-debug.md
echo "---"
head -15 ~/.claude/commands/coworker-tool-slack.md
```
Each should show `name:`, `triggers:`, `services: category:`, `when_to_use:`.

- [ ] **Step 4: Commit source changes**
```bash
cd /home/cicidi/project/ai-coworker
git add personal/skills/
git commit -m "refactor: restructure all skills to coworker-{category} naming + new frontmatter schema"
```

---

## Self-Review

**Spec coverage:**
- ✅ All 34 skills renamed with `coworker-{category}-` prefix
- ✅ All frontmatter updated with `triggers`, `services/category`, `when_to_use`, `when_not_to_use`, `version`
- ✅ Body content preserved unchanged
- ✅ Both installed (`~/.claude/commands/`) and source (`personal/skills/`) updated
- ✅ Backup created before any changes

**Placeholder scan:** No TBDs — all descriptions and when_to_use fields have real content per skill.

**Type consistency:** `awk '/^---/{n++} n==2{print}' | tail -n +2` pattern used consistently across all waves.
