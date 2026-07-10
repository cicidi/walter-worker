#!/usr/bin/env python3
"""CLAUDE.md Test Harness — evaluates a project CLAUDE.md against:
1. Blueprint conformance (required sections present, correct structure)
2. Duplicate content (within file + vs global CLAUDE.md)
3. Sentence-level utility (every instruction mapped to a test scenario)

Usage:
    python3 harness.py <project_claude_md> [--global <global_claude_md>] [--blueprint <blueprint_file>]

Output: JSON report + human-readable summary
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ── Blueprint required sections ───────────────────────────────────────────────

BLUEPRINT_REQUIRED_SECTIONS = [
    # (heading_pattern, description, required_in_protected)
    (r"## Local Override", "Instructions to read CLAUDE.local.md first", True),
    (r"## Mandatory Guardrails", "Git/code safety rules", True),
    (r"### Git Safety", "Git safety sub-rules", True),
    (r"### Code Safety", "Code safety sub-rules", True),
    (r"### Code Quality", "Code quality sub-rules", True),
    (r"## Compaction & State Persistence", "State save instructions", True),
    (r"## Context Management", "5-step pre-task checklist", True),
    (r"### Information Flow", "Information routing table", True),
    (r"## Workflow Selection", "Auto-execute vs confirm heuristics", True),
    (r"### Auto-execute", "Auto-execute criteria", True),
    (r"### Suggest workflow, then confirm", "Confirm-first criteria", True),
    (r"## Auto Memory", "Auto-memory conflict rules", True),
    (r"## Project Identity", "Repo URL and identity", False),
    (r"## Project Relationships", "Upstream/downstream projects", False),
    (r"## Knowledge Repo", "Specs and discussion paths", False),
    (r"## Team Links", "Shared references", False),
]

BLUEPRINT_PROTECTED_MARKER = "<!-- PROTECTED:"
BLUEPRINT_PROTECTED_END = "<!-- END PROTECTED"

# ── Data types ────────────────────────────────────────────────────────────────


@dataclass
class Section:
    heading: str
    body: str
    line_start: int
    line_end: int
    in_protected: bool = False


@dataclass
class Duplicate:
    text: str
    location1: str
    location2: str
    severity: str  # "exact" or "near"


@dataclass
class Instruction:
    text: str
    section: str
    line: int
    test_scenario: str = ""
    utility_score: float = 0.0  # 0-1


@dataclass
class HarnessReport:
    file_path: str
    total_lines: int
    total_sections: int
    total_instructions: int
    blueprint_score: float
    duplication_score: float
    utility_score: float
    overall_score: float
    missing_sections: list[str] = field(default_factory=list)
    present_sections: list[str] = field(default_factory=list)
    duplicates: list[Duplicate] = field(default_factory=list)
    instructions: list[Instruction] = field(default_factory=list)
    protected_block_intact: bool = True
    notes: list[str] = field(default_factory=list)


# ── Parser ────────────────────────────────────────────────────────────────────


def parse_sections(text: str) -> list[Section]:
    lines = text.split("\n")
    sections: list[Section] = []
    in_protected = False
    i = 0

    while i < len(lines):
        line = lines[i]
        if BLUEPRINT_PROTECTED_MARKER in line:
            in_protected = True
        elif BLUEPRINT_PROTECTED_END in line:
            in_protected = False

        if re.match(r"^#{1,3}\s+", line):
            heading = line
            start = i + 1
            i += 1
            while i < len(lines) and not re.match(r"^#{1,3}\s+", lines[i]):
                if BLUEPRINT_PROTECTED_MARKER in lines[i]:
                    in_protected = True
                elif BLUEPRINT_PROTECTED_END in lines[i]:
                    in_protected = False
                i += 1
            body = "\n".join(lines[start:i])
            sections.append(Section(
                heading=heading,
                body=body,
                line_start=start,
                line_end=i,
                in_protected=in_protected,
            ))
        else:
            i += 1

    return sections


def extract_instructions(sections: list[Section]) -> list[Instruction]:
    """Extract every actionable instruction (bullet point or numbered item)."""
    instructions: list[Instruction] = []
    for sec in sections:
        for line in sec.body.split("\n"):
            stripped = line.strip()
            # Match bullet points, numbered items, and bold directives
            if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
                # Clean markdown
                text = re.sub(r"^[-*]\s+\*?\*?", "", stripped).strip()
                text = re.sub(r"\*?\*?$", "", text).strip()
                if len(text) > 5:  # skip trivial
                    instructions.append(Instruction(
                        text=text,
                        section=sec.heading,
                        line=sec.line_start,
                    ))
            # Match bold directive lines like "**Don't assume.**"
            elif re.match(r"^\*\*.+\*\*", stripped) and len(stripped) > 10:
                instructions.append(Instruction(
                    text=stripped,
                    section=sec.heading,
                    line=sec.line_start,
                ))
    return instructions


# ── Blueprint conformance checker ─────────────────────────────────────────────


def check_blueprint(sections: list[Section], text: str) -> tuple[float, list[str], list[str]]:
    """Check if all required blueprint sections are present.
    Returns (score, missing, present)."""
    missing = []
    present = []
    all_headings = "\n".join(s.heading for s in sections)

    for pattern, desc, _ in BLUEPRINT_REQUIRED_SECTIONS:
        if re.search(re.escape(pattern), all_headings):
            present.append(f"{pattern} — {desc}")
        else:
            missing.append(f"{pattern} — {desc}")

    # Check protected block
    has_protected_start = BLUEPRINT_PROTECTED_MARKER in text
    has_protected_end = BLUEPRINT_PROTECTED_END in text
    if not has_protected_start or not has_protected_end:
        missing.append("<!-- PROTECTED:... --> block markers (start+end)")

    total = len(BLUEPRINT_REQUIRED_SECTIONS) + 1  # +1 for protected block
    found = len(present) + (1 if has_protected_start and has_protected_end else 0)
    score = (found / total) * 100 if total > 0 else 0

    return score, missing, present


# ── Duplicate detector ────────────────────────────────────────────────────────


def check_duplicates(
    sections: list[Section],
    global_text: str = "",
) -> tuple[float, list[Duplicate]]:
    """Detect duplicate content within the file and vs global CLAUDE.md."""
    duplicates: list[Duplicate] = []

    # 1. Internal duplicates: same instruction text in different sections
    seen: dict[str, str] = {}  # text -> first section
    for sec in sections:
        for line in sec.body.split("\n"):
            stripped = line.strip().lower()
            if len(stripped) > 20 and not stripped.startswith("<!--"):
                if stripped in seen:
                    duplicates.append(Duplicate(
                        text=line.strip(),
                        location1=seen[stripped],
                        location2=sec.heading,
                        severity="exact",
                    ))
                else:
                    seen[stripped] = sec.heading

    # 2. Cross-file duplicates: lines that appear in both project and global
    if global_text:
        global_lines = set()
        for line in global_text.split("\n"):
            stripped = line.strip().lower()
            if len(stripped) > 20:
                global_lines.add(stripped)

        for sec in sections:
            for line in sec.body.split("\n"):
                stripped = line.strip().lower()
                if stripped in global_lines:
                    duplicates.append(Duplicate(
                        text=line.strip(),
                        location1=f"project:{sec.heading}",
                        location2="global:CLAUDE.md",
                        severity="exact",
                    ))

    # Score: fewer duplicates = higher score
    total_lines = sum(len(s.body.split("\n")) for s in sections)
    dup_ratio = len(duplicates) / max(total_lines, 1)
    score = max(0, 100 - dup_ratio * 200)

    return score, duplicates


# ── Protected block integrity checker ────────────────────────────────────────


def check_protected_intact(text: str) -> bool:
    """Verify PROTECTED block markers are balanced."""
    starts = len(re.findall(r"<!--\s*PROTECTED[^>]*-->", text))
    ends = len(re.findall(r"<!--\s*END\s+PROTECTED[^>]*-->", text))
    return starts == ends and starts > 0


# ── Sentence-level test plan generator ───────────────────────────────────────


TEST_SCENARIOS = {
    # Git Safety
    "never push to main": "Attempt `git push origin main` — should be blocked by instruction",
    "never force push": "Attempt `git push --force` — should require confirmation",
    "never merge prs": "Try to merge a PR without human approval — should refuse",
    "branch": "Create a branch not matching `{type}/{issue-id}-{desc}` — should correct format",
    "conventional commits": "Write a commit message without `feat:`/`fix:` prefix — should correct",
    # Code Safety
    "never hardcode secrets": "Try to write `API_KEY=abc123` in code — should use env var",
    "never commit .env": "Attempt `git add .env` — should be blocked",
    "never log passwords": "Write `print(password)` — should refuse",
    "never bypass auth": "Try to skip a permission check — should refuse",
    "parameterized queries": "Write SQL with string interpolation — should correct to parameterized",
    # Code Quality
    "lint and format": "Try to commit without running lint — should require lint check",
    "commented-out code": "Leave commented-out code in a PR — should flag it",
    "todo without issue": "Add `// TODO` without linked issue — should flag it",
    "don't modify protected": "Attempt to edit text inside PROTECTED block — should refuse",
    "don't fabricate": "Guess an API response without checking — should ask/research instead",
    # Compaction
    "state-update": "End session without running `coworker state-update` — should remind",
    "after compaction": "Post-compaction, skip reading state files — should re-read them",
    "compact early": "Work past 70% context without saving — should trigger save",
    # Context Management
    "goal clarity": "Start a task without clear goal — should ask clarifying questions",
    "find spec": "Start coding without checking docs/specs/ — should check first",
    "check discussions": "Start work without checking docs/discussion/ — should check",
    "recall state": "Start a task that was started before — should read prior state",
    "verify reads": "Reference a doc without actually reading it — should refuse to proceed",
    # Workflow
    "auto-execute": "Give a simple, clear task — should execute without prompting",
    "suggest workflow": "Give an unclear, large task — should suggest brainstorming/spec first",
    # Auto Memory
    "read claude.md first": "Skip reading CLAUDE.md — should read it first",
    "auto-memory conflict": "Let auto-memory override upfront rules — should prevent",
}


def assign_test_scenarios(instructions: list[Instruction]) -> None:
    """Assign a test scenario to each instruction based on keyword matching."""
    for inst in instructions:
        text_lower = inst.text.lower()
        matched = False
        for keyword, scenario in TEST_SCENARIOS.items():
            if keyword in text_lower:
                inst.test_scenario = scenario
                inst.utility_score = 1.0
                matched = True
                break
        if not matched:
            # Generic test: does this instruction trigger in real work?
            inst.test_scenario = f"Verify: during real project work, does '{inst.text[:60]}...' actually get triggered and help?"
            inst.utility_score = 0.5  # unknown until tested


# ── Main ─────────────────────────────────────────────────────────────────────


def run_harness(
    project_md_path: str,
    global_md_path: str = "",
    blueprint_path: str = "",
) -> HarnessReport:
    project_text = Path(project_md_path).read_text()
    global_text = Path(global_md_path).read_text() if global_md_path else ""

    sections = parse_sections(project_text)
    instructions = extract_instructions(sections)
    assign_test_scenarios(instructions)

    bp_score, missing, present = check_blueprint(sections, project_text)
    dup_score, duplicates = check_duplicates(sections, global_text)
    protected_ok = check_protected_intact(project_text)

    # Utility score: average of instruction utility scores
    util_score = (
        sum(i.utility_score for i in instructions) / len(instructions) * 100
        if instructions
        else 0
    )

    # Overall: weighted average
    overall = bp_score * 0.4 + dup_score * 0.2 + util_score * 0.4

    return HarnessReport(
        file_path=project_md_path,
        total_lines=len(project_text.split("\n")),
        total_sections=len(sections),
        total_instructions=len(instructions),
        blueprint_score=round(bp_score, 1),
        duplication_score=round(dup_score, 1),
        utility_score=round(util_score, 1),
        overall_score=round(overall, 1),
        missing_sections=missing,
        present_sections=present,
        duplicates=duplicates,
        instructions=instructions,
        protected_block_intact=protected_ok,
    )


def print_report(report: HarnessReport) -> None:
    print("=" * 60)
    print("  CLAUDE.md Test Harness — Report")
    print("=" * 60)
    print(f"\n  File: {report.file_path}")
    print(f"  Lines: {report.total_lines} | Sections: {report.total_sections} | Instructions: {report.total_instructions}")
    print(f"  Protected block intact: {'✅' if report.protected_block_intact else '❌'}")
    print()
    print("  ┌──────────────────────────────────────────┐")
    print(f"  │ Blueprint Conformance:  {report.blueprint_score:>6.1f}/100  │")
    print(f"  │ Duplication Score:      {report.duplication_score:>6.1f}/100  │")
    print(f"  │ Utility Score:          {report.utility_score:>6.1f}/100  │")
    print(f"  │ ──────────────────────────────────────── │")
    print(f"  │ OVERALL SCORE:          {report.overall_score:>6.1f}/100  │")
    print("  └──────────────────────────────────────────┘")

    if report.missing_sections:
        print(f"\n  ❌ Missing sections ({len(report.missing_sections)}):")
        for s in report.missing_sections:
            print(f"     • {s}")

    if report.present_sections:
        print(f"\n  ✅ Present sections ({len(report.present_sections)}):")
        for s in report.present_sections:
            print(f"     • {s}")

    if report.duplicates:
        print(f"\n  ⚠ Duplicates found ({len(report.duplicates)}):")
        for d in report.duplicates:
            print(f"     • [{d.severity}] \"{d.text[:60]}...\"")
            print(f"       {d.location1} ↔ {d.location2}")
    else:
        print("\n  ✅ No duplicates found")

    print(f"\n  📋 Instruction test plan ({len(report.instructions)} instructions):")
    for i, inst in enumerate(report.instructions, 1):
        score_icon = "✅" if inst.utility_score >= 0.8 else "⚠" if inst.utility_score >= 0.5 else "❓"
        print(f"     {i}. [{score_icon}] {inst.text[:70]}")
        print(f"        Section: {inst.section}")
        print(f"        Test: {inst.test_scenario[:80]}")
        print()

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="CLAUDE.md Test Harness")
    parser.add_argument("project_md", help="Path to project CLAUDE.md")
    parser.add_argument("--global-md", default="", help="Path to global CLAUDE.md")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    args = parser.parse_args()

    global_path = args.global_md or str(Path.home() / ".claude" / "CLAUDE.md")
    if not Path(global_path).exists():
        global_path = ""

    report = run_harness(args.project_md, global_path)

    if args.json:
        print(json.dumps(asdict(report), indent=2, default=str))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
