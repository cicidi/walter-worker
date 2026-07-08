#!/usr/bin/env bash
# Polish-loop tester (deterministic gate). Exit 0 => tests pass, commit allowed.
# Usage: polish-loop-qa.sh <worktree-dir> [pytest-target]
set -euo pipefail

WT="${1:?usage: polish-loop-qa.sh <worktree-dir> [pytest-target]}"
TARGET="${2:-tests}"

cd "$WT"

echo "[qa] worktree=$WT target=$TARGET"
echo "[qa] git status --short:"
git status --short

# 1) full suite (or targeted subset)
echo "[qa] running pytest..."
python3 -m pytest "$TARGET" -q
pytest_rc=$?
# (set -e would exit on failure already, but be explicit)
if [ "$pytest_rc" -ne 0 ]; then
  echo "[qa] FAIL pytest rc=$pytest_rc" >&2
  exit "$pytest_rc"
fi

# 2) guardrail checks on the diff vs base
BASE="fix/fix-plan-round1"
echo "[qa] diff stat vs $BASE:"
git diff --stat "$BASE...HEAD" || true

# 2a) no PROTECTED block MODIFICATIONS (only flag removals of marker lines;
#     new files legitimately add PROTECTED blocks, which show as '+' additions)
if git diff "$BASE...HEAD" -- '*.md' | grep -E '^-.*PROTECTED:' ; then
  echo "[qa] FAIL: diff removes/modifies a PROTECTED block marker" >&2
  exit 2
fi

# 2b) no obvious secret leakage in added lines
if git diff "$BASE...HEAD" | grep -E '^\+' | grep -iE '(sk-[a-z0-9]{20,}|api_?key\s*=\s*["'\''][^"'\'']{8,}|password\s*=\s*["'\''])' ; then
  echo "[qa] FAIL: possible secret in diff" >&2
  exit 3
fi

echo "[qa] OK — all gates passed"
