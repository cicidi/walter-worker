from __future__ import annotations
from pathlib import Path
import yaml


ROOT = Path(__file__).parent.parent.parent
SKILL_FACTORY_SRC = Path.home() / ".config/opencode/skills/skill-factory"
PROJECT_SKILLS_DIR = ROOT / "skills"


class TestSkillFactorySource:
    def test_source_repo_exists(self):
        assert SKILL_FACTORY_SRC.exists(), (
            f"Skill-factory source not found at {SKILL_FACTORY_SRC}"
        )

    def test_source_has_conventions(self):
        conventions = SKILL_FACTORY_SRC / "CONVENTIONS.md"
        assert conventions.exists(), (
            f"CONVENTIONS.md missing from skill-factory source"
        )

    def test_source_has_skill_dirs(self):
        subdirs = {"walter-worker-skills", "personal-skills"}
        for subdir in subdirs:
            path = SKILL_FACTORY_SRC / subdir
            assert path.is_dir(), f"Skill-factory missing directory: {subdir}"

    def test_walter_worker_skills_have_skill_md(self):
        skills_dir = SKILL_FACTORY_SRC / "walter-worker-skills"
        if not skills_dir.is_dir():
            return
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                assert skill_md.is_file(), (
                    f"SKILL.md missing in {skill_dir.name}"
                )

    def test_source_skills_have_valid_frontmatter(self):
        for skills_sub in ["walter-worker-skills", "personal-skills"]:
            skills_dir = SKILL_FACTORY_SRC / skills_sub
            if not skills_dir.is_dir():
                continue
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.is_file():
                    continue
                content = skill_md.read_text()
                assert content.startswith("---"), (
                    f"{skill_dir.name}/SKILL.md missing frontmatter"
                )
                parts = content.split("---", 2)
                assert len(parts) >= 3, (
                    f"{skill_dir.name}/SKILL.md has malformed frontmatter"
                )
                frontmatter = yaml.safe_load(parts[1])
                assert "name" in frontmatter, (
                    f"{skill_dir.name}/SKILL.md frontmatter missing 'name'"
                )
                assert "description" in frontmatter, (
                    f"{skill_dir.name}/SKILL.md frontmatter missing 'description'"
                )


class TestDeployConsistency:
    def test_deployed_source_skills_match(self):
        source_skills_dir = SKILL_FACTORY_SRC / "walter-worker-skills"
        if not source_skills_dir.is_dir():
            return

        source_skills = {
            d.name for d in source_skills_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        }

        deployed_skills = set()
        if PROJECT_SKILLS_DIR.is_dir():
            deployed_skills = {
                d.name for d in PROJECT_SKILLS_DIR.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            }

        # For skills present in both source and deployed, verify both are valid
        common = source_skills & deployed_skills
        assert len(common) > 0, (
            "No common skills between source and deployed"
        )
        for skill_name in common:
            dep_md = PROJECT_SKILLS_DIR / skill_name / "SKILL.md"
            assert dep_md.is_file(), (
                f"Deployed skill '{skill_name}' missing SKILL.md"
            )
            assert dep_md.read_text(encoding="utf-8").strip() != "", (
                f"Deployed skill '{skill_name}/SKILL.md' is empty"
            )

    def test_deployed_personal_skills_have_source(self):
        source_personal_dir = SKILL_FACTORY_SRC / "personal-skills"
        if not source_personal_dir.is_dir():
            return

        source_personal = {
            d.name for d in source_personal_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        }

        if not source_personal:
            return

        if PROJECT_SKILLS_DIR.is_dir():
            for d in PROJECT_SKILLS_DIR.iterdir():
                if d.is_dir() and d.name in source_personal:
                    skill_md = d / "SKILL.md"
                    assert skill_md.is_file(), (
                        f"Deployed personal skill '{d.name}' missing SKILL.md"
                    )

    def test_deployed_skills_have_complete_structure(self):
        if not PROJECT_SKILLS_DIR.is_dir():
            return
        for skill_dir in PROJECT_SKILLS_DIR.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            assert skill_md.is_file(), (
                f"Deployed skill '{skill_dir.name}' missing SKILL.md"
            )
            content = skill_md.read_text()
            assert len(content) > 0, (
                f"Deployed skill '{skill_dir.name}/SKILL.md' is empty"
            )


class TestClaudeMdReferences:
    def test_claude_md_no_dead_template_paths(self):
        claude_md = ROOT / "CLAUDE.md"
        content = claude_md.read_text()

        # Find all potential paths referenced (looking for patterns like
        # `personal/context/projects.yaml`, `docs/...`, `skills/...`)
        path_patterns = [
            "personal/context/projects.yaml",
            ".local_config.yaml",
        ]

        for path_str in path_patterns:
            if path_str in content:
                full_path = ROOT / path_str
                assert full_path.exists(), (
                    f"Template path '{path_str}' in CLAUDE.md does not exist: {full_path}"
                )

    def test_claude_md_skill_factory_references_accurate(self):
        claude_md = ROOT / "CLAUDE.md"
        content = claude_md.read_text()

        # The CLAUDE.md should mention the skill-factory workflow
        if "skill-factory" in content:
            assert SKILL_FACTORY_SRC.exists(), (
                "CLAUDE.md references skill-factory but source does not exist"
            )

    def test_claude_md_self_healing_traces_dir_configured(self):
        traces_dir = ROOT / ".self-healing" / "traces"
        if "self-heal" in (ROOT / "CLAUDE.md").read_text():
            # self-heal directory should exist if referenced
            # (it's created on first use, so just check it's not a file)
            if traces_dir.exists():
                assert traces_dir.is_dir(), (
                    ".self-healing/traces exists but is not a directory"
                )
            # If it doesn't exist, that's OK — it's created on first self-heal
