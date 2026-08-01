# computer-config — Test Plan

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-08-01 | 0.1.0 | Initial draft |
| 2026-08-01 | 0.2.0 | Post devil-advocate review: add TU-5 (model=pro), TI-4a (hex fallback), TI-7a (missing manifest), TI-9 (atomic write); update TI-3/4 to marker-based detection |
| 2026-08-01 | 0.3.0 | Post GLM-5.2 review (scope-corrected): TU-5 → port-as-is (statusline unchanged, model field untouched); add TI-4b (legacy grey-theme migration), TR-6 (ai-coworker manifest exclusion); TI-7 → rm -rf + statusLine pop; TR-2 → preserve rich version as optional; fix 0/1/2 → 0/1/2/3 in §6 |
| 2026-08-01 | 0.4.0 | Add §7 Verification: 4-layer verification (auto/smoke/rollback/coworker-regression), byte-diff for fixed input + human-reported feature checklist for live display, verify.sh modes, S1-S7 / T1-T6 feature checklist, success criteria |

---

## 1. Test Strategy

Covers two workstreams: the claude-tmux-config project (A) and the ai-coworker
strip (B).

Three test layers:
1. **Unit tests** — script logic, parameterization, idempotency logic
2. **Integration tests** — install.sh/uninstall.sh end-to-end (isolated with temp HOME)
3. **Regression tests** — ai-coworker existing test suite stays green

---

## 2. Test Environment

- Temp HOME (`mktemp -d`) isolation, avoiding real-environment pollution
- Mock skill-factory (local fake, no network)
- Assert file states of settings.json / .tmux.conf

---

## 3. Test Cases

### 3.1 claude-tmux-config unit tests

| ID | Case | Expected |
|----|------|----------|
| TU-1 | statusline-command.sh path parameterization | 3 hardcoded paths → `$HOME/.claude/statusline/` |
| TU-2 | statusline-command.sh dependency check | warns (not crashes) when jq/bc/python3 missing |
| TU-3 | status_info.sh simple version | correctly outputs current folder path |
| TU-4 | benjamin-blue.tmux extraction | contains all 6 hexes: `#102D46`, `#EAE7DD`, `#F2C94C`, `#5F8D4E`, `#8EA2AF`, `#30506B` |
| TU-5 | statusline ported unchanged (port-as-is) | `assets/statusline-command.sh` matches the live `~/.claude/statusline-command.sh` except the 3 parameterized paths (§3.11); `settings.json` `model` field is NOT touched by install |

### 3.2 claude-tmux-config integration tests

| ID | Case | Expected |
|----|------|----------|
| TI-1 | install component 1 (y) | `~/.claude/statusline/` two files in place; settings.json statusLine.command points to new path |
| TI-2 | install component 1 (n) | nothing deployed, settings.json unchanged |
| TI-3 | install component 2 (y, no marker, no inline hex) | `~/.tmux/conf.d/benjamin-blue.tmux` in place; `.tmux.conf` has source line + marker `# claude-tmux-config theme` |
| TI-4 | install component 2 (y, marker exists) | only status_info.sh deployed, no duplicate source |
| TI-4a | install component 2 (y, no marker but inline hex present) | only status_info.sh deployed, no duplicate source (hex fallback) |
| TI-4b | install component 2 (y, legacy `# ai-coworker status bar` present) | prompts "Replace grey theme? [y/N]"; on `y` old block stripped + full BB theme deployed; on `n` only status_info.sh deployed |
| TI-5 | install idempotent (repeated run) | no duplicate appends, no side effects |
| TI-6 | install component 2 backup | `.tmux.conf.bak` exists |
| TI-7 | uninstall | statusLine popped from settings.json (atomic write), `~/.claude/statusline/` rm -rf (incl. runtime cache files), source line stripped |
| TI-7a | uninstall with missing manifest | refuses to run, logs warning, lists files to remove manually |
| TI-8 | missing-dependency scenario | component 1 `command -v` check warns before install |
| TI-9 | settings.json write is atomic | simulated mid-write crash leaves `.bak` intact, original not truncated |

### 3.3 ai-coworker strip regression tests

| ID | Case | Expected |
|----|------|----------|
| TR-1 | install.sh has no tmux reference | `grep tmux setup/install.sh` shows no deploy logic |
| TR-2 | setup/status_info.sh removed from ai-coworker | file gone from ai-coworker; rich version preserved as `claude-tmux-config/assets/status_info-rich.sh` (optional) |
| TR-3 | core tests all green | existing pytest + bats pass |
| TR-4 | analytics hooks intact | all 4 hook events still configured |
| TR-5 | permissions/skills/MCP preserved | settings.json still contains these after coworker sync |
| TR-6 | ai-coworker manifest excludes statusline | `~/.coworker/install-manifest.json` has NO entries under `~/.claude/statusline/` after coworker install |

---

## 4. Test Commands

```bash
# claude-tmux-config (if a test framework exists)
cd ~/project/claude-tmux-config && bash tests/run.sh

# ai-coworker full suite
cd ~/project/ai-coworker && python -m pytest
# bats install tests
cd ~/project/ai-coworker && bats tests/setup/*.bats
```

---

## 5. Coverage Matrix

| Requirement | Test |
|-------------|------|
| FR-1 repo creation | prerequisite of TI-1 |
| FR-2/3 statusline adoption | TU-1, TI-1 |
| FR-4 status_info adoption | TU-3, TI-4 |
| FR-5 theme extraction | TU-4 |
| FR-6 confirmation mechanism | TI-2, TI-5 |
| FR-7 statusLine write | TI-1 |
| FR-8 tmux deploy idempotent | TI-3/4/4a/4b/5/6 |
| FR-9 uninstall | TI-7, TI-7a |
| FR-10/11 ai-coworker strip | TR-1/2/3/4/5 |
| FR-12 legacy grey-theme migration | TI-4b |
| FR-13 ai-coworker manifest exclusion | TR-6 |
| port-as-is (statusline unchanged; model field untouched) | TU-5 |
| atomic settings.json write (review C3) | TI-9 |

