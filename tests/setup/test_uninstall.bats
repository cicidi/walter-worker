#!/usr/bin/env bats

# Tests for uninstall.sh — manifest-driven removal.
#
# ~/.coworker holds data the script must keep: the analytics database, the
# backups, and the user's own .env, coworker.yaml and memory graph. Only the
# files install.sh claimed by name may be removed from it. setup() still lists
# ~/.coworker as an owned dir, the way manifests written before the fix did, so
# every test also covers a machine that installed with an older release.

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

  # The user's own data under ~/.coworker; install.sh never writes these.
  mkdir -p "$HOME/.coworker/memory"
  echo 'ANTHROPIC_API_KEY=user-secret' > "$HOME/.coworker/.env"
  echo 'install_mode: global' > "$HOME/.coworker/coworker.yaml"
  echo '{"nodes":[]}' > "$HOME/.coworker/memory/graph.json"

  python3 -c "
import json, os
json.dump({'schema_version': 2,
           'files': [os.path.expanduser('~/.coworker/scripts/thing.sh')],
           'hook_commands': [],
           'owned_dirs': [os.path.expanduser('~/.coworker')]},
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
  # A manifest with no schema_version stands in for every machine that
  # installed before the fix: the file on disk still claims ~/.claude/plugins,
  # session transcripts and the analytics database, so running this script
  # would delete them. Nothing may change — not files, not hooks, not
  # ~/.coworker. The refusal used to cover only the file list.
  mkdir -p "$HOME/.claude/skills/foreign-tool"
  echo 'foreign' > "$HOME/.claude/skills/foreign-tool/SKILL.md"
  cat > "$HOME/.claude/settings.json" << 'JSONEOF'
{"hooks": {"Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "coworker memory capture"}]}]}}
JSONEOF
  cp "$HOME/.claude/settings.json" "$TEST_TMP/settings.before"
  python3 -c "
import json, os
json.dump({'files': [os.path.expanduser('~/.claude/skills/foreign-tool/SKILL.md')],
           'hook_commands': ['coworker memory capture'],
           'owned_dirs': [os.path.expanduser('~/.coworker')]},
          open(os.path.expanduser('~/.coworker/install-manifest.json'), 'w'))
"

  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 1 ]
  [[ "$output" == *"SKIPPED"* ]]

  [ -f "$HOME/.claude/skills/foreign-tool/SKILL.md" ]
  cmp -s "$HOME/.claude/settings.json" "$TEST_TMP/settings.before"
  [ -f "$HOME/.coworker/analytics/analytics.db" ]
  [ -f "$HOME/.coworker/.env" ]
  [ -f "$HOME/.coworker/scripts/thing.sh" ]
  [ -f "$HOME/.coworker/install-manifest.json" ]
}

@test "uninstall keeps the user's data in ~/.coworker" {
  # ~/.coworker was emptied of everything but analytics/ and backups/, which
  # deleted the user's API keys, coworker.yaml and memory graph — none of which
  # install.sh writes. setup() lists ~/.coworker as owned, as old manifests do.
  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]

  [ -f "$HOME/.coworker/.env" ]
  [ -f "$HOME/.coworker/coworker.yaml" ]
  [ -f "$HOME/.coworker/memory/graph.json" ]
  # The claimed file and the manifest itself still go.
  [ ! -f "$HOME/.coworker/scripts/thing.sh" ]
  [ ! -f "$HOME/.coworker/install-manifest.json" ]
}

@test "a real install-then-uninstall keeps the user's data in ~/.coworker" {
  rm -f "$HOME/.coworker/install-manifest.json"
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]
  run grep -c '/.coworker"' "$HOME/.coworker/install-manifest.json"
  [ "$output" -eq 0 ]

  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]
  [ -f "$HOME/.coworker/.env" ]
  [ -f "$HOME/.coworker/memory/graph.json" ]
  [ ! -f "$HOME/.coworker/analytics/hooks/on-stop.sh" ]
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

@test "project-mode uninstall removes the OpenCode mirrors it created" {
  # install --project writes $PROJECT/.opencode/instructions/*.md, but the
  # manifest claimed {home}/.opencode/instructions/{name}.md — always the home
  # path. So the claim matched nothing, and uninstall left every mirror behind
  # pointing at a deleted target.
  PROJ="$TEST_TMP/proj"
  mkdir -p "$PROJ"

  run bash "$REPO_ROOT/setup/install.sh" --project "$PROJ" <<< $'1'
  [ "$status" -eq 0 ]
  [ -d "$PROJ/.opencode/instructions" ]

  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]

  run bash -c "find '$PROJ/.opencode/instructions' -xtype l 2>/dev/null | wc -l"
  [ "$output" = "0" ]
}

