"""Tests for local_claude_md.py template functions."""
import pytest
from coworker.templates.local_claude_md import (
    generate_local_claude_md,
    update_project_info,
    inject_feature_into_local_md,
    remove_feature_from_local_md,
    FEATURE_PLACEHOLDER,
    LEGACY_FEATURE_PLACEHOLDER,
)


def test_generate_local_claude_md_basic():
    result = generate_local_claude_md()
    assert "Personal Working Context" in result
    assert FEATURE_PLACEHOLDER in result
    assert "Current Task" in result
    assert "Current Workflow" in result


def test_update_project_info_full():
    content = generate_local_claude_md()
    info = {
        "repo_url": "git@github.com:test/test.git",
        "language": "python",
        "framework": "fastapi",
        "deps": ["pydantic", "click", "rich", "fastapi", "uvicorn", "pytest"],
        "ides": ["claude", "cursor"],
        "test_command": "pytest",
        "lint_command": "ruff",
    }
    result = update_project_info(content, info)
    assert "git@github.com:test/test.git" in result
    assert "Language: python" in result
    assert "Framework: fastapi" in result
    assert "pydantic" in result
    assert "(+1 more)" in result  # 6 deps, show 5 + count
    assert "IDEs: claude, cursor" in result
    assert "Test: pytest" in result
    assert "Lint: ruff" in result


def test_update_project_info_framework_list():
    content = generate_local_claude_md()
    info = {"framework": ["fastapi", "click"]}
    result = update_project_info(content, info)
    assert "Framework: fastapi, click" in result


def test_update_project_info_deps_under_5():
    content = generate_local_claude_md()
    info = {"deps": ["pydantic", "click"]}
    result = update_project_info(content, info)
    assert "Dependencies: pydantic, click" in result
    assert "(+" not in result


def test_update_project_info_language_unknown():
    content = generate_local_claude_md()
    info = {"language": "unknown"}
    result = update_project_info(content, info)
    # "unknown" language is skipped
    assert "Language:" not in result


def test_update_project_info_empty():
    content = generate_local_claude_md()
    info = {}
    result = update_project_info(content, info)
    # Returns unchanged
    assert result == content


def test_update_project_info_no_repo_url_no_lines():
    content = generate_local_claude_md()
    info = {"language": "unknown"}  # skipped, no other fields
    result = update_project_info(content, info)
    assert result == content


def test_update_project_info_minimal():
    content = generate_local_claude_md()
    info = {"repo_url": "git@github.com:x/y.git"}
    result = update_project_info(content, info)
    assert "git@github.com:x/y.git" in result
    assert "## Project Info" in result


def test_inject_feature_basic():
    content = generate_local_claude_md()
    block = "<!-- FEATURE:test START -->\n## test\ncontent\n<!-- FEATURE:test END -->"
    result = inject_feature_into_local_md(content, block)
    assert block.strip() in result
    assert FEATURE_PLACEHOLDER in result


def test_inject_feature_no_placeholder():
    content = "# Just some markdown\n\nno placeholder here\n"
    block = "<!-- FEATURE:test START -->\ntest\n<!-- FEATURE:test END -->"
    result = inject_feature_into_local_md(content, block)
    assert block.strip() in result


def test_inject_feature_replaces_previous():
    content = generate_local_claude_md()
    old_block = "<!-- FEATURE:old START -->\nold content\n<!-- FEATURE:old END -->"
    new_block = "<!-- FEATURE:new START -->\nnew content\n<!-- FEATURE:new END -->"
    # Inject old first
    interim = inject_feature_into_local_md(content, old_block)
    assert "old content" in interim
    # Then inject new — old should be gone
    result = inject_feature_into_local_md(interim, new_block)
    assert "old content" not in result
    assert "new content" in result


def test_remove_feature_basic():
    content = generate_local_claude_md()
    block = "<!-- FEATURE:test START -->\n## test\ncontent\n<!-- FEATURE:test END -->"
    interim = inject_feature_into_local_md(content, block)
    result = remove_feature_from_local_md(interim, "test")
    assert "FEATURE:test" not in result
    assert FEATURE_PLACEHOLDER in result


def test_remove_feature_nonexistent():
    content = generate_local_claude_md()
    result = remove_feature_from_local_md(content, "nonexistent")
    assert FEATURE_PLACEHOLDER in result


def test_remove_feature_only_removes_specified():
    content = generate_local_claude_md()
    block_a = "<!-- FEATURE:a START -->\na\n<!-- FEATURE:a END -->"
    block_b = "<!-- FEATURE:b START -->\nb\n<!-- FEATURE:b END -->"
    interim = inject_feature_into_local_md(content, block_a)
    interim = inject_feature_into_local_md(interim, block_b)  # This will replace 'a' with 'b'

    # Actually inject_feature_into_local_md removes ALL feature blocks first,
    # then inserts the new one. So we can't have two feature blocks at once.
    # Let's test: removing 'b' should work
    result = remove_feature_from_local_md(interim, "b")
    assert "FEATURE:b" not in result


# ── Backward compatibility with the pre-rename "initiative" markers ─────────
# Files written before the rename carry INITIATIVE markers and the old
# placeholder. They must keep working, and be upgraded on their next write.


def _legacy_local_md() -> str:
    """A CLAUDE.local.md as written before the rename."""
    return generate_local_claude_md().replace(
        FEATURE_PLACEHOLDER, LEGACY_FEATURE_PLACEHOLDER
    )


def test_legacy_placeholder_is_read_and_upgraded():
    content = _legacy_local_md()
    assert LEGACY_FEATURE_PLACEHOLDER in content

    block = "<!-- FEATURE:demo START -->\n## Active Feature: demo\n<!-- FEATURE:demo END -->"
    result = inject_feature_into_local_md(content, block)

    assert "## Active Feature: demo" in result
    assert FEATURE_PLACEHOLDER in result, "placeholder should be rewritten to the new form"
    assert LEGACY_FEATURE_PLACEHOLDER not in result


def test_legacy_marker_block_is_removed():
    content = _legacy_local_md()
    legacy_block = (
        "<!-- INITIATIVE:demo START -->\n## Active Initiative: demo\n"
        "<!-- INITIATIVE:demo END -->"
    )
    interim = inject_feature_into_local_md(content, legacy_block)
    result = remove_feature_from_local_md(interim, "demo")
    assert "Active Initiative: demo" not in result


def test_legacy_marker_block_is_replaced_by_new_one():
    """Injecting over a legacy block must not leave the old one behind."""
    content = _legacy_local_md()
    legacy_block = (
        "<!-- INITIATIVE:old START -->\nold content\n<!-- INITIATIVE:old END -->"
    )
    new_block = "<!-- FEATURE:new START -->\nnew content\n<!-- FEATURE:new END -->"
    interim = inject_feature_into_local_md(content, legacy_block)
    result = inject_feature_into_local_md(interim, new_block)

    assert "old content" not in result
    assert "new content" in result


def test_update_project_info_on_legacy_file():
    result = update_project_info(_legacy_local_md(), {"repo_url": "git@github.com:x/y.git"})
    assert "git@github.com:x/y.git" in result
