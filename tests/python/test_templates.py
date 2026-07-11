# tests/python/test_templates.py
from coworker.templates.global_claude_md import GLOBAL_CLAUDE_MD_TEMPLATE, generate_global_claude_md
from coworker.templates.project_claude_md import generate_project_claude_md
from coworker.templates.local_claude_md import (
    generate_local_claude_md,
    inject_initiative_into_local_md,
    remove_initiative_from_local_md,
    INITIATIVE_PLACEHOLDER,
)


class TestGlobalTemplate:
    def test_exists(self):
        assert len(GLOBAL_CLAUDE_MD_TEMPLATE) > 0

    def test_under_100_lines(self):
        result = generate_global_claude_md()
        lines = result.strip().split("\n")
        assert len(lines) < 100, f"{len(lines)} lines, must be <100"

    def test_contains_all_8_principles(self):
        result = generate_global_claude_md()
        for phrase in [
            "Ask and Confirm",
            "Evidence and Reasoning",
            "Simplicity First",
            "Surgical Changes",
            "Goal-Driven Execution",
            "Decompose Complex Tasks",
            "Plan and Track",
            "Model Upgrade",
        ]:
            assert phrase in result, f"Missing: {phrase}"

    def test_no_tool_specific(self):
        result = generate_global_claude_md()
        assert ".claude/rules/" not in result
        assert "opencode.json" not in result


class TestProjectTemplate:
    def test_under_200_lines(self):
        result = generate_project_claude_md(
            project_name="test", language="python", framework="fastapi",
            repo="git@github.com:test/test.git",
        )
        lines = result.strip().split("\n")
        assert len(lines) < 200, f"{len(lines)} lines, must be <200"

    def test_project_identity_not_in_claude_md(self):
        """Project info moved to CLAUDE.local.md — must not be in project CLAUDE.md."""
        result = generate_project_claude_md(project_name="test")
        assert "Project Identity" not in result
        assert "Project Relationships" not in result
        assert "Knowledge Repo" not in result
        assert "Team Links" not in result
        assert "Repo:" not in result

    def test_contains_local_override(self):
        result = generate_project_claude_md(project_name="test")
        assert "CLAUDE.local.md" in result
        assert "Read tool" in result or "read CLAUDE.local.md" in result.lower()

    def test_contains_workflow_heuristics(self):
        result = generate_project_claude_md(project_name="test")
        assert "low-risk" in result.lower() or "auto-execute" in result.lower()
        assert "Reality check" in result or "overthink" in result.lower()

    def test_guardrails_section(self):
        result = generate_project_claude_md(project_name="test")
        assert "Guardrails" in result
        assert "never push" in result.lower() or "Never push" in result
        assert "secrets" in result.lower() or "credentials" in result.lower()

    def test_section_order(self):
        result = generate_project_claude_md(project_name="test")
        sections = [line.strip().lstrip("# ").strip() for line in result.split("\n") if line.strip().startswith("## ")]
        order = {s: i for i, s in enumerate(sections)}
        assert order["Local Override"] < order["Mandatory Guardrails"]
        assert order["Mandatory Guardrails"] < order["Compaction & State Persistence"]
        assert order["Compaction & State Persistence"] < order["Context Management"]
        assert order["Context Management"] < order["Workflow Selection"]
        assert order["Workflow Selection"] < order["Auto Memory"]

    def test_no_tool_specific(self):
        result = generate_project_claude_md(project_name="test")
        assert ".claude/rules/" not in result

    def test_relationships_in_local_not_claude_md(self):
        """Relationships moved to CLAUDE.local.md — no relationships heading in CLAUDE.md."""
        result = generate_project_claude_md(project_name="test")
        assert "## Project Relationships" not in result

    def test_doc_info_not_in_claude_md(self):
        """Doc map and knowledge repo headings removed from project CLAUDE.md."""
        result = generate_project_claude_md(project_name="test")
        assert "## Knowledge Repo" not in result

    def test_auto_memory_section(self):
        result = generate_project_claude_md(project_name="test")
        assert "Auto Memory" in result
        assert "override" in result.lower()  # upfront rules override auto-memory

    def test_context_management_refs_local_md(self):
        result = generate_project_claude_md(project_name="test")
        assert "CLAUDE.local.md" in result
        assert "state" in result.lower()
        assert "docs/specs/" in result
        assert "docs/discussion/" in result

    def test_compaction_section(self):
        result = generate_project_claude_md(project_name="test")
        assert "Compaction" in result
        assert "state" in result.lower()

    def test_protected_block(self):
        result = generate_project_claude_md(project_name="test")
        assert "PROTECTED:CRITICAL-RULES" in result


class TestLocalTemplate:
    def test_under_50_lines(self):
        result = generate_local_claude_md()
        lines = result.strip().split("\n")
        assert len(lines) < 50, f"{len(lines)} lines — local.md should be minimal without initiative"

    def test_has_initiative_placeholder(self):
        result = generate_local_claude_md()
        assert INITIATIVE_PLACEHOLDER in result

    def test_has_config_path_section(self):
        result = generate_local_claude_md()
        assert "Config" in result

    def test_has_reference_docs_section(self):
        result = generate_local_claude_md()
        assert "Reference Docs" in result

    def test_has_recommended_skills_placeholder(self):
        result = generate_local_claude_md()
        assert "Skills:" in result

    def test_has_task_state_section(self):
        result = generate_local_claude_md()
        assert "Current Task" in result

    def test_inject_initiative_no_duplicates(self):
        content = generate_local_claude_md()
        block = """<!-- INITIATIVE:test START -->
## Active Initiative: test
> test desc
<!-- INITIATIVE:test END -->"""
        updated = inject_initiative_into_local_md(content, block)
        assert "INITIATIVE:test" in updated
        updated2 = inject_initiative_into_local_md(updated, block)
        assert updated2.count("INITIATIVE:test") == 2

    def test_remove_initiative(self):
        content = generate_local_claude_md()
        block = "<!-- INITIATIVE:test START -->\n## test\n<!-- INITIATIVE:test END -->"
        with_init = inject_initiative_into_local_md(content, block)
        assert "INITIATIVE:test" in with_init
        removed = remove_initiative_from_local_md(with_init, "test")
        assert "INITIATIVE:test" not in removed

    def test_remove_nonexistent(self):
        content = generate_local_claude_md()
        result = remove_initiative_from_local_md(content, "nonexistent")
        assert INITIATIVE_PLACEHOLDER in result

    def test_placeholder_survives_injection(self):
        content = generate_local_claude_md()
        block = "<!-- INITIATIVE:test START -->\n## test\n<!-- INITIATIVE:test END -->"
        updated = inject_initiative_into_local_md(content, block)
        assert INITIATIVE_PLACEHOLDER in updated
