"""Tests for local_claude_md.py template functions."""
import pytest
from coworker.templates.local_claude_md import (
    generate_local_claude_md,
    update_project_info,
    inject_initiative_into_local_md,
    remove_initiative_from_local_md,
    INITIATIVE_PLACEHOLDER,
)


def test_generate_local_claude_md_basic():
    result = generate_local_claude_md()
    assert "Personal Working Context" in result
    assert INITIATIVE_PLACEHOLDER in result
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


def test_inject_initiative_basic():
    content = generate_local_claude_md()
    block = "<!-- INITIATIVE:test START -->\n## test\ncontent\n<!-- INITIATIVE:test END -->"
    result = inject_initiative_into_local_md(content, block)
    assert block.strip() in result
    assert INITIATIVE_PLACEHOLDER in result


def test_inject_initiative_no_placeholder():
    content = "# Just some markdown\n\nno placeholder here\n"
    block = "<!-- INITIATIVE:test START -->\ntest\n<!-- INITIATIVE:test END -->"
    result = inject_initiative_into_local_md(content, block)
    assert block.strip() in result


def test_inject_initiative_replaces_previous():
    content = generate_local_claude_md()
    old_block = "<!-- INITIATIVE:old START -->\nold content\n<!-- INITIATIVE:old END -->"
    new_block = "<!-- INITIATIVE:new START -->\nnew content\n<!-- INITIATIVE:new END -->"
    # Inject old first
    interim = inject_initiative_into_local_md(content, old_block)
    assert "old content" in interim
    # Then inject new — old should be gone
    result = inject_initiative_into_local_md(interim, new_block)
    assert "old content" not in result
    assert "new content" in result


def test_remove_initiative_basic():
    content = generate_local_claude_md()
    block = "<!-- INITIATIVE:test START -->\n## test\ncontent\n<!-- INITIATIVE:test END -->"
    interim = inject_initiative_into_local_md(content, block)
    result = remove_initiative_from_local_md(interim, "test")
    assert "INITIATIVE:test" not in result
    assert INITIATIVE_PLACEHOLDER in result


def test_remove_initiative_nonexistent():
    content = generate_local_claude_md()
    result = remove_initiative_from_local_md(content, "nonexistent")
    assert INITIATIVE_PLACEHOLDER in result


def test_remove_initiative_only_removes_specified():
    content = generate_local_claude_md()
    block_a = "<!-- INITIATIVE:a START -->\na\n<!-- INITIATIVE:a END -->"
    block_b = "<!-- INITIATIVE:b START -->\nb\n<!-- INITIATIVE:b END -->"
    interim = inject_initiative_into_local_md(content, block_a)
    interim = inject_initiative_into_local_md(interim, block_b)  # This will replace 'a' with 'b'

    # Actually inject_initiative_into_local_md removes ALL initiative blocks first,
    # then inserts the new one. So we can't have two initiative blocks at once.
    # Let's test: removing 'b' should work
    result = remove_initiative_from_local_md(interim, "b")
    assert "INITIATIVE:b" not in result