@test "the-super-lab's OpenCode symlinks are claimed, so they can be retired" {
  # They are created in step 11b and were never claimed at all, while the
  # comment beside the claim loop said owned_dirs covered them — it holds only
  # .../skills/walter-worker. A skill dropped from the source therefore left a
  # symlink to a deleted directory behind for ever.
  # This file's setup() has no the-super-lab, so nothing would deploy.
  SUPERLAB="$HOME/project/the-super-lab"
  mkdir -p "$SUPERLAB/skills/one" "$SUPERLAB/personal-skills"
  printf -- '---\nname: one\ndescription: t\n---\n# one\n' > "$SUPERLAB/skills/one/SKILL.md"

  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'1'
  [ "$status" -eq 0 ]
  [ -f "$HOME/.cursor/skills/one/SKILL.md" ]

  run python3 -c "
import json, os
m = json.load(open(os.path.expanduser('~/.coworker/install-manifest.json')))
print(sum(1 for f in m.get('files', []) if 'skills/the-super-lab/' in f))
"
  [ "$output" -ge 1 ]
  run python3 -c "
import json, os
m = json.load(open(os.path.expanduser('~/.coworker/install-manifest.json')))
print(sum(1 for f in m.get('files', []) if '.cursor/skills/one/' in f))
"
  [ "$output" -ge 1 ]

  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]
  [ ! -e "$HOME/.cursor/skills/one/SKILL.md" ]

  run bash -c "ls -A '$HOME/.config/opencode/skills/the-super-lab' 2>/dev/null | wc -l"
  [ "$output" = "0" ]
}

@test "a pristine snapshot is taken even when the files do not exist yet" {
  # The guard was the directory's existence, and mkdir ran unconditionally. On
  # a fresh machine there was nothing to copy, so the directory was created
  # empty and `! -d` was false from then on: no snapshot was ever taken and
  # --restore-pristine found an empty directory forever.
  rm -rf "$HOME/.coworker/backups/pristine" "$HOME/.coworker/install-manifest.json"
  rm -f "$HOME/.claude/settings.json" "$HOME/.claude/CLAUDE.md"

  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  [ -f "$HOME/.coworker/backups/pristine/.taken" ]
  run cat "$HOME/.coworker/backups/pristine/absent.txt"
  [[ "$output" == *"settings.json"* ]]

  # Restoring removes what the install created, because that is what pristine
  # means on a machine that had neither file.
  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh' --restore-pristine"
  [ "$status" -eq 0 ]
  [ ! -f "$HOME/.claude/settings.json" ]
}

@test "uninstall retires the directories it emptied" {
  # install.sh retires emptied directories after its own prune; uninstall did
  # nothing of the kind, so 15 empty ~/.claude/skills/<name>/ survived — plus
  # ~/.cursor/skills, ~/.opencode/instructions and the hooks dir — and anything
  # listing them still saw an install.
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'1'
  [ "$status" -eq 0 ]

  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]

  # No leftovers beneath the tree roots.
  run bash -c "find '$HOME/.claude/skills' '$HOME/.cursor/skills' '$HOME/.opencode/instructions' -mindepth 1 2>/dev/null | wc -l"
  [ "$output" = "0" ]

  # The roots are never removed, only their emptied children — but whether a
  # root exists at all depends on whether this install created it, and this
  # sandbox has no the-super-lab, so ~/.claude/skills may never have appeared.
  run bash -c "find '$HOME/.claude/skills' -maxdepth 1 -type d -name 'skills' 2>/dev/null | wc -l"
  [ "$output" = "0" ] || [ -d "$HOME/.claude/skills" ]
}

@test "uninstall strips a coworker hook added after the manifest was written" {
  # `coworker sync` adds `coworker state-update` on any later run and does not
  # rewrite the manifest, so the manifest-driven removal missed it and it kept
  # firing after uninstall — while the closing banner said coworker entries had
  # been stripped. Our hooks are identifiable independently of the manifest.
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  python3 -c "
import json, os
p = os.path.expanduser('~/.claude/settings.json')
cfg = json.load(open(p))
cfg['hooks'].setdefault('Stop', []).append(
    {'matcher': '', 'hooks': [{'type': 'command', 'command': 'coworker state-update'}]})
cfg['hooks'].setdefault('Stop', []).append(
    {'matcher': '', 'hooks': [{'type': 'command', 'command': 'echo MY-OWN'}]})
json.dump(cfg, open(p, 'w'), indent=2)
"

  run bash -c "echo y | bash '$REPO_ROOT/setup/uninstall.sh'"
  [ "$status" -eq 0 ]

  run python3 -c "
import json, os
cfg = json.load(open(os.path.expanduser('~/.claude/settings.json')))
cmds = [h.get('command') for groups in cfg.get('hooks', {}).values()
        for g in groups for h in (g.get('hooks') or [])]
print('|'.join(cmds))
"
  # Ours gone, including the one the manifest never recorded.
  [[ "$output" != *"state-update"* ]]
  [[ "$output" != *"coworker memory"* ]]
  # The user's own hook is theirs and stays.
  [[ "$output" == *"echo MY-OWN"* ]]
}
