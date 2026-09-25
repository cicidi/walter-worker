#!/usr/bin/env bats

# Tests for install.sh — CLAUDE.md creation, skill source, install modes

setup() {
  TEST_TMP="$(mktemp -d)"
  export HOME="$TEST_TMP/home"
  mkdir -p "$HOME/.claude"
  mkdir -p "$HOME/.config/opencode/skills"

  # the-super-lab is the skill source install.sh reads; it no longer clones
  # anything, so a fake checkout at the default location stands in for it.
  SUPERLAB="$HOME/project/the-super-lab"
  _fake_skill "$SUPERLAB/skills/skill-create" skill-create
  _fake_skill "$SUPERLAB/skills/tdd" tdd
  mkdir -p "$SUPERLAB/personal-skills"

  # Mock git — install.sh still pulls the-super-lab
  mkdir -p "$TEST_TMP/bin"
  cat > "$TEST_TMP/bin/git" << 'GITEOF'
#!/usr/bin/env bash
case "$1" in
  pull)
    echo "Already up to date."
    ;;
  -C)
    shift
    "$@"
    ;;
  *)
    exit 0
    ;;
esac
GITEOF
  chmod +x "$TEST_TMP/bin/git"
  export PATH="$TEST_TMP/bin:$PATH"

  # Mock coworker CLI
  cat > "$TEST_TMP/bin/coworker" << 'COEOF'
#!/usr/bin/env bash
exit 0
COEOF
  chmod +x "$TEST_TMP/bin/coworker"

  # Set up repo root pointing to the real install.sh
  export REPO_ROOT
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_DIRNAME")/.." && pwd)"
}

teardown() {
  rm -rf "$TEST_TMP"
}

# Minimal skill in the the-super-lab shape install.sh indexes.
_fake_skill() {
  mkdir -p "$1"
  cat > "$1/SKILL.md" << SKEOF
---
name: $2
description: Use when testing install.sh
license: MIT
compatibility: opencode
metadata:
  triggers:
    - $2
---
# $2
SKEOF
}

# =============================================================================
# Test: Global CLAUDE.md creation
# =============================================================================
@test "creates global CLAUDE.md when missing" {
  rm -f "$HOME/.claude/CLAUDE.md"

  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]
  [ -f "$HOME/.claude/CLAUDE.md" ]
  # Assert against text the current template actually contains. These used to
  # name older wording ("Question Requirement"), which the template no longer
  # has, so the checks had been failing on stale strings.
  grep -q "Ask and Confirm Before Coding" "$HOME/.claude/CLAUDE.md"
  grep -q "clarifying questions to confirm scope" "$HOME/.claude/CLAUDE.md"
}

@test "preserves existing global CLAUDE.md" {
  echo "Custom content" > "$HOME/.claude/CLAUDE.md"

  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]
  grep -q "Custom content" "$HOME/.claude/CLAUDE.md"
}

# =============================================================================
# Test: skill source
# =============================================================================
@test "deploys the-super-lab skills to the three harnesses" {
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]
  # install.sh reads the-super-lab in place and deploys it; it does not clone.
  [ -f "$HOME/.claude/skills/skill-create/SKILL.md" ]
  [ -f "$HOME/.config/opencode/skills/the-super-lab/skill-create/SKILL.md" ]
  [ -f "$HOME/.cursor/rules/skill-create.md" ]
}

# =============================================================================
# Test: Global install mode
# =============================================================================
@test "installs to global Claude Code directory" {
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]
  [ -d "$HOME/.claude/commands" ]
}

# =============================================================================
# Test: Project install mode
# =============================================================================
@test "installs to project Claude Code directory" {
  local project_dir="$TEST_TMP/myproject"
  mkdir -p "$project_dir"

  run bash "$REPO_ROOT/setup/install.sh" --project "$project_dir" <<< $'0'
  [ "$status" -eq 0 ]
  [ -d "$project_dir/.claude/commands" ]
}

