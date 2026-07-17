---
name: ai-coworker-upgrade
version: 0.1.0
description: 'Use when updating the ai-coworker installation — pulls latest code from

  ai-coworker and skill-factory, updates global and project-level CLAUDE.md

  with semantic merge, installs new/updated skills from both repos, re-runs

  install, syncs configs to all IDE tools.

  '
triggers:
- update ai-coworker
- update ai-worker
- update coworker
- upgrade coworker
- pull latest coworker
- refresh coworker
- sync coworker
when-to-use: 'When the user''s ai-coworker installation is out of date and needs

  the latest code, skills, analytics hooks, MCP config, or CLAUDE.md

  rules synced to all IDEs.'
license: MIT
compatibility: claude-code,opencode
---

# ai-coworker-upgrade

Updates the ai-coworker installation end-to-end: pull latest source from
both ai-coworker and skill-factory, semantic-merge CLAUDE.md updates
(global + project-level), install new/updated skills from both repos into
IDE config directories, re-run install for analytics and hooks, sync
configs to all IDEs.

## Process

### Phase 1: Pull latest ai-coworker

**MUST** — find the repo, fetch, merge. If conflicts, report and stop.
After this phase, `ai-coworker/skills/` is up to date on disk.

Step 1 — Locate the ai-coworker repo:

```bash
COWORKER_ROOT=$(git -C ~/project/ai-coworker rev-parse --show-toplevel 2>/dev/null || echo "")
if [[ -z "$COWORKER_ROOT" ]]; then
  echo "ai-coworker repo not found at ~/project/ai-coworker"
  exit 1
fi
```

Step 2 — Check for local modifications first:

```bash
cd "$COWORKER_ROOT"
if ! git diff --quiet; then
  echo "Local changes detected:"
  git diff --stat
  echo ""
fi
```

If local changes exist, ask the user: "Coworker has local changes. Stash them before merging?"

Step 3 — Fetch and merge:

```bash
cd "$COWORKER_ROOT"
git fetch origin main || git fetch upstream main 2>/dev/null
git merge --ff-only origin/main || git merge --ff-only upstream/main 2>/dev/null || {
  echo "Could not fast-forward. Stashing and retrying..."
  git stash
  git merge --ff-only origin/main || git merge --ff-only upstream/main 2>/dev/null
}
```

Step 4 — Confirm the update:

```bash
git log --oneline -3
```

If merge conflicts arise, report them to the user and stop. The user must resolve them manually.

### Phase 2: Update Global CLAUDE.md

This phase reads the current `~/.claude/CLAUDE.md`, extracts the latest
template from `install.sh`, and performs a **semantic merge** — the AI
understands section semantics, not just text diff.

**Do NOT fabricate rules.** The "future" version comes exclusively from
the install.sh template. The AI's job is to classify and present, not to generate.

Step 1 — Read current CLAUDE.md:

```bash
cat ~/.claude/CLAUDE.md 2>/dev/null || echo "(global CLAUDE.md not found)"
```

If not found, write the template directly and skip the merge.

Step 2 — Extract future template from install.sh:

```bash
cd "$COWORKER_ROOT" && python3 -c "
import re
with open('setup/install.sh') as f:
    content = f.read()
m = re.search(r\"CLAUDE_MD_CONTENT='(.*?)'\", content, re.DOTALL)
if m: print(m.group(1))
"
```

The extracted template is the complete, canonical future version. Use it as-is.

Step 3 — Semantic merge classification.

Break both `current` and `future` into sections (by `##` headings). For each
section in either document, classify it into one of four categories:

| Category | Meaning | Handling |
|----------|---------|----------|
| **OUTDATED** | current has a section that future doesn't, AND its topic is about a removed/historic coworker feature (old MCP, deprecated skill reference, stale rule) | Offer to delete |
| **OVERWRITE** | Both have the same heading/section but future's content is materially different | Offer to replace with future version |
| **MERGE_ADD** | future has a section that current doesn't (new capability, new rule, new skill reference) | Offer to append |
| **KEEP** | Section exists only in current and is clearly user-created (custom rules, project-specific notes, user preferences, `<!-- PROTECTED -->` blocks) | Keep unchanged |

