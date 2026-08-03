# Contributing to walter-worker

## Running tests

```bash
# Python test suite
python3 -m pytest tests/ -q

# Install with test extras
pip install -e ".[test]"

# Shell tests (require bats and a temp HOME — hermetic)
bats tests/setup/*.bats
```

## Rules

1. **One PR per fix.** Reference the problem ID in the commit body, e.g. `fix(P3): fence-aware section parser`.
2. **Every fix ships with a test that fails before the fix and passes after.** No exceptions. If you cannot write the test, stop and ask.
3. **Never mutate a user file without a backup.** Every code path that writes to `~/.claude/*`, `CLAUDE.md`, `CLAUDE.local.md`, or `settings.json` must call `backup.snapshot()` first (see `src/coworker/backup.py`).
4. **Never report success you did not verify.** If a step fails, exit non-zero and say so. No `except Exception: pass`, no `2>/dev/null` on operations we depend on.
5. **Deletions announce themselves.** Any code path that removes user-visible content must print what it removed and where the backup is.
6. **Work in phase order.** Later phases depend on earlier ones (backup/CI are the safety net for the dangerous merge-engine work).
7. **Tests must be hermetic.** Run against a temp `HOME` (see `tests/conftest.py`); never read the developer's real `~/.claude` or `~/.coworker`.
8. **Follow the guardrails in `CLAUDE.md`** — Conventional Commits, parameterized SQL, no hardcoded secrets, never edit `<!-- PROTECTED -->` blocks.
