#!/usr/bin/env bats

# on-session-start.sh — the SessionStart hook: registers the session and checks
# that the session's project folder has its own initiative.

setup() {
  TEST_TMP="$(mktemp -d)"
  export HOME="$TEST_TMP/home"
  mkdir -p "$HOME"
  # A parent folder's initiative must not count for a child project.
  printf '<!-- INITIATIVE:parent-initiative START -->\n' > "$HOME/CLAUDE.local.md"
  PROJ="$HOME/project/demo"
  mkdir -p "$PROJ"
  HOOK="$(cd "$(dirname "$BATS_TEST_DIRNAME")/.." && pwd)/src/coworker/analytics/hooks/on-session-start.sh"
}

teardown() {
  rm -rf "$TEST_TMP"
}

_run_hook() {
  run bash -c "printf '{\"session_id\":\"sess1\",\"cwd\":\"%s\",\"source\":\"startup\"}' '$1' | bash '$HOOK'"
}

_context() {
  echo "$output" | python3 -c "import sys,json; print(json.load(sys.stdin)['hookSpecificOutput']['additionalContext'])"
}

@test "registers the session" {
  _run_hook "$PROJ"
  [ "$status" -eq 0 ]
  [ -f "$HOME/.coworker/analytics/sessions/sess1/session.yaml" ]
}

@test "asks for an initiative when the folder has no CLAUDE.local.md" {
  _run_hook "$PROJ"
  ctx="$(_context)"
  [[ "$ctx" == *"Session sess1"* ]]
  [[ "$ctx" == *"has no initiative"* ]]
  [[ "$ctx" == *"coworker feature start <name> -p $PROJ"* ]]
  [[ "$ctx" != *"Initiative: parent-initiative"* ]]
}

@test "asks when CLAUDE.local.md has no marker" {
  echo "# notes" > "$PROJ/CLAUDE.local.md"
  _run_hook "$PROJ"
  [[ "$(_context)" == *"has no initiative"* ]]
}

@test "reports the FEATURE marker" {
  printf '<!-- FEATURE:demo-feature START -->\n' > "$PROJ/CLAUDE.local.md"
  _run_hook "$PROJ"
  [[ "$(_context)" == *"Initiative: demo-feature"* ]]
}

@test "reports the legacy INITIATIVE marker" {
  printf '<!-- INITIATIVE:old-one START -->\n' > "$PROJ/CLAUDE.local.md"
  _run_hook "$PROJ"
  [[ "$(_context)" == *"Initiative: old-one"* ]]
}

@test "reads the git root from a subfolder" {
  git -C "$PROJ" init -q
  printf '<!-- FEATURE:demo-feature START -->\n' > "$PROJ/CLAUDE.local.md"
  mkdir -p "$PROJ/sub/dir"
  _run_hook "$PROJ/sub/dir"
  [[ "$(_context)" == *"Initiative: demo-feature"* ]]
}
