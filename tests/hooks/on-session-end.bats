#!/usr/bin/env bats

# on-session-end.sh — the SessionEnd hook: one summary per session.

setup() {
  TEST_TMP="$(mktemp -d)"
  export HOME="$TEST_TMP/home"
  mkdir -p "$HOME" "$TEST_TMP/bin"
  # The mock records each call with what it read on stdin.
  cat > "$TEST_TMP/bin/coworker" <<MOCK
#!/usr/bin/env bash
sleep \${MOCK_SLEEP:-0}
echo "\$* \$(cat)" >> "$TEST_TMP/calls"
MOCK
  chmod +x "$TEST_TMP/bin/coworker"
  export PATH="$TEST_TMP/bin:$PATH"
  HOOK="$(cd "$(dirname "$BATS_TEST_DIRNAME")/.." && pwd)/src/coworker/analytics/hooks/on-session-end.sh"
}

teardown() {
  rm -rf "$TEST_TMP"
}

_wait_calls() {
  for _ in $(seq 50); do
    [[ -f "$TEST_TMP/calls" ]] && [[ $(wc -l < "$TEST_TMP/calls") -ge $1 ]] && return 0
    sleep 0.1
  done
  return 1
}

@test "runs capture with the payload, then close" {
  run bash -c "echo '{\"session_id\":\"s1\"}' | bash '$HOOK'"
  [ "$status" -eq 0 ]
  _wait_calls 2
  run cat "$TEST_TMP/calls"
  [ "${lines[0]}" = 'memory capture {"session_id":"s1"}' ]
  [[ "${lines[1]}" == "memory close"* ]]
}

# Claude Code gives SessionEnd hooks 1.5 s and the summary takes 15-20 s, so the
# hook must return at once and leave the work running.
@test "returns before the summary finishes" {
  export MOCK_SLEEP=3
  start=$(date +%s)
  run bash -c "echo '{}' | bash '$HOOK'"
  [ "$status" -eq 0 ]
  [ $(( $(date +%s) - start )) -lt 2 ]
  [ ! -f "$TEST_TMP/calls" ]
}

@test "leaves no payload file behind" {
  export TMPDIR="$TEST_TMP/tmp"
  mkdir -p "$TMPDIR"
  run bash -c "echo '{}' | bash '$HOOK'"
  _wait_calls 2
  sleep 0.2
  [ -z "$(ls "$TMPDIR")" ]
}
