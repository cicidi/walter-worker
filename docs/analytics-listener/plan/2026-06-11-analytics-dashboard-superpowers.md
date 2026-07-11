# Analytics Listener + Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete analytics pipeline: listener captures Claude Code + OpenCode sessions → import script processes raw data into SQLite → Knowledge Skill summarizes sessions → Dashboard displays everything.

**Architecture:** Three-layer pipeline. Listener (shell scripts for Claude Code, TypeScript plugin for OpenCode) writes raw JSONL → import.py merges/cleans/parses into SQLite → FastAPI + vanilla JS dashboard reads and displays. Knowledge Skill runs offline via OpenCode SDK to generate session summaries and knowledge cards.

**Tech Stack:** Shell (hooks), TypeScript (OpenCode plugin), Python (import script, FastAPI dashboard), SQLite, vanilla HTML/CSS/JS (frontend), Playwright (E2E tests)

---

## Wave 1: Data Pipeline (Listener → DB → Knowledge Skill)

---

### Task 1: DB Schema & Connection Module

**Files:**
- Create: `src/coworker/analytics/__init__.py`
- Create: `src/coworker/analytics/db.py`

- [ ] **Step 1: Create analytics package**

```bash
mkdir -p src/coworker/analytics
touch src/coworker/analytics/__init__.py
```

- [ ] **Step 2: Create DB schema file `src/coworker/analytics/db.py`**

```python
import sqlite3
import os
from pathlib import Path

DB_PATH = Path.home() / ".coworker" / "analytics" / "analytics.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id            TEXT PRIMARY KEY,
    ide           TEXT NOT NULL,
    project       TEXT,
    cwd           TEXT,
    model         TEXT,
    initiative    TEXT,
    branch        TEXT,
    created_at    TEXT NOT NULL,
    closed_at     TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL REFERENCES sessions(id),
    seq           INTEGER NOT NULL,
    type          TEXT NOT NULL,
    content       TEXT,
    ts            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_msg_session_seq ON messages(session_id, seq);

CREATE TABLE IF NOT EXISTS tool_calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    call_id         TEXT NOT NULL,
    tool            TEXT NOT NULL,
    tool_type       TEXT DEFAULT 'builtin',
    server_name     TEXT,
    parent_call_id  TEXT,
    parent_skill    TEXT,
    args            TEXT,
    result          TEXT,
    duration_ms     INTEGER,
    seq_before      INTEGER,
    seq_after       INTEGER,
    ts              TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tc_session ON tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_tc_parent ON tool_calls(parent_call_id);
CREATE INDEX IF NOT EXISTS idx_tc_tool ON tool_calls(tool);

CREATE TABLE IF NOT EXISTS file_ops (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    call_id     TEXT NOT NULL,
    op          TEXT NOT NULL,
    path        TEXT NOT NULL,
    file_type   TEXT,
    project     TEXT,
    skill_name  TEXT,
    seq         INTEGER NOT NULL,
    ts          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fo_session ON file_ops(session_id);
CREATE INDEX IF NOT EXISTS idx_fo_type ON file_ops(file_type);
CREATE INDEX IF NOT EXISTS idx_fo_project ON file_ops(project);

CREATE TABLE IF NOT EXISTS session_stats (
    session_id    TEXT PRIMARY KEY REFERENCES sessions(id),
    message_count INTEGER DEFAULT 0,
    tool_count    INTEGER DEFAULT 0,
    skill_count   INTEGER DEFAULT 0,
    read_count    INTEGER DEFAULT 0,
    write_count   INTEGER DEFAULT 0,
    bash_count    INTEGER DEFAULT 0,
    duration_min  INTEGER,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    name           TEXT PRIMARY KEY,
    total_calls    INTEGER DEFAULT 0,
    last_invoked   TEXT,
    first_invoked  TEXT
);

CREATE TABLE IF NOT EXISTS knowledge (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    type            TEXT NOT NULL,
    session_id      TEXT REFERENCES sessions(id),
    project         TEXT,
    skills          TEXT,
    summary         TEXT,
    evidence        TEXT,
    generated_at    TEXT NOT NULL,
    merged_to_skill TEXT
);
CREATE INDEX IF NOT EXISTS idx_knowledge_project ON knowledge(project);
CREATE INDEX IF NOT EXISTS idx_knowledge_session ON knowledge(session_id);

CREATE TABLE IF NOT EXISTS session_summaries (
    session_id             TEXT PRIMARY KEY REFERENCES sessions(id),
    sop_workflows          TEXT,
    context_to_remember    TEXT,
    effective_operations   TEXT,
    pitfalls_and_fixes     TEXT,
    wasted_actions         TEXT,
    bottlenecks            TEXT,
    efficiency_tip         TEXT,
    efficiency_score       REAL,
    think_action_ratio     REAL,
    edit_redundancy        REAL,
    loop_count             INTEGER,
    user_wait_minutes      REAL,
    memory_keywords        TEXT,
    generated_at           TEXT NOT NULL
);
"""

def get_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    conn = get_db(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
```

- [ ] **Step 3: Add CLI command for db init**

Add to `src/coworker/cli.py`:

```python
@app.command()
def analytics_db_init():
    """Initialize analytics database."""
    from .analytics.db import init_db
    init_db()
    console.print(f"[green]Created analytics.db[/green]")
```

- [ ] **Step 4: Test DB init**

```bash
python -c "from src.coworker.analytics.db import init_db; conn = init_db('/tmp/test_analytics.db'); print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add src/coworker/analytics/__init__.py src/coworker/analytics/db.py src/coworker/cli.py
git commit -m "feat: add analytics DB schema and init command"
```

---

### Task 2: OpenCode Analytics Plugin

**Files:**
- Create: `.opencode/coworker-analytics/index.ts`
- Create: `.opencode/coworker-analytics/recorder.ts`
- Create: `.opencode/coworker-analytics/session.ts`

- [ ] **Step 1: Create `recorder.ts`**

```typescript
import { appendFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";
import { homedir } from "os";

const BASE_DIR = join(homedir(), ".coworker", "analytics", "sessions");

export class Recorder {
  private seq: number = 0;
  private sessionDir: string;

  constructor(sessionId: string) {
    this.sessionDir = join(BASE_DIR, sessionId);
    if (!existsSync(this.sessionDir)) {
      mkdirSync(this.sessionDir, { recursive: true });
    }
  }

  nextSeq(): number {
    return ++this.seq;
  }

  writeJSONL(file: string, data: Record<string, unknown>): void {
    try {
      const path = join(this.sessionDir, file);
      const line = JSON.stringify(data, null, 0) + "\n";
      appendFileSync(path, line);
    } catch {
      // silent fail
    }
  }

  writeSessionYaml(data: Record<string, string>): void {
    try {
      const path = join(this.sessionDir, "session.yaml");
      let content = "";
      for (const [k, v] of Object.entries(data)) {
        content += `${k}: "${v}"\n`;
      }
      // writeFileSync instead of append for yaml
      const { writeFileSync } = require("fs");
      writeFileSync(path, content);
    } catch {
      // silent fail
    }
  }
}
```

- [ ] **Step 2: Create `session.ts`**

```typescript
import { Recorder } from "./recorder";

function generateSessionId(): string {
  const now = new Date();
  const date = now.toISOString().slice(0, 10);
  const time = now.toTimeString().slice(0, 8).replace(/:/g, "");
  const hex = Math.random().toString(36).slice(2, 8);
  return `${date}-T${time}-${hex}`;
}

export function createSession(cwd: string, ide: string): { id: string; recorder: Recorder } {
  const id = generateSessionId();
  const recorder = new Recorder(id);
  recorder.writeSessionYaml({
    session_id: id,
    created: new Date().toISOString(),
    ide: ide,
    cwd: cwd || "",
    project: "",
    initiative: "",
    branch: "",
  });
  return { id, recorder };
}
```

- [ ] **Step 3: Create plugin entry `index.ts`**

