import json
import random
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from src.coworker.analytics.db import init_db
from src.coworker.analytics.import_data import import_session

PROJECTS = ["walter-worker", "skill-factory", "dotfiles"]
TOOLS = ["Bash", "Read", "Write", "Edit", "Skill", "TodoWrite", "Glob", "Grep", "Task", "Question"]
SKILLS = ["brainstorming", "writing-plans", "systematic-debugging", "executing-plans", "subagent-driven-dev"]
FILES = [
    "CLAUDE.md", "src/coworker/models.py", "src/coworker/cli.py",
    "src/coworker/config.py", "docs/prd/PRD.md", "docs/design/DESIGN.md",
    "coworker-blueprint.md", "pyproject.toml", "setup/install.sh",
]
BRANCHES = ["feat/dashboard", "feat/listener", "fix/config", "main"]
INITIATIVES = ["dashboard-v1", "listener-v1", None]

USER_MSGS = [
    "help me build a dashboard", "analyze the codebase first",
    "what skills should I use?", "now write the implementation",
    "run the tests", "fix the bug in config.py",
    "add a new feature for session replay", "review the code changes",
]
ASSISTANT_MSGS = [
    "I'll start by exploring the project structure.",
    "Found 3 projects in the catalog. Using FastAPI for backend.",
    "I recommend brainstorming first, then writing-plans.",
    "Let me write the dashboard backend with proper error handling.",
    "Tests pass. 8/8 tables created successfully.",
    "The bug was in the import script — missing null check.",
    "Session replay feature added with timeline component.",
    "Code review complete. All changes look good.",
]


def generate_test_session(
    session_id: str, project: str, branch: str, initiative: str | None,
    start: datetime, duration_min: int = 30,
) -> Path:
    session_dir = Path(tempfile.mkdtemp()) / "sessions" / session_id
    session_dir.mkdir(parents=True)

    created = start.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    closed = (start + timedelta(minutes=duration_min)).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    (session_dir / "session.yaml").write_text(
        f'session_id: "{session_id}"\n'
        f'created: "{created}"\n'
        f'closed: "{closed}"\n'
        f'ide: "opencode"\n'
        f'cwd: "/home/cicidi/project/{project}"\n'
        f'project: "{project}"\n'
        f'initiative: "{initiative or ""}"\n'
        f'branch: "{branch}"\n'
    )

    seq = 0
    messages = []
    tools = []

    num_msgs = random.randint(4, 8)
    for i in range(num_msgs):
        seq += 1
        ts = (start + timedelta(seconds=seq * 30)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        messages.append(json.dumps({
            "ts": ts, "type": "user", "seq": seq,
            "content": random.choice(USER_MSGS),
        }) + "\n")
        seq += 1
        ts = (start + timedelta(seconds=seq * 30)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        messages.append(json.dumps({
            "ts": ts, "type": "assistant", "seq": seq,
            "content": random.choice(ASSISTANT_MSGS),
        }) + "\n")

    num_tools = random.randint(8, 20)
    for i in range(num_tools):
        tool = random.choice(TOOLS)
        cid = f"call_{session_id}_{i}"
        seq += 1
        ts = (start + timedelta(seconds=seq * 30)).strftime("%Y-%m-%dT%H:%M:%S+08:00")

        if tool == "Skill":
            args = {"name": random.choice(SKILLS)}
        elif tool in ("Read", "Write", "Edit"):
            args = {"filePath": f"/home/cicidi/project/{project}/{random.choice(FILES)}"}
        elif tool == "Bash":
            args = {"command": random.choice(["ls", "pytest", "git status", "npm run build", "python3 -m pytest"])}
        else:
            args = {"description": f"doing {tool}"}

        tools.append(json.dumps({
            "ts": ts, "phase": "before", "tool": tool, "tool_type": "builtin",
            "call_id": cid, "seq": seq, "args": args,
        }) + "\n")

        seq += 1
        ts = (start + timedelta(seconds=seq * 30)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        result = f"result of {tool} call {cid}"
        tools.append(json.dumps({
            "ts": ts, "phase": "after", "tool": tool, "tool_type": "builtin",
            "call_id": cid, "seq": seq, "result": result,
            "duration_ms": random.randint(100, 50000),
        }) + "\n")

    (session_dir / "messages.jsonl").write_text("".join(messages))
    (session_dir / "tools.jsonl").write_text("".join(tools))
    return session_dir


def generate_test_dataset(db_path: str, num_sessions: int = 10):
    conn = init_db(db_path)
    base_time = datetime(2026, 6, 1, 9, 0, 0)
    for i in range(num_sessions):
        sid = f"test-{i:03d}-{random.randint(1000, 9999)}"
        project = random.choice(PROJECTS)
        branch = random.choice(BRANCHES)
        initiative = random.choice(INITIATIVES)
        start = base_time + timedelta(hours=i * 3)
        session_dir = generate_test_session(sid, project, branch, initiative, start, random.randint(10, 90))
        import_session(session_dir, conn)
    conn.close()
    print(f"Generated {num_sessions} test sessions in {db_path}")


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/analytics_test.db"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    generate_test_dataset(path, count)
