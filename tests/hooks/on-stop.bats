#!/usr/bin/env bats

# on-stop.sh — the Stop hook, run at the end of every session.

setup() {
  TEST_TMP="$(mktemp -d)"
  export HOME="$TEST_TMP/home"
  SESS="$HOME/.coworker/analytics/sessions/sess1"
  mkdir -p "$SESS"
  cat > "$SESS/session.yaml" <<'YAML'
session_id: "sess1"
created: "2026-09-25T10:00:00+0000"
closed: "2026-09-25T10:00:00+0000"
ide: "claude-code"
YAML

  # Mock coworker so the curator call is a no-op.
  mkdir -p "$TEST_TMP/bin"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$TEST_TMP/bin/coworker"
  chmod +x "$TEST_TMP/bin/coworker"
  export PATH="$TEST_TMP/bin:$PATH"

  HOOK="$(cd "$(dirname "$BATS_TEST_DIRNAME")/.." && pwd)/src/coworker/analytics/hooks/on-stop.sh"
}

teardown() {
  rm -rf "$TEST_TMP"
}

# BSD sed, which macOS ships, requires a suffix after -i. `sed -i "s/…/" file`
# makes it read the script as the backup suffix and fail. The hooks set no -e,
# so that failure is silent: the session never gets its closed: stamp and
# every duration derived from it is wrong.
_bsd_sed_shim() {
  mkdir -p "$TEST_TMP/bsd"
  cat > "$TEST_TMP/bsd/sed" <<'SEDEOF'
#!/usr/bin/env bash
for arg in "$@"; do
  if [[ "$arg" == "-i" ]]; then
    echo "sed: -i: invalid option -- BSD sed requires a suffix" >&2
    exit 1
  fi
done
exec /usr/bin/sed "$@"
SEDEOF
  chmod +x "$TEST_TMP/bsd/sed"
  export PATH="$TEST_TMP/bsd:$PATH"
}

@test "refreshes the closed: stamp where sed requires a suffix" {
  _bsd_sed_shim

  run bash -c "echo '{\"session_id\":\"sess1\"}' | bash '$HOOK'"
  [ "$status" -eq 0 ]

  run grep '^closed:' "$SESS/session.yaml"
  [[ "$output" != *"2026-09-25T10:00:00+0000"* ]]
}

@test "leaves no backup file behind" {
  _bsd_sed_shim

  run bash -c "echo '{\"session_id\":\"sess1\"}' | bash '$HOOK'"
  [ "$status" -eq 0 ]

  run bash -c "ls '$SESS'"
  [[ "$output" != *".bak"* ]]
}

@test "still appends closed: when the session has none" {
  _bsd_sed_shim
  grep -v '^closed:' "$SESS/session.yaml" > "$SESS/tmp" && mv "$SESS/tmp" "$SESS/session.yaml"

  run bash -c "echo '{\"session_id\":\"sess1\"}' | bash '$HOOK'"
  [ "$status" -eq 0 ]

  run grep -c '^closed:' "$SESS/session.yaml"
  [ "$output" -eq 1 ]
}

@test "stays quiet when the session has no message files" {
  # `wc -l < missing 2>/dev/null` does not suppress anything: the shell opens
  # the file for the redirection before wc runs, so the "No such file" comes
  # from bash and goes to stderr regardless. Every session without messages or
  # tools printed two of them.
  run bash -c "echo '{\"session_id\":\"sess1\"}' | bash '$HOOK'"

  [ "$status" -eq 0 ]
  [[ "$output" != *"No such file"* ]]
}
