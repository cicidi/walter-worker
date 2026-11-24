"""Semantic merge for CLAUDE.md/doc documents.

Parses markdown into an ordered list of headed Sections (fence-aware,
preserving duplicate heading names and empty/trailing bodies). Classifies
each section as KEEP/OVERWRITE/MERGE_ADD/OUTDATED, respecting <!-- PROTECTED
... --> block-spanning markers. Applies the merge or raises on unknown
classification.

Round-trip invariant: parse_sections followed by sections_to_text on the
same document must produce byte-identical output.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

OUTDATED = "OUTDATED"
OVERWRITE = "OVERWRITE"
MERGE_ADD = "MERGE_ADD"
KEEP = "KEEP"
#: The incoming template would delete lines that exist only in the user's copy.
#: Kept rather than overwritten, and reported, because the alternative is
#: silently destroying text the user wrote.
CONFLICT = "CONFLICT"

_HEADING_RE = re.compile(r"^#{1,3}\s+.+$")
_H1_RE = re.compile(r"^#\s+.+$")
_FENCE_RE = re.compile(r"^\s*(```+|~~~+)\s*$")

_PLACEHOLDER_PATTERNS = [
    re.compile(r"_\(none configured\)_"),
    re.compile(r"_Repo URL auto-discovered by AI\._"),
    re.compile(r"_\(run `coworker init` to scan docs/ structure\)_"),
    re.compile(r"_\(none configured — add shared wikis, Slack channels, design docs\)_"),
]


def _is_placeholder(body: str) -> bool:
    stripped = body.strip()
    if not stripped:
        return False
    return any(p.search(stripped) for p in _PLACEHOLDER_PATTERNS)


# ── data types ────────────────────────────────────────────────────────────────


@dataclass
class SectionClassification:
    heading: str
    category: str
    current_content: str = ""
    future_content: str = ""
    #: For CONFLICT: the lines an overwrite would have deleted.
    at_risk: list[str] = field(default_factory=list)


def _user_added_lines(current_body: str, future_body: str) -> list[str]:
    """Lines the user's copy carries that the incoming template does not.

    Not proof of authorship: a line the template itself dropped between
    versions looks identical from here. So this errs toward preserving — a
    false positive costs the user one review, a false negative costs them the
    text.
    """
    future = {line.strip() for line in future_body.splitlines() if line.strip()}
    return [
        line.strip() for line in current_body.splitlines()
        if line.strip() and line.strip() not in future
    ]


@dataclass
class Section:
    heading: str
    body: str       # body text, no final-normalization guarantee
    occurrence: int = 1
    line_start: int = 0
    line_end: int = 0
    raw: str = ""   # heading + "\n" + body (exact original text for round-trip)


# ── fence-aware line scanner ──────────────────────────────────────────────────


def _scan_lines(text: str) -> list[tuple[str, bool]]:
    """Split text into (line, in_fence) pairs.  Lines inside a ``` or ~~~ fence
    block have in_fence=True and are never treated as headings."""
    result: list[tuple[str, bool]] = []
    in_fence = False
    fence_char = ""
    lines = text.split("\n")
    # Drop trailing empty string artifact from Python's split()
    if lines and lines[-1] == "":
        lines.pop()
    for line in lines:
        m = _FENCE_RE.match(line)
        if m:
            chars = m.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_char = chars
            elif chars == fence_char:
                in_fence = False
                fence_char = ""
        result.append((line, in_fence))
    return result


# ── section parser ────────────────────────────────────────────────────────────


def parse_sections(text: str) -> tuple[str, list[Section]]:
    """Parse markdown text into (header, ordered list of Sections).

    * Duplicate heading names are preserved (ordered, occurrence-indexed).
    * Sections within fenced code blocks are NOT treated as headings.
    * Empty-body and trailing sections are preserved.
    * Round-trip: ``sections_to_text(header, parse_sections(text)[1]) == text``.
    """
    header_lines: list[str] = []
    sections: list[Section] = []
    occurrence: dict[str, int] = {}

    scanned = _scan_lines(text)
    total = len(scanned)

    i = 0
    while i < total and not (scanned[i][1] is False and _HEADING_RE.match(scanned[i][0])):
        header_lines.append(scanned[i][0])
        i += 1

    while i < total:
        heading = scanned[i][0]
        i += 1
        body_start = i
        while i < total and not (scanned[i][1] is False and _HEADING_RE.match(scanned[i][0])):
            i += 1
        body = "\n".join(scanned[j][0] for j in range(body_start, i)) + "\n" if body_start < i else "\n"
        occurrence.setdefault(heading, 0)
        occurrence[heading] += 1
        sections.append(Section(
            heading=heading,
            body=body,
            occurrence=occurrence[heading],
            line_start=body_start + 1,
            line_end=i,
            raw=heading + "\n" + body,
        ))

    return ("\n".join(header_lines), sections)


def sections_to_text(header: str, sections: list[Section]) -> str:
    """Serialize back to markdown.  Normalizes to a single trailing newline."""
    text = header + "".join(s.raw for s in sections)
    if not text:
        return text
    return text.rstrip("\n") + "\n"


# ── protected-range parser ────────────────────────────────────────────────────


# Both marker spellings are accepted, because both are in use:
#   <!-- PROTECTED -->            ... <!-- END PROTECTED -->
#   <!-- PROTECTED START -->      ... <!-- PROTECTED END -->
#
# The start pattern must not match an end marker. It previously did - the old
# `PROTECTED[^>]*` matched "PROTECTED END" too - so writing the second spelling
# opened a *new* span that ran to EOF, and the end pattern (which only knew
# "END PROTECTED") never closed it. Everything after the marker was silently
# over-protected: the section was pinned to its old content forever and
# verify_protected() reported the growing span as a modification.
_PROTECTED_START_RE = re.compile(r"<!--\s*PROTECTED(?![^>]*\bEND\b)[^>]*\s*-->")
_PROTECTED_END_RE = re.compile(
    r"<!--\s*(?:END\s+PROTECTED|PROTECTED[^>]*\bEND\b)[^>]*\s*-->"
)


def protected_ranges(text: str) -> list[tuple[int, int]]:
    """Return inclusive (start_line, end_line) ranges protected by
    ``<!-- PROTECTED.. -->`` and ``<!-- END PROTECTED.. -->`` markers.

    Unclosed start markers protect through EOF.  End markers without a prior
    start are silently ignored (no error — the caller decides severity).
    """
    ranges: list[tuple[int, int]] = []
    stack: list[int] = []  # line numbers of unclosed start markers
    for i, line in enumerate(text.split("\n"), 1):
        if _PROTECTED_START_RE.search(line):
            stack.append(i)
        elif _PROTECTED_END_RE.search(line) and stack:
            start = stack.pop()
            ranges.append((start, i))
    while stack:
        start = stack.pop()
        ranges.append((start, i))  # to EOF
    return ranges


# ── classification ────────────────────────────────────────────────────────────


def classify_sections(
    current: str, future: str, base: str | None = None,
) -> list[SectionClassification]:
    """Compare current and future CLAUDE.md, classify each section.

    Sections wholly inside a <!-- PROTECTED --> .. <!-- END PROTECTED --> span
    are forced KEEP regardless of body changes.  The header (content before the
    first heading) is always kept.

    ``base`` is the template as it was last written to the file. With it, a
    differing section is a three-way decision: only the template changed →
    OVERWRITE; only the user changed → KEEP; both → CONFLICT. Without it, the
    two-way heuristic below decides, and an OVERWRITE lists in ``at_risk`` the
    lines it replaces so the caller can show them before writing.
    """
    header, current_sections = parse_sections(current)
    _, future_sections = parse_sections(future)
    base_by_key: dict[tuple[str, int], Section] = {}
    if base is not None:
        for b in parse_sections(base)[1]:
            base_by_key[(b.heading, b.occurrence)] = b

    # Build (heading, occurrence) -> future section lookup
    future_by_key: dict[tuple[str, int], Section] = {}
    for s in future_sections:
        future_by_key[(s.heading, s.occurrence)] = s

    # Determine which current sections are inside a protected block (P4).
    protected_spans = protected_ranges(current)
    def _is_protected(line_start: int) -> bool:
        return any(lo <= line_start <= hi for (lo, hi) in protected_spans)

    classifications: list[SectionClassification] = []
    for s in current_sections:
        key = (s.heading, s.occurrence)
        fut = future_by_key.get(key)

        # Protected spans force KEEP
        if _is_protected(s.line_start):
            classifications.append(SectionClassification(
                heading=s.heading, category=KEEP, current_content=s.body,
            ))
            continue

        # Legacy heuristic — kept for backward compat with pre-P4 markers.
        # Both marker dialects are protected: INITIATIVE is what CLAUDE.local.md
        # files created before the rename still carry, and letting `coworker
        # upgrade` merge over one would destroy the user's active context.
        if (
            "<!-- PROTECTED" in s.body
            or "<!-- FEATURE:" in s.body
            or "<!-- INITIATIVE:" in s.body
        ):
            classifications.append(SectionClassification(
                heading=s.heading, category=KEEP, current_content=s.body,
            ))
            continue

        if fut is not None:
            if s.body.strip() != fut.body.strip():
                at_risk: list[str] = []
                if _is_placeholder(fut.body) or s.body.strip().startswith(fut.body.strip()):
                    # The user appended to the template's text, or the slot is
                    # still a placeholder: nothing of theirs is at stake.
                    cat = KEEP
                elif key in base_by_key:
                    old = base_by_key[key].body.strip()
                    user_changed = s.body.strip() != old
                    template_changed = fut.body.strip() != old
                    if not user_changed:
                        cat = OVERWRITE
                    elif not template_changed:
                        cat = KEEP
                    else:
                        cat = CONFLICT
                        # The base says which lines are the user's own.
                        theirs = set(_user_added_lines(s.body, base_by_key[key].body))
                        at_risk = [l for l in _user_added_lines(s.body, fut.body) if l in theirs]
                else:
                    user_only = _user_added_lines(s.body, fut.body)
                    template_only = _user_added_lines(fut.body, s.body)
                    if user_only and not template_only:
                        # The user's copy holds everything the template offers
                        # plus lines of its own, so there is no template
                        # improvement here to prefer — overwriting could only
                        # destroy. Keep theirs and say what is at stake.
                        #
                        # Requiring template_only to be empty is what keeps this
                        # from firing on an ordinary template rewording, where
                        # both sides differ; those still overwrite as before.
                        cat = CONFLICT
                        at_risk = user_only
                    else:
                        # No base, so these may be old template lines rather
                        # than the user's; either way they are shown first.
                        cat = OVERWRITE
                        at_risk = user_only
                classifications.append(SectionClassification(
                    heading=s.heading, category=cat,
                    current_content=s.body,
                    # Kept even for KEEP/CONFLICT so a caller can reconsider the
                    # decision — `upgrade --force` flips CONFLICT to OVERWRITE
                    # and needs the text it is switching to.
                    future_content=fut.body,
                    at_risk=at_risk,
                ))
            else:
                classifications.append(SectionClassification(
                    heading=s.heading, category=KEEP, current_content=s.body,
                ))
        else:
            classifications.append(SectionClassification(
                heading=s.heading, category=KEEP, current_content=s.body,
            ))

    for s in future_sections:
        if _H1_RE.match(s.heading):
            continue
        key = (s.heading, s.occurrence)
        if key not in {(cs.heading, None) for cs in current_sections}:
            # Check by heading name only (legacy dict-based lookup fallback)
            cur_names = {c.heading for c in current_sections}
            if s.heading not in cur_names:
                classifications.append(SectionClassification(
                    heading=s.heading, category=MERGE_ADD, future_content=s.body,
                ))

    return classifications


