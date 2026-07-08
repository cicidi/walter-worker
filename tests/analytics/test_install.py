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
    """OpenCode: ai-coworker skills are deployed under .config/opencode/skills/.

    Note: install.sh currently does NOT create/modify the OpenCode plugin
    config on a fresh HOME (it reads config.json and silently warns if absent).
    That registration gap is tracked under G7; this test asserts what
    install.sh reliably produces today — the deployed skill tree.
    """
    skills_dir = installed_home / ".config" / "opencode" / "skills" / "ai-coworker"
    assert skills_dir.is_dir(), "opencode ai-coworker skills dir missing"
    skill_mds = list(skills_dir.rglob("SKILL.md"))
    assert skill_mds, "no SKILL.md files deployed under opencode skills dir"


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
