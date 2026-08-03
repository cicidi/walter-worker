# GLM-5.2 Independent Review Report — computer-config-spec.md

- **Date**: 2026-08-01
- **Reviewer model**: GLM-5.2 (second opinion, after the DeepSeek devil-advocate review)
- **Method**: 4 parallel dimension reviewers (factual / consistency / feasibility / contrarian) → synthesis
- **Overall verdict**: **needs-major-rework**
- **Prior DeepSeek findings**: 7 resolved, 4 still-broken, 1 disagreement

---

## Headline finding (critical) — reframed by the main agent

The live `settings.json` `model` field hex-decodes to **`Z.AI/glm-5.2`** (not the
`deepseek-v4-flash` the spec hardcoded). Root cause: the `model` field is a
**moving target** — it is rewritten every time the user switches models via
`/model`. When first inspected it was flash; after switching to GLM-5.2 it became
glm-5.2. The env vars (`ANTHROPIC_MODEL` = `deepseek-v4-pro`) are static.

**Implication**: documenting a specific decoded value is fragile; the
"reconcile model field to pro" impl step is infeasible AND unnecessary (CCR routes
by env vars; the field just tracks the last `/model` selection). Correct fix:
remove the reconciliation step; document the mechanism, not a snapshot.

## Critical new findings (GLM-5.2)

1. **Old walter-worker grey-theme users have no migration path** — the detection
   algorithm (marker / 6-hex / fresh) doesn't recognize the `# walter-worker status bar`
   grey block; an existing walter-worker user would get Benjamin Blue appended ON TOP
   of the grey theme → polluted `.tmux.conf`.
2. **Cross-project manifest conflict is one-directional** — claude-tmux-config
   scopes its manifest, but walter-worker's install.sh does `os.walk(~/.claude/)`
   recursively and would claim `~/.claude/statusline/*` as its own; walter-worker
   uninstall could then delete them.
3. **`_write_json_atomic` not vendorable into bash** — the walter-worker version
   calls `backup.snapshot()` (an internal Python module). A bash install.sh can't
   import it. Must use stdlib `shutil.copy2` for the `.bak`.
4. **Model-field reconciliation impossible** — installer has no way to obtain the
   "pro routing ID" (CCR generates it at startup). → drop the step (see headline).
5. **New-repo vs subdirectory decision has no decision record** — (note: user
   explicitly chose a new repo; record the rationale).

## Major new findings

- Manifest scope narrative says `~/.tmux/conf.d/ ONLY` but also deploys to `~/.tmux/scripts/` (self-contradiction).
- 4 stale `0/1/2 menu` text refs: PRD FR-6, PRD §5 AC#2, spec §9 AC#2, test-plan §6 AC#1.
- Rich 90-line status_info.sh would be permanently deleted (spec said "or fold in as optional" — impl-plan just says "delete").
- U4 (statusline when CCR down) still unaddressed.
- uninstall JSON-key removal mechanism unspecified.
- ccusage missing → silent `$0.00` cost, no warning.
- Runtime cache files (turn-counter-*.json, ccusage-cache.json) orphaned under manifest-driven deletion.
- NFR-3 (<100ms) has zero test coverage.
- No `tmux source-file` reload step after install (fresh machines see no change).
- **GLM-5x pricing ($1.40/$4.40) possibly ~10x above public Zhipu rates (~$0.14/$0.55)** — needs provider confirmation.
- **Effort threshold table wrong**: spec says high=yellow; code says high=red (brick_red).
- Spec §6.3 incorrectly describes walter-worker manifest scope (omits ~/.claude/ walk).

## Minor / nit

- status_info.sh = 15 lines, spec says 13.
- Spec §2.2 model-field hex malformed (odd-length suffix, copy-paste).
- devil-advocate report not in INDEX.md.
- Test plan references `tests/run.sh` that no workstream creates.
- PRD US-4 "one-click" slightly overpromises (needs menu + y/N).

## Disagreement with DeepSeek

- U3 ("remove tmux tracking = phantom task"): GLM-5.2 says NOT phantom — walter-worker
  manifest does walk ~/.claude/ and lists statusline files; Step B1 needs to specify
  exactly what manifest logic is removed.

---

*Full per-dimension JSON in workflow task output. This report supersedes nothing —
it complements the DeepSeek report.md in the same folder.*
