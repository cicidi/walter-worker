# Contrarian Gap Report — ai-coworker Phase 0+1

## Summary
- 0 gaps at Critical or High severity
- 4 Medium, 3 Low observations
- **Verdict: READY** — all Phase 0+1 items correctly implemented and verified.

## Verification method
Each item checked against the photo plan's acceptance criteria, then spot-verified in the actual code on `fix/fix-plan-round1`. Full test suite: 103 passed, 1 xfailed (pre-existing feature gap), 0 failed.

---

## Medium

| # | Item | Observation | Mitigation |
|---|------|-------------|------------|
| M1 | P7 update.sh | When git is offline, `default_branch()` falls back to `"main"` and `git fetch origin main` fails → exit 1. The error message says "Could not fetch from origin" but won't tell the user the real branch is `master`. Previously the script silently failed too (with 2>/dev/null). This is the intended "fail loud" behavior — the error message could be more descriptive. | Acceptable for Phase 1; improve error message in a follow-up. |
| M2 | H1 CI | The CI workflow references `ludeeus/action-shellcheck@master`, a third-party GitHub Action not yet validated in this repo's CI run. If it's unavailable or broken, the shellcheck job will fail on first push. | CI is a template — first push will validate. Replace with direct `shellcheck` install if the action proves unreliable. |
| M3 | P13 initiative_start | The `_project_name()` helper looks up the project catalog by `local_path`. If two catalog entries have the same `local_path`, the first match wins. The dashboard case (same repo, different entry) could produce wrong naming. | Edge case — project catalog should not have duplicate paths. Known limitation. |
| M4 | G2 reference integrity | The test only scans `setup/*.sh`, not `skills/**/SKILL.md`. Skills prose generates too many false positives. Phantom commands in skill prose will NOT be caught by the automated test — manual review needed when commands change. | Documented in the test's docstring. Acceptable trade-off; the script scan catches the high-risk sites. |

---

## Low

| # | Item | Observation | Mitigation |
|---|------|-------------|------------|
| L1 | P2 backup | `backup.snapshot()` is called on the "overwrite existing CLAUDE.md" path but not the "create new CLAUDE.md" path. This is correct (nothing to back up for a new file) but the asymmetry is worth noting: if `claude_md.write_text(new_content)` crashes mid-write on a new file, there's no rollback. | Low risk — new file creation is safe; the corrupted half-written file is obviously broken. |
| L2 | P6 bash 3.2 | The rename-detection loop uses `md5sum`, which may not exist on all platforms (e.g., some BSD variants use `md5`). The loop is guarded by `[[ ${#OLD_DIRS[@]} -gt 0 ]]` so it silently skips rename detection if no old skills exist — but if `md5sum` is missing entirely, the initial hash computation will error with `command not found` under `set -e`. | The `md5sum` dependency pre-existed the P6 fix. A separate item would replace it with a portable alternative (sha256sum, python hashlib). |
| L3 | P13 gitignore dedup | The append logic writes a `\n` separator before new entries. If the existing `.gitignore` already ends with `\n`, this creates a double newline (blank line between old content and new entries). | Cosmetic — the blank line is harmless and even improves readability. |

---

## Verified correct (all checks passed)

| Item | Check | Result |
|------|-------|--------|
| H1 | LICENSE, CONTRIBUTING, CI, pyproject license+extras, build/ removed | All present, CI YAML valid |
| F-BACKUP | backup.py snapshot/restore + 5 tests | 5/5 pass |
| H2 | Hermetic installed_home fixture, dead asserts fixed, hook schema corrected | 5/5 install tests pass, hook test uses canonical `{matcher,hooks:[...]}` shape |
| P1 | No `from src.coworker` in src/ or setup/; stats keys fixed; get_db() idempotent; smoke test | All clean; 99/99 total pass + smoke |
| P2 | .coworker/ mkdir, sentinel `"## Project Identity"` shared constant, backup.snapshot before overwrite, 3 tests | 3/3 pass |
| P6 | `declare -A` → indexed parallel arrays + empty-array guard | Code verified; installed_home fixture proves install.sh still works |
| P7 | `default_branch()` helper, verify HEAD moved, exit non-zero on failure, `origin main` → dynamic | Code verified; no residual `origin main` in setup/ |
| G2 | Phantom `import-mcp` deleted, Step 9→`skills/init/SKILL.md`, banner `analytics dashboard` | All clean; reference-integrity test passes |
| H4 | `$COWORKER_VAULT_PATH` env var, `~/.config/ai-coworker`→`~/.coworker` | No residual personal paths in setup/ or session-memory |
| P13 | 5 fixes: flask guard deleted, initiative name from catalog, `--global/--project` paired flag, `split("|",1)`, gitignore line-set dedup | Code verified; tests pass |