```typescript
import type { Plugin } from "@opencode-ai/plugin";
import { createSession } from "./session";
import { Recorder } from "./recorder";
import { join } from "path";
import { homedir } from "os";

const BASE_DIR = join(homedir(), ".coworker", "analytics");

let currentRecorder: Recorder | null = null;
let currentSessionId: string | null = null;

export const CoworkerAnalyticsPlugin: Plugin = {
  async event({ event }) {
    try {
      if (event.type === "session.created") {
        const { id, recorder } = createSession(process.cwd(), "opencode");
        currentSessionId = id;
        currentRecorder = recorder;
      }
      if (event.type === "session.deleted" && currentRecorder) {
        currentRecorder.writeSessionYaml({
          session_id: currentSessionId!,
          closed: new Date().toISOString(),
        });
      }
    } catch {}
  },

  "chat.message"(input, output) {
    if (!currentRecorder) return;
    try {
      const msg = output.message;
      const type = msg.role === "user" ? "user" : "assistant";
      const content = msg.parts?.map((p: any) => p.text || "").join("") || "";
      currentRecorder.writeJSONL("messages.jsonl", {
        ts: new Date().toISOString(),
        type,
        seq: currentRecorder.nextSeq(),
        content,
      });
    } catch {}
  },

  "tool.execute.before"(input, output) {
    if (!currentRecorder) return;
    try {
      currentRecorder.writeJSONL("tools.jsonl", {
        ts: new Date().toISOString(),
        phase: "before",
        tool: input.tool,
        tool_type: "builtin",
        call_id: input.callID,
        seq: currentRecorder.nextSeq(),
        args: output.args,
      });
    } catch {}
  },

  "tool.execute.after"(input, output) {
    if (!currentRecorder) return;
    try {
      currentRecorder.writeJSONL("tools.jsonl", {
        ts: new Date().toISOString(),
        phase: "after",
        tool: input.tool,
        tool_type: "builtin",
        call_id: input.callID,
        seq: currentRecorder.nextSeq(),
        result: output.output || "",
        duration_ms: output.metadata?.duration || 0,
      });
    } catch {}
  },

  async dispose() {
    currentRecorder = null;
    currentSessionId = null;
  },
};
```

- [ ] **Step 4: Commit**

```bash
git add .opencode/coworker-analytics/
git commit -m "feat: add OpenCode analytics plugin"
```

---

### Task 3: Claude Code Hook Scripts

**Files:**
- Create: `~/.coworker/analytics/hooks/common.sh` (shared helpers)
- Create: `~/.coworker/analytics/hooks/on-user-prompt.sh`
- Create: `~/.coworker/analytics/hooks/on-pre-tool.sh`
- Create: `~/.coworker/analytics/hooks/on-post-tool.sh`
- Create: `~/.coworker/analytics/hooks/on-stop.sh`

Store canonical copies in `src/coworker/analytics/hooks/`, copied to `~/.coworker/analytics/hooks/` on install.

- [ ] **Step 1: Create `src/coworker/analytics/hooks/common.sh`**

```bash
#!/usr/bin/env bash
BASE="$HOME/.coworker/analytics"
SESSIONS="$BASE/sessions"
SEQ_FILE=""
SESSION_ID=""

generate_session_id() {
  echo "$(date +%Y-%m-%d-T%H%M%S)-$(openssl rand -hex 3)"
}

ensure_session() {
  if [ -z "$SESSION_ID" ] || [ ! -d "$SESSIONS/$SESSION_ID" ]; then
    SESSION_ID=$(ls "$SESSIONS" 2>/dev/null | tail -1)
    if [ -z "$SESSION_ID" ]; then
      SESSION_ID=$(generate_session_id)
      mkdir -p "$SESSIONS/$SESSION_ID"
      cat > "$SESSIONS/$SESSION_ID/session.yaml" <<YAML
session_id: "$SESSION_ID"
created: "$(date '+%Y-%m-%dT%H:%M:%S%z')"
ide: "claude-code"
cwd: "$(pwd)"
project: ""
initiative: ""
branch: ""
YAML
    fi
  fi
  SEQ_FILE="$SESSIONS/$SESSION_ID/.seq"
}

next_seq() {
  local seq=0
  if [ -f "$SEQ_FILE" ]; then
    seq=$(cat "$SEQ_FILE")
  fi
  seq=$((seq + 1))
  echo "$seq" > "$SEQ_FILE"
  echo "$seq"
}

append_jsonl() {
  local file="$1"
  local json="$2"
  echo "$json" >> "$SESSIONS/$SESSION_ID/$file" 2>/dev/null || true
}
```

- [ ] **Step 2: Create `on-user-prompt.sh`**

```bash
#!/usr/bin/env bash
source "$HOME/.coworker/analytics/hooks/common.sh"
ensure_session

content=$(cat)
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')

json=$(printf '{"ts":"%s","type":"user","seq":%s,"content":"%s"}' \
  "$ts" "$seq" "$(echo "$content" | sed 's/"/\\"/g' | tr -d '\n')")
append_jsonl "messages.jsonl" "$json"
```

- [ ] **Step 3: Create `on-pre-tool.sh`**

```bash
#!/usr/bin/env bash
source "$HOME/.coworker/analytics/hooks/common.sh"
ensure_session

input=$(cat)
tool=$(echo "$input" | jq -r '.tool_name // empty')
call_id=$(echo "$input" | jq -r '.tool_use_id // empty')
args=$(echo "$input" | jq -c '.tool_input // empty')
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')

json=$(printf '{"ts":"%s","phase":"before","tool":"%s","tool_type":"builtin","call_id":"%s","seq":%s,"args":%s}' \
  "$ts" "$tool" "$call_id" "$seq" "$args")
append_jsonl "tools.jsonl" "$json"
```

- [ ] **Step 4: Create `on-post-tool.sh`**

```bash
#!/usr/bin/env bash
source "$HOME/.coworker/analytics/hooks/common.sh"
ensure_session

input=$(cat)
tool=$(echo "$input" | jq -r '.tool_name // empty')
call_id=$(echo "$input" | jq -r '.tool_use_id // empty')
result=$(echo "$input" | jq -c '.tool_output // empty')
duration=$(echo "$input" | jq -r '.duration_ms // 0')
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')

json=$(printf '{"ts":"%s","phase":"after","tool":"%s","tool_type":"builtin","call_id":"%s","seq":%s,"result":%s,"duration_ms":%s}' \
  "$ts" "$tool" "$call_id" "$seq" "$result" "$duration")
append_jsonl "tools.jsonl" "$json"
```

- [ ] **Step 5: Create `on-stop.sh`**

```bash
#!/usr/bin/env bash
source "$HOME/.coworker/analytics/hooks/common.sh"
ensure_session

ts=$(date '+%Y-%m-%dT%H:%M:%S%z')

# Update session.yaml with closed time
sed -i "/^closed:/d" "$SESSIONS/$SESSION_ID/session.yaml"
echo "closed: \"$ts\"" >> "$SESSIONS/$SESSION_ID/session.yaml"

# Count stats for index
msg_count=$(wc -l < "$SESSIONS/$SESSION_ID/messages.jsonl" 2>/dev/null || echo 0)
tool_count=$(wc -l < "$SESSIONS/$SESSION_ID/tools.jsonl" 2>/dev/null || echo 0)
created=$(grep "created:" "$SESSIONS/$SESSION_ID/session.yaml" | cut -d'"' -f2)

# Append to index
json=$(printf '{"session_id":"%s","created":"%s","ide":"claude-code","message_count":%s,"tool_count":%s}' \
  "$SESSION_ID" "$created" "$msg_count" "$tool_count")
echo "$json" >> "$BASE/index.jsonl"
```

- [ ] **Step 6: Commit**

```bash
mkdir -p src/coworker/analytics/hooks
git add src/coworker/analytics/hooks/
git commit -m "feat: add Claude Code analytics hook scripts"
```

---

### Task 4: Import Script (JSONL → SQLite)

**Files:**
- Create: `src/coworker/analytics/import_data.py`
- Create: `tests/analytics/__init__.py`
- Create: `tests/analytics/test_import.py`

- [ ] **Step 1: Write failing test `tests/analytics/test_import.py`**

