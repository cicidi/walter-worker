---
name: feature
version: 0.2.0
description: |
  Use when managing cross-project features — create, edit, activate, deactivate,
  list, show, or delete. Use when the user mentions features, wants to switch
  active context, or needs to organize cross-project work.
license: MIT
compatibility: claude-code,opencode
triggers:
  - feature
  - features
  - create feature
  - activate feature
  - switch feature
  - list features
  - delete feature
when-to-use: >
  Use when creating, editing, activating, deactivating, listing, showing, or
  removing a cross-project feature context.
---

# feature

Manage cross-project features — work contexts that group projects, links,
decisions, and reference docs.

Renamed from `initiative`; that name remains available as a deprecated alias.

## When to Use

- Creating, editing, or removing a feature
- Activating or deactivating the current feature context
- Listing or viewing feature details

## When NOT to Use

- Managing projects in the catalog → use /project
- General task tracking → use /status

## Process

### No subcommand given

List current features and ask what the user wants to do. If exactly one
feature is active, show a summary with key info.

### Subcommands

| Subcommand | CLI equivalent | Description |
|------------|---------------|-------------|
| `create <name>` | `coworker feature create <name>` | Create a new feature with guided setup |
| `edit <name>` | `coworker feature edit <name>` | Modify fields, add projects/links/decisions/docs |
| `activate <name>` | `coworker feature activate <name>` | Set as active context, inject into IDE configs |
| `deactivate` | `coworker feature deactivate` | Remove current feature from IDE configs |
| `list` | `coworker feature list` | List all features for the current project |
| `show <name>` | `coworker feature show <name>` | Display full YAML config |
| `delete <name>` | `coworker feature remove <name>` | Permanently remove (asks confirmation) |

`coworker initiative ...` still works and prints a deprecation warning. Prefer
`coworker feature`.

### Create workflow (guided)

When the user runs `create`, don't just pass through to CLI. Instead:
1. Ask for the feature name (kebab-case)
2. Ask for a one-sentence description
3. Ask which projects are in scope (suggest from project catalog)
4. Run `coworker feature start <name> -d "<desc>" -p <project-dir>`
5. Offer to activate immediately

### Edit workflow

1. Show current feature state (all fields)
2. Ask what to change: description, add project (name:role:branches), add link (Title|URL), add decision (date|decision|rationale|by), add reference doc (Title|path)
3. If target feature is currently active, warn: "Changes take effect immediately in IDE context"
4. Run the corresponding `coworker feature edit` command with `--add-*` flags
5. Offer to archive (`--archive`) if the feature is complete

### Delete workflow

1. Show the feature summary before confirming
2. Ask for confirmation — deletion is permanent
3. If the feature is currently active, deactivate first
4. Run `coworker feature remove <name>` (or `--force` to skip prompt)