# ── merge application ─────────────────────────────────────────────────────────


def apply_merge(
    classifications: list[SectionClassification],
    current: str,
    future: str,
) -> str:
    """Apply classified changes to produce the merged document.

    Raises ValueError for any unknown classification — this forces developers
    to explicitly handle new classification types rather than silently skip.
    """
    header, current_sections = parse_sections(current)

    # Build a map: heading -> list of classifications (for same-named sections)
    by_heading: dict[str, list[SectionClassification]] = {}
    for c in classifications:
        by_heading.setdefault(c.heading, []).append(c)

    out: list[Section] = []
    used: dict[str, set[int]] = {}  # per-heading occurrence tracking

    for s in current_sections:
        choices = by_heading.get(s.heading, [])
        # pick the first unused classification for this heading
        choice = None
        used_head = used.setdefault(s.heading, set())
        for idx, cls in enumerate(choices):
            if idx not in used_head and cls.current_content.strip() == s.body.strip():
                choice = cls
                used_head.add(idx)
                break
        if choice is None:
            # no explicit match — default to KEEP
            choice = SectionClassification(heading=s.heading, category=KEEP, current_content=s.body)

        cat = choice.category
        if cat in (KEEP, CONFLICT):
            # CONFLICT keeps the user's section: the difference is that it was
            # reported, not that it was resolved differently.
            out.append(s)
        elif cat == OVERWRITE:
            new_body = choice.future_content.rstrip("\n") + "\n\n" if choice.future_content else ""
            out.append(Section(heading=s.heading, body=choice.future_content,
                              occurrence=s.occurrence, raw=s.heading + "\n" + new_body))
        elif cat == OUTDATED:
            out.append(s)
        else:
            raise ValueError(f"Unknown classification: {cat!r} for section {s.heading!r}")

    # Append MERGE_ADD sections
    for c in classifications:
        if c.category == MERGE_ADD:
            new_body = c.future_content.rstrip("\n") + "\n\n" if c.future_content else ""
            out.append(Section(heading=c.heading, body=c.future_content,
                              occurrence=1, raw=c.heading + "\n" + new_body))
        elif c.category not in (KEEP, CONFLICT, OVERWRITE, OUTDATED):
            raise ValueError(f"Unknown classification: {c.category!r}")

    return sections_to_text(header, out)


