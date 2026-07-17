---
name: initiative-edit
version: 0.1.0
description: Use when editing an existing initiative — adding projects, decisions, links, reference docs, or changing status.
  Use for updating active work context.
triggers:
- edit initiative
- update initiative
- add to initiative
- change initiative
- modify initiative
when-to-use: 'When the user wants to modify an existing initiative. Adding projects,

  decisions, links, or reference docs. Archiving old initiatives.'
license: MIT
compatibility: claude-code,opencode
user-invocable: true
---
# initiative-edit

Modifies an existing initiative YAML file at `~/.coworker/initiatives/<name>.yaml`.

## Process

### Phase 1: Load current state

Run `coworker initiative show <name>` to display the current config.

### Phase 2: Ask what to change

One operation at a time:

| Operation | CLI |
|-----------|-----|
| Set description | `coworker initiative edit <name> --description "New desc"` |
| Add project | `coworker initiative edit <name> --add-project "name:role:branches"` |
| Add link | `coworker initiative edit <name> --add-link "Title\|URL"` |
| Add decision | `coworker initiative edit <name> --add-decision "date\|what\|why\|who"` |
| Add reference doc | `coworker initiative edit <name> --add-doc "Title\|path"` |
| Archive | `coworker initiative archive <name>` |

### Phase 3: If initiative is active

Check status with `coworker initiative list` — active initiative has a ✓ marker.

If the edited initiative is active, warn: "Changes aren't reflected in your IDE until you re-activate. Re-activate now?"

If yes:
```bash
coworker initiative activate <name>
```

### Phase 4: Verify

Run `coworker initiative show <name>` to confirm changes.

### Phase 5: If imported from teammate

If `coworker initiative show <name>` shows a `source.url` field, this initiative was imported. Changes are local only unless you publish:

```bash
coworker initiative publish <name>
```
