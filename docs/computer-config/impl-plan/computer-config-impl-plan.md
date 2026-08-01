# computer-config — Implementation Plan (Impl Plan)

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-08-01 | 0.1.0 | Initial draft |
| 2026-08-01 | 0.2.0 | Post devil-advocate review: menu → 0/1/2/3 (one-click both); component 1 adds settings.json model-field reconciliation to pro; component 2 uses marker-based inline-color detection; A4 manifest defined + missing-manifest handling |

---

## 1. Overview

This plan runs two parallel workstreams:
- **Workstream A**: create the claude-tmux-config standalone project
- **Workstream B**: strip the presentation layer out of ai-coworker

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
3. inline python merge `statusLine` into settings.json, using the vendored
   `_write_json_atomic` pattern (temp + fsync + rename + `.bak`) — NOT plain
   `json.dump` (non-atomic)
4. **Reconcile `settings.json` `model` field**: currently hex-encodes
   `deepseek-v4-flash` while env vars say `deepseek-v4-pro`. Update to the pro
   routing ID so a future sync cannot switch the model to flash.

Component 2 (per spec §6.2 detection algorithm):
1. If `.tmux.conf` contains marker `# claude-tmux-config theme` OR any of the 6
   Benjamin Blue hexes → deploy only `status_info.sh`, do NOT append `source`
2. Else (fresh) → deploy `benjamin-blue.tmux` → `~/.tmux/conf.d/`, append
   `source` line + marker comment
3. Backup `.tmux.conf.bak` before mutation

**Verify**: run `install.sh`, confirm each item; check deployed files + settings.json
(statusLine present, model field = pro).

### Step A4 — uninstall.sh

Manifest-driven (manifest at `~/.coworker/statusline-manifest.json`, per spec
§6.3): remove statusLine, delete `~/.claude/statusline/` and
`~/.tmux/conf.d/`, restore `.tmux.conf` source line (strip the line containing
the marker `# claude-tmux-config theme`).

- If manifest missing → refuse to run, log warning, list files to remove manually.
- If manifest partial → remove only listed files, report the rest as manual.

**Verify**: run uninstall, confirm all traces removed (statusLine gone, dirs
deleted, source line stripped).

### Step A5 — README + docs/claude-tmux.md

README: purpose, install, uninstall, screenshots.
docs/claude-tmux.md: claude-tmux binding docs (no binary auto-install).

**Verify**: docs cover install/uninstall/dependencies/FAQ.

---

## 3. Workstream B: ai-coworker strip

### Step B1 — Remove install.sh Step 16

Remove Step 16 (tmux status bar deploy, ~lines 476-506) and the tmux tracking
from the manifest in `setup/install.sh`.

**Verify**: `grep -n "status_info\|tmux" setup/install.sh` has no residual
deploy logic.

### Step B2 — Delete setup/status_info.sh

Delete `setup/status_info.sh` (rich version).

**Verify**: file gone, no references.

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

Rollback: `uninstall.sh` (claude-tmux-config) + `git revert` (ai-coworker).
