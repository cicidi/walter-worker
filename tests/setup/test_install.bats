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
