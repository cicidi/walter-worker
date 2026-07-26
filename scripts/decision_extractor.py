#!/usr/bin/env python3
"""
Cross-project decision extraction pipeline.

Reads transcripts from Claude Code JSONL and OpenCode DB,
extracts key decisions via LLM, aligns with git commits and
existing docs, and generates doc-organize-compliant output.

Usage:
    python scripts/decision_extractor.py --project ai-coworker --limit 10
    python scripts/decision_extractor.py --all --skip-trivial
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
CLAUDE_PROJECTS = HOME / ".claude" / "projects"
OPENCODE_DB = HOME / ".local" / "share" / "opencode" / "opencode.db"

# Project directory name -> canonical project name
PROJECT_MAP = {
    "ai-coworker": "ai-coworker",
    "-home-cicidi-project-ai-coworker": "ai-coworker",
    "deterministic-ai-agent": "deterministic-workflow",
    "deterministic-workflow": "deterministic-workflow",
    "-home-cicidi-project-deterministic-ai-agent": "deterministic-workflow",
    "mfangdai-ai-agent": "mfangdai",
    "-home-cicidi-project-mfangdai-ai-agent": "mfangdai",
    "skill-factory": "skill-factory",
    "computer-config": "computer-config",
    "hackathon-video-gen": "hackathon-video-gen",
    "-home-cicidi-project-hackathon-video-gen": "hackathon-video-gen",
    "mratequote": "mratequote",
    "-home-cicidi-project-mratequote": "mratequote",
    "luma": "luma",
    "homework-ai": "homework-ai",
    "video-gen-initiative": "video-gen",
    "-home-cicidi-project-video-gen-initiative": "video-gen",
    "mfangdai-video": "mfangdai-video",
    "-home-cicidi-project-mfangdai-video": "mfangdai-video",
    "omnigent": "omnigent",
    "-home-cicidi-project-omnigent": "omnigent",
}

# Projects to SKIP (not first-author or non-project dirs)
SKIP_PROJECTS = {
    "openclaw", "opencode", "andrej-karpathy-skills",
    "guild-agent", "jam-agent", "hermes-agent",
    "-home-cicidi", "-home-cicidi-project",
    "-home-cicidi-project-backup-my-files",
    "-home-cicidi-project-claude-study",
    "-home-cicidi-project-claude-study-openclaw-setup",
    "-home-cicidi-project-openclaw",
    "-home-cicidi-project-ai-coworker--claude-worktrees-feat-test-coverage-95",
}

DECISION_EXTRACTION_PROMPT = """Analyze this AI coding session transcript and extract KEY DEVELOPMENT DECISIONS.

A "decision" is any meaningful choice made during development:
- Architecture choice (library, framework, pattern)
- API design decision (endpoint structure, data format)
- Implementation strategy (algorithm, approach)
- Refactoring direction (what to change and why)
- Bug fix approach (root cause identified + fix strategy)
- Tooling/config choice (which tool, how to configure)
- Scope decision (what to include/exclude from this change)
- Rejected alternatives (considered X but chose Y because Z)

Rules:
- Extract ONLY substantive technical decisions, not trivial chat
- Each decision must include: what was decided, why (rationale), and context (when/where)
- Include rejected alternatives if mentioned
- Skip: hello, test messages, simple reads, boilerplate responses

Session transcript:
__TRANSCRIPT__

