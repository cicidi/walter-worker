#!/usr/bin/env python3
"""Generate realistic session data for the Coworker Analytics Dashboard.

Simulates OpenCode and Claude Code sessions with:
- MCP tool calls (GitHub, Slack, Google Drive)
- Skill invocation chains (brainstorming → writing-plans → executing-plans → ...)
- File operations on real project paths
- Session summaries and knowledge cards
- Multiple initiatives across projects
"""

import json
import random
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.coworker.analytics.db import init_db, get_db, _default_db_path
from src.coworker.analytics.import_data import import_session

# ── Configuration ──────────────────────────────────────────────────────────────

PROJECTS = ["ai-coworker", "skill-factory", "dotfiles", "opencode"]
IDES = ["opencode", "claude"]
BRANCHES = [
    "feat/dashboard-v1", "feat/listener-v1", "feat/knowledge-skill",
    "fix/config-sync", "feat/init-system", "main",
    "chore/update-deps", "docs/api-reference", "refactor/adapters",
]
INITIATIVES = [
    "dashboard-v1", "listener-v1", "knowledge-skill",
    "init-system", "core-architecture", None,
]

# Real project files for file operations
PROJECT_FILES = {
    "ai-coworker": [
        "CLAUDE.md", "src/coworker/models.py", "src/coworker/cli.py",
        "src/coworker/config.py", "src/coworker/dashboard/app.py",
        "src/coworker/dashboard/queries.py",
        "src/coworker/analytics/db.py", "src/coworker/analytics/import_data.py",
        "src/coworker/analytics/hooks/common.sh",
        "src/coworker/analytics/hooks/on-user-prompt.sh",
        "src/coworker/adapters/claude.py", "src/coworker/adapters/opencode.py",
        "static/dashboard.js", "static/dashboard.css", "static/index.html",
        "pyproject.toml", "coworker-blueprint.md",
        "docs/prd/2026-06-11-dashboard-prd.md",
        "docs/spec/2026-06-11-analytics-listener.md",
        "setup/install.sh", "setup/uninstall.sh",
        ".opencode/coworker-analytics/index.ts",
        ".opencode/coworker-analytics/recorder.ts",
        ".local_config.yaml", ".mcp.json",
    ],
    "skill-factory": [
        "skills/brainstorming/SKILL.md", "skills/writing-plans/SKILL.md",
        "skills/systematic-debugging/SKILL.md", "skills/executing-plans/SKILL.md",
        "skills/subagent-driven-development/SKILL.md",
        "src/factory.py", "src/templates.py", "src/validator.py",
        "tests/test_factory.py", "pyproject.toml",
    ],
    "dotfiles": [
        ".zshrc", ".gitconfig", ".tmux.conf", ".config/nvim/init.lua",
        ".config/starship.toml", ".config/alacritty/alacritty.yml",
        "install.sh", "README.md",
    ],
    "opencode": [
        ".opencode/config.json", ".opencode/instructions/core.md",
        ".opencode/coworker-analytics/index.ts",
        ".opencode/package.json", "opencode.jsonc",
    ],
}

# Builtin tools
BUILTIN_TOOLS = [
    "Bash", "Read", "Write", "Edit", "Skill", "TodoWrite",
    "Glob", "Grep", "Task", "Question", "WebFetch", "WebSearch",
]

# MCP tools grouped by server
MCP_TOOLS = {
    "github": ["github_create_issue", "github_create_pull_request", "github_get_pull_request",
               "github_list_issues", "github_search_code", "github_push_files",
               "github_create_branch", "github_add_issue_comment"],
    "slack": ["slack_post_message", "slack_get_channel_history", "slack_list_channels",
              "slack_get_users", "slack_add_reaction"],
    "gdrive": ["google_drive_search", "google_drive_read_file", "google_drive_create_file"],
}

