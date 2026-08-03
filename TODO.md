# walter-worker TODO

## Pending

### 1. Remove docs/ from GitHub, add to .gitignore
- `docs/plan/`, `docs/prd/`, `docs/spec/`, `docs/superpowers/`, `docs/work-review/`
- git rm --cached, add `docs/` to .gitignore

### 2. Remove global/skills/commit/ from GitHub
- Simple git commit helper — not walter-worker specific
- Delete and add to .gitignore

### 3. Merge personal/skills/ → skill-factory personal-skills/
- walter-worker `personal/skills/` (31 files, old format) → skill-factory `personal-skills/` (6 files, new format)
- Convert to directory-per-skill format, unify naming

### 4. Split knowledge-skill → knowledge-save + knowledge-search
- knowledge-save: extract insights from sessions → SQLite + Obsidian
- knowledge-search: query stored knowledge from DB or vault

### 5. Check: does install auto-setup memory DB / RAG / SQLite?
- Verify `coworker init` / `coworker sync` behavior for analytics DB setup

### 6. Clean up personal/skills/ from walter-worker (after merge to skill-factory)
- Remove from GitHub, add to .gitignore