Respond with JSON only (no markdown):
{
  "project": "inferred project name or null",
  "summary": "one-line session summary",
  "decisions": [
    {
      "timestamp": "ISO timestamp if available",
      "decision": "what was decided",
      "context": "why this came up",
      "rationale": "why this choice",
      "alternatives_rejected": ["alt1", "alt2"],
      "scope": "what this affects",
      "confidence": "high|medium|low"
    }
  ],
  "is_trivial": false
}"""


def get_llm_client():
    """Get LLM client for decision extraction."""
    from openai import OpenAI
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=60,
    )


def extract_decisions_from_text(client, text: str, session_info: dict) -> dict:
    """Extract decisions from a transcript using LLM."""
    if len(text) < 100:
        return {"decisions": [], "is_trivial": True, "summary": "too short"}

    # Build prompt with simple replacement to avoid .format() brace issues
    prompt = DECISION_EXTRACTION_PROMPT.replace("__TRANSCRIPT__", text)

    try:
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        return data
    except Exception as e:
        return {"decisions": [], "is_trivial": True, "error": str(e)}


def read_claude_jsonl(jsonl_path: Path) -> str:
    """Read a Claude Code JSONL transcript file and return formatted text."""
    parts = []
    if not jsonl_path.exists():
        return ""
    for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            msg = obj.get("message", {})
            if isinstance(msg, dict):
                role = "assistant" if obj.get("type") == "assistant" else "user"
                content_blocks = msg.get("content", [])
                if isinstance(content_blocks, list):
                    for block in content_blocks:
                        if isinstance(block, dict):
                            btype = block.get("type", "")
                            if btype == "text":
                                text = block.get("text", "").strip()
                                if text:
                                    parts.append(f"[{role}] {text}")
                            elif btype == "tool_use":
                                tname = block.get("name", "?")
                                tinput = block.get("input", {})
                                if isinstance(tinput, dict) and tinput:
                                    key_info = str(tinput)[:150]
                                    parts.append(f"[{role}] 🔧 {tname}: {key_info}")
                                else:
                                    parts.append(f"[{role}] 🔧 {tname}")
                            elif btype == "tool_result":
                                pass  # Skip raw results, they're mostly noise
                else:
                    parts.append(f"[{role}] {str(content_blocks)[:200]}")
        except json.JSONDecodeError:
            continue

    full_text = "\n".join(parts)
    # Keep first portion + last portion (decisions tend to be at start and end)
    if len(full_text) > 15000:
        head = full_text[:4000]
        tail = full_text[-10000:]
        return head + "\n...(middle omitted)...\n" + tail
    return full_text


def read_opencode_session(conn: sqlite3.Connection, session_id: str) -> str:
    """Read an OpenCode session transcript, return formatted text."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT m.data, p.data as part_data
        FROM message m
        JOIN part p ON p.message_id = m.id
        WHERE m.session_id = ?
        ORDER BY m.time_created, p.time_created
    """, (session_id,)).fetchall()

    parts = []
    for row in rows:
        try:
            mdata = json.loads(row["data"])
            pdata = json.loads(row["part_data"]) if row["part_data"] else {}
        except json.JSONDecodeError:
            continue

        role = mdata.get("role", "unknown")

        if pdata.get("type") == "text":
            text = pdata.get("text", "").strip()
            if text:
                parts.append(f"[{role}] {text}")
        elif pdata.get("type") == "tool-call":
            tool = pdata.get("tool", "unknown")
            parts.append(f"[{role}] 🔧 {tool}")
        elif pdata.get("type") == "step-start":
            parts.append(f"[{role}] ▶ Step Start")

    full_text = "\n".join(parts)
    if len(full_text) > 15000:
        head = full_text[:4000]
        tail = full_text[-10000:]
        return head + "\n...(middle omitted)...\n" + tail
    return full_text


def get_git_log(project_path: Path, since: str = "2026-03-01") -> list[dict]:
    """Get git commit log for a project."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", str(project_path), "log", "--all", f"--since={since}",
             "--format=%H|%aI|%s"],
            capture_output=True, text=True, timeout=30,
        )
        commits = []
        for line in result.stdout.strip().split("\n"):
            if "|" not in line:
                continue
            parts = line.split("|", 2)
            if len(parts) >= 3:
                commits.append({
                    "hash": parts[0][:8],
                    "date": parts[1],
                    "message": parts[2],
                })
        return commits
    except Exception as e:
        print(f"  git log error for {project_path}: {e}")
        return []


def process_project(
    project_name: str,
    claude_dirs: list[Path],
    opencode_sessions: list[str],
    opencode_conn: sqlite3.Connection | None,
    project_repo_path: Path | None,
    limit: int | None = None,
    skip_trivial: bool = True,
) -> dict:
    """Process all sessions for a project and extract decisions."""
    llm = get_llm_client()
    all_decisions = []
    stats = {"sessions_processed": 0, "decisions_found": 0, "trivial_skipped": 0}

    # 1. Claude Code JSONL sessions
    for claude_dir in claude_dirs:
        jsonl_files = sorted(claude_dir.glob("*.jsonl"))
        for jf in jsonl_files:
            if limit and stats["sessions_processed"] >= limit:
                break
            text = read_claude_jsonl(jf)
            if not text or len(text) < 100:
                continue
            session_info = {"source": "claude-code", "file": str(jf), "project": project_name}

            print(f"  [{project_name}] Claude: {jf.name} ({len(text)} chars)...")
            result = extract_decisions_from_text(llm, text, session_info)
            stats["sessions_processed"] += 1

            if result.get("is_trivial") and skip_trivial:
                stats["trivial_skipped"] += 1
                continue

            for d in result.get("decisions", []):
                d["source"] = "claude-code"
                d["session_file"] = str(jf)
                d["project"] = project_name
                all_decisions.append(d)
                stats["decisions_found"] += 1

    if limit and stats["sessions_processed"] >= limit:
        pass  # already at limit

    # 2. OpenCode sessions
    if opencode_conn:
        for sid in opencode_sessions:
            if limit and stats["sessions_processed"] >= limit:
                break
            text = read_opencode_session(opencode_conn, sid)
            if not text or len(text) < 100:
                continue
            session_info = {"source": "opencode", "session_id": sid, "project": project_name}

            print(f"  [{project_name}] OpenCode: {sid[:30]}... ({len(text)} chars)")
            result = extract_decisions_from_text(llm, text, session_info)
            stats["sessions_processed"] += 1

            if result.get("is_trivial") and skip_trivial:
                stats["trivial_skipped"] += 1
                continue

            for d in result.get("decisions", []):
                d["source"] = "opencode"
                d["session_id"] = sid
                d["project"] = project_name
                all_decisions.append(d)
                stats["decisions_found"] += 1

    # 3. Git commits (already decisions by definition)
    if project_repo_path and project_repo_path.exists():
        commits = get_git_log(project_repo_path)
        for c in commits:
            all_decisions.append({
                "timestamp": c["date"],
                "decision": c["message"],
                "context": f"git commit {c['hash']}",
                "rationale": "committed change",
                "source": "git-commit",
                "commit_hash": c["hash"],
                "project": project_name,
                "confidence": "high",
            })

    # Sort by timestamp (handle None values)
    all_decisions.sort(key=lambda d: d.get("timestamp") or "", reverse=True)

    stats["total_decisions"] = len(all_decisions)
    return {"decisions": all_decisions, "stats": stats}