# Skills with realistic invocation chains
SKILLS = [
    "brainstorming", "writing-plans", "executing-plans",
    "systematic-debugging", "subagent-driven-development",
    "verification-before-completion", "test-driven-development",
    "requesting-code-review", "receiving-code-review",
    "using-superpowers", "dispatching-parallel-agents",
    "finishing-a-development-branch", "using-git-worktrees",
    "commit", "writing-skills", "add-mcp-skill",
    "customize-opencode", "tmux-setup",
]

# Typical skill invocation order for a feature session
SKILL_CHAIN = [
    "using-superpowers",
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "verification-before-completion",
    "requesting-code-review",
]

# Realistic user/assistant messages per scenario
SCENARIOS = {
    "feature": {
        "user": [
            "build the dashboard analytics page with real data",
            "I need a new knowledge-skill feature for self-healing",
            "add MCP server for Google Drive integration",
            "create the initiative management system",
            "add WebSocket support to the dashboard for real-time updates",
        ],
        "assistant": [
            "Let me start by exploring the existing dashboard code to understand the architecture.",
            "I'll use the brainstorming skill first to design the feature, then writing-plans for implementation.",
            "Looking at the current analytics schema, I need to add a new table for knowledge cards.",
            "The hook system needs to be updated to capture parent-child tool relationships.",
            "Let me verify all the changes work together by running the test suite.",
        ],
    },
    "bugfix": {
        "user": [
            "the dashboard shows empty data even though sessions exist",
            "config sync is broken after the last refactor",
            "hook scripts fail when session directory doesn't exist",
        ],
        "assistant": [
            "Let me debug this systematically. First, checking the database connection.",
            "Found the issue — the import script wasn't handling None values for duration.",
            "The fix is straightforward. The adapter was looking in the wrong config path.",
        ],
    },
    "review": {
        "user": [
            "review the PR for the dashboard feature",
            "code review the new auth adapter implementation",
        ],
        "assistant": [
            "I'll use the receiving-code-review skill to analyze the PR changes.",
            "The implementation looks solid. MCP server integration follows existing patterns.",
            "Found 3 suggestions: better error handling in import_data.py, missing null check in queries.",
        ],
    },
}

# Session summary templates
SUMMARY_TEMPLATES = [
    {
        "sop_workflows": "Explored codebase structure → identified target files → made targeted edits → verified with tests",
        "context_to_remember": "Dashboard frontend uses vanilla JS with FastAPI backend. Analytics data stored in SQLite with 8-table schema. Import pipeline merges pre/post tool call records.",
        "effective_operations": "Using glob+grep tools for codebase exploration, Skill tool for workflow management, Edit tool for surgical changes",
        "pitfalls_and_fixes": "Import script needed null-check for duration_ms field. Tool call merging requires matching call_id across before/after phases.",
        "wasted_actions": "Initial full codebase grep when targeted glob would have sufficed; redundant Read of already-loaded files",
        "bottlenecks": "Sequential tool calls could be parallelized; repeated schema checks on each import",
        "efficiency_tip": "Use Task subagents for parallel exploration and use Edit tool instead of full Write when possible",
        "think_action_ratio": 0.35,
        "edit_redundancy": 0.12,
        "loop_count": 2,
        "user_wait_minutes": 3.5,
        "memory_keywords": "dashboard, FastAPI, SQLite, analytics, hook-system, import-pipeline, tool-calls, opencode-plugin",
    },
    {
        "sop_workflows": "Read PRD → created feature spec → implemented code → tested → updated docs → requested review",
        "context_to_remember": "Knowledge cards use LLM analysis to extract patterns from sessions. Cards typed as trap/best/pattern. Cards get merged into skills via skill-factory pipeline.",
        "effective_operations": "Brainstorming skill for design, Test-driven-development for implementation, systematic-debugging for edge cases",
        "pitfalls_and_fixes": "Initial implementation stored cards in sessions table — moved to separate knowledge table for query performance",
        "wasted_actions": "Rewrote summary generation twice due to unclear requirements; should have clarified format first",
        "bottlenecks": "LLM analysis runs synchronously blocking session close; moved to background queue",
        "efficiency_tip": "Clarify output format requirements before implementing LLM-generated content",
        "think_action_ratio": 0.28,
        "edit_redundancy": 0.18,
        "loop_count": 1,
        "user_wait_minutes": 5.2,
        "memory_keywords": "knowledge-cards, LLM, self-healing, skill-factory, pattern-extraction, session-analysis",
    },
    {
        "sop_workflows": "Identified bug → isolated reproduction → traced root cause → implemented fix → verified with tests → created PR",
        "context_to_remember": "Config sync bug was in path resolution — adapter used relative path where absolute was needed. Affected all 4 IDE adapters.",
        "effective_operations": "Systematic-debugging skill, Read for code inspection, Edit for surgical fixes, Bash for test runs",
        "pitfalls_and_fixes": "Cache invalidation not happening after sync — added explicit cache clear in adapter post_sync hook",
        "wasted_actions": "Time spent checking database when issue was in-memory config object",
        "bottlenecks": "Test setup requiring 4 IDE directories slowed verification",
        "efficiency_tip": "Check in-memory state first before checking persistent storage when debugging sync issues",
        "think_action_ratio": 0.42,
        "edit_redundancy": 0.05,
        "loop_count": 3,
        "user_wait_minutes": 2.1,
        "memory_keywords": "config-sync, adapter, path-resolution, cache, debugging, hooks",
    },
]

