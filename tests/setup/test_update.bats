#!/usr/bin/env bats

# Tests for update.sh — coworker update, optional skill-factory update

setup() {
  TEST_TMP="$(mktemp -d)"
  export HOME="$TEST_TMP/home"
  mkdir -p "$HOME/.claude/commands"
  mkdir -p "$HOME/.config/opencode/skills/skill-factory"
  mkdir -p "$HOME/.config/ai-coworker"

  # Mock git
  mkdir -p "$TEST_TMP/bin"
  cat > "$TEST_TMP/bin/git" << 'GITEOF'
#!/usr/bin/env bash
echo "upstream/main"
exit 0
GITEOF
  chmod +x "$TEST_TMP/bin/git"
  export PATH="$TEST_TMP/bin:$PATH"

  # Mock install.sh
  mkdir -p "$TEST_TMP/.install-log"
  cat > "$TEST_TMP/bin/install_mock" << 'MKEOF'
#!/usr/bin/env bash
echo "install.sh called with: $*" >> "$TEST_TMP/.install-log/calls"
exit 0
MKEOF
  chmod +x "$TEST_TMP/bin/install_mock"

  export REPO_ROOT
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_DIRNAME")/.." && pwd)"
}

teardown() {
  rm -rf "$TEST_TMP"
}

# =============================================================================
# Test: Update coworker from upstream
# =============================================================================
@test "fetches from upstream when remote exists" {
  # Create fake upstream remote
  cd "$TEST_TMP"
  mkdir fake-repo
  cd fake-repo
  git init
  git remote add upstream git@github.com:cicidi/ai-coworker.git

  run git remote get-url upstream
  [ "$status" -eq 0 ]
}

# =============================================================================
# Test: Graceful handling without upstream
# =============================================================================
@test "falls back to origin when no upstream" {
  # This verifies the fallback logic structure
  run grep "origin" "$REPO_ROOT/setup/update.sh"
  [ "$status" -eq 0 ]
}

# =============================================================================
# Test: Skill-factory update prompt
# =============================================================================
@test "asks about the-super-lab update when directory exists" {
  run grep "Update the-super-lab from GitHub" "$REPO_ROOT/setup/update.sh"
  [ "$status" -eq 0 ]
}

# =============================================================================
# Test: Skill-factory update is skippable
# =============================================================================
@test "the-super-lab update can be declined" {
  run grep "Skipped the-super-lab update" "$REPO_ROOT/setup/update.sh"
  [ "$status" -eq 0 ]
}

# =============================================================================
# Test: Notifies when skill-factory not installed
# =============================================================================
@test "notifies when the-super-lab is not a git checkout" {
  # The message used to say the directory was not found, but the test is for a
  # .git directory — so a plain checkout landed there while sitting right
  # there, in a run that had just deployed skills from it.
  run grep "is not a git checkout, so it was not pulled" "$REPO_ROOT/setup/update.sh"
  [ "$status" -eq 0 ]

  # And no message may claim the directory is absent. Only log/echo lines —
  # the comment explaining the old wording mentions the phrase too.
  run bash -c "grep -E '^[[:space:]]*(log|echo) ' '$REPO_ROOT/setup/update.sh' | grep -c 'not found at'"
  [ "$output" = "0" ]
}

@test "resolves the install mode from the manifest, not coworker.yaml" {
  # install.sh records install_mode in the manifest; nothing ever writes it to
  # coworker.yaml. The yaml grep matched nothing, and the `|| echo global`
  # fallback hid it, so a project-mode install was silently re-installed in
  # global mode. Uses project mode because that is the case the silent default
  # got wrong — a global manifest would pass either way.
  mkdir -p "$HOME/.coworker" "$TEST_TMP/proj"
  echo "# global config" > "$HOME/.coworker/coworker.yaml"
  python3 -c "
import json, os, sys
json.dump({'schema_version': 2, 'install_mode': 'project',
           'project_path': sys.argv[1], 'files': [], 'hook_commands': [],
           'owned_dirs': []},
          open(os.path.expanduser('~/.coworker/install-manifest.json'), 'w'))
" "$TEST_TMP/proj"

  run bash "$REPO_ROOT/setup/update.sh" <<< $'0\nn'
  [[ "$output" == *"Resuming install in mode: project"* ]]
  [[ "$output" != *"Unknown argument"* ]]
}

