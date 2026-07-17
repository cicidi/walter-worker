---
name: ai-coworker-fix
version: 0.1.0
description: Fix the ai-coworker project itself, then distribute via upgrade. Use when user asks to fix an issue and it's
  in ai-coworker source code (not just usage/config).
triggers:
- coworker-fix
- fix-coworker
when-to-use: Fix the ai-coworker project itself, then distribute via upgrade. Use when user asks to fix an issue and it's
  in ai-coworker source code (not just usage/config).
aliases:
- coworker-fix
- fix-coworker
user-invocable: true
---
# ai-coworker-fix

Fix issues in the ai-coworker project source code, run tests, commit, push, then invoke `ai-coworker-upgrade` to distribute the fix.

## Workflow

### 1. Analyze

Determine if the issue is in ai-coworker source code — not just a usage or config problem.

Indicators:
- Bug in `setup/install.sh`, `src/coworker/`, templates (`src/coworker/templates/`), or skills (`skills/`)
- Behavior that affects ALL projects (global config, hooks, CLAUDE.md generation)
- Skill produces wrong output due to bad instructions
- Config/settings are corrupted because ai-coworker wrote wrong values

If the issue is NOT in ai-coworker code, report it as a separate issue and stop here.

### 2. Fix

Edit the ai-coworker source files. Follow project conventions:
- Match existing code style
- Update design docs and blueprint alongside code changes
- No speculative changes, no unrelated refactoring

### 3. Verify

Run tests and ensure nothing breaks:
```bash
python -m pytest tests/ -x -q
```

Also verify the install script is valid:
```bash
bash setup/install.sh --dry-run 2>&1 || true
```

### 4. Commit & Push

```bash
git add -A
git diff --cached --stat
git commit -m "fix: {desc}"
git push origin main
```

### 5. Distribute

Invoke the `ai-coworker-upgrade` skill to apply the fix to all projects and IDE configs. This pulls latest code, merges CLAUDE.md, installs skills, and syncs configs.

## Rules

- Only fix ai-coworker code — don't fix symptoms in individual project configs
- Always run tests before committing
- Always push before upgrading (upgrade pulls from remote)
- If tests fail, loop: fix → verify → retry until all pass
- Keep commits focused on one fix at a time