Classification guidelines:
- Sections with matching `## Heading` names → compare content. If identical, KEEP. If different, OVERWRITE.
- Sections in current but not in future → check topic. If about coworker mechanics → OUTDATED. If user custom content → KEEP.
- Sections in future but not in current → MERGE_ADD.
- `<!-- PROTECTED -->` blocks in current → always KEEP, never touch.
- Initiative context blocks (`<!-- INITIATIVE:... -->`) → always KEEP (managed by initiative system).

Step 4 — Present the merge plan to the user.

Format each classified section as:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Global CLAUDE.md — Merge Plan
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[OUTDATED] ## Old Feature X
  This section references a removed feature. (delete)

[OVERWRITE] ## Question Requirement
  Current:  "ask 2 questions before acting"
  Future:   "ask 1-3 clarifying questions before acting..."
  (replace with future version)

[MERGE_ADD] ## Initiative Context
  New section from template, not in current. (append)

[KEEP] ## My Custom Rules
  User-defined content. (unchanged)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Accept all? [y / n: revoke one-by-one / q: skip CLAUDE.md update]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Step 5 — Handle user response:
- **y (accept all):** Apply all classifications — generate the merged file, write it to `~/.claude/CLAUDE.md`.
- **n (revoke one-by-one):** For each change item, ask: "[OUTDATED] ## Old X — delete? [y/n/s(keep)]". Then apply the final set of approved changes.
- **q (skip):** Skip this phase, do not modify global CLAUDE.md.

Step 6 — Apply merged result:

```bash
cat /tmp/merged_global_claude.md > ~/.claude/CLAUDE.md
```

### Phase 3: Update Project-Level CLAUDE.md

Scans for project CLAUDE.md files, asks user which to update, then runs
the same semantic merge per project. The future template comes from the
coworker init system, NOT from install.sh.

Step 1 — Discover projects with CLAUDE.md.

Method A (preferred) — use coworker catalog:

```bash
coworker project list 2>/dev/null
```

Method B (fallback) — filesystem scan:

```bash
find ~/project -maxdepth 3 -name ".git" -type d 2>/dev/null | sed 's|/.git||' | while read p; do
  if [[ -f "$p/CLAUDE.md" ]]; then echo "$p|$(stat -c %y "$p/CLAUDE.md" 2>/dev/null | cut -d'.' -f1)"; fi
done
```

Step 2 — Present project list and ask which to update:

```
Detected project CLAUDE.md files:

  1) ~/project/ai-coworker        (last modified: 2026-06-28)
  2) ~/project/skill-factory      (last modified: 2026-06-20)
  3) ~/project/backend-service    (last modified: 2026-05-15)

Which projects to update? [1 2 / all / none]
```

Step 3 — For each selected project, run the semantic merge.

**Generate future template** for this project:

```bash
cd <project_dir>
coworker init --project 2>/dev/null
```

This scans the project (language, framework, deps, IDE) and generates a
`## Project Context` section. Capture that output as the future template.

If `coworker init --project` is not available, skip this project and report.

Step 4 — Read current project CLAUDE.md and classify.

Same four-category classification as Phase 2 (OUTDATED / OVERWRITE / MERGE_ADD / KEEP),
with project-specific additions:

- The `## Project Context` section generated by `coworker init` → OVERWRITE if materially different
- User-defined project rules → KEEP
- Project-specific skill references → KEEP
- `<!-- PROTECTED -->` blocks → KEEP

Step 5 — Present per-project merge plan:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CLAUDE.md — ~/project/skill-factory
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[OVERWRITE] ## Project Context
  Current generated:   Node.js, Express, 6 deps
  Future (re-scanned): Node.js, Express, 8 deps (new: zod, vitest)
  (replace with re-scanned version)

