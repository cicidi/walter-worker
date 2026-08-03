# computer-config — Implementation Plan (Impl Plan)

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-08-01 | 0.1.0 | Initial draft |
| 2026-08-01 | 0.2.0 | Post devil-advocate review: menu → 0/1/2/3 (one-click both); component 1 adds settings.json model-field reconciliation to pro; component 2 uses marker-based inline-color detection; A4 manifest defined + missing-manifest handling |
| 2026-08-01 | 0.3.0 | Post GLM-5.2 review (scope-corrected): DROP model-field reconciliation (CCR-managed, not our concern); atomic write → stdlib-only; component 2 adds legacy grey-theme migration + tmux reload note; A4 uninstall uses rm -rf + python pop statusLine; add B1.5 (walter-worker manifest excludes ~/.claude/statusline/); B2 preserves rich status_info as optional rather than deleting |

---

## 1. Overview

This plan runs two parallel workstreams:
- **Workstream A**: create the claude-tmux-config standalone project
- **Workstream B**: strip the presentation layer out of walter-worker

They are independent and can run in parallel.

---

## 2. Workstream A: claude-tmux-config project

### Step A1 — Repo skeleton

```bash
mkdir ~/project/claude-tmux-config
cd ~/project/claude-tmux-config
git init
```

Create structure:
```
claude-tmux-config/
├── README.md
├── install.sh
├── uninstall.sh
├── assets/
└── docs/
```

**Verify**: `git status` clean, directory structure correct.

### Step A2 — Adopt assets

| Asset | From | To | Handling |
|-------|------|----|----------|
| `statusline-command.sh` | `~/.claude/` | `assets/statusline-command.sh` | Parameterize 3 paths: `:150` turn-counter, `:199` ccusage-cache, `:370` wrap-statusline.py → `$HOME/.claude/statusline/` |
| `wrap-statusline.py` | `~/.claude/` | `assets/wrap-statusline.py` | As-is |
| `status_info.sh` | `~/.tmux/scripts/` | `assets/status_info.sh` | As-is (simple version) |
| Benjamin Blue theme | inline in .tmux.conf | `assets/benjamin-blue.tmux` | Extract color block into standalone file |

**Verify**: each asset's paths parameterized correctly; no leftover `~/.claude/`
old paths (except the target dir).

### Step A3 — install.sh

Implement 0/1/2/3 menu + y/N confirm (default 0, supports one-click both):

```
🎯 What to install? (default skip, non-destructive)
  0) Skip
  1) Claude Code statusline only (statusline + statusLine setting)
  2) tmux theme + status bar only (Benjamin Blue + source theme file)
  3) Both — full statusline + theme (one click)
Choose [0]:
```

Component 1:
1. `command -v jq && command -v bc && command -v python3` check, warn if missing
2. Deploy `statusline-command.sh` + `wrap-statusline.py` → `~/.claude/statusline/`
   **unchanged** (port-as-is; only the 3 hardcoded paths in §3.11 are
   parameterized to `$HOME/.claude/statusline/`). Do NOT touch the
   `settings.json` `model` field — it is CCR-managed.
3. Inline `python3 -c` merge `statusLine` into settings.json using the
   **stdlib-only atomic write** (spec §6.3: `shutil.copy2` → `.bak`, temp,
   `os.fsync`, `os.replace`). NOT plain `json.dump`, NOT walter-worker's
   `backup.snapshot()` (unimportable from bash).

Component 2 (per spec §6.2 detection algorithm):
1. If `.tmux.conf` contains the **legacy `# walter-worker status bar` marker** →
   prompt "Replace old grey theme with Benjamin Blue? [y/N]"; on `y`, strip the
   old block then do a full deploy; on `n`, deploy only `status_info.sh`.
2. Else if marker `# claude-tmux-config theme` OR any of the 6 Benjamin Blue
   hexes is present → deploy only `status_info.sh`, do NOT append `source`.
3. Else (fresh) → deploy `benjamin-blue.tmux` → `~/.tmux/conf.d/`, append
   `source` line + marker comment.
