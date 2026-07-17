# Initiative — Global to Project-Level Design

> **SUPERSEDED on 2026-07-02**: This design was reversed. Initiatives are now stored GLOBALLY at `~/.coworker/initiatives/` (not project-level). The storage spec below is kept for historical reference. See `src/coworker/config.py:INITIATIVES_DIR` and `coworker-blueprint.md §7` for the current global model.

## 1. Requirements

Initiatives (work context) moved from global to project-level:
- Each project manages its own initiatives
- Dashboard only shows data for current project + initiative
- Initiatives shared naturally via project git commits, removing publish/import

## 2. Storage Changes

| Item | Before | After |
|------|--------|-------|
| Initiative YAML | `~/.coworker/initiatives/<name>.yaml` | `{project}/.coworker/initiatives/<name>.yaml` |
| Create/Edit/Remove | Global directory operations | Per-project operations |
| Active Initiative | Injected into CLAUDE.md (unchanged) | Injected into current project's CLAUDE.md |

## 3. Code Changes

### 3.1 config.py

```python
# Before
INITIATIVES_DIR = GLOBAL_DIR / "initiatives"

# After — converted to function, accepts project_dir
def get_initiatives_dir(project_dir: Path | None = None) -> Path:
    p = Path(project_dir) if project_dir else Path.cwd()
    return p / ".coworker" / "initiatives"
```

`list_initiatives`, `load_initiative`, `save_initiative`, `initiative_exists` all add `project_dir` parameter.

### 3.2 models.py

Remove `InitiativeConfig.source: ImportSource | None` field.

### 3.3 manager.py

```python
class InitiativeManager:
    def __init__(self, project_dir: Path | None = None):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.initiatives_dir = self.project_dir / ".coworker" / "initiatives"
```

- `create()` — creates in `self.initiatives_dir`
- `edit()` — read/write from `self.initiatives_dir`
- `activate()` — `_resolve_target_dirs()` simplified to only return `self.project_dir`
- `deactivate()` — only cleans `self.project_dir` files
- `list_all()` — only lists from `self.initiatives_dir`
- `remove()` — removes from `self.initiatives_dir`
- **Delete** `publish()`, `import_from_url()` methods

### 3.4 cli.py

All initiative commands add `--project`:

```python
@click.option("--project", "-p", default=None, help="Project directory (default: current)")
```

Defaults to `os.getcwd()`. Delete `publish` and `import` commands.

### 3.5 adapters/claude.py + opencode.py

`inject_initiative()` / `remove_initiative()` no changes needed (already accept `project_dir` parameter, operate on project-level files).

### 3.6 skills/initiative-create/SKILL.md + initiative-edit/SKILL.md

Update CLI examples in docs, add `--project` parameter, remove publish/import references.

### 3.7 Dashboard — Frontend

- Add project dropdown filter (top of Overview page)
- New `/api/projects` endpoint: returns all unique project names
- Sessions/Initiatives views already have project column, no query logic changes needed

### 3.8 setup/install.sh

Remove global initiatives directory initialization.

## 4. Items Removed

| Item | Reason |
|------|--------|
| `coworker initiative publish` | Git commits handle sharing |
| `coworker initiative import` | No cross-project import needed |
| `InitiativeConfig.source` | No longer tracking import source |
| `manager.py:publish()`, `manager.py:import_from_url()` | Corresponding CLI commands removed |

## 5. Effort Estimate

| File | Lines Changed | Type |
|------|--------------|------|
| `src/coworker/config.py` | ~20 | Add parameter to function signatures |
| `src/coworker/models.py` | ~5 | Remove source field |
| `src/coworker/initiatives/manager.py` | ~80 | Remove publish/import, add project_dir param |
| `src/coworker/cli.py` | ~30 | Add --project, remove publish/import commands |
| `src/coworker/adapters/claude.py` | ~0 | No changes needed |
| `src/coworker/adapters/opencode.py` | ~0 | No changes needed |
| `skills/initiative-create/SKILL.md` | ~10 | Update docs |
| `skills/initiative-edit/SKILL.md` | ~10 | Update docs |
| `static/dashboard.js` | ~20 | Add project filter |
| `src/coworker/dashboard/queries.py` | ~5 | Add /api/projects query |
| `src/coworker/dashboard/app.py` | ~3 | Add route |
| `tests/python/test_config.py` | ~10 | Update tests |
| `setup/install.sh` | ~1 | Remove global init dir |
| **Total** | **~194** | Small change footprint |

## 6. Test Plan

1. `test_initiative_project_scoped` — verify initiative created under project directory
2. `test_initiative_activate_single_project` — verify activate only injects into current project
3. `test_initiative_list_project_only` — verify list only shows current project's initiatives
4. `test_dashboard_project_filter` — verify /api/projects returns correct data
5. Regression: all existing tests continue passing

## 7. New Dashboard API

```python
@app.get("/api/projects")
def api_projects():
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT project FROM sessions WHERE project IS NOT NULL AND project != '' ORDER BY project"
    ).fetchall()
    conn.close()
    return [r["project"] for r in rows]
```
