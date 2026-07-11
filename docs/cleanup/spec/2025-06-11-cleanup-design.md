# Cleanup Design: ai-coworker

Date: 2025-06-11
Status: Approved

## Overview

4-part cleanup: remove photos, migrate skills to skill-factory, remove templates, optimize setup scripts.

## Part 1: Photo Cleanup

- **Source**: `.pic/` (15 HEIC, ~34MB), `Photos-3-001/` (21 HEIC + 21 JPG, ~50MB)
- **Action**: Backup to `~/project/ai-coworker-backup/photos/`, then delete from repo

## Part 2: Skill Migration

6 skills migrate to `~/project/skill-factory/` via `skill-create` workflow (original as idea only):

| Source | Target Dir | New Name |
|--------|-----------|----------|
| `coworker-meta-doc-protection.md` | `personal-skills/` | `ai-coworker-doc-protect` |
| `coworker-meta-merge-docs.md` | `ai-coworker-skills/` | `ai-coworker-doc-merge` |
| `coworker-meta-self-analyze.md` | `personal-skills/` | `ai-coworker-self-analyze` |
| `coworker-meta-self-healing-trace.md` | `personal-skills/` | `ai-coworker-self-healing-trace` |
| `coworker-meta-report-issue.md` | `ai-coworker-skills/` | `ai-coworker-issue-report` |
| `coworker-meta-setup-coworker.md` | Keep in ai-coworker + install to IDE | original name |

Remaining 28 skills: backup to `~/project/ai-coworker-backup/skills/`, delete from repo.

## Part 3: Template Cleanup

- Backup `templates/` to `~/project/ai-coworker-backup/templates/`
- Delete `templates/` from repo

## Part 4: Setup Optimization

### install.sh

1. Ensure `~/.claude/CLAUDE.md` exists with Question Requirement rule
2. Clone/pull `https://github.com/cicidi/skill-factory` to `~/.config/opencode/skills/skill-factory`
3. User selects install location: global (default) or project
4. User selects skills: none (default), all, or select individually
5. `coworker-meta-setup-coworker` always installed
6. Claude Code is primary target; OpenCode uses symlink/copy
7. Run `coworker sync` for MCP config

### update.sh

- Primary: update coworker itself (git pull + re-install)
- Optional: update skill-factory (ask user)
- `uninstall.sh` deferred

### Testing

- Framework: bats (Bash Automated Testing System)
- Tests: install modes, update flow, CLAUDE.md creation, skill selection combinations
