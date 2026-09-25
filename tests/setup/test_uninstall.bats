#!/usr/bin/env bats

# Tests for uninstall.sh — manifest-driven removal.
#
# ~/.coworker is recorded as an owned dir, but it also holds data the script
# promises to keep, so the removal has to be selective rather than a rmtree of
# the whole directory.

setup() {
  TEST_TMP="$(mktemp -d)"
  export HOME="$TEST_TMP/home"
  mkdir -p "$HOME/.claude"
  mkdir -p "$HOME/.coworker/backups/pristine"
  mkdir -p "$HOME/.coworker/analytics"
  mkdir -p "$HOME/.coworker/scripts"

  # Data the closing message promises to preserve
  echo 'fake-db' > "$HOME/.coworker/analytics/analytics.db"
  echo '{"pristine":true}' > "$HOME/.coworker/backups/pristine/settings.json"
  echo '# pristine claude md' > "$HOME/.coworker/backups/pristine/CLAUDE.md"

  # Files install.sh would have created
  echo 'x' > "$HOME/.coworker/scripts/thing.sh"
  echo '{"user":"edited-after-install"}' > "$HOME/.claude/settings.json"

  python3 -c "
import json, os
json.dump({'files': [], 'hook_commands': [], 'owned_dirs': [os.path.expanduser('~/.coworker')]},
          open(os.path.expanduser('~/.coworker/install-manifest.json'), 'w'))
"

  export REPO_ROOT
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_DIRNAME")/.." && pwd)"
}

teardown() {
  rm -rf "$TEST_TMP"
}

@test "preserves analytics data it claims to preserve" {
  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]

  # The closing banner says analytics is "preserved — delete manually".
  [ -f "$HOME/.coworker/analytics/analytics.db" ]
}

@test "removes files install.sh created" {
  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]

  [ ! -f "$HOME/.coworker/scripts/thing.sh" ]
  [ ! -f "$HOME/.coworker/install-manifest.json" ]
}

@test "restore-pristine can read its own backup" {
  # The backup lives under an owned dir; removing the directory whole deleted
  # it before the restore ran, so this option could never succeed.
  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh' --restore-pristine"
  [ "$status" -eq 0 ]

  [ -f "$HOME/.coworker/backups/pristine/settings.json" ]
  run cat "$HOME/.claude/settings.json"
  [[ "$output" == *pristine* ]]
  [ "$output" != *"edited-after-install"* ]
}

@test "aborts without confirmation" {
  run bash -c "echo n | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]

  [ -f "$HOME/.coworker/analytics/analytics.db" ]
  [ -f "$HOME/.coworker/scripts/thing.sh" ]
}

@test "install saves a pristine snapshot that uninstall can restore" {
  # Start from a pre-existing setup and no snapshot, the state a first install
  # sees. The snapshot has to be taken before install.sh mutates either file.
  rm -rf "$HOME/.coworker/backups/pristine"
  rm -f "$HOME/.coworker/install-manifest.json"
  echo '{"pre":"existing"}' > "$HOME/.claude/settings.json"
  echo '# pre-existing claude md' > "$HOME/.claude/CLAUDE.md"

  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  [ -f "$HOME/.coworker/backups/pristine/settings.json" ]
  [ -f "$HOME/.coworker/backups/pristine/CLAUDE.md" ]
  run cat "$HOME/.coworker/backups/pristine/settings.json"
  [[ "$output" == *'"pre":"existing"'* ]]

  # install.sh added hooks to settings.json; the restore must undo that.
  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh' --restore-pristine"
  [ "$status" -eq 0 ]

  run cat "$HOME/.claude/settings.json"
  [[ "$output" == *'"pre":"existing"'* ]]
  [[ "$output" != *hooks* ]]
  run cat "$HOME/.claude/CLAUDE.md"
  [[ "$output" == *"pre-existing claude md"* ]]
}
