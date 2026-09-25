from __future__ import annotations
import os
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).parent.parent.parent
# Mirrors setup/install.sh's THE_SUPER_LAB_DIR override, so this can point at a
# different checkout — and so the absence path below is reachable and testable.
THE_SUPER_LAB_SRC = Path(
    os.environ.get("THE_SUPER_LAB_DIR", str(Path.home() / "project" / "the-super-lab"))
)
PROJECT_SKILLS_DIR = ROOT / "skills"

# These tests assert against a *second* repository, which is not part of this
# one. A fresh clone and CI do not have it, so they must skip rather than fail —
# as written they hard-asserted the author's own checkout and went red for
# everyone else.
pytestmark = pytest.mark.skipif(
    not THE_SUPER_LAB_SRC.exists(),
    reason=f"the-super-lab not found at {THE_SUPER_LAB_SRC} (set THE_SUPER_LAB_DIR)",
)


class TestSuperLabSource:
    def test_source_repo_exists(self):
        assert THE_SUPER_LAB_SRC.exists(), (
            f"the-super-lab source not found at {THE_SUPER_LAB_SRC}"
        )

    def test_source_has_conventions(self):
        conventions = THE_SUPER_LAB_SRC / "CONVENTIONS.md"
        assert conventions.exists(), (
            f"CONVENTIONS.md missing from the-super-lab source"
        )

    def test_source_has_skill_dirs(self):
        subdirs = {"skills", "personal-skills"}
        for subdir in subdirs:
            path = THE_SUPER_LAB_SRC / subdir
            assert path.is_dir(), f"the-super-lab missing directory: {subdir}"

    def test_walter_worker_skills_have_skill_md(self):
        skills_dir = THE_SUPER_LAB_SRC / "skills"
        if not skills_dir.is_dir():
            return
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            # Not every directory in there is a skill. This walks a repo we do
            # not control, where scratch dirs appear and vanish with whatever
            # runs in it; one left behind turned this suite red on a machine
            # where nothing in *this* repo had changed. A skill keeps its
            # SKILL.md at the top level, so a directory with no top-level
            # files — only nested scratch like state/ — is not a skill.
            if not any(p.is_file() for p in skill_dir.iterdir()):
                continue
            skill_md = skill_dir / "SKILL.md"
            assert skill_md.is_file(), (
                f"SKILL.md missing in {skill_dir.name}"
            )

    def test_source_skills_have_valid_frontmatter(self):
        for skills_sub in ["skills", "personal-skills"]:
            skills_dir = THE_SUPER_LAB_SRC / skills_sub
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
        source_skills_dir = THE_SUPER_LAB_SRC / "skills"
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

        # The two repos deliberately share no skill names: walter-worker's
        # skills moved into this repo, so overlap is not the invariant. What
        # matters is that any skill present in both is valid on the deployed
        # side, and that the source itself is populated.
        assert source_skills, f"No skills found in {source_skills_dir}"

        for skill_name in source_skills & deployed_skills:
            dep_md = PROJECT_SKILLS_DIR / skill_name / "SKILL.md"
            assert dep_md.is_file(), (
                f"Deployed skill '{skill_name}' missing SKILL.md"
            )
            assert dep_md.read_text(encoding="utf-8").strip() != "", (
                f"Deployed skill '{skill_name}/SKILL.md' is empty"
            )

    def test_deployed_personal_skills_have_source(self):
        source_personal_dir = THE_SUPER_LAB_SRC / "personal-skills"
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

    def test_claude_md_super_lab_references_accurate(self):
        claude_md = ROOT / "CLAUDE.md"
        content = claude_md.read_text()

        # The CLAUDE.md should mention the the-super-lab workflow
        if "the-super-lab" in content:
            assert THE_SUPER_LAB_SRC.exists(), (
                "CLAUDE.md references the-super-lab but source does not exist"
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
