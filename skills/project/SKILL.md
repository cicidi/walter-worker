---
name: project
description: |
  Use when managing the project catalog — add, edit, remove, list, show,
  or sync projects. Use when the user mentions project catalog, adding a
  project, or syncing IDE configs.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - project
    - project catalog
    - add project
    - remove project
    - list projects
    - sync projects
---

# project

Manage the project catalog (`~/.coworker/project.yaml`). Each entry tracks
a project's local path, repo URL, team, and upstream/downstream relationships.

## When to Use

- Adding, editing, or removing a project from the catalog
- Listing tracked projects
- Syncing project context into IDE configs

## When NOT to Use

- Creating an initiative (cross-project work context) → use /initiative
- Managing skills → use /skill

## Process

### No subcommand given

List all projects and ask what the user wants to do.

### Subcommands

| Subcommand | CLI equivalent | Description |
|------------|---------------|-------------|
| `add <name>` | `coworker project add <name>` | Add current directory as a tracked project |
| `edit <name>` | `coworker project edit <name>` | Modify path, repo, upstream/downstream |
| `remove <name>` | `coworker project remove <name>` | Remove from catalog |
| `list` | `coworker project list` | List all tracked projects |
| `show <name>` | `coworker project show <name>` | Show full project entry as YAML |
| `sync` | `coworker project sync` | Re-inject static project context into IDE configs |

### add workflow

When the user runs `add`:
1. Auto-detect: language, framework, repo URL (from git remote), IDE support
2. Ask for: team name, upstream/downstream project names
3. Run `coworker project add <name> --path . --repo <url> --team <team>`
4. If upstream/downstream given, run `coworker project edit <name> --add-upstream X --add-downstream Y`