def categorize_opencode_sessions(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Group OpenCode sessions by project using directory field."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT s.id, s.directory, s.project_id, s.title, s.time_created
        FROM session s
        ORDER BY s.time_created
    """).fetchall()

    project_sessions: dict[str, list[str]] = defaultdict(list)
    unknown = []

    for row in rows:
        directory = row["directory"] or ""
        sid = row["id"]

        # Map directory to project
        matched = False
        for dir_key, proj_name in PROJECT_MAP.items():
            if dir_key in directory:
                if proj_name not in SKIP_PROJECTS:
                    project_sessions[proj_name].append(sid)
                matched = True
                break

        if not matched:
            unknown.append(sid)

    if unknown:
        project_sessions["_unknown"] = unknown

    return dict(project_sessions)


def generate_doc_organize_output(
    project_name: str,
    decisions: list[dict],
    commits: list[dict],
    output_dir: Path,
):
    """Generate doc-organize compliant decision-history docs."""
    initiative = project_name
    dec_dir = output_dir / "docs" / initiative / "decision-history"
    dec_dir.mkdir(parents=True, exist_ok=True)

    # Group decisions by date
    by_date = defaultdict(list)
    for d in decisions:
        ts = d.get("timestamp") or ""
        date = ts[:10] if ts else "unknown"
        by_date[date].append(d)

    # Write per-date decision files
    for date in sorted(by_date, reverse=True):
        day_decisions = by_date[date]
        if not day_decisions:
            continue

        # Pick a topic from the first decision
        first = day_decisions[0]["decision"][:50].replace(" ", "-").lower()
        safe_topic = "".join(c for c in first if c.isalnum() or c == "-")[:60]

        filename = f"{date}-{safe_topic}-decision.md"
        filepath = dec_dir / filename

        lines = [
            f"# Decision Record — {date}",
            f"> Project: {project_name}",
            f"> Decisions: {len(day_decisions)}",
            "",
            "## Change Log",
            f"| Date | Change |",
            "|------|--------|",
            f"| {datetime.now(timezone.utc).strftime('%Y-%m-%d')} | Auto-generated from session analysis |",
            "",
            "## Decisions",
            "",
        ]

        for i, d in enumerate(day_decisions, 1):
            source = d.get("source", "unknown")
            lines.append(f"### {i}. {d['decision'][:100]}")
            lines.append(f"- **Source**: {source}")
            if d.get("timestamp"):
                lines.append(f"- **Timestamp**: {d['timestamp']}")
            if d.get("context"):
                lines.append(f"- **Context**: {d['context']}")
            if d.get("rationale"):
                lines.append(f"- **Rationale**: {d['rationale']}")
            if d.get("alternatives_rejected"):
                lines.append(f"- **Alternatives rejected**: {', '.join(d['alternatives_rejected'])}")
            if d.get("commit_hash"):
                lines.append(f"- **Commit**: `{d['commit_hash']}`")
            lines.append(f"- **Confidence**: {d.get('confidence', 'unknown')}")
            lines.append("")

        filepath.write_text("\n".join(lines))
        print(f"  Wrote: {filepath}")

    # Also write a consolidated timeline
    timeline_path = dec_dir.parent / "state" / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-decision-timeline.md"
    timeline_path.parent.mkdir(parents=True, exist_ok=True)

    tlines = [
        f"# Decision Timeline — {project_name}",
        f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"> Total decisions: {len(decisions)}",
        "",
        "## Timeline",
        "",
    ]

    for d in sorted(decisions, key=lambda x: x.get("timestamp") or "", reverse=True):
        ts = (d.get("timestamp") or "")[:19]
        source_icon = {"git-commit": "🔀", "claude-code": "💬", "opencode": "💬"}.get(d.get("source", ""), "📝")
        tlines.append(f"- {ts} {source_icon} {d['decision'][:120]}")
        tlines.append("")

    timeline_path.write_text("\n".join(tlines))
    print(f"  Wrote timeline: {timeline_path}")

    return dec_dir


# ============================================================================
# Main
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cross-project decision extraction")
    parser.add_argument("--project", help="Process a single project")
    parser.add_argument("--all", action="store_true", help="Process all projects")
    parser.add_argument("--limit", type=int, default=None, help="Max sessions per project")
    parser.add_argument("--skip-trivial", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true", help="List sessions without extracting")
    args = parser.parse_args()

    # Scan Claude Code JSONL projects
    claude_projects = {}
    if CLAUDE_PROJECTS.exists():
        for proj_dir in CLAUDE_PROJECTS.iterdir():
            if not proj_dir.is_dir():
                continue
            dir_name = proj_dir.name
            canonical = PROJECT_MAP.get(dir_name, dir_name)
            if canonical in SKIP_PROJECTS:
                continue
            if canonical not in claude_projects:
                claude_projects[canonical] = []
            claude_projects[canonical].append(proj_dir)

    # Scan OpenCode sessions
    opencode_conn = None
    opencode_sessions = {}
    if OPENCODE_DB.exists():
        opencode_conn = sqlite3.connect(str(OPENCODE_DB))
        opencode_sessions = categorize_opencode_sessions(opencode_conn)

    # Merge all project sources
    all_projects = set(claude_projects.keys()) | set(opencode_sessions.keys())
    all_projects.discard("_unknown")

    print(f"=== Projects found: {len(all_projects)} ===")
    for proj in sorted(all_projects):
        cc = len(claude_projects.get(proj, []))
        oc = len(opencode_sessions.get(proj, []))
        print(f"  {proj}: {cc} Claude dirs, {oc} OpenCode sessions")

    unknown_count = len(opencode_sessions.get("_unknown", []))
    if unknown_count:
        print(f"  _unknown: {unknown_count} sessions to attribute")

    if args.dry_run:
        return

    # Determine which projects to process
    targets = []
    if args.all:
        targets = sorted(all_projects)
    elif args.project:
        if args.project in all_projects:
            targets = [args.project]
        else:
            print(f"Project '{args.project}' not found. Available: {sorted(all_projects)}")
            sys.exit(1)
    else:
        print("Specify --project <name> or --all")
        sys.exit(1)

    # Process each project
    for proj_name in targets:
        print(f"\n{'='*60}")
        print(f"Processing: {proj_name}")
        print(f"{'='*60}")

        cc_dirs = claude_projects.get(proj_name, [])
        oc_ids = opencode_sessions.get(proj_name, [])

        # Determine repo path
        repo_path_map = {
            "ai-coworker": HOME / "project" / "ai-coworker",
            "deterministic-workflow": HOME / "project" / "deterministic-workflow",
            "mfangdai": HOME / "project" / "mfangdai",
            "skill-factory": HOME / "project" / "skill-factory",
            "computer-config": HOME / "project" / "computer-config",
            "hackathon-video-gen": HOME / "project" / "hackathon-video-gen",
            "mratequote": HOME / "project" / "mratequote",
            "luma": HOME / "project" / "luma",
            "video-gen": HOME / "project" / "video-gen",
            "homework-ai": HOME / "project" / "homework-ai",
        }
        repo_path = repo_path_map.get(proj_name)

        result = process_project(
            proj_name, cc_dirs, oc_ids, opencode_conn, repo_path,
            limit=args.limit, skip_trivial=args.skip_trivial,
        )

        print(f"  Stats: {result['stats']}")

        if result["decisions"]:
            commits = [d for d in result["decisions"] if d.get("source") == "git-commit"]
            output_dir = repo_path if repo_path else HOME / "project" / proj_name
            generate_doc_organize_output(proj_name, result["decisions"], commits, output_dir)

            # Save raw decisions JSON for later use
            raw_path = output_dir / "docs" / proj_name / "raw" / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-decisions-raw.json"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(json.dumps(result["decisions"], indent=2, default=str))
            print(f"  Raw data: {raw_path}")

    if opencode_conn:
        opencode_conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