```python
import json
import tempfile
from pathlib import Path
from src.coworker.analytics.db import init_db, get_db
from src.coworker.analytics.import_data import import_session

def test_import_basic_session():
    tmp = Path(tempfile.mkdtemp())
    session_dir = tmp / "sessions" / "test-session"
    session_dir.mkdir(parents=True)

    # Write raw data
    (session_dir / "session.yaml").write_text(
        'session_id: "test-session"\n'
        'created: "2026-06-11T14:30:52+08:00"\n'
        'ide: "opencode"\n'
        'cwd: "/home/test/project"\n'
        'project: "test-project"\n'
        'initiative: "test-init"\n'
        'branch: "feat/test"\n'
    )
    (session_dir / "messages.jsonl").write_text(
        '{"ts":"2026-06-11T14:30:52+08:00","type":"user","seq":1,"content":"hello"}\n'
        '{"ts":"2026-06-11T14:31:05+08:00","type":"assistant","seq":2,"content":"hi"}\n'
    )
    (session_dir / "tools.jsonl").write_text(
        '{"ts":"2026-06-11T14:31:05+08:00","phase":"before","tool":"bash","tool_type":"builtin","call_id":"c1","seq":3,"args":{"command":"ls"}}\n'
        '{"ts":"2026-06-11T14:31:10+08:00","phase":"after","tool":"bash","tool_type":"builtin","call_id":"c1","seq":4,"result":"file.py","duration_ms":5000}\n'
    )

    db_path = tmp / "analytics.db"
    conn = init_db(db_path)

    import_session(session_dir, conn)

    # Verify session
    rows = conn.execute("SELECT id, ide, project, initiative, branch FROM sessions").fetchall()
    assert len(rows) == 1
    assert rows[0]["id"] == "test-session"
    assert rows[0]["initiative"] == "test-init"

    # Verify messages
    msgs = conn.execute("SELECT type, content FROM messages ORDER BY seq").fetchall()
    assert len(msgs) == 2
    assert msgs[0]["type"] == "user"
    assert msgs[1]["type"] == "assistant"

    # Verify tool calls merged
    tcs = conn.execute("SELECT tool, call_id, args, result, duration_ms FROM tool_calls").fetchall()
    assert len(tcs) == 1
    assert tcs[0]["tool"] == "bash"
    assert json.loads(tcs[0]["args"])["command"] == "ls"
    assert tcs[0]["result"] == "file.py"
    assert tcs[0]["duration_ms"] == 5000

    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/analytics/test_import.py::test_import_basic_session -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'src.coworker.analytics.import_data'`

- [ ] **Step 3: Write `src/coworker/analytics/import_data.py`**

```python
import json
import sys
from pathlib import Path
from collections import defaultdict
from src.coworker.analytics.db import get_db

HOME = Path.home()
BASE = HOME / ".coworker" / "analytics"
SESSIONS = BASE / "sessions"

def parse_session_yaml(session_dir: Path) -> dict:
    yaml_file = session_dir / "session.yaml"
    if not yaml_file.exists():
        return {}
    data = {}
    for line in yaml_file.read_text().strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"')
            data[key.strip()] = val
    return data

def import_session(session_dir: Path, conn_or_path=None):
    conn = conn_or_path if hasattr(conn_or_path, 'execute') else get_db(conn_or_path)

    info = parse_session_yaml(session_dir)
    session_id = info.get("session_id", session_dir.name)

    conn.execute(
        """INSERT OR REPLACE INTO sessions (id, ide, project, cwd, model, initiative, branch, created_at, closed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, info.get("ide", ""), info.get("project", ""), info.get("cwd", ""),
         info.get("model", ""), info.get("initiative", ""), info.get("branch", ""),
         info.get("created", ""), info.get("closed", "")),
    )

    # Messages
    msgs_file = session_dir / "messages.jsonl"
    if msgs_file.exists():
        for line in msgs_file.read_text().strip().split("\n"):
            if not line.strip():
                continue
            m = json.loads(line)
            conn.execute(
                "INSERT OR IGNORE INTO messages (session_id, seq, type, content, ts) VALUES (?, ?, ?, ?, ?)",
                (session_id, m.get("seq", 0), m.get("type", ""), m.get("content", ""), m.get("ts", "")),
            )

    # Tool calls — merge pre+post
    pre_calls = {}  # call_id -> pre_data
    post_calls = {}  # call_id -> post_data
    tools_file = session_dir / "tools.jsonl"
    if tools_file.exists():
        for line in tools_file.read_text().strip().split("\n"):
            if not line.strip():
                continue
            t = json.loads(line)
            cid = t.get("call_id", "")
            if t.get("phase") == "before":
                pre_calls[cid] = t
            elif t.get("phase") == "after":
                post_calls[cid] = t

        all_call_ids = set(pre_calls.keys()) | set(post_calls.keys())
        for cid in all_call_ids:
            pre = pre_calls.get(cid, {})
            post = post_calls.get(cid, {})

            tool = pre.get("tool") or post.get("tool", "")
            tool_type = pre.get("tool_type") or post.get("tool_type", "builtin")
            server_name = pre.get("server_name") or post.get("server_name", "")
            args_json = json.dumps(pre.get("args", {})) if pre.get("args") else None
            result = post.get("result") or ""
            duration = post.get("duration_ms") or 0
            seq_before = pre.get("seq")
            seq_after = post.get("seq")
            ts = pre.get("ts") or post.get("ts", "")

            conn.execute(
                """INSERT OR IGNORE INTO tool_calls
                   (session_id, call_id, tool, tool_type, server_name, args, result, duration_ms, seq_before, seq_after, ts)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, cid, tool, tool_type, server_name or None, args_json, result, duration, seq_before, seq_after, ts),
            )

            # Detect file operations
            if tool in ("Read", "Write", "Edit", "Glob") and args_json:
                args = json.loads(args_json)
                file_path = args.get("filePath") or args.get("path") or ""
                if file_path:
                    op_map = {"Read": "read", "Write": "write", "Edit": "edit", "Glob": "glob"}
                    op = op_map.get(tool, tool.lower())
                    file_type = Path(file_path).suffix.lstrip(".") or None
                    project = info.get("project", "")
                    conn.execute(
                        """INSERT OR IGNORE INTO file_ops (session_id, call_id, op, path, file_type, project, seq, ts)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (session_id, cid, op, file_path, file_type, project, tool.get("seq", 0) if isinstance(tool, dict) else 0, ts),
                    )

    # Skills aggregation
    skill_names = set()
    for cid, pre in pre_calls.items():
        if pre.get("tool") == "Skill":
            args = pre.get("args", {})
            if isinstance(args, dict):
                name = args.get("name", "")
            elif isinstance(args, str):
                try:
                    name = json.loads(args).get("name", "")
                except:
                    name = ""
            if name:
                skill_names.add(name)

    for name in skill_names:
        conn.execute("""INSERT OR IGNORE INTO skills (name) VALUES (?)""", (name,))
        conn.execute(
            """UPDATE skills SET
               total_calls = total_calls + 1,
               last_invoked = MAX(COALESCE(last_invoked, ''), ?),
               first_invoked = CASE WHEN first_invoked IS NULL THEN ? ELSE first_invoked END
               WHERE name = ?""",
            (info.get("created", ""), info.get("created", ""), name),
        )

    # Session stats
    msg_count = conn.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)).fetchone()[0]
    tool_count = conn.execute("SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", (session_id,)).fetchone()[0]
    skill_count = conn.execute("SELECT COUNT(*) FROM tool_calls WHERE session_id = ? AND tool = 'Skill'", (session_id,)).fetchone()[0]
    read_count = conn.execute("SELECT COUNT(*) FROM file_ops WHERE session_id = ? AND op = 'read'", (session_id,)).fetchone()[0]
    write_count = conn.execute("SELECT COUNT(*) FROM file_ops WHERE session_id = ? AND op IN ('write', 'edit')", (session_id,)).fetchone()[0]
    bash_count = conn.execute("SELECT COUNT(*) FROM tool_calls WHERE session_id = ? AND tool = 'Bash'", (session_id,)).fetchone()[0]

    # Duration
    created = info.get("created", "")
    closed = info.get("closed", "")
    duration_min = None
    if created and closed:
        try:
            from datetime import datetime
            c1 = datetime.fromisoformat(created)
            c2 = datetime.fromisoformat(closed)
            duration_min = int((c2 - c1).total_seconds() / 60)
        except:
            pass

    from datetime import datetime as dt
    conn.execute(
        """INSERT OR REPLACE INTO session_stats
           (session_id, message_count, tool_count, skill_count, read_count, write_count, bash_count, duration_min, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, msg_count, tool_count, skill_count, read_count, write_count, bash_count, duration_min, dt.now().isoformat()),
    )

    conn.commit()

def import_all():
    conn = get_db()
    if not SESSIONS.exists():
        print("No sessions directory found")
        return
    for session_dir in sorted(SESSIONS.iterdir()):
        if session_dir.is_dir():
            print(f"Importing {session_dir.name}...")
            import_session(session_dir, conn)
    conn.close()
    print("Done.")

if __name__ == "__main__":
    import_all()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/analytics/test_import.py::test_import_basic_session -v
```
Expected: PASS

- [ ] **Step 5: Add CLI command `coworker analytics import`**

In `src/coworker/cli.py`:

```python
@app.command()
def analytics_import():
    """Import raw JSONL sessions into SQLite."""
    from .analytics.import_data import import_all
    import_all()
```

- [ ] **Step 6: Commit**

