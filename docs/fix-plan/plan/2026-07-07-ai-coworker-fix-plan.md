# ai-coworker Fix Plan — 2026-07-07

**Audience**: Junior engineer. Work through items top-to-bottom by priority.
**Scope**: All open issues found via (a) GitHub Issue #1, (b) `TODO.md` items, (c) full source audit, (d) test-suite failures.
**How to use this doc**: Each item is self-contained — File, Problem, Reproduction, Fix steps, Verification. Do the Criticals first; they are mostly small, surgical changes. One GitHub issue / one PR per item unless noted. Follow `CLAUDE.md` guardrails (Conventional Commits, branch `fix/{issue-id}-{slug}`, never push to master, parameterized SQL, no hardcoded secrets).

**Test command** (run after every change): `python3 -m pytest tests/ -v`
**Baseline at audit time**: 2 failed, 92 passed. Goal: 0 failed.

---

## Summary Table

| ID | Severity | Title | File(s) | Effort |
|----|----------|-------|---------|--------|
| C1 | Critical | `coworker analytics once` always crashes (KeyError) | `cli.py:848` | S (15 min) |
| C2 | Critical | `from src.coworker...` imports break installed package | `analytics/*.py`, `dashboard/*.py` | M (1 hr) |
| C3 | Critical | Fresh-DB crash — `get_db()` never creates schema | `analytics/db.py:122` | S (20 min) |
| C4 | Critical | `coworker init`/`sync` never bootstrap analytics DB (TODO #5) | `cli.py:202-277,333-350` | S (20 min) |
| C5 | Critical | `coworker init --project` silently overwrites `CLAUDE.md` | `cli.py:243-254` | M (1 hr) |
| GH1 | Critical | Issue #1 — setup-coworker hardcodes `~/ai-coworker` | `skills/coworker-meta-setup-coworker.md:34-39` | M (1 hr) |
| H1 | High | Path traversal in initiative name (arbitrary file read/write/delete) | `config.py:134,145,151`; `manager.py:76` | S (30 min) |
| H2 | High | One bad session aborts entire import + connection leak | `analytics/import_data.py:170-180` | S (30 min) |
| H3 | High | Skill `total_calls` double-counted on every re-import | `import_data.py:125-133`; `auto_import.py:108-109` | M (1 hr) |
| H4 | High | `inject_static_context` crashes on missing END marker | `adapters/claude.py:31-38` | S (20 min) |
| H5 | High | `activate/deactivate/inject` swallow all errors, report false success | `initiatives/manager.py:89-93,103-111,137-141` | M (1 hr) |
| M1 | Medium | All file I/O missing `encoding="utf-8"` (breaks Windows) | many — see item | M (1 hr) |
| M2 | Medium | Non-atomic config writes (corruption risk on interrupt) | `config.py:76-80,98-102,142-147`; adapters | M (1 hr) |
| M3 | Medium | `initiative start` never records current project | `cli.py:608-619` | S (20 min) |
| M4 | Medium | Scanned language/framework/test-cmd never written to CLAUDE.md | `templates/project_claude_md.py:106-166`; `cli.py:187-196` | M (1 hr) |
| M5 | Medium | Gemini adapter skips skills + all context injection | `adapters/gemini.py:10-44` | L (2-3 hr) |
| M6 | Medium | Claude-JSONL importer writes no `tool_calls` rows | `analytics/auto_import.py:63-147` | M (1 hr) |
| M7 | Medium | `bash_count` always 0; `tool_count` undercounts (JSONL) | `auto_import.py:111-112,144-145` | S (30 min) |
| M8 | Medium | `skill_count` semantics differ between importers | `auto_import.py:145` vs `import_data.py:137-139` | S (20 min) |
| M9 | Medium | OpenCode sessions imported with NULLs → "Project: None" in LLM prompts | `auto_import.py:212-216`; `knowledge.py:28-33` | S (30 min) |
| M10 | Medium | Connection leaks on every error path (no `try/finally`) | `dashboard/queries.py`, `knowledge.py`, `auto_import.py` | M (1 hr) |
| M11 | Medium | No `busy_timeout` → "database is locked" under concurrency | `analytics/db.py:122-129` | S (10 min) |
| T1 | Medium | TODO #1 — Remove `docs/` from git, add to `.gitignore` | repo root | S (20 min) |
| T4 | Medium | TODO #4 — Split `knowledge-skill` → `knowledge-save` + `knowledge-search` | `skills/knowledge-skill/` | L (2-3 hr) |
| L1–L9 | Low | See Low-severity section | various | S each |
| TF1 | — | Failing test `test_claude_hooks_configured` | `tests/analytics/test_install.py` | S |
| TF2 | — | Failing test `test_skill_references_valid` | `tests/python/test_cli.py:81` | S |

> TODO #2 (remove `global/skills/commit`) — **already done** (gitignored). TODO #3 (merge `personal/skills`) — partially done, `personal/` is gitignored; skill-factory `personal-skills/` has 2 entries. TODO #6 depends on #3. These are tracked in `TODO.md`, not re-listed here.

---

# CRITICAL

---

## C1 — `coworker analytics once` always crashes with `KeyError`

- **File**: `src/coworker/cli.py:848`
- **Problem**: `analytics_once()` reads `stats['claude_imported']` and `stats['opencode_imported']`, but `run_once()` (`analytics/auto_import.py:230`) returns keys `{"claude_jsonl", "claude_hooks", "opencode", "skipped"}`. The referenced keys don't exist → `KeyError` after all import work is done.
- **Reproduction**: `coworker analytics once` (with or without sessions present).
- **Fix**:
  1. Open `src/coworker/cli.py`, find `analytics_once` (~line 840).
  2. Replace the print line (~848) to use the real keys:
     ```python
     console.print(
         f"[green]Imported:[/green] "
         f"claude_jsonl={stats['claude_jsonl']} "
         f"claude_hooks={stats['claude_hooks']} "
         f"opencode={stats['opencode']} skipped={stats['skipped']}"
     )
     ```
  3. Optionally add a tiny unit test in `tests/analytics/test_data.py` asserting `run_once()` return dict shape, so this can't drift again.
- **Verification**: `coworker analytics once` exits 0 and prints a summary line. `python3 -m pytest tests/analytics/ -v`.

---

## C2 — `from src.coworker...` imports break the installed package

- **Files** (5 modules, all use absolute `src.`-rooted imports):
  - `src/coworker/analytics/import_data.py:4`
  - `src/coworker/analytics/auto_import.py:6`
  - `src/coworker/analytics/knowledge.py:3`
  - `src/coworker/dashboard/queries.py:2`
  - `src/coworker/dashboard/app.py:6`
- **Problem**: `pyproject.toml` declares `[tool.setuptools.packages.find] where = ["src"]`, so the installed top-level package is `coworker`, **not** `src.coworker`. There is no `src/__init__.py`. The CLI imports these submodules via correct relative imports, but the moment a submodule loads, its own top-level `from src.coworker...` executes and crashes with `ModuleNotFoundError: No module named 'src'`. Only works in dev when CWD = repo root (PEP 420 namespace accident).
- **Reproduction**: `pip install .` then `coworker analytics import` (or `once`, `daemon`, `dashboard`).
- **Fix**: Convert every `from src.coworker.X import Y` to a **relative** import:
  - `analytics/import_data.py:4` → `from .db import get_db, init_db` (adjust names to what's actually used)
  - `analytics/auto_import.py:6` → `from .db import get_db` (and `from .import_data import ...` if it re-uses helpers)
  - `analytics/knowledge.py:3` → `from .db import get_db`
  - `dashboard/queries.py:2` → `from ..analytics.db import get_db`
  - `dashboard/app.py:6` → `from . import queries` (and any `from ..analytics...` needed)
  - Verify each module's other intra-package imports are also relative.
- **Verification**:
  1. `pip install -e . --break-system-packages` then `cd /tmp && python3 -c "import coworker.analytics.import_data, coworker.analytics.auto_import, coworker.analytics.knowledge, coworker.dashboard.queries, coworker.dashboard.app"` — must succeed with no `ModuleNotFoundError`.
  2. `coworker analytics import` from `/tmp`.
  3. `python3 -m pytest tests/ -v`.

---

## C3 — Fresh-DB crash: `get_db()` never creates the schema

- **File**: `src/coworker/analytics/db.py:122` (`get_db`)
- **Problem**: `get_db()` opens the connection and sets PRAGMAs but does **not** run `SCHEMA`. Only `init_db()` (db.py:132) calls `executescript(SCHEMA)`. Every entrypoint except `coworker analytics create-db` calls `get_db()` directly → on a missing/empty DB the first query throws `sqlite3.OperationalError: no such table: sessions`.
- **Reproduction**: `rm -f ~/.coworker/analytics/analytics.db && coworker analytics once`.
- **Fix**: Make `get_db()` idempotently ensure the schema. In `db.py` `get_db()`, after the PRAGMAs:
  ```python
  conn.executescript(SCHEMA)   # every stmt is CREATE ... IF NOT EXISTS — safe to repeat
  conn.commit()
  ```
  Then `init_db()` can simply `return get_db()` (keep it for backward compat / CLI use).
- **Verification**:
  1. `rm -f ~/.coworker/analytics/analytics.db && coworker analytics once` → no `OperationalError`.
  2. `coworker analytics dashboard`, hit `http://localhost:8000/api/overview` → 200 with empty stats, not 500.
  3. `python3 -m pytest tests/analytics/ -v`.

---

## C4 — `coworker init`/`sync` never bootstrap the analytics DB (TODO #5)

- **Files**: `src/coworker/cli.py:202-277` (`init`), `:333-350` (`sync`)
- **Problem (answers TODO.md #5)**: `coworker init` creates only YAML config, `CLAUDE.md`, docs dirs, `.gitignore`. `coworker sync` only writes IDE configs. Neither calls `init_db()`. Users must manually run `coworker analytics create-db`, and if they skip it, every other `analytics` subcommand crashes (see C3).
- **Fix**:
  1. In `cli.py` `init` (the `--global` path, ~line 209), after writing global config, call `init_db()` (wrap in `try/except` + `console.print` so a DB failure doesn't abort init). Import: `from .analytics.db import init_db`.
  2. Same in `sync` (~line 345) before walking adapters — cheap and idempotent.
  3. With C3 fixed, this becomes belt-and-suspenders, but it's still the right place to create the DB so analytics "just work" after install.
- **Verification**: Fresh machine: `rm -rf ~/.coworker && coworker init --global` → `~/.coworker/analytics/analytics.db` exists; `coworker analytics once` works without `create-db`.
- **After C3+C4**: update `TODO.md` to mark item #5 resolved.

---

## C5 — `coworker init --project` silently overwrites `CLAUDE.md` (data loss)

- **File**: `src/coworker/cli.py:243-254` (guard at 247, overwrite at 250)
- **Problem**: When `CLAUDE.md` exists, the code skips regeneration only if the file contains the literal `"## Identity & Project Context"`. But the canonical template (`templates/project_claude_md.py:156`) emits `"## Project Identity"`. The guard never matches a coworker-generated file, so re-running `coworker init --project` (or running it in any project with a hand-written CLAUDE.md) fully overwrites the file, destroying all user/PROTECTED content. This violates the README promise: "Your content outside these comment blocks is never modified."
- **Reproduction**: `coworker init --project`; edit `CLAUDE.md`; `coworker init --project` again → edits gone.
- **Fix** (two-part):
  1. **Immediate (correct the guard)**: change the substring check at `cli.py:247` from `"## Identity & Project Context"` to `"## Project Identity"` so re-runs on a coworker-generated file are skipped. Add a `--force` flag to allow explicit regeneration.
  2. **Proper (semantic merge)**: when the file exists and is NOT coworker-generated, use the existing `semantic_merge` module (currently dead code — see L1) to preserve user sections and only inject/replace the managed `<!-- PROTECTED:CRITICAL-RULES -->` and `<!-- COWORKER:STATIC ... -->` blocks. If wiring semantic_merge is out of scope for this PR, at minimum: back up the existing `CLAUDE.md` to `CLAUDE.md.bak` before overwriting, and print a warning.
- **Verification**:
  1. `coworker init --project` twice → second run skips, content preserved.
  2. In a project with a hand-written CLAUDE.md: `coworker init --project` preserves user content (or backs it up + warns).
  3. Add a regression test in `tests/python/test_injection.py`: create a CLAUDE.md with custom content + the managed markers, run init, assert custom content survives.
- **Note**: This is the highest-impact data-loss bug. Prefer the semantic-merge approach if time allows; the guard fix is the minimum.

---

## GH1 — GitHub Issue #1: setup-coworker hardcodes `~/ai-coworker`

- **Source file**: `skills/coworker-meta-setup-coworker.md:34-39` (currently only on `feat/dashboard` branch / in the `.worktrees/feat-dashboard/` copy and installed IDE copies; on `master` it was renamed to `skills/init/` in commit `47740a4`).
- **Problem**: Step 2 specifically checks for "the ai-coworker repo," breaking for users whose related repos have different names/locations.
- **Acceptance criteria** (from the issue):
  - Step 2 does not reference a hardcoded repo name
  - User can provide any local path to a related repo
  - If no related repo, setup continues to Step 3 automatically
  - `.local_config.yaml` optionally stores the related repo path
- **Open question to confirm with issue author before coding** (the audit found a config-architecture discrepancy):
  - `.local_config.yaml` is **deprecated** per `coworker-blueprint.md:524,605` ("Removed — all personal config in `CLAUDE.local.md`"), yet the issue's acceptance criteria mention it. The current config system is `.coworker/coworker.yaml` (`config.py:7-9`) and the Project Catalog at `~/.coworker/project.yaml` whose `ProjectEntry.local_path` (`models.py:89`) already models "a related repo path."
  - **Recommendation**: store the related-repo path in the Project Catalog (`ProjectEntry.local_path`) rather than reviving `.local_config.yaml`. Confirm with the issue author; if they insist on `.local_config.yaml`, follow their preference.
- **Fix steps**:
  1. Check out `feat/dashboard` (or cherry-pick the skill file back to `master` if that's the intended home — confirm with maintainer). The skill currently lives at `skills/coworker-meta-setup-coworker.md` on `feat/dashboard`.
  2. Edit Step 2 (lines 34-39) from:
     ```
     → Check if ai-coworker repo is cloned locally
     → If no: guide through: git clone + upstream remote setup
     → If yes: validate path exists and upstream is set
     ```
     to:
     ```
     → Ask: "Is there a related project repo? (paste a local path, or 'skip')"
     → If a path is given:
         → Validate it exists (Path(p).expanduser().is_dir())
         → Validate it's a git repo with an upstream remote:
             git -C <path> rev-parse --show-toplevel   # must succeed
             git -C <path> remote -v                    # must list an upstream
         → If invalid: report the specific problem and re-prompt (max 3 tries)
         → Record the path (see config decision above)
     → If 'skip' or empty: continue to Step 3 without blocking
     ```
  3. Update the "Output" section (line 69) to match the chosen config storage (drop the `.local_config.yaml` line if using the Project Catalog, or keep it if the author confirms).
  4. Reusable utilities already in the repo:
     - Repo-root detection pattern: `skills/ai-coworker-upgrade/SKILL.md:44-52` (`git -C <path> rev-parse --show-toplevel`).
     - Config persistence: `config.py` `load_config`/`save_config`/`find_project_config`.
     - Existing model field: `models.py:89` `ProjectEntry.local_path`.
  5. Also fix the **other hardcoded `~/ai-coworker` assumptions** the audit found (same root cause):
     - `README.md:29-30,66` — install instructions and example catalog hardcode `~/ai-coworker`. Change to a generic `~/<your-ai-coworker-dir>` and note the path is user-chosen.
     - `skills/ai-coworker-upgrade/SKILL.md:47,49,203` — hardcodes `~/project/ai-coworker`. Make it discover the repo (scan `~/project/ai-coworker`, `~/ai-coworker`, or accept `COWORKER_ROOT` env var).
     - `skills/ai-coworker-setup-in-project/SKILL.md:34-35` — `cd ~/project/ai-coworker`. Same discovery approach.
  6. Reinstall updated skill to IDE copies: `coworker sync` (or manually update `~/.claude/commands/`, `~/.opencode/instructions/`, `~/.gemini/`, `~/.cursor/rules/`).
- **Side-finding (fix in same PR or separate)**: `setup/install.sh:264-272,325-339` references `skills/coworker-meta-setup-coworker.md` which doesn't exist on `master` (renamed to `init/`). The `bats` test `tests/setup/test_install.bats:130-176` asserts this file is installed → fails on master. Either restore the file on master or update `install.sh` + the test to use the new `init/SKILL.md` path.
- **Verification**:
  1. Run the setup skill in a project with NO related repo → proceeds to Step 3.
  2. Provide a valid repo path → validated and recorded.
  3. Provide a bogus path → re-prompted with a clear error.
  4. `grep -rn "ai-coworker repo is cloned" skills/` returns nothing.
  5. `python3 -m pytest tests/setup/ -v` (fix the bats test per step above).

---

# HIGH

---

## H1 — Path traversal in initiative name (security)

- **Files**: `src/coworker/config.py:134` (`load_initiative`), `:145` (`save_initiative`), `:151` (`initiative_path`); `src/coworker/initiatives/manager.py:76-77` (`remove` → `path.unlink()`)
- **Problem**: `name` is interpolated directly into a filesystem path with no sanitization. `create()` validates kebab-case (`manager.py:39-40`), but `show`/`edit`/`remove`/`activate` do **not** re-validate. A name like `../../../../tmp/secret` resolves outside `~/.coworker/initiatives/`, enabling arbitrary file read (`show`), overwrite (`edit`/`save_initiative`), and delete (`remove` → `unlink`). Violates the Code Safety guardrail.
- **Reproduction**:
  - `coworker initiative show "../../../../tmp/secret"` reads `/tmp/secret.yaml`.
  - `coworker initiative remove "../../../../tmp/secret" --force` deletes it.
- **Fix**: Add a name-validation helper and call it at the `config.*` boundary (defense in depth — also enforce in `manager.show/edit/remove/activate`):
  ```python
  # config.py
  import re
  _KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

  def _safe_initiative_name(name: str) -> str:
      if not name or "/" in name or "\\" in name or ".." in name or not _KEBAB_RE.match(name):
          raise ValueError(f"Invalid initiative name: {name!r}")
      return name
  ```
  Call `_safe_initiative_name(name)` at the top of `load_initiative`, `save_initiative`, `initiative_path`, `initiative_exists`. Also use it in `manager.show/edit/remove/activate`.
- **Verification**:
  1. `coworker initiative show "../../etc/passwd"` → exits non-zero with "Invalid initiative name".
  2. Normal names still work.
  3. Add a test in `tests/python/test_cli.py`: assert `ValueError` / non-zero exit for traversal names.

---

## H2 — One bad session aborts entire import + connection leak

- **File**: `src/coworker/analytics/import_data.py:170-180`
- **Problem**: `import_all()` loops over session dirs calling `import_session(session_dir, conn)` with no `try/except`. A single malformed file (non-`JSONDecodeError` exception, unreadable file, `IntegrityError`) propagates and aborts the run; `conn.close()` (line 180) is never reached → connection leak. Already-imported sessions were committed individually, but everything from the bad session onward is skipped.
- **Fix**: Wrap per-session call in try/except, log + continue; use `try/finally` (or `contextlib.closing`) for the connection:
  ```python
  from contextlib import closing
  ...
  with closing(get_db()) as conn:
      for session_dir in sorted(SESSIONS.iterdir()):
          if not session_dir.is_dir():
              continue
          try:
              import_session(session_dir, conn)
          except Exception as e:
              print(f"  [skip] {session_dir.name}: {e}")
              conn.rollback()
  ```
- **Verification**: Drop a malformed session dir into `~/.coworker/analytics/sessions/`; `coworker analytics import` completes and logs a skip line; other sessions still import.

---

## H3 — Skill `total_calls` double-counted on every re-import

- **Files**: `src/coworker/analytics/import_data.py:125-133`; `src/coworker/analytics/auto_import.py:108-109`
- **Problem**: Messages/tool_calls/file_ops use `INSERT OR IGNORE` (idempotent), but the skill counter does `INSERT OR IGNORE INTO skills (name)` then unconditionally `UPDATE skills SET total_calls = total_calls + 1`. Each re-run of `coworker analytics import` (or overlap between `import` and `once`) inflates `skills.total_calls`. No guard checks whether the session was already counted.
- **Fix** (pick one, recommend the first):
  1. **Guard by session**: before incrementing, check `SELECT 1 FROM sessions WHERE id=? AND imported=1` (add an `imported`/`imported_at` column to `sessions` if not present; set it at end of `import_session`). If already imported, skip the whole session's counting.
  2. **Or make counting idempotent**: create a `skill_calls(call_id, skill_name)` child table with `INSERT OR IGNORE` keyed by a unique call id (the tool_use message id), and compute `total_calls` as `COUNT(*)` at query time instead of storing a counter.
- **Verification**: `coworker analytics import` twice on the same sessions → `SELECT name, total_calls FROM skills` unchanged after the second run. Add a test in `tests/analytics/test_data.py`.

---

## H4 — `inject_static_context` crashes on a missing END marker

- **File**: `src/coworker/adapters/claude.py:31-38` (used at `:134`)
- **Problem**: `_replace_or_append_block` does `if start in content:` then `content.index(end)`. If a `CLAUDE.md` contains `<!-- COWORKER:STATIC START -->` but the matching `<!-- COWORKER:STATIC END -->` was deleted, `str.index` raises `ValueError`. Combined with H5 this becomes a silent no-op; if the adapter is called directly it crashes.
- **Fix**: Use `find` and handle the corrupt case:
  ```python
  start_idx = content.find(start)
  if start_idx != -1:
      end_idx = content.find(end, start_idx)
      if end_idx == -1:
          # corrupt block (START without END) — replace from START to EOF
          content = content[:start_idx] + block
      else:
          content = content[:start_idx] + block + content[end_idx + len(end):]
  else:
      content = (content.rstrip() + "\n\n" + block + "\n") if content else block + "\n"
  ```
- **Verification**: Manually delete the `<!-- COWORKER:STATIC END -->` line from a CLAUDE.md, then `coworker project sync` → no crash, block rewritten cleanly.

---

## H5 — `activate`/`deactivate`/`inject` swallow all errors, report false success

- **File**: `src/coworker/initiatives/manager.py:89-93`, `:103-111`, `:137-141`
- **Problem**: Every adapter call is wrapped in `try: ... except Exception: pass`. If all injectors raise (permission error, template bug, H4), the exception is discarded and the code still prints "Activated initiative 'X'" / "Static context synced." The user is told it worked while nothing was written. Also hides programming errors during development. In `activate()`, `deactivate()` runs first (line 87) removing old context, then injection fails silently → net data loss.
- **Fix**:
  1. Collect outcomes instead of swallowing:
     ```python
     results = []
     for label, fn in injectors:
         try:
             fn()
             results.append((label, True, None))
         except Exception as e:
             results.append((label, False, str(e)))
     ```
  2. Append an action line per result (`console.print`), and only write the `ACTIVE_MARKER` / report success if at least one injector succeeded.
  3. Narrow `except Exception` to the expected I/O errors (`OSError`, `PermissionError`) where possible; let programming bugs surface.
  4. In `activate()`, if all injectors fail, do NOT write the `ACTIVE_MARKER` (so the state isn't left half-activated) and re-raise or return non-zero.
- **Verification**: Make CLAUDE.local.md unreadable (`chmod 000`), `coworker initiative activate foo` → reports failure, does not write `.active`. Restore perms.

---

# MEDIUM

---

## M1 — All file I/O missing `encoding="utf-8"` (breaks Windows / non-UTF-8 locales)

- **Files** (many): `config.py:24,79,93,101,122,137,146`; `cli.py:119,138,216,240,250,253,263,268,271,319,321`; `adapters/claude.py:56,94,137,160,181`; `adapters/gemini.py:22,40`; `adapters/opencode.py:28,47,57,83`; plus `manager.py` writes.
- **Problem**: Every `open(...)`, `read_text()`, `write_text()` uses the platform default encoding. Templates contain em-dashes (`—`), smart quotes, etc. On Windows (cp1252) or non-UTF-8 locales this raises `UnicodeEncodeError`/`UnicodeDecodeError`. Codebase is effectively Linux/macOS-only.
- **Fix**: Pass `encoding="utf-8"` to every `open`, `read_text`, `write_text` call. Use `rg "open\(" src/` and `rg "\.(read|write)_text\(" src/` to find them all. This is mechanical but touches many files — do it in one dedicated PR.
- **Verification**: `python3 -m pytest tests/ -v`. Optionally set `PYTHONIOENCODING` and locale tests; on Windows CI this would surface.

---

## M2 — Non-atomic config writes (corruption risk on interrupt)

- **Files**: `config.py:76-80` (`save_config`), `:98-102` (`save_project_catalog`), `:142-147` (`save_initiative`); JSON writes in `adapters/claude.py:94`, `gemini.py:40`, `opencode.py:47,57`.
- **Problem**: Writes go directly to the live file with `open(path, "w")`. A kill/disk-full/exception mid-dump leaves the file truncated/empty, losing the previous valid config. For IDE `settings.json`/`config.json` this can break the IDE.
- **Fix**: Add a helper and use it everywhere:
  ```python
  import os, tempfile
  def _atomic_write(path: Path, data: str) -> None:
      path.parent.mkdir(parents=True, exist_ok=True)
      fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
      try:
          with os.fdopen(fd, "w", encoding="utf-8") as f:
              f.write(data)
          os.replace(tmp, path)
      except BaseException:
          os.unlink(tmp)
          raise
  ```
  Replace `path.write_text(data)` / `with open(path,"w") as f: f.write(...)` with `_atomic_write(path, data)`.
- **Verification**: Unit test that interrupts a write (monkeypatch `os.replace` to raise) and asserts the original file is intact.

---

## M3 — `initiative start` never records the current project

- **File**: `src/coworker/cli.py:608-619`
- **Problem**: README (`:47`) and the docstring (`:596`) describe `initiative start` as "create, add project, and activate in one step." But the project-add block is guarded by `if proj_dir:` where `proj_dir` defaults to `None`. So `coworker initiative start foo` creates + activates but never records the current project in the initiative's `projects` list, even though `pd = Path.cwd()` was computed.
- **Fix**: Drop the `if proj_dir:` guard (or change to `proj_dir = proj_dir or str(pd)`), and always append an `InitiativeProjectRef` for the current dir when not already present (dedup by `name`). Also fix the related L6 (store `name` from the folder basename, not the full path) so it's consistent with `initiative_edit --add-project`.
- **Verification**: `coworker initiative start my-init` then `coworker initiative show my-init` → `projects` lists the current dir.

---

## M4 — Scanned language/framework/test-cmd never written to CLAUDE.md

- **Files**: `src/coworker/templates/project_claude_md.py:106-166` (params `language, framework, package_manager, build_cmd, lint_cmd, test_cmd, ides` at `:108-114` are never used in the body); caller `src/coworker/cli.py:187-196` doesn't pass them.
- **Problem**: `_scan_project` collects language/framework/deps/test/lint commands and prints them, but `generate_project_claude_md` accepts those params and silently ignores them. README claims "Auto-scan projects — detect language, framework, dependencies" and "Inject context into CLAUDE.md," but none of that detected info reaches the generated file.
- **Fix** (pick one):
  1. **Render it**: add a `## Build & Test` / `## Stack` section to the template that emits `language`, `framework`, `package_manager`, `build_cmd`, `lint_cmd`, `test_cmd`, `ides` from the params, and pass them from `_build_project_claude_md` (`cli.py:187-196`). This satisfies the README claim.
  2. **Or remove the dead params + scan fields** and stop claiming it in the README.
  Recommend option 1.
- **Verification**: `coworker init --project` in this repo → CLAUDE.md contains a Stack/Build section listing Python / pytest. Add a template test in `tests/python/test_templates.py`.

---

## M5 — Gemini adapter skips skills + all context injection

- **File**: `src/coworker/adapters/gemini.py:10-44` (no skills handling); `initiatives/manager.py:89,103,137` (injector lists contain only claude + opencode).
- **Problem**: README presents Gemini as a first-class target for skill sync and context injection. In reality `gemini.sync` only writes MCP servers + `extra`, never installs skills (unlike `claude.py:100-118`), and Gemini has no `inject_static_context`/`inject_initiative`/`remove_initiative`, so `coworker initiative activate`, `coworker project sync`, and `coworker sync --tool gemini` all skip skills and all context injection for Gemini.
- **Fix** (pick one, confirm with maintainer):
  1. **Implement**: add `install_skills`/`inject_static_context`/`inject_initiative`/`remove_initiative` to `gemini.py`, and add `gemini` to the injector lists in `manager.py:89,103,137`. Skills → `~/.gemini/skills/` (or whatever Gemini CLI expects); context → Gemini's equivalent of CLAUDE.md (`GEMINI.md` or `~/.gemini/...`).
  2. **Or correct the README** to state Gemini is MCP/override-only, and remove it from the "first-class" marketing.
  Recommend option 1 if Gemini CLI supports it; otherwise option 2 to stop misleading users.
- **Verification**: `coworker sync --tool gemini` installs a configured skill; `coworker initiative activate X` injects a Gemini context block.

---

## M6 — Claude-JSONL importer writes no `tool_calls` rows

- **File**: `src/coworker/analytics/auto_import.py:63-147` (`import_claude_jsonl`)
- **Problem**: Inserts into `sessions`, `session_stats`, `file_ops`, `skills`, but never `tool_calls`. Dashboard endpoints `/api/tools` (`queries.py:46-54`) and the `tool_calls` portion of `/api/sessions/{id}` aggregate over `tool_calls`. Since Claude-Code JSONL sessions (the dominant source — `~/.claude/projects/*`) produce zero `tool_calls` rows, those endpoints return empty/wrong data.
- **Fix**: In the `tool_use` branch of `import_claude_jsonl`, also:
  ```python
  conn.execute(
      "INSERT OR IGNORE INTO tool_calls "
      "(session_id, call_id, tool, tool_type, args, ts, seq_before, seq_after) "
      "VALUES (?,?,?,?,?,?,?,?)",
      (sid, call_id, tname, tool_type, json.dumps(tinput), ts, seq_before, seq_after),
  )
  ```
  Match the column names/types defined in `db.py` `SCHEMA`.
- **Verification**: `coworker analytics once` on a session that used tools → `SELECT COUNT(*) FROM tool_calls WHERE session_id=?` > 0; dashboard `/api/tools` returns data.

---

## M7 — `bash_count` always 0; `tool_count` undercounts (JSONL)

- **File**: `src/coworker/analytics/auto_import.py:111-112,144-145`
- **Problem**: The branch `tname in ("Read","Write","Edit","Glob","Bash")` increments `file_count` for **all five** including `Bash`, then `session_stats.tool_count` is set from `file_count`. So (a) Bash is misclassified as a file op; (b) `tool_count` excludes every other tool (Skill, Task, WebFetch, …); (c) `bash_count` is hardcoded `0` at INSERT even though Bash was counted. The hooks importer (`import_data.py:135-146`) computes these correctly, so the two importers disagree.
- **Fix**: Keep a separate `tool_total` incremented for **every** `tool_use`; track `bash_count` explicitly; only count Read/Write/Edit/Glob in `file_count`. Then `session_stats` gets `tool_count=tool_total`, `bash_count=bash_count`, `file_count=file_count`.
- **Verification**: Import a session using Skill + Bash → `tool_count` reflects all tools, `bash_count` > 0, `file_count` excludes Bash.

---

## M8 — `skill_count` semantics differ between importers

- **Files**: `auto_import.py:145` vs `import_data.py:137-139`
- **Problem**: Hooks path stores `skill_count = COUNT(*) FROM tool_calls WHERE tool='Skill'` (invocations). JSONL path stores `skill_count = len(_get_skills(jsonl_file))` (unique skill names). Dashboard cross-session comparisons are meaningless. Also `len(_get_skills(...))` re-reads and re-parses the entire JSONL a second time (already read at line 66).
- **Fix**: Standardize on **invocation count** (consistent with `skills.total_calls`). In `import_claude_jsonl`, compute `skill_count` from already-parsed data (count `tool_use` events with `tname == "Skill"`) instead of re-calling `_get_skills`.
- **Verification**: Import the same session via both paths → `session_stats.skill_count` matches.

---

## M9 — OpenCode sessions imported with NULLs → "Project: None" in LLM prompts

- **Files**: `auto_import.py:212-216` (writes NULLs); `knowledge.py:28-33,39-53`
- **Problem**: `import_opencode_meta` inserts sessions with only `id, ide, model, created_at` — `project`, `cwd`, `initiative`, `branch`, `closed_at` are NULL. `knowledge.get_session_data` then does `data['project'] = session["project"]` (None) and `build_summary_prompt` renders `"Project: None"`, `"Initiative: None"`, `"Branch: None"`, `"Duration: None to None"`. The LLM receives garbage context; grouping by project misses these sessions.
- **Fix**:
  1. In `knowledge.get_session_data`, coalesce NULLs: `data['project'] = session["project"] or ""` (and same for cwd/initiative/branch/closed_at).
  2. In `import_opencode_meta`, populate `project`/`cwd` from the opencode DB when available (query the opencode session record for `cwd`, derive `project` from the folder name).
- **Verification**: Import an opencode session, run `coworker knowledge ...` → prompt has no literal "None" tokens.

---

## M10 — Connection leaks on every error path (no `try/finally`)

- **Files**: `dashboard/queries.py:6-14,18-28,40-43,47-54,58-71,75-78,82-91,95-127`; `knowledge.py:7-24,72-94,98-115,119-125`; `auto_import.py:191-197,229,279`; `import_data.py:170-180`; `cli.py:824-825`.
- **Problem**: Connections opened with bare `conn = get_db()` and closed only on the happy path. Any exception between open and close leaves the connection (and in `import_opencode_meta` a second `oc` connection) dangling. In the long-running dashboard this is per-request; under load it accumulates FDs and WAL locks.
- **Fix**: Use `from contextlib import closing` and `with closing(get_db()) as conn:` everywhere, or add a small context manager in `db.py`:
  ```python
  @contextmanager
  def get_conn():
      conn = get_db()
      try:
          yield conn
      finally:
          conn.close()
  ```
  Replace all `conn = get_db()` ... `conn.close()` with `with get_conn() as conn:`. In `import_opencode_meta`, close `oc` in a `finally`.
- **Verification**: `python3 -m pytest tests/ -v`; stress the dashboard with many concurrent requests → no FD growth / no "database is locked".

---

## M11 — No `busy_timeout` → "database is locked" under concurrency

- **File**: `src/coworker/analytics/db.py:122-129`
- **Problem**: `get_db()` sets `journal_mode=WAL` and `foreign_keys=ON` but no `busy_timeout`. Two writers (daemon running while user runs `import`, or two dashboard writes) collide and raise `sqlite3.OperationalError: database is locked` immediately instead of waiting.
- **Fix**: In `get_db()`, add `conn.execute("PRAGMA busy_timeout=5000")` alongside the other PRAGMAs.
- **Verification**: Start `coworker analytics daemon`, concurrently run `coworker analytics import` → no "database is locked".

---

## T1 — TODO #1: Remove `docs/` from git, add to `.gitignore`

- **Verified state**: `docs/` IS tracked — `git ls-files docs/` returns 4 files (`docs/plan/2026-07-01-claude-md-redesign.md`, `docs/spec/2026-06-12-initiative-project-level-design.md`, `docs/spec/2026-07-01-claude-md-best-practices-paper.md`, `docs/spec/2026-07-01-claude-md-design.md`). `.gitignore` does NOT contain `docs/`.
- **Fix**:
  1. `git rm -r --cached docs/`
  2. Add `docs/` to `.gitignore` (keep the existing `docs/state/` line or consolidate).
  3. Commit with `chore: stop tracking docs/ (local-only design notes)`.
- **Verification**: `git ls-files docs/` empty; `docs/` still present locally; `.gitignore` contains `docs/`.
- **Note**: `docs/specs/` and `docs/discussion/` are referenced in `CLAUDE.md` as committed knowledge repos. Confirm with maintainer whether ALL of `docs/` should be untracked, or only `docs/plan/` + `docs/prd/` + `docs/spec/` (the original TODO text lists those subdirs specifically). Don't blindly untrack `docs/specs/` if it's meant to be shared.

---

## T4 — TODO #4: Split `knowledge-skill` → `knowledge-save` + `knowledge-search`

- **Verified state**: `skills/knowledge-skill/` is a single skill (`SKILL.md` only). Not yet split.
- **Goal**: `knowledge-save` extracts insights from sessions → SQLite + Obsidian; `knowledge-search` queries stored knowledge from DB or vault.
- **Fix steps**:
  1. Read `skills/knowledge-skill/SKILL.md` and `src/coworker/analytics/knowledge.py` to understand current behavior.
  2. Create `skills/knowledge-save/SKILL.md` — workflow: pick session → run `coworker knowledge save` → LLM extracts insights → writes summary to SQLite (`knowledge_summaries` table) + a Markdown card to the Obsidian vault.
  3. Create `skills/knowledge-search/SKILL.md` — workflow: query `coworker knowledge search "<query>"` → searches SQLite (FTS if available) + vault filenames → returns ranked hits.
  4. Split the CLI: `coworker knowledge save <session-id>` and `coworker knowledge search <query>` (currently `knowledge.py` has `get_session_data`/`build_summary_prompt`/`save_summary`/`save_card` — reuse these for `save`; add a `search` function for `search`).
  5. Remove `skills/knowledge-skill/` (or leave a deprecation pointer).
  6. Update `CLAUDE.md` / skills catalog references.
- **Verification**: `coworker knowledge save <id>` writes a summary + card; `coworker knowledge search "term"` returns hits. New tests in `tests/analytics/test_data.py`.
- **Effort**: Large — consider a separate initiative; use `brainstorming` skill first if requirements are unclear.

---

# LOW

Each is small; batch into one "cleanup" PR or fold into related items.

| ID | File:line | Problem | Fix |
|----|-----------|---------|-----|
| L1 | `src/coworker/semantic_merge.py` (whole file) | Dead code (nothing imports it); `OUTDATED` const never assigned; `_parse_sections` drops empty-body sections (`if current_body:`). Needed for C5 proper fix. | Either delete, or fix (`drop the if current_body guard`; assign empty string) and wire it into `cli.py` init path for C5. |
| L2 | `src/coworker/cli.py:141` | Flask heuristic `and "flask" != pyproject.lower()[:100]` is always-true → collapses to substring match; misfires on `flask-cors` etc. Same weakness for FastAPI/Django/Click. | Parse `[project.dependencies]` with `tomllib` and match exact distribution names. |
| L3 | `adapters/claude.py:139`; `adapters/opencode.py:85` | `verb = "updated" if STATIC_START in content else "injected"` checked AFTER mutation → always "updated". | Capture `had_block = STATIC_START in content` before replacement; branch on it. |
| L4 | `config.py:112-114,150-155` | `initiative_path`/`initiative_exists` call `_initiatives_dir()` which `mkdir`s — read ops create the dir. | Return path without mkdir; only `save_initiative`/`list_initiatives` ensure the dir. |
| L5 | `config.py:12-20` | `find_project_config` loop `while current != current.parent:` exits before checking root. | `for current in [Path.cwd(), *Path.cwd().parents]:` |
| L6 | `adapters/claude.py:84-92`; `adapters/opencode.py:53-55` | Assumes `hooks["Stop"]` / `permission.bash` is a list; a dict → `AttributeError` on `.get`. | `if isinstance(stop_hooks, list):` guard; skip/normalize otherwise. |
| L7 | `adapters/opencode.py:45-58` | Writes config twice (once without `permission`, once with) → partial-state window. | Build full dict (incl. permission) first, write once. |
| L8 | `cli.py:270-274` | `.gitignore` dedup uses raw-substring `in` — `docs/state/backup/` causes `docs/state/` to be skipped. | Compare against `set(existing.splitlines())`. |
| L9 | `cli.py:309,484,758,374` | Duplicate/mid-function imports (`datetime`, `yaml`, `find_project_config`). | Hoist to top-level imports; drop re-imports. |
| L10 | `manager.py:36-49` | `create()` checks existence before name validity → confusing error on malformed names. | Reverse order: validate name first. |
| L11 | `cli.py:608-619` | `initiative start --project /x/y` stores full path as `name`; `initiative_edit --add-project` stores basename. Inconsistent dedup. | Store `Path(proj_dir).name` as `name` in both paths. (Same PR as M3.) |
| L12 | `cli.py:821-826` | `init_db()` returns a connection the CLI discards (leak). | `with closing(init_db()) as _: pass`. |
| L13 | `dashboard/app.py:63-65` | Static path `os.path.join(dirname(__file__), "..","..","..","static")` breaks when installed in site-packages. | Use `importlib.resources` or ship static inside the package. |
| L14 | `import_data.py:93-110`; `auto_import.py:111-129` | `Glob` counted as file-op but its arg is `pattern`, not `filePath` → `file_path=""` → insert skipped. | Also read `args.get("pattern")`, or drop Glob from the file-op set. |
| L15 | `import_data.py:11-20`; `auto_import.py:160-165` | Hand-rolled `parse_session_yaml` (split on first `:`, strip quotes) — breaks on nested/lists/comments. PyYAML is already a dep. | `yaml.safe_load(f.read_text()) or {}`. |
| L16 | `dashboard/app.py:51-60` | WebSocket `except Exception: pass` swallows all errors silently. | Log the exception; send an error frame to the client. |
| L17 | `dashboard/app.py:17`; `queries.py:5` | `/api/sessions?limit=` unbounded (and `limit=-1` = no limit in SQLite). | `limit = max(1, min(limit, 500))`; FastAPI `Query(ge=1, le=500)`. |
| L18 | `manager.py:36-49` | `initiative_exists` checked before `KEBAB_RE` → wrong error type. | (Same as L10.) |

---

# FAILING TESTS (fix alongside the relevant item)

## TF1 — `tests/analytics/test_install.py::test_claude_hooks_configured`

- **Failure**: `AssertionError` — the test asserts Claude hooks are configured after install, but they aren't.
- **Likely cause**: Tied to the `install.sh` / skill-file rename breakage on `master` (see GH1 side-finding): `setup/install.sh:264-272,325-339` reference `skills/coworker-meta-setup-coworker.md` which no longer exists on master (renamed to `init/`). The hooks-config step depends on files that didn't install.
- **Fix**: Resolve the `install.sh` path references (GH1 side-finding) so the install actually configures hooks, then re-run the test. Inspect `tests/analytics/test_install.py` to see exactly what it asserts and align.

## TF2 — `tests/python/test_cli.py::TestSkillReferences::test_skill_references_valid`

- **Failure**: `AssertionError: No skill references found in CLAUDE.local.md` — the test expects `CLAUDE.local.md` to contain skill references (`skill-create`, `skill-edit`, `self-heal`, `self-analyze`), but it doesn't.
- **Cause**: `coworker init` / the local template (`templates/local_claude_md.py`) doesn't write skill references into `CLAUDE.local.md`. This is a feature gap (related to M4 — detected/auto-managed metadata not reaching generated files).
- **Fix** (confirm with maintainer): either (a) have `templates/local_claude_md.py` emit a "## Available Skills" section listing detected skills, or (b) update the test to match current intended behavior (skip if no skills section). Prefer (a) — it matches the test's stated intent ("Skills are auto-detected and written to CLAUDE.local.md").

---

# Suggested PR ordering

1. **PR1 — Critical crash fixes** (C1, C2, C3, C4): unblock `coworker analytics *` for real installs. ~2-3 hrs.
2. **PR2 — Data-loss fix** (C5 + L1 if wiring semantic_merge): protect user CLAUDE.md. ~1-2 hrs.
3. **PR3 — Security** (H1): path traversal. ~30 min.
4. **PR4 — Analytics integrity** (H2, H3, M6, M7, M8): correct counts. ~3 hrs.
5. **PR5 — Injection robustness** (H4, H5): no false success. ~1.5 hrs.
6. **PR6 — Issue #1** (GH1 + install.sh/test fix): hardcoded path. ~1.5 hrs.
7. **PR7 — Cross-platform + atomicity** (M1, M2): encoding + atomic writes. ~2 hrs.
8. **PR8 — Feature gaps** (M3, M4, M5, M9): initiative project, scanned-stack→CLAUDE.md, Gemini, NULL coalesce. ~3-4 hrs.
9. **PR9 — Resource/concurrency** (M10, M11): connection mgmt + busy_timeout. ~1 hr.
10. **PR10 — TODO housekeeping** (T1): untrack `docs/`. ~20 min.
11. **PR11 — Low-severity cleanup** (L1–L18 + TF1/TF2): batch. ~2-3 hrs.
12. **Separate initiative** (T4): split knowledge-skill — larger, brainstorm first.

---

# Repo conventions for the junior engineer (from CLAUDE.md)

- **Branch**: `fix/{issue-id}-{short-description}` (e.g. `fix/c1-analytics-once-keyerror`). Never push to `master`.
- **Commits**: Conventional Commits — `fix: ...`, `feat: ...`, `chore: ...`, `refactor: ...`, `docs: ...`.
- **Code safety**: no hardcoded secrets; parameterized SQL only (no f-strings/`%` for SQL); never commit `.env`.
- **Code quality**: lint + format before commit; no commented-out code in PRs; no `TODO` without a linked GitHub issue; never edit `<!-- PROTECTED -->` blocks.
- **Verification**: run `python3 -m pytest tests/ -v` before every commit; goal is 0 failures. For risky changes (C5, H1, C2) add a regression test.
- **When uncertain**: ask. Don't fabricate. The audit includes open questions (GH1 config storage, M5 Gemini scope) — confirm with maintainer before implementing.
