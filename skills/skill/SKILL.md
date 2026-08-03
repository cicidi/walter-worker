---
name: skill
description: |
  Use when creating, editing, importing, or listing skills in the skill-factory.
  Use when the user wants to capture a workflow as a skill, modify an existing
  skill, import from GitHub, or see what skills are available.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - skill
    - create skill
    - edit skill
    - import skill
    - list skills
    - new skill
    - make a skill
---

# skill

Manage skills in the skill-factory. Create self-contained SKILL.md files from
workflows, edit existing skills, import from external sources, and list what's
available.

## When to Use

- Capturing a reusable workflow as a new skill
- Modifying or fixing an existing skill's instructions
- Importing a skill from a GitHub URL or external repo
- Listing configured or available skills

## When NOT to Use

- Running an existing skill — just invoke it directly
- Creating an initiative → use /initiative
- Managing the project catalog → use /project

## Process

### No subcommand given

List current skills and ask what the user wants to do.

### Subcommands

| Subcommand | Description |
|------------|-------------|
| `create <name>` | Create a new SKILL.md with guided setup + quality gates |
| `edit <name>` | Modify an existing skill's content or frontmatter |
| `import <url>` | Import a skill from GitHub URL into import-skills/ |
| `list` | List all configured skills |

### create workflow

1. Ask for the skill name (kebab-case, `{verb}-{object}` format)
2. Search for existing similar skills (locally, GitHub, web) — avoid duplicates
3. Read CONVENTIONS.md for frontmatter and body structure rules
4. Draft the SKILL.md with:
   - Frontmatter: name, description ("Use when...", third person), license, compatibility
   - Body: # heading + overview, When to Use, When NOT to Use, Process, Quality Gates
5. Present the draft for review
6. On approval: save to `walter-worker-skills/<name>/SKILL.md`

### edit workflow

1. Read the current SKILL.md
2. Ask what to change (frontmatter fields, process steps, quality gates, triggers)
3. Apply changes while preserving: no TBD/TODO, no emoji in body, description
   must stay ≤1024 chars and start with "Use when"
4. Show diff and confirm before saving

### import workflow

1. Fetch the SKILL.md from the GitHub URL
2. Convert to skill-factory conventions:
   - Add `license: MIT` if missing
   - Add `compatibility: claude-code,opencode` if missing
   - Verify description starts with "Use when..."
   - Add When to Use / When NOT to Use sections if missing
3. Save to `import-skills/<original-name>/SKILL.md`
4. Report what was converted vs kept as-is

### list workflow

Run `coworker skill list` to show all configured skills with name, path,
and enabled status.