```bash
git add src/coworker/analytics/import_data.py tests/analytics/ src/coworker/cli.py
git commit -m "feat: add analytics import script with tests"
```

---

### Task 5: Installer Integration (Out-of-Box)

**Files:**
- Modify: `setup/install.sh`

- [ ] **Step 1: Add analytics setup to install.sh**

Add this section after Step 12 (gitignore) and before Step 13 (MCP sync), renaming subsequent steps:

```bash
# =============================================================================
# Step 13 — Analytics Listener Setup
# =============================================================================
echo ""
log "Setting up analytics listener..."

ANALYTICS_DIR="$HOME/.coworker/analytics"
mkdir -p "$ANALYTICS_DIR/sessions"
mkdir -p "$ANALYTICS_DIR/hooks"

# Copy Claude Code hook scripts
HOOKS_SRC="$REPO_ROOT/src/coworker/analytics/hooks"
if [[ -d "$HOOKS_SRC" ]]; then
  cp "$HOOKS_SRC/"*.sh "$ANALYTICS_DIR/hooks/"
  chmod +x "$ANALYTICS_DIR/hooks/"*.sh
  ok "Claude Code hook scripts installed to $ANALYTICS_DIR/hooks/"
else
  warn "Hook scripts not found at $HOOKS_SRC — skipping"
fi

# Configure Claude Code hooks in settings.json
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
if [[ ! -f "$CLAUDE_SETTINGS" ]]; then
  echo '{}' > "$CLAUDE_SETTINGS"
fi
python3 -c "
import json
p = '$CLAUDE_SETTINGS'
with open(p) as f:
    cfg = json.load(f)
cfg.setdefault('hooks', {})
cfg['hooks']['UserPromptSubmit'] = [{'command': '$HOME/.coworker/analytics/hooks/on-user-prompt.sh'}]
cfg['hooks']['PreToolUse'] = [{'command': '$HOME/.coworker/analytics/hooks/on-pre-tool.sh'}]
cfg['hooks']['PostToolUse'] = [{'command': '$HOME/.coworker/analytics/hooks/on-post-tool.sh'}]
cfg['hooks']['Stop'] = [{'command': '$HOME/.coworker/analytics/hooks/on-stop.sh'}]
with open(p, 'w') as f:
    json.dump(cfg, f, indent=2)
print('Claude Code hooks configured')
" 2>/dev/null && ok "Claude Code hooks configured in $CLAUDE_SETTINGS" || \
    warn "Failed to configure Claude Code hooks"

# Initialize DB
python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from src.coworker.analytics.db import init_db
init_db()
" 2>/dev/null && ok "SQLite analytics database initialized" || \
    warn "Analytics DB init skipped (run: coworker analytics-db-init)"

echo "Analytics listener setup complete."
```

- [ ] **Step 2: Renumber subsequent steps in install.sh**

After inserting the analytics setup, renumber:
- Step 13 → Step 14 (MCP config sync)
- Done section continues unchanged

- [ ] **Step 3: Test installer end-to-end**

```bash
# Run in a clean temp directory with a fresh coworker copy
./setup/install.sh --global
```

Verify:
- `~/.coworker/analytics/hooks/` contains 4 .sh files
- `~/.coworker/analytics/analytics.db` exists with all tables
- `~/.claude/settings.json` contains hooks config
- `~/.coworker/analytics/sessions/` directory exists

- [ ] **Step 4: Commit**

```bash
git add setup/install.sh
git commit -m "feat: add out-of-box analytics listener setup to installer"
```

---

### Task 6: Knowledge Skill (Session Summarizer)

**Files:**
- Create: `skills/knowledge-skill/SKILL.md`
- Create: `src/coworker/analytics/knowledge.py`

- [ ] **Step 1: Create skill definition `skills/knowledge-skill/SKILL.md`**

```markdown
---
name: knowledge-skill
description: |
  Reads session data from SQLite, feeds to LLM for structured analysis,
  writes session summaries and knowledge cards back to SQLite.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - analyze this session
    - summarize what I did
    - generate knowledge cards
    - summarize session
    - analyze today sessions
    - run knowledge skill
  when_to_use: |
    After completing a session to extract insights.
    Periodic batch analysis of recent sessions.
---

# knowledge-skill

Reads session data from analytics.db, sends to LLM for structured analysis,
writes back session_summaries and knowledge cards.

## Process

### Step 1: Load session data

Run `coworker knowledge summarize <session_id>` which:
1. Reads messages + tool_calls from analytics.db
2. Formats as structured prompt
3. Sends to LLM (uses current model)
4. Writes result to session_summaries + knowledge tables

### Step 2: Generate session summary

Prompt template instructs LLM to produce:
- SOP workflows discovered
- Context to remember for next session
- Effective operations that worked well
- Pitfalls and fixes (what failed, what solved it)
- Wasted actions (loops, dead ends)
- Bottlenecks (longest think times, repetitive calls)
- One efficiency tip
- Memory keywords for Obsidian graph

### Step 3: Generate knowledge cards

For patterns recurring across ≥2 sessions, generate knowledge cards:
- Type: trap, best_practice, pattern, decision, constraint
- Title, summary, evidence, related skills
- Write to knowledge table

### Step 4: Batch mode

`coworker knowledge analyze --since yesterday`
`coworker knowledge analyze --all`
```

- [ ] **Step 2: Create `src/coworker/analytics/knowledge.py`**

```python
import json
from datetime import datetime, timedelta
from src.coworker.analytics.db import get_db


def get_session_data(session_id: str):
    """Read all data for a session, formatted for LLM prompt."""
    conn = get_db()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not session:
        conn.close()
        return None

    msgs = conn.execute(
        "SELECT seq, type, content FROM messages WHERE session_id = ? ORDER BY seq",
        (session_id,)
    ).fetchall()

    tools = conn.execute(
        "SELECT call_id, tool, args, result, duration_ms, seq_before, seq_after "
        "FROM tool_calls WHERE session_id = ? ORDER BY COALESCE(seq_before, seq_after)",
        (session_id,)
    ).fetchall()

    conn.close()

    return {
        "session_id": session_id,
        "ide": session["ide"],
        "project": session["project"],
        "initiative": session["initiative"],
        "branch": session["branch"],
        "started": session["created_at"],
        "ended": session["closed_at"],
        "messages": [dict(m) for m in msgs],
        "tool_calls": [dict(t) for t in tools],
    }


def build_summary_prompt(data: dict) -> str:
    return f"""Analyze this AI coding session data and produce a structured summary.

Session: {data['session_id']}
IDE: {data['ide']}
Project: {data['project']}
Initiative: {data['initiative']}
Branch: {data['branch']}
Duration: {data['started']} to {data['ended']}

Messages:
{json.dumps(data['messages'], indent=2)}

Tool calls:
{json.dumps(data['tool_calls'], indent=2)}

Output a JSON object with these fields:
{{
  "sop_workflows": ["reusable step sequences discovered"],
  "context_to_remember": "project state, branch status, unfinished work",
  "effective_operations": ["specific tool invocations that worked well"],
  "pitfalls_and_fixes": [{{"problem": "...", "attempts": ["..."], "solution": "..."}}],
  "wasted_actions": ["loops, unnecessary reads, dead-end explorations"],
  "bottlenecks": ["longest think times, most repetitive tool calls"],
  "efficiency_tip": "one actionable suggestion",
  "efficiency_score": 0.0-1.0,
  "memory_keywords": ["keyword1", "keyword2"]
}}

Return ONLY the JSON, no markdown code blocks."""


def build_knowledge_prompt(sessions_data: list[dict]) -> str:
    sessions_json = json.dumps([{
        "session_id": s["session_id"],
        "project": s["project"],
        "initiative": s["initiative"],
        "messages": s["messages"],
        "tool_calls": s["tool_calls"],
    } for s in sessions_data], indent=2)

    return f"""Analyze these {len(sessions_data)} AI coding sessions and extract cross-session knowledge cards.

Sessions:
{sessions_json}

Output a JSON array of knowledge cards:
[
  {{
    "title": "short title",
    "type": "trap|best_practice|pattern|decision|constraint",
    "session_id": "source session id",
    "project": "project name",
    "skills": ["related", "skills"],
    "summary": "one sentence",
    "evidence": ["evidence item 1", "evidence item 2"]
  }}
]

Only include patterns that appear in ≥2 sessions. Return ONLY the JSON array."""


def write_summary(session_id: str, result: dict):
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO session_summaries
           (session_id, sop_workflows, context_to_remember, effective_operations,
            pitfalls_and_fixes, wasted_actions, bottlenecks, efficiency_tip,
            efficiency_score, memory_keywords, generated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            json.dumps(result.get("sop_workflows", [])),
            result.get("context_to_remember", ""),
            json.dumps(result.get("effective_operations", [])),
            json.dumps(result.get("pitfalls_and_fixes", [])),
            json.dumps(result.get("wasted_actions", [])),
            json.dumps(result.get("bottlenecks", [])),
            result.get("efficiency_tip", ""),
            result.get("efficiency_score"),
            json.dumps(result.get("memory_keywords", [])),
            datetime.now().isoformat(),
        )
    )
    conn.commit()
    conn.close()


def write_knowledge(cards: list[dict]):
    conn = get_db()
    for card in cards:
        conn.execute(
            """INSERT INTO knowledge (title, type, session_id, project, skills, summary, evidence, generated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                card["title"], card["type"], card.get("session_id", ""),
                card.get("project", ""), json.dumps(card.get("skills", [])),
                card.get("summary", ""), json.dumps(card.get("evidence", [])),
                datetime.now().isoformat(),
            ),
        )
    conn.commit()
    conn.close()
```

