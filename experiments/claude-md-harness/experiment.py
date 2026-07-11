#!/usr/bin/env python3
"""CLAUDE.md Experiment Runner — evaluates and optimizes the 3-layer CLAUDE.md stack.

Usage:
    python3 experiment.py round <n>  — run a specific round
    python3 experiment.py auto 10    — run 10 rounds automatically
    python3 experiment.py score      — score the current stack
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

PROJECT = "mfangdai-ai-agent"
PROJECT_DIR = Path.home() / "project" / "mfangdai-ai-agent"
GLOBAL_MD = Path.home() / ".claude" / "CLAUDE.md"
RESULTS_DIR = Path(__file__).parent / "results"

BLUEPRINT_SECTIONS = [
    "## Local Override",
    "## Mandatory Guardrails",
    "### Git Safety",
    "### Code Safety",
    "### Code Quality",
    "## Compaction & State Persistence",
    "## Context Management",
    "### Information Flow",
    "## Workflow Selection",
    "## Auto Memory",
]

BLUEPRINT_LOCAL_SECTIONS = [
    "## Config Paths",
    "## Project Info",
    "## Reference Docs",
    "## Current Task State",
    "## Current Workflow",
    "## Personal Preferences",
]

BLUEPRINT_BUDGETS = {
    "global": 100,
    "project": 200,
    "local_template": 60,
}


@dataclass
class RoundResult:
    round_num: int
    commit: str
    global_lines: int = 0
    project_lines: int = 0
    local_lines: int = 0
    blueprint_score: float = 0.0
    duplication_score: float = 0.0
    utility_score: float = 0.0
    budget_score: float = 0.0
    overall_score: float = 0.0
    notes: list[str] = field(default_factory=list)
    instructions_count: int = 0
    instructions_useful: int = 0


def count_lines(path: Path) -> int:
    return len(path.read_text().split("\n")) if path.exists() else 0


def check_blueprint_3layer(project_md: str, local_md: str) -> tuple[float, list[str]]:
    missing = []
    present = []

    for section in BLUEPRINT_SECTIONS:
        if section in project_md:
            present.append(section)
        else:
            missing.append(f"[CLA.md] {section}")

    for section in BLUEPRINT_LOCAL_SECTIONS:
        if section in local_md:
            present.append(section)
        else:
            missing.append(f"[LOCAL.md] {section}")

    has_protected = "<!-- PROTECTED:CRITICAL-RULES -->" in project_md and "<!-- END PROTECTED:CRITICAL-RULES -->" in project_md
    if not has_protected:
        missing.append("[CLA.md] PROTECTED block markers")

    total = len(BLUEPRINT_SECTIONS) + len(BLUEPRINT_LOCAL_SECTIONS) + 1
    found = len(present) + (1 if has_protected else 0)
    score = (found / total) * 100
    return score, missing


def check_budget(g_lines: int, p_lines: int, l_lines: int) -> tuple[float, list[str]]:
    issues = []
    for name, limit, actual in [
        ("Global", BLUEPRINT_BUDGETS["global"], g_lines),
        ("Project", BLUEPRINT_BUDGETS["project"], p_lines),
        ("Local", BLUEPRINT_BUDGETS["local_template"], l_lines),
    ]:
        if actual > limit:
            issues.append(f"{name}: {actual}/{limit} lines (over by {actual - limit})")

    if not issues:
        return 100.0, []
    penalty = sum(5 for _ in issues)
    return max(0, 100 - penalty), issues


def extract_instructions(text: str) -> list[str]:
    """Extract actionable bullet-point instructions."""
    instructions = []
    for line in text.split("\n"):
        stripped = line.strip()
        if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            text_clean = re.sub(r"^[-*\d]+\s+\*?\*?", "", stripped).strip()
            text_clean = re.sub(r"\*?\*?$", "", text_clean).strip()
            if len(text_clean) > 5 and not text_clean.startswith("<!--"):
                instructions.append(text_clean)
    return instructions


def check_duplicates(g_text: str, p_text: str, l_text: str) -> tuple[float, list[str]]:
    """Check for cross-layer duplicates."""
    dupes = []
    seen = {}  # text -> location

    for layer_name, text in [("global", g_text), ("project", p_text), ("local", l_text)]:
        for line in text.split("\n"):
            s = line.strip().lower()
            if len(s) > 25:
                if s in seen:
                    dupes.append(f"'{line.strip()[:50]}...' in [{seen[s]}] and [{layer_name}]")
                else:
                    seen[s] = layer_name

    total_lines = len(g_text.split("\n")) + len(p_text.split("\n")) + len(l_text.split("\n"))
    score = max(0, 100 - len(dupes) * 3)
    return score, dupes


def score_stack(global_md: Path, project_md: Path, local_md: Path) -> RoundResult:
    g_text = global_md.read_text() if global_md.exists() else ""
    p_text = project_md.read_text() if project_md.exists() else ""
    l_text = local_md.read_text() if local_md.exists() else ""

    g_lines = len(g_text.split("\n"))
    p_lines = len(p_text.split("\n"))
    l_lines = len(l_text.split("\n"))

    bp_score, bp_missing = check_blueprint_3layer(p_text, l_text)
    budget_score, budget_issues = check_budget(g_lines, p_lines, l_lines)
    dup_score, dupes = check_duplicates(g_text, p_text, l_text)

    # Utility: count instructions and estimate usefulness
    instructions = extract_instructions(p_text) + extract_instructions(l_text)
    useful_count = len([i for i in instructions if _is_useful(i)])
    utility = (useful_count / len(instructions) * 100) if instructions else 0

    overall = bp_score * 0.35 + budget_score * 0.15 + dup_score * 0.15 + utility * 0.35

    return RoundResult(
        round_num=0,
        commit="",
        global_lines=g_lines,
        project_lines=p_lines,
        local_lines=l_lines,
        blueprint_score=bp_score,
        duplication_score=dup_score,
        utility_score=utility,
        budget_score=budget_score,
        overall_score=overall,
        notes=budget_issues + [f"Missing: {', '.join(bp_missing[:3])}"],
        instructions_count=len(instructions),
        instructions_useful=useful_count,
    )


def _is_useful(instruction: str) -> bool:
    """Estimate if an instruction is genuinely useful in real work."""
    low_utility = [
        "auto-discovered by AI",
        "none configured",
        "auto-discovered",
        "run `coworker init`",
        "(none configured",
        "(auto-discovered",
        "scan docs/ structure",
        "_(e.g.,",
        "auto-timestamp if none given",
    ]
    for lu in low_utility:
        if lu in instruction.lower():
            return False
    return True


def run_round(round_num: int) -> RoundResult:
    """Execute one optimization round."""
    result = score_stack(
        GLOBAL_MD,
        PROJECT_DIR / "CLAUDE.md",
        PROJECT_DIR / "CLAUDE.local.md",
    )
    result.round_num = round_num
    return result


def print_result(r: RoundResult):
    print(f"\n{'='*55}")
    print(f"  Round {r.round_num} — Score Report")
    print(f"{'='*55}")
    print(f"  Lines: Global={r.global_lines} | Project={r.project_lines} | Local={r.local_lines}")
    print(f"  Instructions: {r.instructions_count} (useful: {r.instructions_useful})")
    print(f"")
    print(f"  Blueprint:  {r.blueprint_score:6.1f}/100")
    print(f"  Budget:     {r.budget_score:6.1f}/100")
    print(f"  Duplication:{r.duplication_score:6.1f}/100")
    print(f"  Utility:    {r.utility_score:6.1f}/100")
    print(f"  ─────────────────────────")
    print(f"  OVERALL:    {r.overall_score:6.1f}/100")
    print(f"")
    for note in r.notes:
        print(f"  📝 {note}")
    print(f"{'='*55}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["score", "round"])
    parser.add_argument("n", nargs="?", type=int, default=0)
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.command == "score":
        result = score_stack(GLOBAL_MD, PROJECT_DIR / "CLAUDE.md", PROJECT_DIR / "CLAUDE.local.md")
        print_result(result)

    elif args.command == "round":
        result = run_round(args.n)
        print_result(result)
        # Save result
        out_file = RESULTS_DIR / f"round_{args.n:02d}.json"
        out_file.write_text(json.dumps(result.__dict__, indent=2, default=str))


if __name__ == "__main__":
    main()
