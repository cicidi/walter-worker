# Adversarial Review Report — computer-config-spec.md

- **Date**: 2026-08-01
- **Document under review**: `docs/computer-config/spec/computer-config-spec.md`
- **Review method**: devil-advocate 3-agent debate (con/pro/judge), 1 round + manual verification
- **Result**: 9 rulings — **8 con-wins, 1 pro-wins, 0 deferred**

---

## 1. Consensus Findings

### 🔴 Critical (must fix before implementation)

| # | Finding | Evidence | Status |
|---|---------|----------|--------|
| C1 | **Model ID contradiction**: settings.json `model` hex-decodes to `DeepSeek/deepseek-v4-flash`, but 3 env vars (`ANTHROPIC_MODEL` / `CCR_CLAUDE_CODE_MODEL` / `CODEXL_CLAUDE_CODE_MODEL`) all say `deepseek-v4-pro` | `bytes.fromhex('44656570...')` → `DeepSeek/deepseek-v4-flash`; env vars say pro | ✅ **INDEPENDENTLY VERIFIED** |
| C2 | Cost-savings claim (~17x) may be wrong: if actual model is flash ($0.28/M output), savings are ~53x | Spec section 3.5 uses dspro rate 0.87; model ID says flash | Depends on C1 |
| C3 | **Atomic writes name-dropped** (`_write_json_atomic` 3×) with zero mechanism defined; `json.dump()` is non-atomic | Spec 6.3/6.4/8; impl-plan A3.3 says "inline python merge" | Confirmed |
| C4 | **Manifest format unspecified** (word 8×, zero schema); cross-project conflict: walter-worker install.sh recursively walks `~/.claude/`, would claim claude-tmux-config files | Spec 6.3/6.4; walter-worker install.sh Step 16-second walks `~/.claude/` | Confirmed |
| C5 | **Inline Benjamin Blue detection algorithm undefined** — "detected" is a wish, not a spec; 4 possible strategies produce different behavior | Spec 6.2; test TI-4 | Confirmed |

### 🟡 Minor (factual errors — fix in spec)

| # | Finding | Actual | Spec says |
|---|---------|--------|-----------|
| C6 | .tmux.conf line count | 36 | 34 |
| C7 | settings.json top-level keys | 10 | 11 |
| C8 | enabledPlugins count | 13 (12 enabled + 1 disabled) | 12 |

### 🟡 Design contradiction

| # | Finding | Detail |
|---|---------|--------|
| C9 | 0/1/2 single-choice menu contradicts PRD US-4 "one-click install of full statusline+theme" | Installing both requires 2 runs of install.sh; fix: add option "3) Both" or multi-select |

---

## 2. Pro-Wins (validated, no change needed)

| Claim | Reason |
|-------|--------|
| DeepSeek 1M context window, 5x Claude's 200k | Math correct (5.24x); matches live statusline-command.sh context-detection code |

---

## 3. Unresolved Items

| # | Item | Impact if ignored |
|---|------|-------------------|
| U1 | Which model actually routes through CCR — flash or pro? | Cost/context/performance claims all unverifiable; statusline cost display wrong (flash @$0.28 vs pro @$0.87 in rate table) |
| U2 | Cross-project manifest conflict | walter-worker uninstall could delete claude-tmux-config deployed assets in `~/.claude/statusline/` |
| U3 | Impl-plan Step B1 "remove tmux tracking from manifest" — phantom task? | Current manifest does not track tmux; may be describing intent not existing code |
| U4 | Statusline behavior when CCR is down | compute_real_cost depends on CCR classifying tokens during session |
| U5 | Test gaps: rollback, missing deps at runtime, non-BB colors, concurrent installs | Real failure modes untested |

---

## 4. Recommendations

1. **Resolve C1/U1 first**: determine the actual routing model (flash vs pro). Check CCR config, running session transcript, or `claude` CLI. If flash, update spec cost table + env vars to be consistent, and fix statusline `compute_real_cost` rate selection.
2. **Define atomic write mechanism**: specify temp-file + `fsync` + `os.rename` in the spec; reference walter-worker's existing `_write_json_atomic` in `src/coworker/adapters/claude.py` (it already implements this correctly — cite it).
3. **Define manifest schema**: fields (install_mode, files, owned_dirs, hook_commands), creation logic, corruption handling. Address cross-project coexistence: claude-tmux-config manifest must NOT recursively claim `~/.claude/`; scope to `~/.claude/statusline/` only.
4. **Define inline-color detection algorithm**: e.g., grep for marker comment `# claude-tmux-config theme` added by install (reliable, idempotent), rather than hex-matching which false-positives.
5. **Fix 0/1/2 menu**: add option "3) Both" (or multi-select) to satisfy PRD US-4.
6. **Fix factual errors** (C6/C7/C8): correct line/key/plugin counts to match live state, or explicitly note "describes target state after migration."

---

## 5. Top Risks (ranked)

1. **Model ambiguity (C1)** — wrong model in spec cascades into wrong cost numbers and potentially wrong statusline pricing
2. **Cross-project manifest conflict (C4/U2)** — data-loss risk: walter-worker uninstall deletes claude-tmux-config files
3. **Undefined atomic writes (C3)** — settings.json corruption on interrupt (real on laptop suspend/battery)
4. **Undefined inline-color detection (C5)** — .tmux.conf pollution or skipped installs, the very thing the safety gate is for
5. **Unspecified manifest (C4)** — uninstall leaves orphans or deletes wrong files

---

*Output directory: `docs/devil-advocate/2026-08-01-computer-config-spec/`*