[KEEP] ## My Build Rules
  User-defined. (unchanged)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Accept for this project? [y / n / q: skip project]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Step 6 — Apply per project:

```bash
cat /tmp/merged_project_claude.md > <project_dir>/CLAUDE.md
```

Step 7 — Report summary of project-level updates:

```
Project CLAUDE.md updates:
  ✅ skill-factory  — Project Context refreshed (2 new deps)
  ✅ ai-coworker    — no changes needed (up to date)
  ⏭  backend-service — skipped by user
```

### Phase 4: Install Skills

Scans both ai-coworker (already pulled in Phase 1) and skill-factory skills,
compares against deployed skills in `~/.claude/skills/`, and installs
any new or updated skills.

Step 1 — Pull skill-factory to get latest skills:

```bash
SKILL_FACTORY_DIR="$HOME/.config/opencode/skills/skill-factory"
if [[ -d "$SKILL_FACTORY_DIR" ]]; then
  git -C "$SKILL_FACTORY_DIR" pull --ff-only origin main 2>/dev/null && \
    echo "Skill-factory pulled." || \
    echo "Could not pull skill-factory (dirty, offline, or no upstream)."
else
  echo "Skill-factory not installed at $SKILL_FACTORY_DIR"
fi
```

Step 2 — Scan ai-coworker skills.

For each `SKILL.md` under `$COWORKER_ROOT/skills/*/`:

```bash
for skill_dir in "$COWORKER_ROOT/skills"/*/; do
  [[ -d "$skill_dir" ]] || continue
  skill_file="${skill_dir}SKILL.md"
  [[ -f "$skill_file" ]] || continue
  name=$(grep -m1 '^name:' "$skill_file" 2>/dev/null | sed 's/name: *//' | xargs)
  [[ -n "$name" ]] || continue

  target="$HOME/.claude/skills/$name/SKILL.md"
  if [[ ! -f "$target" ]]; then
    echo "NEW (ai-coworker): $name"
  elif [[ "$skill_file" -nt "$target" ]]; then
    echo "UPDATE (ai-coworker): $name"
  else
    echo "SKIP (ai-coworker): $name (current)"
  fi
done
```

Step 3 — Scan skill-factory skills.

For each SKILL.md under `$SKILL_FACTORY_DIR/ai-coworker-skills/*/` and
`$SKILL_FACTORY_DIR/personal-skills/*/`:

```bash
for cat_dir in "$SKILL_FACTORY_DIR/ai-coworker-skills" "$SKILL_FACTORY_DIR/personal-skills"; do
  [[ -d "$cat_dir" ]] || continue
  for skill_dir in "$cat_dir"/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_file="${skill_dir}SKILL.md"
    [[ -f "$skill_file" ]] || continue
    name=$(grep -m1 '^name:' "$skill_file" 2>/dev/null | sed 's/name: *//' | xargs)
    [[ -n "$name" ]] || continue
    base=$(basename "$skill_dir")

    target="$HOME/.claude/skills/$name/SKILL.md"
    if [[ ! -f "$target" ]]; then
      echo "NEW (skill-factory): $name"
    elif [[ "$skill_file" -nt "$target" ]]; then
      echo "UPDATE (skill-factory): $name"
    else
      echo "SKIP (skill-factory): $name (current)"
    fi
  done
done
```

Step 4 — Present summary to user:

Group results by category (NEW / UPDATE / SKIP) and source (ai-coworker / skill-factory):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Skills to Install
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEW (ai-coworker):
  analytics-create-db        analytics-daemon
  analytics-dashboard        analytics-import
  analytics-once             bug-hunt
  bug-report                 init
  initiative-activate        initiative-create
  ... (total 26)

NEW (skill-factory):
  auto-tdd                   contrarian-review
  devil-advocate             english-grammar-fix
  work-review                (total 5)

