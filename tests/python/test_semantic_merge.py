# tests/python/test_semantic_merge.py
import pytest

from coworker.semantic_merge import (
    classify_sections,
    apply_merge,
    verify_protected,
    protected_ranges,
    parse_sections,
    sections_to_text,
    _is_placeholder,
    SectionClassification,
    Section,
    OVERWRITE,
    MERGE_ADD,
    KEEP,
    OUTDATED,
)

CURRENT = """# Project CLAUDE.md

## Identity
python, fastapi

## My Custom Rules
my custom content

<!-- PROTECTED -->
do not touch
<!-- END PROTECTED -->

## Context Management
old version
"""

FUTURE = """# Project CLAUDE.md

## Identity
python, fastapi, pydantic

## Context Management
new version

## Workflow Heuristics
new workflow guide
"""


class TestClassifySections:
    def test_overwrite_identity(self):
        c = classify_sections(CURRENT, FUTURE)
        identity = [x for x in c if x.category == OVERWRITE and "Identity" in x.heading]
        assert len(identity) == 1

    def test_overwrite_context_mgmt(self):
        c = classify_sections(CURRENT, FUTURE)
        ctx = [x for x in c if x.category == OVERWRITE and "Context Management" in x.heading]
        assert len(ctx) == 1

    def test_keep_custom_rules(self):
        c = classify_sections(CURRENT, FUTURE)
        keeps = [x for x in c if x.category == KEEP]
        headings = [x.heading for x in keeps]
        assert any("Custom Rules" in h for h in headings)

    def test_merge_add_workflow(self):
        c = classify_sections(CURRENT, FUTURE)
        adds = [x for x in c if x.category == MERGE_ADD]
        assert any("Workflow Heuristics" in x.heading for x in adds)

    def test_protected_block_kept(self):
        c = classify_sections(CURRENT, FUTURE)
        protected = [x for x in c if "PROTECTED" in x.current_content]
        assert len(protected) >= 1
        assert protected[0].category == KEEP


class TestApplyMerge:
    def test_merged_contains_overwrite(self):
        c = classify_sections(CURRENT, FUTURE)
        result = apply_merge(c, CURRENT, FUTURE)
        assert "pydantic" in result
        assert "new version" in result

    def test_merged_keeps_custom(self):
        c = classify_sections(CURRENT, FUTURE)
        result = apply_merge(c, CURRENT, FUTURE)
        assert "my custom content" in result

    def test_merged_adds_new_sections(self):
        c = classify_sections(CURRENT, FUTURE)
        result = apply_merge(c, CURRENT, FUTURE)
        assert "new workflow guide" in result

    def test_merged_keeps_protected(self):
        c = classify_sections(CURRENT, FUTURE)
        result = apply_merge(c, CURRENT, FUTURE)
        assert "do not touch" in result

    def test_no_duplicate_headings(self):
        c = classify_sections(CURRENT, FUTURE)
        result = apply_merge(c, CURRENT, FUTURE)
        assert result.count("## Identity") == 1


class TestIsPlaceholder:
    """Cover _is_placeholder including all patterns and the line-37 fallthrough."""

    def test_empty_body_returns_false(self):
        assert _is_placeholder("") is False
        assert _is_placeholder("   ") is False
        assert _is_placeholder("\n") is False

    def test_none_configured_placeholder(self):
        assert _is_placeholder("_(none configured)_") is True

    def test_repo_url_placeholder(self):
        assert _is_placeholder("_Repo URL auto-discovered by AI._") is True

    def test_coworker_init_placeholder(self):
        assert _is_placeholder("_(run `coworker init` to scan docs/ structure)_") is True

    def test_none_configured_add_shared_placeholder(self):
        assert _is_placeholder(
            "_(none configured — add shared wikis, Slack channels, design docs)_"
        ) is True

    def test_placeholder_inside_larger_body(self):
        """Placeholder detection is substring-based, not exact match."""
        assert _is_placeholder("Some text\n_(none configured)_\nmore text") is True

    def test_non_placeholder_body_returns_false(self):
        """Line 37: stripped body that doesn't match any pattern -> False."""
        assert _is_placeholder("This is actual content") is False
        assert _is_placeholder("## Section\nbody text") is False


class TestProtectedRanges:
    """Cover protected_ranges edge cases: unclosed markers (line 164-165)
    and end-without-start (silently ignored)."""

    def test_unclosed_marker_protects_to_eof(self):
        """Lines 164-165: start marker with no end — protects through end of file."""
        text = (
            "## Intro\n"
            "regular text\n"
            "<!-- PROTECTED -->\n"
            "secret content\n"
            "more secret content\n"
        )
        ranges = protected_ranges(text)
        assert ranges == [(3, 6)], f"Expected [(3,6)], got {ranges}"

    def test_end_without_start_ignored(self):
        """End marker without prior start is silently skipped."""
        text = (
            "## Intro\n"
            "some text\n"
            "<!-- END PROTECTED -->\n"
            "more text\n"
        )
        ranges = protected_ranges(text)
        assert ranges == []

    def test_nested_protected_blocks(self):
        """Nested protected markers produce overlapping ranges."""
        text = (
            "<!-- PROTECTED -->\n"
            "outer content\n"
            "<!-- PROTECTED -->\n"
            "inner content\n"
            "<!-- END PROTECTED -->\n"
            "outer still\n"
            "<!-- END PROTECTED -->\n"
        )
        ranges = protected_ranges(text)
        assert len(ranges) == 2
        assert ranges[0] == (3, 5)   # inner pair
        assert ranges[1] == (1, 7)   # outer pair


