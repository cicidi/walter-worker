#!/usr/bin/env python3
"""
Document gap filler — generates missing doc-organize documents from decision history.

Reads decision raw data, uses LLM to synthesize PRD/spec/design docs,
and writes them in doc-organize format.

Usage:
    python scripts/gap_filler.py --project ai-coworker
    python scripts/gap_filler.py --all
"""
from __future__ import annotations

import json, os, sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

from openai import OpenAI

HOME = Path.home()

DOC_TYPE_PROMPTS = {
    "prd": """You are writing a Product Requirements Document (PRD) based on the development history of a project.

Below are ALL decisions made during the project's development, extracted from git commits,
Claude Code sessions, and OpenCode sessions. Use them to reconstruct the PRD.

A PRD should include:
1. Project overview and goals
2. Target users / use cases
3. Core features and requirements
4. Success metrics
5. Non-goals (what we explicitly decided NOT to build)

Base the PRD on the actual decisions made, NOT speculation. Every requirement should
trace back to at least one decision.

Decisions (sorted by time):
{decisions}

Write a complete PRD in markdown. Include a Change Log section at the top.
Title: "{project_name} PRD"
""",

    "spec": """You are writing a Technical Specification based on the development history of a project.

Below are ALL decisions made during development. Extract the technical specifications
that were actually implemented.

A Spec should include:
1. System architecture overview
2. Key interfaces / APIs (based on what was built)
3. Data models / schemas (based on actual implementations)
4. Component interactions
5. Configuration / environment requirements

Base everything on actual decisions and commits, not speculation.

Decisions (sorted by time):
{decisions}

Write a complete Spec in markdown. Include a Change Log section at the top.
Title: "{project_name} Technical Specification"
""",

    "design": """You are writing a Technical Design document based on the development history of a project.

Below are ALL decisions made during development. Extract the architectural and design
decisions that shaped the project.

A Design doc should include:
1. High-level architecture
2. Design patterns used
3. Technology choices and rationale
4. Data flow and service topology
5. Key trade-offs and why specific approaches were chosen

Base everything on actual decisions, not speculation.

Decisions (sorted by time):
{decisions}

Write a complete Design document in markdown. Include a Change Log section at the top.
Title: "{project_name} Design"
""",

    "impl-plan": """You are writing an Implementation Plan based on the development history of a project.

Below are ALL decisions made during development. Organize them into an implementation
plan showing how the project was built.

An Implementation Plan should include:
1. Milestones / phases
2. Key deliverables per phase
3. Dependencies between components
4. Build/execution order
5. Key commits linked to each milestone

Decisions (sorted by time):
{decisions}

Write a complete Implementation Plan in markdown. Include a Change Log section at the top.
Title: "{project_name} Implementation Plan"
""",

    "test-plan": """You are writing a Test Plan based on the development history of a project.

Below are ALL decisions made during development. Identify testing strategies that were
or should have been applied.

A Test Plan should include:
1. Testing strategy (unit, integration, e2e)
2. Key test scenarios
3. Quality gates / acceptance criteria
4. Tools and frameworks used
5. Bug patterns found and how they were fixed

Decisions (sorted by time):
{decisions}

Write a complete Test Plan in markdown. Include a Change Log section at the top.
Title: "{project_name} Test Plan"
""",
}


def get_llm():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com", timeout=120)


def generate_doc(client, doc_type: str, project_name: str, decisions: list[dict]) -> str:
    """Generate a document from decisions using LLM."""
    # Format decisions for the prompt - focus on the most informative ones
    decision_texts = []
    for d in sorted(decisions, key=lambda x: x.get("timestamp") or ""):
        ts = (d.get("timestamp") or "")[:19]
        decision = d.get("decision", "")
        rationale = d.get("rationale", "")
        context = d.get("context", "")
        source = d.get("source", "unknown")

        parts = [f"[{ts}] [{source}]"]
        if decision:
            parts.append(f"Decision: {decision}")
        if context and context != "committed change":
            parts.append(f"Context: {context}")
        if rationale and rationale != "committed change":
            parts.append(f"Rationale: {rationale}")
        decision_texts.append(" | ".join(parts))

    # Take most relevant decisions (first 200, last 50 for recency)
    if len(decision_texts) > 250:
        decision_texts = decision_texts[:200] + ["...(middle omitted)..."] + decision_texts[-50:]

    decisions_str = "\n".join(decision_texts)

    prompt = DOC_TYPE_PROMPTS[doc_type].format(
        decisions=decisions_str[:30000],
        project_name=project_name,
    )

    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=4000,
    )
    return resp.choices[0].message.content or ""


def fill_project_gaps(project_name: str, project_path: Path, limit_types: list[str] | None = None):
    """Fill missing document types for a project."""
    raw_path = project_path / "docs" / project_name / "raw" / "2026-07-26-decisions-raw.json"
    if not raw_path.exists():
        print(f"  {project_name}: no decision data, skipping")
        return 0

    decisions = json.loads(raw_path.read_text())
    if len(decisions) < 5:
        print(f"  {project_name}: only {len(decisions)} decisions, too few for docs")
        return 0

    docs_dir = project_path / "docs" / project_name
    client = get_llm()

    types_to_fill = list(DOC_TYPE_PROMPTS.keys())
    if limit_types:
        types_to_fill = [t for t in types_to_fill if t in limit_types]

    generated = 0
    for doc_type in types_to_fill:
        type_dir = docs_dir / doc_type
        type_dir.mkdir(parents=True, exist_ok=True)

        # Skip if already has docs
        existing = list(type_dir.glob("*.md"))
        if existing:
            print(f"  {project_name}/{doc_type}: already has {len(existing)} files")
            continue

        print(f"  {project_name}/{doc_type}: generating...")
        content = generate_doc(client, doc_type, project_name, decisions)

        if content:
            filename = f"{project_name}-{doc_type}.md"
            filepath = type_dir / filename
            filepath.write_text(content)
            generated += 1
            print(f"    → {filepath}")

    return generated


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", help="Single project name")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--types", nargs="*", default=None, help="Doc types to generate")
    args = parser.parse_args()

    project_map = {
        "ai-coworker": HOME / "project" / "ai-coworker",
        "skill-factory": HOME / "project" / "skill-factory",
        "mfangdai": HOME / "project" / "mfangdai",
        "hackathon-video-gen": HOME / "project" / "hackathon-video-gen",
        "computer-config": HOME / "project" / "computer-config",
        "mratequote": HOME / "project" / "mratequote",
        "luma": HOME / "project" / "luma",
        "video-gen": HOME / "project" / "video-gen",
        "mfangdai-video": HOME / "project" / "mfangdai-video",
        "homework-ai": HOME / "project" / "homework-ai",
        "deterministic-workflow": HOME / "project" / "deterministic-workflow",
        "omnigent": HOME / "project" / "omnigent",
    }

    targets = []
    if args.all:
        targets = list(project_map.keys())
    elif args.project:
        if args.project in project_map:
            targets = [args.project]
        else:
            print(f"Unknown project: {args.project}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    total = 0
    for proj in targets:
        print(f"\n{'='*50}")
        print(f"Filling gaps: {proj}")
        count = fill_project_gaps(proj, project_map[proj], args.types)
        total += count

    print(f"\nTotal docs generated: {total}")


if __name__ == "__main__":
    main()
