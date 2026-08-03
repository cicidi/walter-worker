---
name: initiative
description: |
  Use when managing cross-project initiatives — create, edit, activate,
  deactivate, list, show, or delete. Use when the user mentions initiatives,
  wants to switch active context, or needs to organize cross-project work.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - initiative
    - initiatives
    - create initiative
    - activate initiative
    - switch initiative
    - list initiatives
    - delete initiative
---

# initiative

Manage cross-project initiatives — work contexts that group projects, links,
decisions, and reference docs for a feature or epic.

## When to Use

- Creating, editing, or removing an initiative
- Activating or deactivating the current initiative context
- Listing or viewing initiative details

## When NOT to Use

- Managing projects in the catalog → use /project
- General task tracking → use /status

## Process

### No subcommand given

List current initiatives and ask what the user wants to do. If exactly one
initiative is active, show a summary with key info.

### Subcommands

| Subcommand | CLI equivalent | Description |
|------------|---------------|-------------|
| `create <name>` | `coworker initiative create <name>` | Create a new initiative with guided setup |
| `edit <name>` | `coworker initiative edit <name>` | Modify fields, add projects/links/decisions/docs |
| `activate <name>` | `coworker initiative activate <name>` | Set as active context, inject into IDE configs |
| `deactivate` | `coworker initiative deactivate` | Remove current initiative from IDE configs |
| `list` | `coworker initiative list` | List all initiatives for the current project |
| `show <name>` | `coworker initiative show <name>` | Display full YAML config |
| `delete <name>` | `coworker initiative remove <name>` | Permanently remove (asks confirmation) |

### Create workflow (guided)

When the user runs `create`, don't just pass through to CLI. Instead:
1. Ask for the initiative name (kebab-case)
2. Ask for a one-sentence description
3. Ask which projects are in scope (suggest from project catalog)
4. Run `coworker initiative start <name> -d "<desc>" -p <project-dir>`
5. Offer to activate immediately

### Edit workflow

1. Show current initiative state (all fields)
2. Ask what to change: description, add project (name:role:branches), add link (Title|URL), add decision (date|decision|rationale|by), add reference doc (Title|path)
3. If target initiative is currently active, warn: "Changes take effect immediately in IDE context"
4. Run the corresponding `coworker initiative edit` command with `--add-*` flags
5. Offer to archive (`--archive`) if the initiative is complete

### Delete workflow

1. Show the initiative summary before confirming
2. Ask for confirmation — deletion is permanent
3. If the initiative is currently active, deactivate first
4. Run `coworker initiative remove <name>` (or `--force` to skip prompt)