# =============================================================================
# Test: the core init skill is always installed
# =============================================================================
@test "always installs the core init skill" {
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]
  # Was named coworker-meta-setup-coworker before the skill consolidation; the
  # file it points at was dropped from the repo at the same time, so this
  # assertion was failing on a name that no longer existed either way.
  [ -f "$HOME/.claude/commands/init.md" ]
}

# =============================================================================
# Test: Skill selection — none (default)
# =============================================================================
@test "installs no extra skills when none selected" {
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]
  # Only the core skill should be installed
  [ -f "$HOME/.claude/commands/init.md" ]
  run ls "$HOME/.claude/commands/"
  # Should have exactly 1 file
  [ "${#lines[@]}" -eq 1 ]
}

# =============================================================================
# Test: Skill selection — all
# =============================================================================
@test "installs all skills when 'all' selected" {
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'1'
  [ "$status" -eq 0 ]
  [ -f "$HOME/.claude/commands/init.md" ]
  [ -f "$HOME/.claude/commands/skill-create.md" ]
  [ -f "$HOME/.claude/commands/tdd.md" ]
}

# =============================================================================
# Test: Skill upgrade (existing file updated)
# =============================================================================
@test "updates existing skill when source changed" {
  # Install first time
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  # Modify the installed file to simulate an old version
  echo "old content" > "$HOME/.claude/commands/init.md"

  # Re-install — should update
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]
  ! grep -q "old content" "$HOME/.claude/commands/init.md"
}

# =============================================================================
# Test: Skill skips when identical
# =============================================================================
@test "skips already up-to-date skills" {
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  # Re-install — should skip
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "Skipped"
}

# =============================================================================
# Test: Invalid install choice fails gracefully
# =============================================================================
@test "handles invalid mode choice gracefully" {
  run bash "$REPO_ROOT/setup/install.sh" <<< $'99'
  [ "$status" -ne 0 ]
}

@test "manifest never claims claude-tmux-config's statusline files" {
  # The exclusion used a trailing slash, so it matched only the (empty)
  # statusline/ directory while the three files beside it were claimed anyway -
  # and uninstall.sh removes every file the manifest lists.
  mkdir -p "$HOME/.claude/statusline"
  echo 'x' > "$HOME/.claude/statusline-command.sh"
  echo 'x' > "$HOME/.claude/statusline-command.sh.bak"
  echo 'x' > "$HOME/.claude/wrap-statusline.py"
  echo 'x' > "$HOME/.claude/statusline/inner.sh"

  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  run python3 -c "
import json, os
m = json.load(open(os.path.expanduser('~/.coworker/install-manifest.json')))
print(len([f for f in m.get('files', []) if 'statusline' in f]))
"
  [ "$output" = "0" ]
}

@test "manifest still records ordinary claude files" {
  # The guard must not have grown so wide it stops tracking anything.
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  run python3 -c "
import json, os
m = json.load(open(os.path.expanduser('~/.coworker/install-manifest.json')))
print('yes' if any(f.endswith('CLAUDE.md') for f in m.get('files', [])) else 'no')
"
  [ "$output" = "yes" ]
}

@test "on-correction.py is registered as a UserPromptSubmit hook" {
  # install.sh copied this file into the hooks dir but never wired it to an
  # event. The author's machine had it hand-registered, so the correction
  # detector worked there and for nobody else: a fresh install silently lost
  # the first stage of the self-heal loop.
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  run python3 -c "
import json, os
cfg = json.load(open(os.path.expanduser('~/.claude/settings.json')))
cmds = [h.get('command', '')
        for groups in cfg.get('hooks', {}).values() if isinstance(groups, list)
        for g in groups if isinstance(g, dict)
        for h in (g.get('hooks') or []) if isinstance(h, dict)]
print('\n'.join(c for c in cmds if 'on-correction.py' in c))
"
  [[ "$output" == *"on-correction.py"* ]]
}