- [ ] **Step 3: Add CLI commands for knowledge skill**

In `src/coworker/cli.py`:

```python
@app.command()
def knowledge_summarize(session_id: str):
    """Generate session summary for a given session."""
    from .analytics.knowledge import get_session_data, build_summary_prompt
    data = get_session_data(session_id)
    if not data:
        console.print(f"[red]Session {session_id} not found[/red]")
        return
    prompt = build_summary_prompt(data)
    console.print("[green]Prompt ready. Run through LLM:[/green]")
    console.print(prompt[:500] + "...")

@app.command()
def knowledge_analyze(
    since: str = "yesterday",
    all_sessions: bool = False,
):
    """Generate knowledge cards from sessions."""
    from .analytics.knowledge import get_session_data, build_knowledge_prompt
    from .analytics.db import get_db

    conn = get_db()
    if all_sessions:
        rows = conn.execute("SELECT id FROM sessions ORDER BY created_at").fetchall()
    else:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        rows = conn.execute("SELECT id FROM sessions WHERE created_at >= ?", (date,)).fetchall()
    conn.close()

    if not rows:
        console.print("[dim]No sessions found[/dim]")
        return

    sessions_data = []
    for row in rows:
        data = get_session_data(row["id"])
        if data:
            sessions_data.append(data)

    prompt = build_knowledge_prompt(sessions_data)
    console.print("[green]Prompt ready for {len(sessions_data)} sessions. Run through LLM:[/green]")
    console.print(prompt[:500] + "...")
```

- [ ] **Step 4: Commit**

```bash
git add skills/knowledge-skill/ src/coworker/analytics/knowledge.py src/coworker/cli.py
git commit -m "feat: add knowledge skill for session summarization"
```

---

## Wave 2: Dashboard + Tests

---

### Task 7: Dashboard Backend (FastAPI)

**Files:**
- Create: `src/coworker/dashboard/__init__.py`
- Create: `src/coworker/dashboard/app.py`
- Create: `src/coworker/dashboard/queries.py`

- [ ] **Step 1: Create queries module `src/coworker/dashboard/queries.py`**

```python
from src.coworker.analytics.db import get_db

def query_sessions(limit=50):
    conn = get_db()
    rows = conn.execute(
        """SELECT s.*, ss.message_count, ss.tool_count, ss.skill_count, ss.duration_min
           FROM sessions s LEFT JOIN session_stats ss ON s.id = ss.session_id
           ORDER BY s.created_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def query_session_detail(session_id: str):
    conn = get_db()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    msgs = conn.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY seq", (session_id,)).fetchall()
    tools = conn.execute("SELECT * FROM tool_calls WHERE session_id = ? ORDER BY COALESCE(seq_before, seq_after)", (session_id,)).fetchall()
    files = conn.execute("SELECT * FROM file_ops WHERE session_id = ? ORDER BY seq", (session_id,)).fetchall()
    summary = conn.execute("SELECT * FROM session_summaries WHERE session_id = ?", (session_id,)).fetchone()
    conn.close()
    return {
        "session": dict(session) if session else None,
        "messages": [dict(m) for m in msgs],
        "tool_calls": [dict(t) for t in tools],
        "file_ops": [dict(f) for f in files],
        "summary": dict(summary) if summary else None,
    }

def query_skills():
    conn = get_db()
    skills = conn.execute("SELECT * FROM skills ORDER BY total_calls DESC").fetchall()
    conn.close()
    return [dict(s) for s in skills]

def query_tools():
    conn = get_db()
    tools = conn.execute(
        """SELECT tool, tool_type, server_name, COUNT(*) as calls,
                  AVG(duration_ms) as avg_ms, MAX(duration_ms) as max_ms
           FROM tool_calls GROUP BY tool, tool_type"""
    ).fetchall()
    conn.close()
    return [dict(t) for t in tools]

def query_files(project=None, file_type=None):
    conn = get_db()
    params = []
    sql = """SELECT f.*, COUNT(*) OVER (PARTITION BY f.path) as total_ops
             FROM file_ops f WHERE 1=1"""
    if project:
        sql += " AND f.project = ?"
        params.append(project)
    if file_type:
        sql += " AND f.file_type = ?"
        params.append(file_type)
    sql += " ORDER BY f.ts DESC LIMIT 500"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def query_knowledge():
    conn = get_db()
    rows = conn.execute("SELECT * FROM knowledge ORDER BY generated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def query_initiatives():
    conn = get_db()
    rows = conn.execute(
        """SELECT s.initiative, s.project,
                  COUNT(DISTINCT s.id) as session_count,
                  COUNT(DISTINCT t.call_id) as tool_count
           FROM sessions s LEFT JOIN tool_calls t ON s.id = t.session_id
           WHERE s.initiative IS NOT NULL AND s.initiative != ''
           GROUP BY s.initiative"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 2: Create FastAPI app `src/coworker/dashboard/app.py`**

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
from src.coworker.dashboard import queries
from src.coworker.analytics.db import get_db, DB_PATH

app = FastAPI(title="Coworker Dashboard")

STATIC_DIR = str(DB_PATH.parent.parent.parent / "static")


@app.get("/api/sessions")
def api_sessions(limit: int = 50):
    return queries.query_sessions(limit)

@app.get("/api/sessions/{session_id}")
def api_session_detail(session_id: str):
    return queries.query_session_detail(session_id)

@app.get("/api/skills")
def api_skills():
    return queries.query_skills()

@app.get("/api/tools")
def api_tools():
    return queries.query_tools()

@app.get("/api/files")
def api_files(project: str = None, file_type: str = None):
    return queries.query_files(project, file_type)

@app.get("/api/knowledge")
def api_knowledge():
    return queries.query_knowledge()

@app.get("/api/initiatives")
def api_initiatives():
    return queries.query_initiatives()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"status": "ok"}))
    except WebSocketDisconnect:
        pass

# Serve static files
import os
static_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "static")
if os.path.exists(static_path):
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")
```

- [ ] **Step 3: Add CLI command**

In `src/coworker/cli.py`:

```python
@app.command()
def dashboard(port: int = 8080):
    """Start the analytics dashboard."""
    import uvicorn
    from .dashboard.app import app
    console.print(f"[green]Dashboard starting at http://localhost:{port}[/green]")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
```

- [ ] **Step 4: Commit**

```bash
git add src/coworker/dashboard/ src/coworker/cli.py
git commit -m "feat: add dashboard FastAPI backend"
```

---

### Task 8: Dashboard Frontend

**Files:**
- Create: `static/index.html`
- Create: `static/dashboard.css`
- Create: `static/dashboard.js`

