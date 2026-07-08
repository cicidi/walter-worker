---
name: ai-coworker-setup-in-project
description: Interactive interview to generate project-level CLAUDE.md and CLAUDE.local.md with auto-detected skills, guardrails, and state persistence hooks.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - setup project claude md
    - setup project
    - configure project claude.md
    - setup ai coworker for project
    - init project rules
  when_to_use: When setting up a project with the new three-layer CLAUDE.md architecture. Use after `coworker init`.
  audience: ai-coworker
---

# ai-coworker-setup-in-project

Interactive interview to generate project-level and local-level CLAUDE.md for a project using the three-layer architecture.

## Process

### Phase 1: Global CLAUDE.md

Step 1 — Check if Global CLAUDE.md exists:

```bash
cat ~/.claude/CLAUDE.md 2>/dev/null | head -5
```

Step 2 — If NOT exists, generate from canonical template:

```bash
cd ~/project/ai-coworker && python3 -c "
from src.coworker.templates.global_claude_md import generate_global_claude_md
print(generate_global_claude_md())
" > ~/.claude/CLAUDE.md
```

Step 3 — If EXISTS, show warning and do NOT override:

```
Global CLAUDE.md already exists at ~/.claude/CLAUDE.md.
I will not override it. Compare with latest template manually:
  diff ~/.claude/CLAUDE.md <(python3 -c "from src.coworker.templates.global_claude_md import generate_global_claude_md; print(generate_global_claude_md())")
```

### Phase 2: Project Interview

Ask one question at a time. Use multiple-choice when possible.

After each answer, confirm: "Got it. Next question?"

1. **Project Relationships:** Any upstream/downstream/peer projects?
   - Ask: "Does this project depend on or serve other projects? Select all that apply."
   - Options: list from `coworker project list`
   - For each selected, ask: "Role? upstream/downstream/peer"
   - Record as `| <this-project> | <role> | <other-project> |`

2. **Knowledge Repo:** Where are design docs, PRDs, and specs?
   - Ask: "Where are your project's design documents?"
   - Options: `docs/specs/` (default), custom path, "no docs yet", URLs (wiki/Notion/etc.)
   - Record as doc_map entries

3. **Architecture Quirks:** Anything not obvious from scanning the repo?
   - Ask: "Any architecture conventions or quirks a new developer should know?"
   - Free text. Record as project context notes.

4. **Testing Conventions:** Any project-specific test patterns?
   - Ask: "Any special testing requirements beyond the default test command?"
   - Free text or "nothing special"

5. **Team Guardrails:** Any additional rules beyond defaults?
   - Show default guardrails summary
   - Ask: "Any additional team rules to add? (e.g., deployment restrictions, review requirements)"
   - Free text

### Phase 3: Generate Project CLAUDE.md

Generate to `<project>/CLAUDE.md`:

```bash
cd <project_dir> && python3 -c "
from src.coworker.templates.project_claude_md import generate_project_claude_md
print(generate_project_claude_md(
    project_name='<name>',
    relationships='''<relationships>''',
    doc_map='''<doc_map>''',
))
" > CLAUDE.md
```

Show summary: "Created CLAUDE.md with X sections. Would you like to review before saving? [y/N]"

### Phase 4: Generate CLAUDE.local.md

Generate to `<project>/CLAUDE.local.md` with auto-detected skills:

```bash
cd <project_dir> && python3 -c "
from src.coworker.templates.local_claude_md import generate_local_claude_md
print(generate_local_claude_md())
" > CLAUDE.local.md
```

Show: "Detected N available skills. Local.md created."

### Phase 5: Create docs/ structure

```bash
mkdir -p <project_dir>/docs/specs <project_dir>/docs/discussion
```

### Phase 6: Gitignore

```bash
cd <project_dir>
for entry in "CLAUDE.local.md" "docs/state-*.md"; do
  if ! grep -qxF "$entry" .gitignore 2>/dev/null; then
    echo "$entry" >> .gitignore
  fi
done
```

### Phase 7: Configure hooks

Claude Code — add state-update hook:

```bash
cd <project_dir> && python3 -c "
import json
from pathlib import Path
settings = Path('.claude/settings.json')
cfg = {}
if settings.exists():
    cfg = json.loads(settings.read_text())
cfg.setdefault('hooks', {})
stop_hooks = cfg['hooks'].get('Stop', [])
has_state_update = any(
    h.get('command') == 'coworker state-update'
    for g in stop_hooks if isinstance(g, dict)
    for h in (g.get('hooks') or [])
)
if not has_state_update:
    stop_hooks.append({'matcher': '', 'hooks': [{'type': 'command', 'command': 'coworker state-update'}]})
    cfg['hooks']['Stop'] = stop_hooks
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(cfg, indent=2))
    print('Hooks configured for Claude Code')
"
```

OpenCode — allow coworker commands:

```bash
cd <project_dir> && python3 -c "
import json
from pathlib import Path
cfg_path = Path('.opencode/config.json')
cfg = {}
if cfg_path.exists():
    cfg = json.loads(cfg_path.read_text())
cfg.setdefault('permission', {})
bash_perms = cfg['permission'].get('bash', {})
if isinstance(bash_perms, dict):
    bash_perms['coworker *'] = 'allow'
    cfg['permission']['bash'] = bash_perms
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2))
    print('Permissions configured for OpenCode')
"
```

### Phase 8: Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Project Setup Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Global CLAUDE.md:  [existing — not modified]
Project CLAUDE.md: <project>/CLAUDE.md
CLAUDE.local.md:   <project>/CLAUDE.local.md (N skills detected)
State hooks:        Claude Code + OpenCode configured
Docs:               docs/specs/ docs/discussion/
Gitignore:          CLAUDE.local.md docs/state-*.md

Next: Activate your initiative with `coworker initiative activate <name>`
      Start working — state auto-saves every 5 turns.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Anti-Patterns

- Do NOT override existing Global CLAUDE.md without explicit user permission
- Do NOT include auto-discoverable info (language/framework/test commands) in project CLAUDE.md
- Do NOT skip the hooks/permissions configuration — state persistence depends on it