UPDATE:
  skill-create (skill-factory) — newer version available

SKIP (already current):
  ai-coworker-upgrade, doc-merge, doc-protect, ... (total 8)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Install all? [y / s: select / q: skip]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Step 5 — Install confirmed skills.

For each confirmed skill, install as directory symlinks to both IDEs:

```bash
install_one_skill() {
  local src="$1"        # path to SKILL.md (inside source skill directory)
  local name="$2"       # skill name from frontmatter
  local src_dir
  src_dir="$(dirname "$src")"        # e.g., ~/project/ai-coworker/skills/write-doc/
  local claude_dir="$HOME/.claude/skills"
  local opencode_dir="$HOME/.opencode/skills"

  # Claude Code: symlink entire skill directory
  mkdir -p "$claude_dir"
  if [[ -L "$claude_dir/$name" ]]; then
    rm -f "$claude_dir/$name"
  elif [[ -d "$claude_dir/$name" ]]; then
    # Real directory exists — upgrade by removing + symlink
    rm -rf "$claude_dir/$name"
  fi
  ln -sf "$src_dir" "$claude_dir/$name"

  # OpenCode: symlink entire skill directory
  mkdir -p "$opencode_dir"
  if [[ -L "$opencode_dir/$name" ]]; then
    rm -f "$opencode_dir/$name"
  elif [[ -d "$opencode_dir/$name" ]]; then
    rm -rf "$opencode_dir/$name"
  fi
  ln -sf "$src_dir" "$opencode_dir/$name"

  echo "Installed: $name ($src_dir → claude + opencode)"
}
```

Report install summary:

```
Skills installed:
  ✅ 26 NEW from ai-coworker
  ✅ 5 NEW from skill-factory
  ✅ 1 UPDATED
  ⏭  8 skipped (current)
```

### Phase 5: Re-run install (analytics + hooks)

Re-run install.sh to deploy analytics hooks, MCP config, and project configs.
**Do NOT select skills** — skill installation is handled by Phase 4 above.

Step 1 — Detect install mode:

```bash
CONFIG="$HOME/.coworker/coworker.yaml"
if [[ -f "$CONFIG" ]]; then
  MODE=$(grep "install_mode:" "$CONFIG" 2>/dev/null | awk '{print $2}' || echo "global")
else
  MODE="global"
fi
```

Step 2 — Run install with skill selection skipped:

```bash
cd "$COWORKER_ROOT" && echo "0" | bash setup/install.sh "--$MODE"
```

The `echo "0"` pipes "None" to the skill selection prompt, so only
analytics hooks, MCP config, and project config are processed.

### Phase 6: Sync MCP config

```bash
MCP_JSON="$COWORKER_ROOT/.mcp.json"
if [[ -f "$MCP_JSON" ]]; then
  # (coworker import-mcp removed — not yet implemented; MCP servers are managed via coworker sync)
fi
```

### Phase 7: Sync configs to all IDEs

```bash
coworker sync --tool all 2>/dev/null || {
  python3 -c "
import sys; sys.path.insert(0, '$COWORKER_ROOT')
from src.coworker.cli import sync
sync('all', False, False)
" 2>/dev/null || echo "Sync skipped (CLI not available)"
}
```

### Phase 8: Verify

Report a comprehensive summary of everything that was updated:

```bash
echo "=== ai-coworker ==="
cd "$COWORKER_ROOT" && git log --oneline -3

echo ""
echo "=== Global CLAUDE.md ==="
head -5 ~/.claude/CLAUDE.md 2>/dev/null || echo "(not found)"

echo ""
echo "=== Installed skills (~/.claude/skills/) ==="
ls ~/.claude/skills/ 2>/dev/null | wc -l

echo ""
echo "=== Active initiative ==="
cat ~/.coworker/initiatives/.active 2>/dev/null || echo "(none)"

echo ""
echo "=== Analytics hooks ==="
ls ~/.coworker/analytics/hooks/ 2>/dev/null || echo "(not installed)"

echo ""
echo "=== Skill-factory ==="
git -C ~/.config/opencode/skills/skill-factory log --oneline -1 2>/dev/null || echo "(not installed)"
```