- [ ] **Step 1: Create `static/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Coworker Dashboard</title>
<link rel="stylesheet" href="dashboard.css">
</head>
<body>
<div id="app">
  <nav class="sidebar" id="sidebar"></nav>
  <main class="main" id="main"></main>
</div>
<script src="dashboard.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `static/dashboard.css`**

```css
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,monospace;background:#0d1117;color:#c9d1d9;height:100vh;overflow:hidden}
#app{display:flex;height:100vh}
.sidebar{width:200px;min-width:200px;background:#161b22;border-right:1px solid #30363d;padding:16px 0;overflow-y:auto}
.nav-item{display:flex;align-items:center;gap:8px;padding:8px 16px;font-size:12px;color:#8b949e;cursor:pointer;border-left:2px solid transparent}
.nav-item:hover{color:#e6edf3;background:#1c2129}
.nav-item.active{color:#58a6ff;border-left-color:#58a6ff;background:#1c2129}
.main{flex:1;overflow-y:auto;padding:24px}
h2{font-size:18px;margin-bottom:8px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:12px}
.card-title{font-size:13px;font-weight:bold;margin-bottom:10px;color:#e6edf3}
.tag{display:inline-block;font-size:10px;padding:3px 10px;border-radius:12px;margin:3px}
.tag-skill{color:#f85149;border:1px solid #f85149}
.tag-tool{color:#58a6ff;border:1px solid #58a6ff}
.tag-file{color:#3fb950;border:1px solid #3fb950}
.tag-knowledge{color:#bc8cff;border:1px solid #bc8cff}
.tag-session{color:#d29922;border:1px solid #d29922}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.stat{font-size:24px;font-weight:bold}
.stat-label{font-size:11px;color:#8b949e}
table{width:100%;border-collapse:collapse;font-size:12px}
th{text-align:left;padding:8px 12px;border-bottom:1px solid #30363d;color:#8b949e;font-size:10px;text-transform:uppercase}
td{padding:8px 12px;border-bottom:1px solid #21262d}
tr:hover{background:#1c2129}
.clickable{cursor:pointer;color:#58a6ff}
.clickable:hover{text-decoration:underline}
.bar{height:4px;background:#30363d;border-radius:2px;margin-top:4px}
.bar-fill{height:100%;border-radius:2px}
.bar-skill{background:#f85149}
.bar-tool{background:#58a6ff}
.bar-file{background:#3fb950}
.loading{text-align:center;padding:40px;color:#8b949e}
.error{color:#f85149;padding:8px}
```

- [ ] **Step 3: Create `static/dashboard.js`**

```javascript
const API = '/api';
let currentView = 'overview';

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

function renderSidebar() {
  const items = [
    { id: 'overview', label: 'Overview' },
    { id: 'sessions', label: 'Sessions' },
    { id: 'skills', label: 'Skills' },
    { id: 'tools', label: 'Tools' },
    { id: 'files', label: 'Files' },
    { id: 'knowledge', label: 'Knowledge' },
    { id: 'initiatives', label: 'Initiatives' },
  ];
  document.getElementById('sidebar').innerHTML = items.map(i =>
    `<div class="nav-item${i.id === currentView ? ' active' : ''}" onclick="navigate('${i.id}')">${i.label}</div>`
  ).join('');
}

function navigate(view) {
  currentView = view;
  renderSidebar();
  const main = document.getElementById('main');
  main.innerHTML = '<div class="loading">Loading...</div>';
  const loaders = {
    overview: loadOverview, sessions: loadSessions,
    skills: loadSkills, tools: loadTools,
    files: loadFiles, knowledge: loadKnowledge,
    initiatives: loadInitiatives
  };
  (loaders[view] || loadOverview)();
}

async function loadOverview() {
  const [sessions, skills, tools, knowledge] = await Promise.all([
    fetchJSON(`${API}/sessions?limit=10`),
    fetchJSON(`${API}/skills`),
    fetchJSON(`${API}/tools`),
    fetchJSON(`${API}/knowledge`),
  ]);

  const activeCount = sessions.filter(s => !s.closed_at).length;
  document.getElementById('main').innerHTML = `
    <h2>Dashboard Overview</h2>
    <div class="grid3" style="margin-bottom:24px">
      <div class="card">
        <div class="stat">${sessions.length}</div>
        <div class="stat-label">Total Sessions</div>
        <div class="stat" style="font-size:16px;margin-top:8px;color:#3fb950">${activeCount}</div>
        <div class="stat-label">Active Now</div>
      </div>
      <div class="card">
        <div class="stat">${skills.length}</div>
        <div class="stat-label">Skills Used</div>
      </div>
      <div class="card">
        <div class="stat">${knowledge.length}</div>
        <div class="stat-label">Knowledge Cards</div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Recent Sessions</div>
      <table>
        <tr><th>Session</th><th>IDE</th><th>Branch</th><th>Project</th><th>Tools</th><th>Duration</th></tr>
        ${sessions.map(s => `
          <tr>
            <td><span class="clickable" onclick="viewSession('${s.id}')">${s.id.slice(0, 20)}...</span></td>
            <td>${s.ide}</td>
            <td>${s.branch || '-'}</td>
            <td>${s.project || '-'}</td>
            <td>${s.tool_count || 0}</td>
            <td>${s.duration_min ? s.duration_min + 'm' : '-'}</td>
          </tr>`).join('')}
      </table>
    </div>`;
}

async function loadSessions() {
  const sessions = await fetchJSON(`${API}/sessions?limit=50`);
  document.getElementById('main').innerHTML = `
    <h2>Sessions</h2>
    <table>
      <tr><th>Session ID</th><th>IDE</th><th>Project</th><th>Branch</th><th>Initiative</th><th>Started</th><th>Messages</th><th>Tools</th></tr>
      ${sessions.map(s => `
        <tr>
          <td><span class="clickable" onclick="viewSession('${s.id}')">${s.id}</span></td>
          <td>${s.ide}</td>
          <td>${s.project || '-'}</td>
          <td>${s.branch || '-'}</td>
          <td>${s.initiative || '-'}</td>
          <td>${(s.created_at || '').slice(0, 16)}</td>
          <td>${s.message_count || 0}</td>
          <td>${s.tool_count || 0}</td>
        </tr>`).join('')}
    </table>`;
}

async function loadSkills() {
  const skills = await fetchJSON(`${API}/skills`);
  document.getElementById('main').innerHTML = `
    <h2>Skills</h2>
    ${skills.map(s => `
      <div class="card">
        <div class="card-title">${s.name}</div>
        <div>Calls: ${s.total_calls} | Last: ${(s.last_invoked || '').slice(0, 16)} | First: ${(s.first_invoked || '').slice(0, 16)}</div>
        <div class="bar" style="margin-top:8px"><div class="bar-fill bar-skill" style="width:${Math.min(s.total_calls * 5, 100)}%"></div></div>
      </div>`).join('')}`;
}

async function loadTools() {
  const tools = await fetchJSON(`${API}/tools`);
  document.getElementById('main').innerHTML = `
    <h2>Tools</h2>
    <table>
      <tr><th>Tool</th><th>Type</th><th>Calls</th><th>Avg (ms)</th><th>Max (ms)</th></tr>
      ${tools.map(t => `
        <tr>
          <td>${t.tool}</td>
          <td>${t.tool_type}${t.server_name ? ' (' + t.server_name + ')' : ''}</td>
          <td>${t.calls}</td>
          <td>${Math.round(t.avg_ms || 0)}</td>
          <td>${Math.round(t.max_ms || 0)}</td>
        </tr>`).join('')}
    </table>`;
}

async function loadFiles() {
  const files = await fetchJSON(`${API}/files`);
  document.getElementById('main').innerHTML = `
    <h2>Files</h2>
    <table>
      <tr><th>Path</th><th>Op</th><th>Project</th><th>Type</th><th>Skill</th></tr>
      ${files.map(f => `
        <tr>
          <td>${f.path}</td>
          <td>${f.op}</td>
          <td>${f.project || '-'}</td>
          <td>${f.file_type || '-'}</td>
          <td>${f.skill_name || '-'}</td>
        </tr>`).join('')}
    </table>`;
}

async function loadKnowledge() {
  const cards = await fetchJSON(`${API}/knowledge`);
  document.getElementById('main').innerHTML = `
    <h2>Knowledge Cards</h2>
    ${cards.map(k => `
      <div class="card">
        <div class="card-title">${k.type}: ${k.title}</div>
        <div style="margin-bottom:8px">${k.summary || ''}</div>
        <div style="font-size:10px;color:#8b949e">Project: ${k.project || '-'} | Session: ${(k.session_id || '').slice(0, 20)}</div>
      </div>`).join('')}`;
}

async function loadInitiatives() {
  const items = await fetchJSON(`${API}/initiatives`);
  document.getElementById('main').innerHTML = `
    <h2>Initiatives</h2>
    <table>
      <tr><th>Initiative</th><th>Project</th><th>Sessions</th><th>Tool Calls</th></tr>
      ${items.map(i => `
        <tr>
          <td>${i.initiative}</td>
          <td>${i.project}</td>
          <td>${i.session_count}</td>
          <td>${i.tool_count}</td>
        </tr>`).join('')}
    </table>`;
}

async function viewSession(id) {
  const data = await fetchJSON(`${API}/sessions/${id}`);
  const s = data.session;
  document.getElementById('main').innerHTML = `
    <h2>Session: ${s.id}</h2>
    <div class="grid2" style="margin-bottom:16px">
      <div class="card">
        <div class="card-title">Info</div>
        <div>IDE: ${s.ide} | Project: ${s.project || '-'} | Branch: ${s.branch || '-'}</div>
        <div>Initiative: ${s.initiative || '-'} | Started: ${(s.created_at || '').slice(0, 16)}</div>
      </div>
      <div class="card">
        <div class="card-title">Stats</div>
        <div>Messages: ${data.messages.length} | Tool Calls: ${data.tool_calls.length} | Files: ${data.file_ops.length}</div>
      </div>
    </div>
    ${data.summary ? `
    <div class="card">
      <div class="card-title">Session Summary</div>
      <div style="font-size:12px;line-height:1.6">
        <p><b>Context to remember:</b> ${data.summary.context_to_remember || '-'}</p>
        <p><b>Efficiency tip:</b> ${data.summary.efficiency_tip || '-'}</p>
        <p><b>Score:</b> ${data.summary.efficiency_score || '-'}</p>
      </div>
    </div>` : ''}
    <div class="card">
      <div class="card-title">Messages</div>
      ${data.messages.map(m => `<div style="font-size:12px;padding:4px 0;border-bottom:1px solid #21262d">[${m.type}] ${(m.content || '').slice(0, 200)}</div>`).join('')}
    </div>
    <div class="card">
      <div class="card-title">Tool Calls</div>
      <table>
        <tr><th>Tool</th><th>Args</th><th>Duration</th></tr>
        ${data.tool_calls.map(t => `
          <tr>
            <td>${t.tool}</td>
            <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(t.args || '').slice(0, 80)}</td>
            <td>${t.duration_ms || '-'}ms</td>
          </tr>`).join('')}
      </table>
    </div>
    <div style="margin-top:16px"><span class="clickable" onclick="navigate('sessions')">Back to Sessions</span></div>`;
}

// Init
renderSidebar();
navigate('overview');
```

- [ ] **Step 4: Add FastAPI dependencies to pyproject.toml**

```toml
dependencies = [
    "fastapi",
    "uvicorn",
]
```

- [ ] **Step 5: Commit**

```bash
git add static/ src/coworker/dashboard/ pyproject.toml
git commit -m "feat: add dashboard frontend with overview, sessions, skills, tools, files, knowledge views"
```

---

### Task 9: Test Data Generator

**Files:**
- Create: `tests/analytics/test_data.py`

- [ ] **Step 1: Write test data generator `tests/analytics/test_data.py`**

```python
import json
import random
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from src.coworker.analytics.db import init_db
from src.coworker.analytics.import_data import import_session

PROJECTS = ["ai-coworker", "skill-factory", "dotfiles"]
TOOLS = ["Bash", "Read", "Write", "Edit", "Skill", "TodoWrite", "Glob", "Grep", "Task", "Question"]
SKILLS = ["brainstorming", "writing-plans", "systematic-debugging", "executing-plans", "subagent-driven-dev"]
FILES = [
    "CLAUDE.md", "src/coworker/models.py", "src/coworker/cli.py",
    "src/coworker/config.py", "docs/prd/PRD.md", "docs/design/DESIGN.md",
    "coworker-blueprint.md", "pyproject.toml", "setup/install.sh",
]
BRANCHES = ["feat/dashboard", "feat/listener", "fix/config", "main"]
INITIATIVES = ["dashboard-v1", "listener-v1", None]


def generate_test_session(session_id: str, project: str, branch: str, initiative: str | None,
                          start: datetime, duration_min: int = 30):
    session_dir = Path(tempfile.mkdtemp()) / "sessions" / session_id
    session_dir.mkdir(parents=True)

    created = start.strftime("%Y-%m-%dT%H:%M:%S%z")
    closed = (start + timedelta(minutes=duration_min)).strftime("%Y-%m-%dT%H:%M:%S%z")

    # session.yaml
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

    # Generate user messages + assistant responses
    user_msgs = [
        "help me build a dashboard",
        "analyze the codebase first",
        "what skills should I use?",
        "now write the implementation",
        "run the tests",
    ]
    assistant_msgs = [
        "I'll start by exploring the project structure.",
        "Found 3 projects in the catalog. The codebase uses Python with FastAPI.",
        "I recommend using brainstorming first, then writing-plans.",
        "Let me write the dashboard backend with FastAPI.",
        "Tests pass. Ready for review.",
    ]

    for i in range(min(len(user_msgs), random.randint(3, 5))):
        seq += 1
        ts = (start + timedelta(seconds=seq * 30)).strftime("%Y-%m-%dT%H:%M:%S%z")
        messages.append(
            json.dumps({"ts": ts, "type": "user", "seq": seq, "content": user_msgs[i]}) + "\n"
        )
        seq += 1
        ts = (start + timedelta(seconds=seq * 30)).strftime("%Y-%m-%dT%H:%M:%S%z")
        messages.append(
            json.dumps({"ts": ts, "type": "assistant", "seq": seq, "content": assistant_msgs[i]}) + "\n"
        )

    # Generate tool calls
    num_tools = random.randint(5, 15)
    for i in range(num_tools):
        tool = random.choice(TOOLS)
        cid = f"call_{session_id}_{i}"
        seq += 1
        ts = (start + timedelta(seconds=seq * 30)).strftime("%Y-%m-%dT%H:%M:%S%z")

        if tool == "Skill":
            args = {"name": random.choice(SKILLS)}
        elif tool in ("Read", "Write", "Edit"):
            args = {"filePath": f"/home/cicidi/project/{project}/{random.choice(FILES)}"}
        elif tool == "Bash":
            args = {"command": random.choice(["ls", "pytest", "git status", "npm run build"])}
        else:
            args = {"description": f"doing {tool}"}

        tools.append(json.dumps({
            "ts": ts, "phase": "before", "tool": tool, "tool_type": "builtin",
            "call_id": cid, "seq": seq, "args": args,
        }) + "\n")

        seq += 1
        ts = (start + timedelta(seconds=seq * 30)).strftime("%Y-%m-%dT%H:%M:%S%z")
        duration = random.randint(100, 50000)
        result = f"result of {tool} call {cid}"
        tools.append(json.dumps({
            "ts": ts, "phase": "after", "tool": tool, "tool_type": "builtin",
            "call_id": cid, "seq": seq, "result": result, "duration_ms": duration,
        }) + "\n")

    (session_dir / "messages.jsonl").write_text("".join(messages))
    (session_dir / "tools.jsonl").write_text("".join(tools))

    return session_dir


def generate_test_dataset(db_path: str, num_sessions: int = 10):
    conn = init_db(db_path)
    sessions_dirs = []

    base_time = datetime(2026, 6, 1, 9, 0, 0)
    for i in range(num_sessions):
        sid = f"test-session-{i:03d}-{random.randint(1000, 9999)}"
        project = random.choice(PROJECTS)
        branch = random.choice(BRANCHES)
        initiative = random.choice(INITIATIVES)
        start = base_time + timedelta(hours=i * 4)
        session_dir = generate_test_session(sid, project, branch, initiative, start, random.randint(15, 120))
        import_session(session_dir, conn)

    conn.close()
    print(f"Generated {num_sessions} test sessions in {db_path}")


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/analytics_test.db"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    generate_test_dataset(path, count)
```

- [ ] **Step 2: Run test data generation to verify**

```bash
python tests/analytics/test_data.py /tmp/analytics_test.db 10
```
Expected: "Generated 10 test sessions in /tmp/analytics_test.db"

- [ ] **Step 3: Verify DB contents**

```bash
python -c "
from src.coworker.analytics.db import get_db
conn = get_db('/tmp/analytics_test.db')
for t in ['sessions','messages','tool_calls','file_ops','skills','session_stats']:
    print(f'{t}: {conn.execute(f\"SELECT COUNT(*) FROM {t}\").fetchone()[0]}')
conn.close()
"
```
Expected: Each table has >0 rows

- [ ] **Step 4: Commit**

```bash
git add tests/analytics/test_data.py
git commit -m "feat: add test data generator for analytics"
```

---

### Task 10: E2E Tests

**Files:**
- Create: `tests/dashboard/__init__.py`
- Create: `tests/dashboard/test_api.py`
- Create: `tests/dashboard/test_e2e.py`

- [ ] **Step 1: Write API tests `tests/dashboard/test_api.py`**

```python
from fastapi.testclient import TestClient
from src.coworker.dashboard.app import app

client = TestClient(app)

def test_sessions_endpoint():
    r = client.get("/api/sessions?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_skills_endpoint():
    r = client.get("/api/skills")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_tools_endpoint():
    r = client.get("/api/tools")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_files_endpoint():
    r = client.get("/api/files")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_knowledge_endpoint():
    r = client.get("/api/knowledge")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)

def test_initiatives_endpoint():
    r = client.get("/api/initiatives")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
```

- [ ] **Step 2: Run API tests**

```bash
python -m pytest tests/dashboard/test_api.py -v
```
Expected: All PASS

- [ ] **Step 3: Write E2E Playwright test `tests/dashboard/test_e2e.py`**

```python
import subprocess
import time
import pytest

@pytest.fixture
def dashboard_url():
    proc = subprocess.Popen(
        ["python", "-m", "uvicorn", "src.coworker.dashboard.app:app",
         "--host", "127.0.0.1", "--port", "18080"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    time.sleep(2)
    yield "http://127.0.0.1:18080"
    proc.terminate()
    proc.wait()

def test_dashboard_loads(page, dashboard_url):
    """Test that the dashboard page loads and renders."""
    page.goto(dashboard_url)
    page.wait_for_selector("#sidebar")
    page.wait_for_selector("#main")

    assert page.title() == "Coworker Dashboard"

def test_dashboard_overview(page, dashboard_url):
    """Test overview shows session data."""
    page.goto(dashboard_url)
    page.wait_for_selector(".stat")

    stats = page.query_selector_all(".stat")
    assert len(stats) >= 3

def test_dashboard_navigate_sessions(page, dashboard_url):
    """Test clicking sessions nav item loads sessions table."""
    page.goto(dashboard_url)
    page.click("text=Sessions")
    page.wait_for_selector("table")
    assert page.query_selector("table")

def test_dashboard_navigate_skills(page, dashboard_url):
    """Test skills view loads."""
    page.goto(dashboard_url)
    page.click("text=Skills")
    page.wait_for_selector(".card")
    assert page.query_selector(".card")

def test_dashboard_navigate_tools(page, dashboard_url):
    """Test tools view loads."""
    page.goto(dashboard_url)
    page.click("text=Tools")
    page.wait_for_selector("table")
    assert page.query_selector("table")

def test_dashboard_navigate_files(page, dashboard_url):
    """Test files view loads."""
    page.goto(dashboard_url)
    page.click("text=Files")
    page.wait_for_selector("table")
    assert page.query_selector("table")

def test_dashboard_navigate_knowledge(page, dashboard_url):
    """Test knowledge view loads."""
    page.goto(dashboard_url)
    page.click("text=Knowledge")
    assert page.query_selector(".card") or page.query_selector("table")
```

- [ ] **Step 4: Write full E2E setup test**

Create `tests/analytics/test_e2e_setup.py`:

```python
"""Full E2E test: setup → generate data → import → dashboard → query.

This test validates the entire pipeline works out-of-box:
1. DB schema initialized correctly
2. Test data generated
3. Import script processes raw data
4. All tables populated correctly
5. Dashboard API returns data
6. Dashboard UI loads
"""
import json
import subprocess
import tempfile
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


def test_full_pipeline():
    """End-to-end: raw data → SQLite → API queries."""
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "analytics.db"

    # 1. Init DB
    from src.coworker.analytics.db import init_db
    conn = init_db(db_path)

    # 2. Generate test data
    from tests.analytics.test_data import generate_test_dataset
    os.makedirs(tmp / "raw_sessions", exist_ok=True)
    generate_test_dataset(str(db_path), num_sessions=5)

    # 3. Verify tables populated
    tables = ["sessions", "messages", "tool_calls", "file_ops", "skills", "session_stats"]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count > 0, f"Table {table} is empty"

    # 4. Verify session count
    session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    assert session_count == 5

    # 5. Verify messages per session
    msg_counts = conn.execute(
        "SELECT session_id, COUNT(*) FROM messages GROUP BY session_id"
    ).fetchall()
    for row in msg_counts:
        assert row[1] >= 4  # each session has at least 4 messages (2 user + 2 assistant)

    # 6. Verify tool calls have before+after pairs merged
    tcs = conn.execute("SELECT tool, args, result FROM tool_calls LIMIT 5").fetchall()
    assert len(tcs) > 0
    assert tcs[0]["tool"]

    # 7. Verify file_ops contain extracted file paths
    fos = conn.execute("SELECT op, path FROM file_ops").fetchall()
    for fo in fos:
        assert fo["op"] in ("read", "write", "edit", "glob")
        assert fo["path"]

    conn.close()


def test_dashboard_api_with_test_data():
    """Test that dashboard API endpoints return data from test DB."""
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "analytics.db"

    from src.coworker.analytics.db import init_db
    init_db(db_path)

    from tests.analytics.test_data import generate_test_dataset
    generate_test_dataset(str(db_path), num_sessions=5)

    # Override DB_PATH for dashboard
    import src.coworker.analytics.db as db_module
    original_path = db_module.DB_PATH
    db_module.DB_PATH = db_path

    try:
        from src.coworker.dashboard.app import app
        client = TestClient(app)

        # All endpoints should return valid JSON
        endpoints = [
            "/api/sessions",
            "/api/skills",
            "/api/tools",
            "/api/files",
            "/api/knowledge",
            "/api/initiatives",
        ]
        for ep in endpoints:
            r = client.get(ep)
            assert r.status_code == 200, f"{ep} returned {r.status_code}"
            data = r.json()
            assert isinstance(data, list), f"{ep} should return array"

        # Session detail endpoint
        sessions = client.get("/api/sessions?limit=1").json()
        if sessions:
            sid = sessions[0]["id"]
            r = client.get(f"/api/sessions/{sid}")
            assert r.status_code == 200
            detail = r.json()
            assert "session" in detail
            assert "messages" in detail
            assert "tool_calls" in detail
            assert "file_ops" in detail

    finally:
        db_module.DB_PATH = original_path


def test_setup_idempotent():
    """Test that running setup twice does not corrupt data."""
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "analytics.db"

    # First init
    from src.coworker.analytics.db import init_db
    conn1 = init_db(db_path)
    conn1.close()

    # Second init should not fail
    conn2 = init_db(db_path)
    count = conn2.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    assert count == 8  # 8 tables defined
    conn2.close()
```

- [ ] **Step 4: Add Playwright to pyproject.toml**

```toml
[project.optional-dependencies]
test = ["pytest-playwright"]
```

- [ ] **Step 5: Run E2E tests**

```bash
pip install pytest-playwright
playwright install chromium
python -m pytest tests/dashboard/test_e2e.py -v --headed
```

Expected: All PASS (dashboard loads, all views render)

- [ ] **Step 6: Commit**

```bash
git add tests/dashboard/ pyproject.toml
git commit -m "test: add API and E2E Playwright tests for dashboard"
```

---

## Wave Summary

| Wave | Tasks | Output |
|------|-------|--------|
| 1 | 1-6 | Listener (Claude + OpenCode), DB schema, import script, knowledge skill, installer |
| 2 | 7-10 | FastAPI backend, vanilla JS frontend, test data gen, E2E tests |

## Verification (MAC)

After Wave 1:
- [ ] `./setup/install.sh --global` — runs without errors, all artifacts created
- [ ] `~/.coworker/analytics/hooks/` — contains 4 .sh scripts, all executable
- [ ] `~/.claude/settings.json` — contains hooks config for all 4 events
- [ ] `~/.coworker/analytics/analytics.db` — exists with 8 tables
- [ ] `python -m pytest tests/analytics/ -v` — all import + E2E setup tests pass
- [ ] `python tests/analytics/test_data.py /tmp/test.db 20` — generates 20 sessions
- [ ] `coworker analytics-import` — processes JSONL into SQLite (or import script manually)
- [ ] `analytics.db` contains sessions, messages, tool_calls, file_ops, skills, session_stats, knowledge, session_summaries tables

After Wave 2:
- [ ] `coworker dashboard` — starts on port 8080 without errors
- [ ] Dashboard loads in browser at http://localhost:8080
- [ ] All 7 sidebar views render (overview, sessions, skills, tools, files, knowledge, initiatives)
- [ ] Session detail view shows messages + tool calls + summary
- [ ] `python -m pytest tests/dashboard/test_api.py -v` — all API tests pass
- [ ] `python -m pytest tests/dashboard/test_e2e.py -v` — all E2E Playwright tests pass
- [ ] `python -m pytest tests/analytics/test_e2e_setup.py -v` — full pipeline test passes (setup → data → import → API)