def next_base(
    classifications: list[SectionClassification],
    future: str,
    old_base: str | None,
) -> str:
    """The base to store after an upgrade: the template just merged, except
    that a CONFLICT section keeps its old base (or is left out when there was
    none). Taking the new template text there would make the next upgrade read
    the section as "template unchanged, user changed" and stop reporting it.
    """
    conflicts = {c.heading for c in classifications if c.category == CONFLICT}
    header, future_sections = parse_sections(future)
    old = {}
    if old_base is not None:
        old = {(s.heading, s.occurrence): s for s in parse_sections(old_base)[1]}
    out: list[Section] = []
    for s in future_sections:
        if s.heading not in conflicts:
            out.append(s)
        elif (s.heading, s.occurrence) in old:
            out.append(old[(s.heading, s.occurrence)])
    return sections_to_text(header, out)


# ── protection verification ───────────────────────────────────────────────────


def verify_protected(original: str, merged: str) -> list[str]:
    """Return violation descriptions.  Each span in 'original' that is marked
    <!-- PROTECTED --> ... <!-- END PROTECTED --> must appear byte-identical,
    in the same order, in 'merged'.  Returns empty list if all spans match.

    Spans are paired by order, not by line number: a section above a span may
    legitimately grow or shrink, and comparing at the old line numbers reported
    that as a modification of a span nobody touched.
    """
    violations: list[str] = []

    def spans(text: str) -> list[str]:
        lines = text.split("\n")
        return ["\n".join(lines[lo - 1 : hi]) for lo, hi in protected_ranges(text)]

    merged_spans = spans(merged)
    for i, ((lo, hi), orig_span) in enumerate(zip(protected_ranges(original), spans(original))):
        if i >= len(merged_spans):
            violations.append(f"Protected span {lo}-{hi} is missing from the merged document")
            continue
        merged_span = merged_spans[i]
        if merged_span == orig_span:
            continue
        if orig_span.startswith(merged_span):
            violations.append(f"Protected span {lo}-{hi} is truncated in merged document")
        else:
            violations.append(
                f"Protected span {lo}-{hi} was modified. "
                f"Original {len(orig_span)} bytes, merged {len(merged_span)} bytes."
            )
    return violations