KNOWLEDGE_CARDS = [
    {
        "title": "Always use verification-before-completion before claiming work is done",
        "type": "best",
        "summary": "Across 8 sessions, verifying work with tests/commands before claiming completion prevented 5 false-positive completions. The verification skill catches edge cases that simple code inspection misses.",
        "skills": "verification-before-completion",
        "evidence": "session test-002-8734: verification caught missing import; session test-005-2210: test revealed broken WebSocket handler; session test-008-4492: linting found 2 unused imports",
    },
    {
        "title": "Don't Write new files when Edit on existing file is sufficient",
        "type": "trap",
        "summary": "In 4 sessions, using Write to replace entire files instead of Edit caused merge conflicts with uncommitted changes and removed valuable comments. Edit with targeted oldString/newString is safer.",
        "skills": "writing-plans, executing-plans",
        "evidence": "session test-003-1256: full Write on dashboard.js lost hand-written comments; session test-007-6521: Write overwrote config changes from another branch",
    },
    {
        "title": "Task subagents are 3x faster for parallel codebase exploration",
        "type": "pattern",
        "summary": "Sessions using Task-based subagents for exploration completed file discovery in 1/3 the time compared to sequential Read/Glob/Grep calls. Best used for exploring new codebases or large directories.",
        "skills": "subagent-driven-development, dispatching-parallel-agents",
        "evidence": "session test-001-4102: 4 parallel agents explored 200 files in 12s vs 35s sequential; session test-004-9987: 3 agents found all hooks implementations in 8s",
    },
    {
        "title": "Skill chain: brainstorming → writing-plans → executing-plans is the golden path",
        "type": "best",
        "summary": "Sessions that followed the brainstorming → writing-plans → executing-plans chain had 40% fewer wasted actions and 2x higher efficiency scores. The upfront design investment pays off in implementation clarity.",
        "skills": "brainstorming, writing-plans, executing-plans",
        "evidence": "session test-001-4102: chain followed, efficiency 85%; session test-006-3341: skipped brainstorming, efficiency 52%, 3 rewrites",
    },
    {
        "title": "MCP tool calls timeout silently when session context is too large",
        "type": "trap",
        "summary": "GitHub MCP tools (github_create_pr, github_push_files) failed silently in 2 sessions when the AI context was full. The issue only surfaced after reviewing tool call results for empty returns.",
        "skills": "systematic-debugging",
        "evidence": "session test-004-9987: 3 github_create_pr calls returned empty; session test-009-7742: github_push_files timed out after 120s",
    },
]

# ── Generator ──────────────────────────────────────────────────────────────────

