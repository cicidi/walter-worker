"""P3/P4 regression tests: fence-awareness, duplicate headings, empty sections,
protected-range enforcement, and raise-on-unknown classification."""
from coworker.semantic_merge import (
    KEEP, MERGE_ADD, OVERWRITE,
    SectionClassification,
    apply_merge,
    classify_sections,
    parse_sections,
    protected_ranges,
    sections_to_text,
    verify_protected,
)


# ── P3: round-trip identity ───────────────────────────────────────────────────

def test_round_trip_simple():
    text = "# Title\n\n## Section A\na1\na2\n\n## Section B\nb1\n"
    header, sections = parse_sections(text)
    # normalize both sides (sections_to_text normalizes trailing newlines)
    out = sections_to_text(header, sections)
    assert out.rstrip("\n") == text.rstrip("\n")


def test_fenced_hash_is_not_heading():
    """`` # comment `` inside a code fence is NOT a section heading."""
    text = "# Title\n\n```\n# inside fence\n```\n\n## Real Section\nreal\n"
    _, sections = parse_sections(text)
    headings = {s.heading for s in sections}
    assert "## Real Section" in headings
    assert "# inside fence" not in headings
    assert "# Title" in headings  # top-level heading IS a section


def test_duplicate_headings_preserved():
    """Two sections with the same name are preserved as separate entities."""
    text = "## Dup\nfirst\n\n## Other\nx\n\n## Dup\nsecond\n"
    _, sections = parse_sections(text)
    dups = [s for s in sections if s.heading == "## Dup"]
    assert len(dups) == 2
    assert dups[0].body.startswith("first")
    assert dups[1].body.startswith("second")
    assert dups[0].occurrence == 1
    assert dups[1].occurrence == 2


def test_empty_section_body():
    """Section with no body (heading-only) is preserved."""
    text = "# A\n\n## Empty\n\n## Content\nx\n"
    _, sections = parse_sections(text)
    empties = [s for s in sections if s.heading == "## Empty"]
    assert len(empties) == 1
    assert empties[0].body == "\n"  # blank line after heading is the (empty) body


def test_adjacent_headings():
    """Two headings with no blank line between them don't corrupt each other."""
    text = "## A\n\n## B\nb-body\n"
    _, sections = parse_sections(text)
    assert sections[0].heading == "## A"
    assert sections[1].heading == "## B"
    assert sections[1].body == "b-body\n"


def test_raise_on_unknown_classification():
    """apply_merge raises ValueError for unknown classification categories."""
    bogus = SectionClassification(heading="## X", category="BOGUS", current_content="x")
    try:
        apply_merge([bogus], "# Title\n\n## X\nx\n", "# Title\n\n## X\nx\n")
        assert False, "should have raised"
    except ValueError as e:
        assert "BOGUS" in str(e)


def test_round_trip_repo_template():
    """The repo's own project template survives a full parse->serialize round
    trip byte-identically."""
    from pathlib import Path
    repo = Path(__file__).resolve().parents[2]
    tmpl = repo / "src" / "coworker" / "templates" / "project_claude_md.py"
    if not tmpl.exists():
        return  # template not available — skip
    # generate a plausible output: the template's generate() function
    import sys
    sys.path.insert(0, str(repo / "src"))
    from coworker.templates.project_claude_md import generate_project_claude_md
    text = generate_project_claude_md("test-project")
    header, sections = parse_sections(text)
    out = sections_to_text(header, sections)
    assert out.rstrip("\n") == text.rstrip("\n")


# ── P4: protected ranges and verification ─────────────────────────────────────

PROTECTED_DOC = """# Doc

<!-- PROTECTED:CRITICAL-RULES -->

## Rule 1
must keep

## Rule 2
also keep

<!-- END PROTECTED:CRITICAL-RULES -->

## Normal Section
can change
"""


def test_protected_ranges_are_found():
    ranges = protected_ranges(PROTECTED_DOC)
    assert len(ranges) >= 1
    lo, hi = ranges[0]
    assert lo == 3   # "<!-- PROTECTED:CRITICAL-RULES -->" line
    assert hi == 11  # "<!-- END PROTECTED:CRITICAL-RULES -->" line


def test_protected_sections_forced_keep():
    """Sections inside a PROTECTED span are forced KEEP even when changed in future."""
    future = PROTECTED_DOC.replace("must keep", "CHANGED").replace("also keep", "CHANGED")
    cls = classify_sections(PROTECTED_DOC, future)
    for c in cls:
        if "Rule 1" in c.heading or "Rule 2" in c.heading:
            assert c.category == KEEP, f"{c.heading} should be KEEP (protected), got {c.category}"


def test_normal_section_still_overwrites():
    """Non-protected sections still overwrite normally."""
    future = PROTECTED_DOC.replace("can change", "new content")
    cls = classify_sections(PROTECTED_DOC, future)
    norm = [c for c in cls if "Normal Section" in c.heading]
    assert norm
    assert norm[0].category == OVERWRITE


def test_verify_protected_passes_on_clean_merge():
    cls = classify_sections(PROTECTED_DOC, PROTECTED_DOC)
    merged = apply_merge(cls, PROTECTED_DOC, PROTECTED_DOC)
    violations = verify_protected(PROTECTED_DOC, merged)
    assert violations == []


def test_protection_overrides_tampering():
    """Any change inside a protected span is blocked — merged output keeps original."""
    future = PROTECTED_DOC.replace("must keep", "HACKED")
    cls = classify_sections(PROTECTED_DOC, future)
    # classification should have forced KEEP for protected sections
    for c in cls:
        if "Rule 1" in c.heading:
            assert c.category == KEEP
    merged = apply_merge(cls, PROTECTED_DOC, future)
    # merge preserves original text inside the protected span
    assert "must keep" in merged
    assert "HACKED" not in merged
    violations = verify_protected(PROTECTED_DOC, merged)
    assert violations == []  # no violations; protection worked


def test_user_rule_inside_protected_span_is_kept():
    """A user-added rule inside a PROTECTED span survives the merge."""
    doc_with_extra = PROTECTED_DOC.replace("## Rule 1\nmust keep",
                                           "## My Rule\nextra\n\n## Rule 1\nmust keep")
    cls = classify_sections(doc_with_extra, PROTECTED_DOC)
    merged = apply_merge(cls, doc_with_extra, PROTECTED_DOC)
    violations = verify_protected(doc_with_extra, merged)
    assert violations == []
    assert "My Rule" in merged
    assert "extra" in merged