@test "no shipped on-* hook is left unregistered" {
  # Guards the whole class rather than the one instance: the hooks dir and the
  # registration list are maintained separately, so a hook can be added to one
  # and forgotten in the other. common.sh is a sourced helper, not an event
  # hook, which is why the glob is on-* rather than *.
  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  run python3 -c "
import glob, json, os
home = os.path.expanduser('~')
shipped = sorted(os.path.basename(p) for p in glob.glob(home + '/.coworker/analytics/hooks/on-*'))
cfg = json.load(open(home + '/.claude/settings.json'))
registered = ' '.join(
    h.get('command', '')
    for groups in cfg.get('hooks', {}).values() if isinstance(groups, list)
    for g in groups if isinstance(g, dict)
    for h in (g.get('hooks') or []) if isinstance(h, dict))
print('\n'.join(s for s in shipped if s not in registered))
"
  [ -z "$output" ]
}

@test "does not register an OpenCode plugin path that does not exist" {
  # .opencode/ is gitignored and its plugin sources were removed from the repo,
  # so a fresh clone has no .opencode/coworker-analytics. install.sh registered
  # the path unconditionally, writing an entry pointing at nothing into the
  # user's OpenCode config — which OpenCode then failed to load.
  #
  # Build a stand-in repo without .opencode/ to stand in for that clone.
  local fake="$TEST_TMP/fake-repo"
  mkdir -p "$fake"
  cp -r "$REPO_ROOT/setup" "$fake/setup"
  cp -r "$REPO_ROOT/skills" "$fake/skills"
  cp -r "$REPO_ROOT/src" "$fake/src"

  mkdir -p "$HOME/.config/opencode"
  echo '{"plugin": []}' > "$HOME/.config/opencode/config.json"

  run bash "$fake/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  run python3 -c "
import json, os
cfg = json.load(open(os.path.expanduser('~/.config/opencode/config.json')))
bogus = [p for p in cfg.get('plugin', []) if not os.path.isdir(p)]
print('bogus=' + ','.join(bogus))
"
  [ "$output" = "bogus=" ]
}

@test "still registers the OpenCode plugin when it is present" {
  # The guard must not switch the feature off for a checkout that does have it.
  local fake="$TEST_TMP/fake-repo2"
  mkdir -p "$fake/.opencode/coworker-analytics"
  cp -r "$REPO_ROOT/setup" "$fake/setup"
  cp -r "$REPO_ROOT/skills" "$fake/skills"
  cp -r "$REPO_ROOT/src" "$fake/src"

  mkdir -p "$HOME/.config/opencode"
  echo '{"plugin": []}' > "$HOME/.config/opencode/config.json"

  run bash "$fake/setup/install.sh" --global <<< $'0'
  [ "$status" -eq 0 ]

  run python3 -c "
import json, os
cfg = json.load(open(os.path.expanduser('~/.config/opencode/config.json')))
print('registered=' + str(any('coworker-analytics' in p for p in cfg.get('plugin', []))))
"
  [ "$output" = "registered=True" ]
}

@test "installs on a platform without md5sum" {
  # md5sum is GNU coreutils. macOS ships BSD `md5` and has no md5sum, and this
  # script deliberately supports macOS (see the bash-3.2 note by the parallel
  # arrays). Under `set -euo pipefail` the command substitution failed and the
  # whole install aborted, so the platform the script was written to support
  # could not install at all. A failing md5sum stands in for an absent one.
  cat > "$TEST_TMP/bin/md5sum" <<'MDEOF'
#!/usr/bin/env bash
echo "md5sum: command not found" >&2
exit 127
MDEOF
  chmod +x "$TEST_TMP/bin/md5sum"

  run bash "$REPO_ROOT/setup/install.sh" --global <<< $'1'
  [ "$status" -eq 0 ]
  [ -f "$HOME/.claude/commands/init.md" ]
}