def generate_session_yaml(session_dir: Path, session_id: str, ide: str, project: str,
                          branch: str, initiative: str | None,
                          start: datetime, duration_min: int):
    created = start.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    closed = (start + timedelta(minutes=duration_min)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    cwd = f"/home/cicidi/project/{project}"

    (session_dir / "session.yaml").write_text(
        f'session_id: "{session_id}"\n'
        f'created: "{created}"\n'
        f'closed: "{closed}"\n'
        f'ide: "{ide}"\n'
        f'cwd: "{cwd}"\n'
        f'project: "{project}"\n'
        f'initiative: "{initiative or ""}"\n'
        f'branch: "{branch}"\n'
        f'model: "deepseek-v4-pro"\n'
    )
    return created, closed


def generate_messages(scenario_type: str, start: datetime, duration_min: int):
    """Generate realistic message sequence for a session."""
    scenario = SCENARIOS.get(scenario_type, SCENARIOS["feature"])
    num_rounds = random.randint(3, 6)
    messages = []
    seq = 0
    interval = (duration_min * 60) / (num_rounds * 3)  # seconds per event

    for i in range(num_rounds):
        seq += 1
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        messages.append(json.dumps({
            "ts": ts, "type": "user", "seq": seq,
            "content": random.choice(scenario["user"]),
        }))

        seq += 1
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        messages.append(json.dumps({
            "ts": ts, "type": "assistant", "seq": seq,
            "content": random.choice(scenario["assistant"]),
        }))

    return messages


def generate_tool_calls(project: str, start: datetime, duration_min: int, base_seq: int):
    """Generate realistic tool calls with MCP tools and skill chains."""
    tools = []
    seq = base_seq
    interval = (duration_min * 60) / 50  # rough spacing

    # Phase 1: Exploration (Read, Glob, Grep)
    exploration_files = random.sample(PROJECT_FILES.get(project, PROJECT_FILES["ai-coworker"]),
                                       k=random.randint(3, 6))
    for f in exploration_files:
        seq += 1
        cid = f"call_exp_{seq}"
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        tool = random.choice(["Read", "Glob", "Grep"])
        args = {"filePath" if tool == "Read" else "pattern": f"/home/cicidi/project/{project}/{f}"}
        tools.append(("before", cid, tool, "builtin", None, seq, ts, args))

        seq += 1
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        result = f"Content of {f} (found match)" if tool == "Grep" else f"File content: {f} ({random.randint(80, 500)} lines)"
        tools.append(("after", cid, tool, "builtin", None, seq, ts, None, result, random.randint(50, 3000)))

    # Phase 2: Skill invocations (following the skill chain)
    skills_used = random.sample(SKILL_CHAIN, k=random.randint(2, 4))
    if "using-superpowers" not in skills_used:
        skills_used.insert(0, "using-superpowers")

    for skill_name in skills_used:
        seq += 1
        cid = f"call_skill_{seq}"
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        args = {"name": skill_name}
        tools.append(("before", cid, "Skill", "builtin", None, seq, ts, args))
        seq += 1
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        tools.append(("after", cid, "Skill", "builtin", None, seq, ts, None,
                      f"Loaded skill: {skill_name}", random.randint(500, 8000)))

    # Phase 3: Implementation tools (Write, Edit, Bash)
    edit_files = random.sample(exploration_files, k=min(3, len(exploration_files)))
    for i, f in enumerate(edit_files):
        tool = random.choice(["Edit", "Write"])
        seq += 1
        cid = f"call_impl_{seq}"
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        args = {"filePath": f"/home/cicidi/project/{project}/{f}",
                "oldString": "old code block" if tool == "Edit" else None,
                "newString": "new code block"}
        tools.append(("before", cid, tool, "builtin", None, seq, ts, args))
        seq += 1
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        tools.append(("after", cid, tool, "builtin", None, seq, ts, None,
                      f"File {'edited' if tool == 'Edit' else 'written'}", random.randint(100, 15000)))

    # Phase 4: Bash commands (test, lint, git)
    bash_cmds = random.sample([
        "pytest tests/ -x -q", "npm run lint", "python -m pytest tests/analytics/",
        "git status", "git diff --stat", "python3 -c 'from src.coworker.dashboard.queries import query_overview; print(query_overview())'",
        "npm run typecheck", "ruff check src/", "git log --oneline -5",
    ], k=random.randint(2, 4))
    for cmd in bash_cmds:
        seq += 1
        cid = f"call_bash_{seq}"
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        args = {"command": cmd, "description": f"Run {cmd}"}
        tools.append(("before", cid, "Bash", "builtin", None, seq, ts, args))
        seq += 1
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        tools.append(("after", cid, "Bash", "builtin", None, seq, ts, None,
                      "Command completed successfully. All tests passed." if "pytest" in cmd else "ok",
                      random.randint(200, 60000)))

    # Phase 5: MCP tool calls (GitHub, Slack, etc.)
    mcp_servers = ["github", "slack"]
    for server in mcp_servers:
        if random.random() > 0.5:
            continue
        mcp_tool = random.choice(MCP_TOOLS[server])
        seq += 1
        cid = f"call_mcp_{seq}"
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        if server == "github":
            args = {"owner": "cicidi", "repo": project,
                    "title" if "issue" in mcp_tool or "pr" in mcp_tool else "q": f"Test {mcp_tool}"}
        else:
            args = {"channel_id": "C12345", "text": "PR ready for review"}
        tools.append(("before", cid, mcp_tool, "mcp", server, seq, ts, args))
        seq += 1
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        tools.append(("after", cid, mcp_tool, "mcp", server, seq, ts, None,
                      f"{{'ok': true, 'url': 'https://github.com/cicidi/{project}/pull/1'}}",
                      random.randint(300, 120000)))

    # Phase 6: More skills (commit, review, finishing)
    extra_skills = random.sample(
        ["commit", "requesting-code-review", "finishing-a-development-branch",
         "verification-before-completion", "systematic-debugging"],
        k=random.randint(0, 2))
    for skill_name in extra_skills:
        seq += 1
        cid = f"call_skill2_{seq}"
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        args = {"name": skill_name}
        tools.append(("before", cid, "Skill", "builtin", None, seq, ts, args))
        seq += 1
        ts = (start + timedelta(seconds=int(seq * interval))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        tools.append(("after", cid, "Skill", "builtin", None, seq, ts, None,
                      f"Skill {skill_name} completed", random.randint(200, 5000)))

    return tools


def generate_session_summary(conn, session_id: str, generated_at: str):
    """Insert a random session summary."""
    summary = random.choice(SUMMARY_TEMPLATES)
    conn.execute(
        """INSERT OR REPLACE INTO session_summaries
           (session_id, sop_workflows, context_to_remember, effective_operations,
            pitfalls_and_fixes, wasted_actions, bottlenecks, efficiency_tip,
            efficiency_score, think_action_ratio, edit_redundancy, loop_count,
            user_wait_minutes, memory_keywords, generated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, summary["sop_workflows"], summary["context_to_remember"],
         summary["effective_operations"], summary["pitfalls_and_fixes"],
         summary["wasted_actions"], summary["bottlenecks"], summary["efficiency_tip"],
         random.uniform(0.45, 0.92), summary["think_action_ratio"],
         summary["edit_redundancy"], summary["loop_count"],
         summary["user_wait_minutes"], summary["memory_keywords"], generated_at),
    )


def generate_knowledge_cards(conn, session_id: str, project: str, generated_at: str):
    """Insert 1-2 knowledge cards per session."""
    cards = random.sample(KNOWLEDGE_CARDS, k=random.randint(0, 2))
    for card in cards:
        conn.execute(
            """INSERT INTO knowledge (title, type, session_id, project, skills,
               summary, evidence, generated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (card["title"], card["type"], session_id, project,
             card["skills"], card["summary"], card["evidence"], generated_at),
        )


def generate_full_session(session_id: str, ide: str, project: str, branch: str,
                          initiative: str | None, start: datetime,
                          duration_min: int, scenario_type: str) -> Path:
    """Create a complete session directory with messages.jsonl and tools.jsonl."""
    session_dir = Path(tempfile.mkdtemp()) / "sessions" / session_id
    session_dir.mkdir(parents=True)

    created, closed = generate_session_yaml(
        session_dir, session_id, ide, project, branch, initiative, start, duration_min)

    messages = generate_messages(scenario_type, start, duration_min)
    base_seq = len(messages)

    tools = generate_tool_calls(project, start, duration_min, base_seq)

    lines = [m + "\n" for m in messages]
    (session_dir / "messages.jsonl").write_text("".join(lines))

    tool_lines = []
    for entry in tools:
        phase, cid, tool, tool_type, server, seq, ts, args, *rest = entry
        if phase == "before":
            obj = {"ts": ts, "phase": "before", "tool": tool, "tool_type": tool_type,
                   "call_id": cid, "seq": seq, "args": args}
            if server:
                obj["server_name"] = server
        else:
            result, duration = rest
            obj = {"ts": ts, "phase": "after", "tool": tool, "tool_type": tool_type,
                   "call_id": cid, "seq": seq, "result": result, "duration_ms": duration}
            if server:
                obj["server_name"] = server
        tool_lines.append(json.dumps(obj))

    (session_dir / "tools.jsonl").write_text("\n".join(tool_lines) + "\n")
    return session_dir


# ── Main ───────────────────────────────────────────────────────────────────────

def seed_dashboard(num_sessions: int = 25):
    """Generate synthetic sessions and populate the production database."""
    db_path = _default_db_path()
    print(f"Initializing database at {db_path}...")
    conn = init_db(db_path)

    # Clear existing data
    conn.execute("DELETE FROM file_ops")
    conn.execute("DELETE FROM tool_calls")
    conn.execute("DELETE FROM messages")
    conn.execute("DELETE FROM session_summaries")
    conn.execute("DELETE FROM session_stats")
    conn.execute("DELETE FROM knowledge")
    conn.execute("DELETE FROM skills")
    conn.execute("DELETE FROM sessions")
    conn.commit()
    print("Cleared existing data.")

    base_time = datetime(2026, 6, 1, 8, 0, 0)
    sessions_generated = 0
    temp_dirs = []

    for i in range(num_sessions):
        days_ago = random.randint(0, 14)
        hour = random.randint(7, 22)
        minute = random.randint(0, 59)
        start = base_time + timedelta(days=days_ago, hours=hour - base_time.hour,
                                       minutes=minute - base_time.minute)

        project = random.choice(PROJECTS)
        ide = random.choice(IDES)
        branch = random.choice(BRANCHES)
        initiative = random.choice(INITIATIVES)
        duration = random.randint(15, 120)
        scenario = random.choice(["feature", "feature", "feature", "bugfix", "review"])

        sid = f"{ide}-{start.strftime('%Y%m%dT%H%M%S')}-{random.randint(100, 999)}"

        session_dir = generate_full_session(sid, ide, project, branch, initiative,
                                            start, duration, scenario)
        temp_dirs.append(session_dir.parent.parent)

        import_session(session_dir, conn)
        sessions_generated += 1

        # Add session summary
        closed_ts = (start + timedelta(minutes=duration)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        generate_session_summary(conn, sid, closed_ts)

        # Add knowledge cards
        generate_knowledge_cards(conn, sid, project, closed_ts)

        print(f"  [{i+1}/{num_sessions}] {sid} | {ide} | {project} | {duration}m | {scenario}")

    conn.commit()
    conn.close()

    # Cleanup temp dirs
    for d in temp_dirs:
        shutil.rmtree(d, ignore_errors=True)

    print(f"\nDone! Generated {sessions_generated} sessions.")
    print(f"Database: {db_path}")

    # Print stats
    conn = get_db()
    counts = {
        "sessions": conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
        "messages": conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
        "tool_calls": conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0],
        "file_ops": conn.execute("SELECT COUNT(*) FROM file_ops").fetchone()[0],
        "skills": conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0],
        "knowledge": conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0],
        "summaries": conn.execute("SELECT COUNT(*) FROM session_summaries").fetchone()[0],
    }
    for k, v in counts.items():
        print(f"  {k}: {v}")
    conn.close()


if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    seed_dashboard(count)
