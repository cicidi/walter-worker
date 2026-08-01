# computer-config — Test Plan

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-08-01 | 0.1.0 | Initial draft |
| 2026-08-01 | 0.2.0 | Post devil-advocate review: add TU-5 (model=pro), TI-4a (hex fallback), TI-7a (missing manifest), TI-9 (atomic write); update TI-3/4 to marker-based detection |

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
| TU-5 | settings.json model field = pro | after install, `model` field no longer hex-encodes `deepseek-v4-flash`; matches `env.ANTHROPIC_MODEL` = `DeepSeek/deepseek-v4-pro` |

### 3.2 claude-tmux-config integration tests

| ID | Case | Expected |
|----|------|----------|
| TI-1 | install component 1 (y) | `~/.claude/statusline/` two files in place; settings.json statusLine.command points to new path |
| TI-2 | install component 1 (n) | nothing deployed, settings.json unchanged |
| TI-3 | install component 2 (y, no marker, no inline hex) | `~/.tmux/conf.d/benjamin-blue.tmux` in place; `.tmux.conf` has source line + marker `# claude-tmux-config theme` |
| TI-4 | install component 2 (y, marker exists) | only status_info.sh deployed, no duplicate source |
| TI-4a | install component 2 (y, no marker but inline hex present) | only status_info.sh deployed, no duplicate source (hex fallback) |
| TI-5 | install idempotent (repeated run) | no duplicate appends, no side effects |
| TI-6 | install component 2 backup | `.tmux.conf.bak` exists |
| TI-7 | uninstall | statusLine removed, `~/.claude/statusline/` deleted, source line stripped |
| TI-7a | uninstall with missing manifest | refuses to run, logs warning, lists files to remove manually |
| TI-8 | missing-dependency scenario | component 1 `command -v` check warns before install |
| TI-9 | settings.json write is atomic | simulated mid-write crash leaves `.bak` intact, original not truncated |

### 3.3 ai-coworker strip regression tests

| ID | Case | Expected |
|----|------|----------|
| TR-1 | install.sh has no tmux reference | `grep tmux setup/install.sh` shows no deploy logic |
| TR-2 | setup/status_info.sh deleted | file does not exist |
| TR-3 | core tests all green | existing pytest + bats pass |
| TR-4 | analytics hooks intact | all 4 hook events still configured |
| TR-5 | permissions/skills/MCP preserved | settings.json still contains these after coworker sync |

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
| FR-8 tmux deploy idempotent | TI-3/4/4a/5/6 |
| FR-9 uninstall | TI-7, TI-7a |
| FR-10/11 ai-coworker strip | TR-1/2/3/4/5 |
| model field = pro (review C1) | TU-5 |
| atomic settings.json write (review C3) | TI-9 |

---

## 6. Acceptance

After all tests pass, manual acceptance:
1. Run `install.sh` in the real environment, observe 0/1/2 menu + confirm prompts
2. Open Claude Code, confirm the 4-line statusline renders
3. Open tmux, confirm the Benjamin Blue theme
4. Run `uninstall.sh`, confirm clean removal
5. Confirm ai-coworker install no longer touches tmux
