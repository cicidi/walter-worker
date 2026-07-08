# Changelog

## 2026-07-08 — Polish Loop (autonomous, manager + deepseek worker + QA gate)

### Pipeline validated
- Manager(glm) → worker(deepseek-v4-pro) → tester(pytest) → reviewer(glm) → push. Worktree-isolated, never touches master.

### Fixes
- **B1**: fix 3 failing `tests/python/test_state_update.py` tests. Root cause: `tests/python/test_skill_frontmatter.py::test_scaffold_conforms` used a raw `os.chdir(tmp)` (never restored) → process cwd pointed at a deleted `TemporaryDirectory` → subsequent `monkeypatch.chdir` raised `FileNotFoundError: os.getcwd()`. Switched to the `monkeypatch` fixture. Suite: **167 passed, 0 failed** (was 3 failed, 164 passed). Branch `fix/b1-state-update-tests`.
- **S1**: removed root `static/` (assets already moved into `src/coworker/dashboard/static/`); `.gitignore` added `.coworker/`, `*.bak`, `docs/work-review/`, `docs/superpowers/`, `.polish-loop-stop`.

## 2026-06-24 — Review & Testing Update

### Fixes
- Fixed broken references in CLAUDE.md to non-existent `templates/team-common/` paths

### Tests
- Added `tests/python/test_cli.py` — 11 CLI tests (version, status, help, project list, config validation, skill references)
- Added `tests/python/test_skill_factory_integration.py` — 11 integration tests (source repo validation, deploy consistency, CLAUDE.md references)
- All 33+ existing tests still pass; 22 new tests added

### Documentation
- Updated README with testing instructions and skill management workflow