---

## 6. Acceptance

After all tests pass, manual acceptance:
1. Run `install.sh` in the real environment, observe 0/1/2/3 menu + confirm prompts
2. Open Claude Code, confirm the 4-line statusline renders
3. Open tmux, run `tmux source-file ~/.tmux.conf`, confirm the Benjamin Blue theme
4. Run `uninstall.sh`, confirm clean removal (statusLine gone, dirs removed)
5. Confirm ai-coworker install no longer touches tmux
6. (Existing ai-coworker user) confirm grey-theme → Benjamin Blue migration prompt appears

---

## 7. Verification — How to confirm it actually worked

> This section defines the **verification deliverable**: how to confirm the
> migration succeeded on a real machine, beyond the automated tests above.
> Core principle: **fixed input → byte diff** (deterministic, immune to live
> data changes); **live display → human-reported feature checklist** (the user
> pastes terminal text, the reviewer checks ANSI-encoded features).

### 7.1 Four verification layers

| Layer | Name | Executor | How it verifies |
|-------|------|----------|-----------------|
| L1 | Automation | `verify.sh auto` (unattended) | temp HOME + byte diff + idempotency + uninstall |
| L2 | Real-machine smoke | user pastes terminal text → reviewer checks | feature checklist + ANSI inspection |
| L3 | Rollback | `verify.sh rollback` (unattended) | install → verify → uninstall → verify → reinstall → verify |
| L4 | ai-coworker regression | `pytest` + `bats` | full suite green |

### 7.2 Verification deliverables (in claude-tmux-config repo)

```
claude-tmux-config/
└── verify/
    ├── fixtures/sample-status.json      # fixed stdin input → deterministic statusline output
    ├── expected/statusline-golden.txt   # captured BEFORE install: script output for the fixture
    ├── expected/tmux-status-golden.txt  # tmux status bar output
    ├── expected/feature-checklist.md    # human-readable expected-feature table (shared with user)
    └── verify.sh                        # modes: auto | smoke | rollback
```

### 7.3 verify.sh modes

```
verify.sh auto       # L1: temp HOME + byte diff + idempotent + uninstall
verify.sh smoke      # L2: real-machine render → prints "paste terminal text" prompt → reviewer checks
verify.sh rollback   # L3: install → verify → uninstall → verify → reinstall → verify
```

### 7.4 Boundary (what goes in the repo vs. what's collaborative)

**In the repo** (executable/mechanical):
1. `fixtures/sample-status.json` — fixed input for deterministic rendering.
2. `verify.sh auto` — byte-diffs the deployed script's output against the golden
   (verifies script renders correctly, not just that files exist).
3. `expected/feature-checklist.md` — the shared expectation table (for BOTH the
   user to read and the reviewer to check against pasted text).

**NOT in the repo** (human/model collaborative): the ANSI feature-checking on
pasted live text. When the user pastes their Claude Code / tmux terminal text,
the reviewer (Claude) inspects the ANSI escape sequences against the checklist.
This is not automated code — it's a live review step.

### 7.5 Judgment rules

```
Fixed input  → byte diff      (stable; immune to cost/model/turns changing)
Live display → user pastes text → reviewer runs feature checks on the ANSI
   all pass → PASS ✅ (print per-feature detail)
   any fail → report the specific feature + likely cause + fix command
```

### 7.6 Feature checklist (what the reviewer checks on pasted text)

**Claude Code statusline** (bottom 4 lines):

| ID | Feature | Check |
|----|---------|-------|
| S1 | 4 lines present | line count = 4 |
| S2 | `project` label green | `\x1b[38;5;71m` in the 📁 label |
| S3 | context bar blue blocks + pct | `ctx:` followed by block chars + `NN%` |
| S4 | cost color by threshold | green <$1 / yellow $1-3 / red >$3 |
| S5 | `branch` label green | `\x1b[38;5;71m` in the 🌿 label |
| S6 | add/del red-green | `+N` green, `-M` red |
| S7 | path line | line 4 starts with 📂 |

**tmux status bar**:

| ID | Feature | Check |
|----|---------|-------|
| T1 | deep-ocean bg | `status-style bg=#102D46` (from `tmux show`) |
| T2 | left = session name (yellow) + green dot | status-left content |
| T3 | right = 📂 + folder path | status-right references `status_info.sh` |
| T4 | current window yellow-bg | window-status-current `fg=#102D46,bg=#F2C94C` |
| T5 | active pane border yellow | pane-active-border `fg=#F2C94C` |
| T6 | claude-tmux binding | `bind C-c` exists |

### 7.7 Rollback verification (L3)

```
verify.sh rollback
  1. install → 2. run all feature checks → 3. uninstall
  4. confirm files gone → 5. reinstall → 6. re-run feature checks
  all pass → rollback is safe (can be re-applied cleanly)
```

### 7.8 Success criteria (end-to-end)

1. `verify.sh auto` → PASS on a temp HOME (L1).
2. User runs `install.sh` on the real machine; pastes Claude Code + tmux terminal
   text → reviewer runs the S1-S7 / T1-T6 checks → all PASS (L2).
3. `verify.sh rollback` → PASS (L3).
4. ai-coworker `pytest` + `bats` → green, and `install-manifest.json` contains no
   `~/.claude/statusline/` entries (L4).