class TestSectionsToText:
    """Cover the line-137 early-return when header and sections are empty."""

    def test_empty_input_returns_empty_string(self):
        """Line 137: sections_to_text with empty header and no sections."""
        result = sections_to_text("", [])
        assert result == ""


class TestParseSectionsEdgeCases:
    """Cover parse_sections edge cases including heading-inside-fence
    (exercising line 109-110 header accumulation)."""

    def test_fenced_heading_not_treated_as_section(self):
        """A heading (#, ##, ###) inside a fenced code block before the
        first real heading should be treated as header content, not a section."""
        text = (
            "Preamble text\n"
            "```\n"
            "## Not a real heading\n"
            "body in fence\n"
            "```\n"
            "## Real Heading\n"
            "real body\n"
        )
        header, sections = parse_sections(text)
        assert "## Not a real heading" in header, (
            "Fenced heading should appear in header"
        )
        assert len(sections) == 1
        assert sections[0].heading == "## Real Heading"


class TestClassifySectionsEdgeCases:
    """Cover classification edges: placeholder KEEP (lines 214-215)."""

    def test_placeholder_future_triggers_keep(self):
        """Lines 213-215: when future body is a placeholder,
        the section is classified as KEEP with current content preserved."""
        current = (
            "## Active Initiative: test\n"
            "_(none configured)_\n"
        )
        future = (
            "## Active Initiative: test\n"
            "_(none configured)_\n"
        )
        # current == future, so it's already KEEP via the equality branch.
        # Force the placeholder path: modify current so it differs.
        current = (
            "## Active Initiative: test\n"
            "user's real initiative content\n"
        )
        # future still has the placeholder — the tool template
        c = classify_sections(current, future)
        section = [x for x in c if x.heading == "## Active Initiative: test"]
        assert len(section) == 1
        assert section[0].category == KEEP, (
            "Placeholder future body should not overwrite user content"
        )
        assert section[0].current_content == "user's real initiative content\n"

    def test_non_placeholder_different_body_triggers_overwrite(self):
        """Contrast: when future body is NOT a placeholder and differs,
        classification is OVERWRITE."""
        current = (
            "## Context Management\n"
            "old version\n"
        )
        future = (
            "## Context Management\n"
            "new version\n"
        )
        c = classify_sections(current, future)
        section = [x for x in c if x.heading == "## Context Management"]
        assert len(section) == 1
        assert section[0].category == OVERWRITE


class TestApplyMergeEdgeCases:
    """Cover apply_merge edges: OUTDATED (line 292) and unknown class (line 303)."""

    def test_outdated_classification_kept_as_is(self):
        """Line 292: OUTDATED classification keeps the original section."""
        classifications = [
            SectionClassification(
                heading="## Old Section",
                category=OUTDATED,
                current_content="old body\n",
            ),
        ]
        result = apply_merge(classifications, "## Old Section\nold body\n", "")
        assert "## Old Section" in result
        assert "old body" in result

    def test_unknown_classification_raises_value_error(self):
        """Line 303: a classification with an unknown category raises ValueError."""
        classifications = [
            SectionClassification(
                heading="## Bogus",
                category="UNKNOWN_CATEGORY",
                current_content="body\n",
            ),
        ]
        current = "## Bogus\nbody\n"
        with pytest.raises(ValueError, match="Unknown classification"):
            apply_merge(classifications, current, "")

    def test_merge_add_preserved_in_output(self):
        """MERGE_ADD sections are appended when they do not exist in current."""
        classifications = [
            SectionClassification(
                heading="## New Section",
                category=MERGE_ADD,
                future_content="new content\n",
            ),
        ]
        result = apply_merge(classifications, "## Existing\nold content\n", "")
        assert "## New Section" in result
        assert "new content" in result
        assert "## Existing" in result


class TestVerifyProtected:
    """Cover verify_protected: truncation (lines 320-321) and modification
    (line 325)."""

    def test_truncated_protected_span_detected(self):
        """Lines 320-321: when merged document is shorter than the protected
        span, a truncation violation is reported."""
        original = (
            "## Safe\n"
            "ok\n"
            "<!-- PROTECTED -->\n"
            "line one\n"
            "line two\n"
            "line three\n"
            "<!-- END PROTECTED -->\n"
        )
        # Merged is truncated — the protected span extends past its end.
        merged = (
            "## Safe\n"
            "ok\n"
            "<!-- PROTECTED -->\n"
            "line one\n"
        )
        violations = verify_protected(original, merged)
        assert len(violations) >= 1
        assert any("truncated" in v for v in violations)

    def test_modified_protected_span_detected(self):
        """Line 325: when protected content differs, a modification violation
        is reported."""
        original = (
            "## Safe\n"
            "ok\n"
            "<!-- PROTECTED -->\n"
            "secret content\n"
            "<!-- END PROTECTED -->\n"
        )
        merged = (
            "## Safe\n"
            "ok\n"
            "<!-- PROTECTED -->\n"
            "changed content\n"
            "<!-- END PROTECTED -->\n"
        )
        violations = verify_protected(original, merged)
        assert len(violations) >= 1
        assert any("modified" in v for v in violations)

    def test_no_violations_when_protected_intact(self):
        """Happy path: identical protected spans yield no violations."""
        original = (
            "## Safe\n"
            "ok\n"
            "<!-- PROTECTED -->\n"
            "secret content\n"
            "<!-- END PROTECTED -->\n"
        )
        violations = verify_protected(original, original)
        assert violations == []
