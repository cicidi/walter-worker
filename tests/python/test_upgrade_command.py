"""Tests for the worker upgrade command (G1)."""
import json
from pathlib import Path

from click.testing import CliRunner

from coworker.cli import main
from coworker.templates.global_claude_md import generate_global_claude_md


def _setup_home(tmp_path, monkeypatch, content=None):
    home = tmp_path / "home"
    home.mkdir()
    claude = home / ".claude"
    claude.mkdir(parents=True)
    md = claude / "CLAUDE.md"
    if content is not None:
        md.write_text(content, encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    return md


def test_upgrade_pristine_is_up_to_date(tmp_path, monkeypatch):
    """Upgrade over a freshly generated file reports 'already up to date'."""
    prist = generate_global_claude_md()
    _setup_home(tmp_path, monkeypatch, content=prist)

    runner = CliRunner()
    result = runner.invoke(main, ["upgrade", "--yes"])
    assert result.exit_code == 0, f"failed: {result.output}"
    assert "Already up to date" in result.output


def test_upgrade_user_edited_keeps_user_sections(tmp_path, monkeypatch):
    """User-added sections survive; modified sections overwrite; merge completes."""
    orig = generate_global_claude_md()
    # Modify a template section to trigger OVERWRITE, and add a user section
    edited = orig.replace("Behavioral guidelines to reduce common LLM coding mistakes.",
                          "MY CUSTOM BODY TEXT")
    edited += "\n## My Custom Rules\nmy content\n"
    md = _setup_home(tmp_path, monkeypatch, content=edited)

    runner = CliRunner()
    result = runner.invoke(main, ["upgrade", "--yes"])
    assert result.exit_code == 0, f"failed: {result.output}"

    out = md.read_text()
    assert "My Custom Rules" in out
    assert "my content" in out
    assert "CLAUDE.md upgraded" in result.output


def test_upgrade_dry_run_writes_nothing(tmp_path, monkeypatch):
    """--dry-run prints a plan but does not write."""
    orig = generate_global_claude_md()
    edited = orig + "\n## Extra\nx\n"
    md = _setup_home(tmp_path, monkeypatch, content=edited)

    before = md.read_text()
    runner = CliRunner()
    result = runner.invoke(main, ["upgrade", "--dry-run"])
    assert result.exit_code == 0
    assert "--dry-run" in result.output
    assert md.read_text() == before  # unchanged


def test_upgrade_no_tty_without_yes_refuses(tmp_path, monkeypatch):
    """When stdout is not a TTY and --yes is absent, refuse."""
    orig = generate_global_claude_md()
    edited = orig + "\n## X\nx\n"
    _setup_home(tmp_path, monkeypatch, content=edited)

    runner = CliRunner()
    # CliRunner's stdout is not a TTY by default
    result = runner.invoke(main, ["upgrade"])
    assert "stdout is not a TTY" in result.output


class TestShippedGlobalTemplate:
    """The global template is seeded into every new user's ~/.claude/CLAUDE.md.

    It carried the author's own projects and paths as illustrative examples.
    A stranger installing walter-worker has never heard of any of them, so the
    guidance reads as broken rather than as an example.
    """

    def test_names_no_project_of_the_authors(self):
        tpl = generate_global_claude_md()
        leaked = [n for n in ("deterministic-workflow", "skill-factory", "cicidi")
                  if n in tpl]
        assert leaked == [], f"author-specific names in the shipped template: {leaked}"

    def test_names_no_absolute_home_path(self):
        import re

        tpl = generate_global_claude_md()
        found = re.findall(r"/home/[a-z0-9_-]+/", tpl)
        assert found == [], f"absolute home paths in the shipped template: {found}"


class TestTemplateSkillReferences:
    """Section 9 of the template sends the agent to skills by name.

    walter-worker-fix and walter-worker-upgrade were dropped from skills/ in a
    consolidation pass, and the template went on promising them — so on every
    install the instruction pointed at a skill nobody had. Reinstating the
    skills is only half the fix; this is the half that notices next time.
    """

    def test_every_walter_worker_skill_the_template_names_is_shipped(self):
        import re

        skills_dir = Path(__file__).resolve().parents[2] / "skills"
        shipped = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}

        named = set(re.findall(r"`(walter-worker-[a-z-]+)`", generate_global_claude_md()))
        assert named, "expected the template to name at least one skill"

        missing = sorted(named - shipped)
        assert missing == [], (
            f"the global template invokes skills that are not shipped: {missing}"
        )


class TestUserEditsInsideATemplateSection:
    """`upgrade` deleted a line the user inserted mid-section.

    The old rule was position-dependent: a line appended at the END of a
    template section made the user's body start with the template's, so it was
    KEPT; the same line inserted MID-section did not, so the section was
    OVERWRITTEN and the line silently vanished. The plan said only
    "content differs", so --dry-run could not warn you either.
    """

    def test_a_line_inserted_mid_section_survives(self, tmp_path, monkeypatch):
        runner = CliRunner()
        orig = generate_global_claude_md()
        # Insert a user line in the middle of a template section.
        edited = orig.replace(
            "- No abstractions for single-use code.",
            "- BUT always add the metrics dashboard the boss asked for.\n"
            "- No abstractions for single-use code.",
        )
        assert edited != orig
        md = _setup_home(tmp_path, monkeypatch, content=edited)

        result = runner.invoke(main, ["upgrade", "--yes"])

        assert result.exit_code == 0, result.output
        assert "BUT always add the metrics dashboard" in md.read_text()
        # And the user is told, rather than left to diff the file.
        assert "you have edited" in result.output

    def test_a_template_rewording_still_applies(self, tmp_path, monkeypatch):
        """The conflict rule must not freeze ordinary template updates."""
        runner = CliRunner()
        orig = generate_global_claude_md()
        edited = orig.replace(
            "- No abstractions for single-use code.",
            "- No abstractions for code you will only write once.",
        )
        md = _setup_home(tmp_path, monkeypatch, content=edited)

        result = runner.invoke(main, ["upgrade", "--yes"])

        assert result.exit_code == 0, result.output
        # Both sides differ, so this is a template change, not a user addition;
        # the template's wording wins exactly as it did before.
        assert "No abstractions for single-use code." in md.read_text()

    def test_force_takes_the_template_version(self, tmp_path, monkeypatch):
        runner = CliRunner()
        orig = generate_global_claude_md()
        edited = orig.replace(
            "- No abstractions for single-use code.",
            "- BUT always add the metrics dashboard the boss asked for.\n"
            "- No abstractions for single-use code.",
        )
        md = _setup_home(tmp_path, monkeypatch, content=edited)

        result = runner.invoke(main, ["upgrade", "--yes", "--force"])

        assert result.exit_code == 0, result.output
        assert "BUT always add the metrics dashboard" not in md.read_text()
