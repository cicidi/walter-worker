---
name: initiative-create
version: 0.1.0
description: Use when creating a new initiative — a cross-project work context that groups links, decisions, reference docs,
  and upstream/downstream project branches. Walks through interview, YAML generation, and optional activation.
triggers:
- start an initiative
- create an initiative
- new initiative
- begin initiative
- setup initiative
when-to-use: 'When the user wants to create a new work context to scope a feature,

  epic, or milestone. When switching to a different workstream.'
license: MIT
compatibility: claude-code,opencode
user-invocable: true
---
# initiative-create

Creates a new initiative YAML file at `~/.coworker/initiatives/<name>.yaml`.

## Process

### Phase 1: Interview

Ask one question at a time. Use multiple-choice when possible.

1. **Name:** What should this initiative be called?
   - Must be kebab-case (lowercase, hyphens): `auth-migration`, `payment-refactor`
2. **Description:** One sentence describing what this initiative covers?
3. **Projects:** Which projects are involved?
   - Run `coworker project list` to show available projects
   - For each project selected, ask:
     - Role? (upstream / downstream / peer)
     - Branches? (comma-separated, e.g., `main,feat/oauth2`)
4. **Links:** Any external URLs relevant to this work?
   - Wiki pages, design docs, PRDs, issue trackers
5. **Decisions:** Any key decisions already made?
   - Date, what was decided, rationale, who decided
6. **Reference docs:** Any local files important for this work?
   - Spec files, runbooks, config templates

### Phase 2: Generate

Step 1 — Create the base initiative:
```bash
coworker initiative create <name> -d "<description>"
```

Step 2 — Add projects, links, decisions, and docs:
```bash
coworker initiative edit <name> --add-project "auth-service:upstream:main,feat/oauth2"
coworker initiative edit <name> --add-link "Design Doc|https://wiki.internal.com/design"
coworker initiative edit <name> --add-decision "2026-06-01|Use OAuth2|Industry standard|cicidi"
coworker initiative edit <name> --add-doc "OAuth2 Spec|~/docs/oauth2-spec.md"
```

### Phase 3: Verify

Run `coworker initiative show <name>` and confirm:
- name is kebab-case
- status is `active`
- all projects exist in `coworker project list`
- YAML is valid

### Phase 4: Activate & Share

Ask: "Activate this initiative now? This injects its context into CLAUDE.md."

If yes:
```bash
coworker initiative activate <name>
```

Ask: "Publish to your coworker fork? This commits to `initiatives/` and outputs a shareable URL."

If yes:
```bash
coworker initiative publish <name>
```