4. Backup `.tmux.conf.bak` before mutation.
5. After deploy, print: *"Run `tmux source-file ~/.tmux.conf` (or restart tmux)
   to apply the theme."* (fresh machines need a reload.)

**Verify**: run `install.sh`, confirm each item; check deployed files +
settings.json (statusLine present; `model` field untouched).

### Step A4 — uninstall.sh

Manifest-driven (manifest at `~/.coworker/statusline-manifest.json`, per spec
§6.3):

- `settings.json`: inline `python3 -c` → `cfg.pop('statusLine', None)` → write
  atomically (same stdlib pattern as install).
- `~/.claude/statusline/`: `rm -rf` the whole directory (catches runtime cache
  files `turn-counter-*.json`, `ccusage-cache.json` that aren't in the manifest).
- `~/.tmux/conf.d/benjamin-blue.tmux`: delete.
- `~/.tmux.conf`: strip the line containing the marker `# claude-tmux-config
  theme` (leave any legacy walter-worker grey block untouched — that's walter-worker's
  responsibility; document this scope in README).
- If manifest missing → refuse to run, log warning, list files to remove manually.
- If manifest partial → remove only listed files, report the rest as manual.

**Verify**: run uninstall, confirm all traces removed (statusLine gone, dirs
deleted, source line stripped).

### Step A5 — README + docs/claude-tmux.md

README: purpose, install, uninstall, screenshots.
docs/claude-tmux.md: claude-tmux binding docs (no binary auto-install).

**Verify**: docs cover install/uninstall/dependencies/FAQ.

---

## 3. Workstream B: walter-worker strip

### Step B1 — Remove install.sh Step 16

Remove Step 16 (tmux status bar deploy, ~lines 476-506) from `setup/install.sh`.

**Verify**: `grep -n "status_info\|tmux" setup/install.sh` has no residual
deploy logic.

### Step B1.5 — Exclude `~/.claude/statusline/` from walter-worker's manifest walk

walter-worker's manifest step does `os.walk(~/.claude/)` recursively, so it would
claim `~/.claude/statusline/*` (claude-tmux-config's deployed files) and could
delete them on walter-worker uninstall. Add an exclusion so the walk skips
`~/.claude/statusline/` (and `~/.tmux/conf.d/`). This makes the cross-project
conflict resolution bidirectional (spec §6.3).

**Verify**: after running walter-worker install, `~/.coworker/install-manifest.json`
contains NO entries under `~/.claude/statusline/`.

### Step B2 — Move setup/status_info.sh to claude-tmux-config (don't delete)

The 90-line rich `setup/status_info.sh` is removed from walter-worker, but
**preserved** as `claude-tmux-config/assets/status_info-rich.sh` (optional
enhancement for users who want git/worktree/initiative info). The user's current
simple version remains the default `assets/status_info.sh`. This keeps the
working code reversible rather than permanently deleting it.

**Verify**: walter-worker `setup/status_info.sh` gone; rich version lives in
claude-tmux-config as optional.

### Step B3 — Update affected tests

Involved: `tests/conftest.py`, `tests/setup/test_install.bats`,
`tests/setup/test_update.bats`, `tests/analytics/test_install.py`,
`tests/analytics/test_data.py`.

**Verify**: run full test suite, all green.

### Step B4 — Docs placement + index update

- Move this design doc to `docs/computer-config/spec/`
- Generate `docs/computer-config/{prd,impl-plan,test-plan}/`
- Update `docs/INDEX.md`

**Verify**: INDEX.md contains all computer-config initiative entries.

---

## 4. Dependencies & Order

```
A1 → A2 → A3 → A4 → A5
B1 → B2 → B3 → B4
A and B run in parallel
```

---

## 5. Risks & Rollback

| Risk | Mitigation |
|------|------------|
| settings.json corruption | atomic write + .bak |
| .tmux.conf pollution | backup + idempotent marker |
| test breakage | run full test baseline before strip |

Rollback: `uninstall.sh` (claude-tmux-config) + `git revert` (walter-worker).
