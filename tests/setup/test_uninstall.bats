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

@test "manifest claims only what install.sh wrote, not everything under shared dirs" {
  # install.sh used to os.walk ~/.claude, ~/.opencode and ~/.coworker/analytics
  # and claim every file found there; uninstall.sh then removed them all —
  # plugin caches, session transcripts, other tools' skills, node_modules, and
  # the analytics database the closing banner promises to preserve.
  #
  # The files list had no coverage: setup() writes a manifest with an empty one,
  # so only the owned_dirs path was ever exercised.
  mkdir -p "$HOME/.claude/plugins/foreign-plugin" \
           "$HOME/.claude/projects/some-session/memory" \
           "$HOME/.claude/skills/foreign-tool" \
           "$HOME/.opencode/node_modules"
  echo plugin     > "$HOME/.claude/plugins/foreign-plugin/index.js"
  echo transcript > "$HOME/.claude/projects/some-session/transcript.jsonl"
  echo memory     > "$HOME/.claude/projects/some-session/memory/note.md"
  echo foreign    > "$HOME/.claude/skills/foreign-tool/SKILL.md"
  echo dep        > "$HOME/.opencode/node_modules/pkg.js"

  # Generate a real manifest, the way an actual install does.
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]

  # Written by install.sh, so it must be removed.
  [ ! -f "$HOME/.coworker/analytics/hooks/on-stop.sh" ]

  # None of these were written by install.sh, so none may be touched.
  [ -f "$HOME/.claude/plugins/foreign-plugin/index.js" ]
  [ -f "$HOME/.claude/projects/some-session/transcript.jsonl" ]
  [ -f "$HOME/.claude/projects/some-session/memory/note.md" ]
  [ -f "$HOME/.claude/skills/foreign-tool/SKILL.md" ]
  [ -f "$HOME/.opencode/node_modules/pkg.js" ]
  [ -f "$HOME/.coworker/analytics/analytics.db" ]
}

@test "refuses to remove files from a pre-schema_version manifest" {
  # Setup() writes exactly such a manifest (no schema_version). It stands in for
  # every machine that installed before the fix: the file on disk still claims
  # ~/.claude/plugins, session transcripts and the analytics database, so
  # running this script would delete them. Nothing may be removed.
  mkdir -p "$HOME/.claude/skills/foreign-tool"
  echo 'foreign' > "$HOME/.claude/skills/foreign-tool/SKILL.md"

  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]

  [ -f "$HOME/.coworker/analytics/analytics.db" ]
  [ -f "$HOME/.claude/skills/foreign-tool/SKILL.md" ]
  [[ "$output" == *"SKIPPED"* ]]
}

@test "uninstall keeps the user's own CLAUDE.md and their own hooks" {
  # install.sh deliberately declines to overwrite an existing global
  # CLAUDE.md, and it registers only its own hooks. But the manifest claimed
  # the file whenever it existed and every hook command it could find in
  # settings.json — so a plain uninstall deleted a hand-written CLAUDE.md and
  # stripped hooks the user had added themselves.
  echo '# MY PRECIOUS USER INSTRUCTIONS' > "$HOME/.claude/CLAUDE.md"
  python3 -c "
import json, os
p = os.path.expanduser('~/.claude/settings.json')
json.dump({'hooks': {'Stop': [{'matcher': '', 'hooks': [
    {'type': 'command', 'command': 'echo MY-OWN-HOOK'}]}]}}, open(p, 'w'))
"

  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]

  # The user's CLAUDE.md is theirs; install never wrote it.
  [ -f "$HOME/.claude/CLAUDE.md" ]
  run grep -c "MY PRECIOUS" "$HOME/.claude/CLAUDE.md"
  [ "$output" = "1" ]

  # Their hook survives too.
  run python3 -c "
import json, os
cfg = json.load(open(os.path.expanduser('~/.claude/settings.json')))
cmds = [h.get('command') for g in cfg.get('hooks', {}).get('Stop', [])
        for h in (g.get('hooks') or [])]
print('kept' if 'echo MY-OWN-HOOK' in cmds else 'GONE')
"
  [ "$output" = "kept" ]
}
