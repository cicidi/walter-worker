"""Install artifact tests — run against a hermetic temp HOME (installed_home).

Never reads the developer's real ~/.claude or ~/.coworker.
"""
import json

from coworker.analytics.db import get_db


def test_install_creates_all_artifacts(installed_home):
    """install.sh creates hooks, DB, config under the temp HOME."""
    analytics_dir = installed_home / ".coworker" / "analytics"

    hooks = analytics_dir / "hooks"
    assert hooks.is_dir(), "hooks directory missing"
    for script in ["common.sh", "on-user-prompt.sh", "on-pre-tool.sh", "on-post-tool.sh", "on-stop.sh"]:
        assert (hooks / script).exists(), f"Missing hook: {script}"

    db = analytics_dir / "analytics.db"
    assert db.exists(), "analytics.db missing"

    conn = get_db(str(db))
    try:
        table_names = [t[0] for t in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
    finally:
        conn.close()
    for t in ["sessions", "messages", "tool_calls", "file_ops", "session_stats", "skills", "knowledge", "session_summaries"]:
        assert t in table_names, f"Table {t} missing"


def test_claude_hooks_configured(installed_home):
    """Claude Code hooks use the canonical {matcher, hooks:[{type,command}]} shape."""
    settings = installed_home / ".claude" / "settings.json"
    assert settings.exists(), "settings.json missing"
    cfg = json.loads(settings.read_text(encoding="utf-8"))
    hooks = cfg.get("hooks", {})
    for event in ["UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"]:
        assert event in hooks, f"Claude hook {event} missing"
        groups = hooks[event]
        assert isinstance(groups, list) and groups, f"{event} hooks not a non-empty list"
        for g in groups:
            assert isinstance(g, dict), f"{event} group not a dict: {g!r}"
            assert "matcher" in g and "hooks" in g, \
                f"{event} group missing matcher/hooks wrapper: {g!r}"
            for h in g["hooks"]:
                cmd = h.get("command", "")
                assert "coworker/analytics/hooks/" in cmd, \
                    f"{event} command points wrong: {cmd}"


def test_opencode_skills_deployed(installed_home):
    """OpenCode: walter-worker skills are deployed under .config/opencode/skills/.

    Note: install.sh currently does NOT create/modify the OpenCode plugin
    config on a fresh HOME (it reads config.json and silently warns if absent).
    That registration gap is tracked under G7; this test asserts what
    install.sh reliably produces today — the deployed skill tree.
    """
    skills_dir = installed_home / ".config" / "opencode" / "skills" / "walter-worker"
    assert skills_dir.is_dir(), "opencode walter-worker skills dir missing"
    skill_mds = list(skills_dir.rglob("SKILL.md"))
    assert skill_mds, "no SKILL.md files deployed under opencode skills dir"


def test_super_lab_skills_deploy_to_three_harnesses(installed_home):
    """the-super-lab skills reach Claude Code, OpenCode, and Cursor.

    Claude and OpenCode receive whole directories so sibling files travel;
    Cursor receives a flattened verbatim copy.
    """
    skill_md = installed_home / "project/the-super-lab/skills/alpha-skill/SKILL.md"

    # Claude Code — directory copy, sibling files travel
    claude_skill = installed_home / ".claude/skills/alpha-skill"
    assert (claude_skill / "SKILL.md").is_file(), "Claude SKILL.md missing"
    assert (claude_skill / "REFERENCE.md").is_file(), \
        "sibling file did not travel to Claude"

    # OpenCode — symlink to the source directory
    opencode_skill = (
        installed_home / ".config/opencode/skills/the-super-lab/alpha-skill"
    )
    assert opencode_skill.is_symlink(), "OpenCode entry is not a symlink"
    assert (opencode_skill / "SKILL.md").is_file()
    assert (opencode_skill / "REFERENCE.md").is_file(), \
        "sibling file not reachable through the OpenCode symlink"

    # Cursor — flattened verbatim copy
    cursor_rule = installed_home / ".cursor/rules/alpha-skill.md"
    assert cursor_rule.is_file(), "Cursor rule missing"
    assert cursor_rule.read_text(encoding="utf-8") == skill_md.read_text(
        encoding="utf-8"
    ), "Cursor rule is not a verbatim copy"


def test_install_creates_hook_scripts(installed_home):
    """The on-user-prompt hook script exists and is executable."""
    hooks_file = installed_home / ".coworker" / "analytics" / "hooks" / "on-user-prompt.sh"
    assert hooks_file.exists(), "on-user-prompt.sh missing"
    import os
    assert os.access(hooks_file, os.X_OK), f"{hooks_file} not executable"


def test_session_dir_exists(installed_home):
    """sessions directory created."""
    sessions = installed_home / ".coworker" / "analytics" / "sessions"
    assert sessions.is_dir()


def test_install_prunes_stale_opencode_symlinks(tmp_path):
    """install.sh must not let the OpenCode mirror grow without bound.

    It synced CLAUDE_DIR -> OPENCODE_DIR additively, so a symlink created by an
    earlier run kept pointing at CLAUDE_DIR after its target was deleted, and
    nothing removed it. 78 such dangling links had accumulated, which is what
    the 30-minute health check reported as COMMANDS_DIFF.
    """
    import os
    import subprocess
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    home = tmp_path / "home"
    claude = home / ".claude" / "commands"
    opencode = home / ".opencode" / "instructions"
    claude.mkdir(parents=True)
    opencode.mkdir(parents=True)

    # A current skill and its working link.
    (claude / "kept.md").write_text("---\nname: kept\n---\n", encoding="utf-8")
    os.symlink(claude / "kept.md", opencode / "kept.md")
    # Two links whose targets no longer exist.
    for stale in ("gone-a.md", "gone-b.md"):
        os.symlink(claude / stale, opencode / stale)
    # A regular file is not install.sh's to delete.
    (opencode / "user-file.md").write_text("mine\n", encoding="utf-8")

    env = {**os.environ, "HOME": str(home)}
    proc = subprocess.run(
        ["bash", str(repo / "setup" / "install.sh"), "--global"],
        input="0\n", text=True, env=env, cwd=str(repo),
        capture_output=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr

    remaining = sorted(p.name for p in opencode.iterdir())
    assert "kept.md" in remaining, "a live skill link must survive"
    assert "user-file.md" in remaining, "a regular file must not be pruned"
    assert "gone-a.md" not in remaining, "dangling symlinks must be pruned"
    assert "gone-b.md" not in remaining