Report to user in structured summary:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ai-coworker-upgrade — Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Coworker:       abc1234 → def5678 (+3 commits)
Global MD:      1 section overwritten, 1 added
Project MDs:    2 updated, 1 skipped
Skills:         26 NEW (ai-coworker), 5 NEW (skill-factory), 1 UPDATED, 8 skipped
Analytics:      hooks installed, DB initialized
Skill-factory:  pulled (latest: xyz9012)
Active:         skill-migration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Anti-Patterns

### 1. Fabricating CLAUDE.md rules

**Symptom:** The AI generates new rules or sections that were not in the
install.sh template or `coworker init` output.

**Why wrong:** CLAUDE.md governs the AI's own behavior. Fabricated rules
are unvetted and may conflict with coworker's design.

**Fix:** Every rule change must trace back to either `install.sh` template
or `coworker init --project` output. If neither source produces content for a
topic, do NOT add it.

### 2. Deleting user content without confirmation

**Symptom:** Sections marked OUTDATED are deleted without user review.

**Why wrong:** The AI's classification may be wrong. What looks like an
old coworker rule may actually be a user modification.

**Fix:** Always present the merge plan before applying. Never delete
without user approval. When in doubt, classify as KEEP.

### 3. Skipping global CLAUDE.md because it already exists

**Symptom:** The install.sh logic skips CLAUDE.md if the file exists
(Step 2 of install.sh). This skill's semantic merge handles the
"already exists" case.

**Why wrong:** Without this phase, global CLAUDE.md never gets updated
after initial install.

**Fix:** Phase 2 always runs, regardless of whether global CLAUDE.md exists.

### 4. Running update when nothing has changed

**Symptom:** Pull returns "Already up to date", all CLAUDE.md sections are KEEP,
no new skills found, and install produces no changes.

**Why wrong:** Wastes time.

**Fix:** After Phase 1, if no new commits, and after Phase 4 if all skills are
already current, report "Everything up to date. No changes needed." and
skip to Phase 8 (Verify). Still run Verify to confirm.

### 5. Guarding PROTECTED blocks

**Symptom:** `<!-- PROTECTED -->` blocks are modified or deleted during merge.

**Why wrong:** PROTECTED blocks are explicitly marked as "never change" per
coworker rules.

**Fix:** Before writing any merged CLAUDE.md, scan for
`<!-- PROTECTED -->...<!-- END PROTECTED -->` blocks and verify they are
identical to the current version. If any differ, stop and report the violation.

### 6. Installing skills from install.sh instead of Phase 4

**Symptom:** Phase 5 (install.sh) is run with "1" (All) for skill selection,
installing skills that are already managed by Phase 4.

**Why wrong:** Duplicate logic — Phase 4 is the authoritative skill installer.
Using install.sh for skills creates confusion about which source is canonical.

**Fix:** Always pipe `"0"` to install.sh to skip skill selection. Skill
installation happens exclusively in Phase 4.

## Sources

- Phase 1: confidence high — based on `setup/update.sh` fetch/merge logic
- Phase 2: confidence high — template from `install.sh` CLAUDE_MD_CONTENT variable; classification model derived from coworker rules
- Phase 3: confidence high — scanner from `coworker init --project`; classification same as Phase 2
- Phase 4: confidence high — skill scanning from ai-coworker/skills/ and skill-factory; install via cp to IDE config dirs
- Phase 5: confidence high — install.sh replay with piped "0" to skip skill selection
- Phase 6-7: confidence medium — MCP import and sync may vary by coworker version
- Phase 8: confidence high — standard verification commands
- Anti-patterns: confidence high — informed by known update failure modes
