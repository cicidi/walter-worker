"""G11: All skills/*/SKILL.md must conform to the canonical frontmatter schema.
Required fields: name, version, description, triggers (list, >=1), when-to-use."""
from pathlib import Path
import pytest
import yaml

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
REQUIRED = {"name", "version", "description", "triggers", "when-to-use"}


def _skill_files():
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def _parse_fm(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None, "no opening ---"
    closing = text.find("---", 3)
    if closing == -1:
        return None, "no closing ---"
    try:
        fm = yaml.safe_load(text[3:closing])
    except yaml.YAMLError as e:
        return None, f"YAML error: {e}"
    return fm, None


@pytest.mark.parametrize("skill_file", _skill_files(), ids=lambda p: p.parent.name)
def test_frontmatter_has_required_fields(skill_file):
    fm, err = _parse_fm(skill_file)
    assert err is None, f"{skill_file}: {err}"
    assert isinstance(fm, dict), f"{skill_file}: frontmatter must be a YAML mapping"
    missing = REQUIRED - set(fm.keys())
    assert not missing, f"{skill_file}: missing required fields: {missing}"
    assert isinstance(fm["version"], str) and fm["version"], f"{skill_file}: version required"
    triggers = fm.get("triggers", [])
    assert isinstance(triggers, list) and len(triggers) >= 1, \
        f"{skill_file}: triggers must be a non-empty list"
    when = fm.get("when-to-use", "")
    assert isinstance(when, str) and when.strip(), f"{skill_file}: when-to-use required and non-empty"


def test_scaffold_conforms():
    """Running 'coworker skill new test-skill' produces schema-compliant output."""
    from click.testing import CliRunner
    from coworker.cli import main
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmp:
        # skill new --global writes to GLOBAL_DIR/skills/name
        monkey = pytest.MonkeyPatch()
        monkey.setenv("COWORKER_HOME", tmp)  # if supported
        # Use --project to write to local dir
        runner = CliRunner()
        os.chdir(tmp)
        result = runner.invoke(main, ["skill", "new", "--project", "test-skill"])
        assert result.exit_code == 0

        skill_md = Path(tmp) / ".coworker" / "skills" / "test-skill" / "SKILL.md"
        assert skill_md.exists()

        fm, err = _parse_fm(skill_md)
        assert err is None
        assert fm["name"] == "test-skill"
        assert fm["version"] == "0.1.0"
        assert isinstance(fm["triggers"], list) and len(fm["triggers"]) >= 1
        assert fm["when-to-use"].strip()
