"""The redesigned dashboard: /api/v2 queries, the memory evidence, and the page files.

The rules under test are the ones a reader of the dashboard relies on:
a prompt is something a person typed; error rates ignore calls with no
recorded outcome; filters narrow every figure; reading memory never counts
as using it.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from importlib.resources import files as resource_files

import pytest
from coworker.analytics.db import SCHEMA
from coworker.dashboard import queries_memory_roi as roi
from coworker.dashboard import queries_v2 as v2
from coworker.dashboard.app import app
from coworker.dashboard.queries_v2 import Filters
from fastapi.testclient import TestClient


def _ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "analytics.db"

    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    conn = connect()
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT INTO sessions (id, ide, project, cwd, model, created_at, closed_at) VALUES (?,?,?,?,?,?,?)",
        [("a", "claude-code", "alpha", "/p/alpha", "claude-x", _ago(2), _ago(2)),
         ("b", "opencode", "beta", "/p/beta", "deepseek", _ago(40), _ago(40)),
         ("c", "claude-code", "alpha", "/p/alpha", "", _ago(1), _ago(1))])
    conn.executemany(
        "INSERT INTO messages (session_id, seq, type, content, ts) VALUES (?,?,?,?,?)",
        [("a", 1, "user", "Fix the login bug in the auth module please", _ago(2)),
         ("a", 2, "assistant", "On it.", _ago(2)),
         ("a", 3, "user", "<task-notification>done</task-notification>", _ago(2)),  # injected, not a prompt
         ("a", 4, "user", "\n", _ago(2)),                                            # empty, not a prompt
         ("a", 5, "user", "不对，还是失败", _ago(2)),                                  # a correction
         ("b", 1, "user", "ok", _ago(40)), ("b", 2, "user", "ok", _ago(40)), ("b", 3, "user", "OK", _ago(40)),
         ("c", 1, "user", "<command-name>/loop</command-name>", _ago(1))])
    conn.executemany(
        """INSERT INTO tool_calls (session_id, call_id, tool, tool_type, args, result, duration_ms,
                                   seq_before, ts, is_error) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        [("a", "1", "Edit", "builtin", "{}", "Could not find oldString in /home/u/p/x.py line 12", 5, 1, _ago(2), 1),
         ("a", "2", "Edit", "builtin", "{}", "Could not find oldString in /home/u/p/y.py line 99", 5, 2, _ago(2), 1),
         ("a", "3", "Edit", "builtin", "{}", "ok", 5, 3, _ago(2), 0),
         ("a", "4", "Read", "builtin", "{}", "text", 5, 4, _ago(2), None),  # outcome never recorded
         ("a", "5", "EnterPlanMode", "builtin", "{}", "", 5, 5, _ago(2), 0),
         ("b", "6", "Bash", "builtin", '{"command": "coworker memory query retries"}', "", 9, 1, _ago(40), 0),
         ("b", "7", "WebFetch", "builtin", "{}", "HTTP 403", 9, 2, _ago(40), 1),
         ("c", "8", "Agent", "builtin", "{}", "", 9, 1, _ago(1), 0)])
    conn.executemany(
        "INSERT INTO file_ops (session_id, call_id, op, path, file_type, project, seq, ts) VALUES (?,?,?,?,?,?,?,?)",
        [("a", "1", "edit", "/p/alpha/src/x.py", "py", "alpha", 1, _ago(2)),
         ("a", "4", "read", "/p/alpha/src/x.py", "py", "alpha", 2, _ago(2)),
         ("b", "6", "read", "/p/beta/README.md", "md", "beta", 1, _ago(40))])
    conn.executemany(
        """INSERT INTO session_stats (session_id, message_count, tool_count, duration_min, tokens_input,
                                      tokens_output, tokens_cache_read, cost, updated_at) VALUES (?,?,?,?,?,?,?,?,?)""",
        [("a", 5, 5, 20, 100, 50, 900, 0, _ago(2)), ("b", 3, 2, 90, 1000, 400, 0, 1.5, _ago(40))])
    conn.execute(
        "INSERT INTO session_summaries (session_id, context_to_remember, memory_keywords, generated_at) "
        "VALUES ('a', 'remember this', 'k1', ?)", (_ago(2),))
    conn.commit()
    conn.close()
    monkeypatch.setattr(v2, "get_db", connect)
    monkeypatch.setattr(roi, "get_db", connect)
    return connect


# ── Filters and counting rules ───────────────────────────────────────────────

class TestPulse:
    def test_counts_only_prompts_a_person_typed(self, db):
        k = v2.pulse(Filters())["kpis"]
        assert k["sessions"] == 3
        assert k["prompts"] == 5  # 2 in a, 3 in b; injected, empty and command blocks are not prompts
        assert k["tool_calls"] == 8

    def test_error_rate_ignores_calls_without_an_outcome(self, db):
        k = v2.pulse(Filters())["kpis"]
        assert (k["errors"], k["calls_known"]) == (3, 7)
        assert k["error_rate"] == round(3 / 7, 4)

    @pytest.mark.parametrize("f,sessions", [
        (Filters(ide="claude-code"), 2), (Filters(ide="opencode"), 1), (Filters(project="alpha"), 2),
        (Filters(model="unknown"), 1), (Filters(days=7), 2), (Filters(ide="opencode", days=7), 0)])
    def test_filters_narrow_the_figures(self, db, f, sessions):
        assert v2.pulse(f)["kpis"]["sessions"] == sessions

    def test_daily_series_is_zero_filled_and_ends_today(self, db):
        daily = v2.pulse(Filters(days=7))["daily"]
        assert len(daily) == 7
        assert sum(d["sessions"] for d in daily) == 2


class TestFriction:
    def test_rates_and_immediate_retries(self, db):
        fr = v2.friction(Filters())
        edit = next(t for t in fr["tools"] if t["tool"] == "Edit")
        assert (edit["errors"], edit["known"], edit["rate"]) == (2, 3, round(2 / 3, 4))
        assert edit["retries"] == 2  # both failed Edits were followed by another Edit
        assert fr["unknown_outcome"] == 1

    def test_reasons_group_across_paths_and_numbers(self, db):
        d = v2.friction_tool("Edit", Filters())
        assert d["failed"] == 2
        assert d["reasons"] == [{"reason": "Could not find oldString in <path> line N", "count": 2}]

    def test_filter_applies(self, db):
        assert [t["tool"] for t in v2.friction(Filters(ide="opencode"))["tools"]] == ["WebFetch"]


class TestAdoption:
    def test_share_of_sessions_per_feature(self, db):
        feats = {f["key"]: f for f in v2.adoption(Filters())["features"]}
        assert feats["plan"]["sessions"] == 1 and feats["plan"]["share"] == round(1 / 3, 4)
        assert feats["subagents"]["sessions"] == 1
        assert feats["memory"]["sessions"] == 1  # `coworker memory query` through Bash
        assert feats["workflows"]["sessions"] == 0

    def test_sessions_drilldown_and_unknown_key(self, db):
        assert [r["id"] for r in v2.adoption_sessions("plan", Filters())] == ["a"]
        assert v2.adoption_sessions("no-such-feature", Filters()) == []


class TestPrompts:
    def test_habits(self, db):
        pr = v2.prompts(Filters())
        assert pr["total"] == 5 and sum(b["count"] for b in pr["histogram"]) == 5
        assert pr["short_repeats"][0] == {"text": "ok", "count": 3, "sessions": 1}
        assert pr["corrections_total"] == 1
        assert pr["commands"] == [{"command": "/loop", "count": 1, "sessions": 1}]

    def test_sessions_grouped_by_opening_prompt(self, db):
        by = {r["bucket"]: r for r in v2.prompts(Filters())["by_opening"]}
        assert by["20–79"]["sessions"] == 1 and by["20–79"]["avg_turns"] == 2.0
        assert by["under 20"]["sessions"] == 1


class TestOtherPages:
    def test_sessions_sorted_by_failures(self, db):
        d = v2.sessions(Filters(), sort="errors")
        assert d["total"] == 3 and d["rows"][0]["id"] == "a"
        assert d["rows"][0]["errors"] == 2 and d["rows"][0]["prompts"] == 2
        assert d["rows"][0]["first_prompt"].startswith("Fix the login")

    def test_an_unknown_sort_falls_back_instead_of_reaching_sql(self, db):
        assert v2.sessions(Filters(), sort="1; DROP TABLE sessions")["total"] == 3

    def test_tool_families(self):
        assert v2._family("Bash") == "Built-in"
        assert v2._family("mcp__github__search_code") == "MCP: github"
        assert v2._family("mcp__plugin_playwright_playwright__browser_click") == "MCP: playwright"

    def test_files_and_cost_and_shape(self, db):
        f = v2.files(Filters())
        assert f["totals"] == {"files": 2, "reads": 2, "writes": 1}
        models = {m["model"]: m for m in v2.cost(Filters())["models"]}
        assert models["claude-x"]["cache_share"] == 0.9
        assert models["unknown"]["sessions_with_tokens"] is None  # no stats row: not recorded, not zero
        assert sum(d["sessions"] for d in v2.shape(Filters())["durations"]) == 2

    def test_health_reports_coverage(self, db):
        checks = {c["name"]: c for c in v2.health()["checks"]}
        assert (checks["Model recorded"]["covered"], checks["Model recorded"]["total"]) == (2, 3)
        assert (checks["Tool call outcome known"]["covered"], checks["Tool call outcome known"]["total"]) == (7, 8)


# ── Memory evidence ──────────────────────────────────────────────────────────

class FakeMem0:
    def __init__(self, entries):
        self.entries = entries

    def search(self, *a, **kw):
        raise AssertionError("search() bumps use_count; reading for the dashboard must not call it")

    def list_entries(self, filters=None, top_k=1000, user_id="default"):
        return self.entries[:top_k]


def _lesson(i, **meta):
    base = {"type": "lesson", "project": "alpha", "topic": "t", "state": "active",
            "source_session": "a", "use_count": i}
    return {"id": f"m{i}", "memory": f"lesson {i} about retries", "created_at": f"2026-11-0{i}T00:00:00Z",
            "metadata": {**base, **meta}}


@pytest.fixture
def memory_home(tmp_path):
    mem = tmp_path / ".coworker" / "memory"
    mem.mkdir(parents=True)
    (mem / "audit.log").write_text(
        "2026-11-24T01:00:00Z sync stop a tool=session-end lessons=4 ms=2000 ok\n"
        "2026-11-24T02:00:00Z sync stop a tool=session-end lessons=2 ms=4000 ok\n"
        '2026-11-25T01:00:00Z sync stop b tool=session-end lessons=0 ms=6000 error reason="store is locked"\n'
        "garbage line\n")
    (mem / "MEMORY.md").write_text("# MEMORY.md\n> Generated: 2026-11-24 06:29:58 UTC\n> Total entries: 976\n")
    (tmp_path / "CLAUDE.local.md").write_text(
        "# notes\n<!-- MEMORY:alpha START -->\n<!-- No stored memories yet -->\n<!-- MEMORY:alpha END -->\n")
    return tmp_path


class TestMemoryRoi:
    def run(self, home, entries=None):
        client = FakeMem0(entries if entries is not None else [_lesson(1), _lesson(2, source_session="b", use_count=0)])
        return roi.memory_roi(mem0_client=client, memory_dir=home / ".coworker" / "memory", home=home)

    def test_capture_comes_from_the_audit_log(self, db, memory_home):
        c = self.run(memory_home)["capture"]
        assert (c["attempts"], c["ok"], c["errors"], c["lessons"]) == (3, 2, 1, 6)
        assert c["error_rate"] == round(1 / 3, 4) and c["unparsed_lines"] == 1
        assert c["error_reasons"] == [{"reason": "store is locked", "count": 1}]
        assert [d["day"] for d in c["daily"]] == ["2026-11-24", "2026-11-25"]

    def test_funnel_and_recall(self, db, memory_home):
        r = self.run(memory_home)
        assert [s["value"] for s in r["funnel"]] == [3, 2, 2, 1]
        assert r["recall"]["calls"] == 1 and r["recall"]["recent"][0]["args"] == "coworker memory query retries"

    def test_a_placeholder_block_counts_as_no_lessons(self, db, memory_home):
        r = self.run(memory_home)
        assert r["inject"]["snapshot_lines"] == 0
        assert r["inject"]["export"]["entries"] == 976
        text = " ".join(v["text"] for v in r["verdicts"] if v["tone"] == "bad")
        assert "holds 0 lessons" in text

    def test_a_filled_block_is_counted(self, db, memory_home):
        (memory_home / "CLAUDE.local.md").write_text(
            "<!-- MEMORY:alpha START -->\n## Memory Snapshot\n- one\n- two\n<!-- MEMORY:alpha END -->\n")
        assert self.run(memory_home)["inject"]["snapshot_lines"] == 3

    def test_summaries_coverage(self, db, memory_home):
        s = self.run(memory_home)["summaries"]
        assert (s["count"], s["sessions"], s["coverage"]) == (1, 3, round(1 / 3, 4))
        filled = {f["field"]: f["filled"] for f in s["fields"]}
        assert filled["context_to_remember"] == 1 and filled["efficiency_score"] == 0

    def test_an_unreadable_store_is_reported_not_zeroed(self, db, memory_home):
        class Broken:
            def list_entries(self, **kw):
                raise RuntimeError("Storage folder is already accessed")

        r = roi.memory_roi(mem0_client=Broken(), memory_dir=memory_home / ".coworker" / "memory", home=memory_home)
        assert r["store"] is None and "already accessed" in r["store_error"]
        assert r["funnel"][2]["value"] is None

    def test_browse_filters_and_never_searches(self):
        client = FakeMem0([_lesson(1), _lesson(2, type="convention"), _lesson(3, project="beta")])
        assert roi.memories(mem0_client=client)["total"] == 3
        assert [r["id"] for r in roi.memories(type_="convention", mem0_client=client)["rows"]] == ["m2"]
        assert [r["id"] for r in roi.memories(project="beta", mem0_client=client)["rows"]] == ["m3"]
        assert roi.memories(q="LESSON 3", mem0_client=client)["rows"][0]["id"] == "m3"
        assert [r["id"] for r in roi.memories(mem0_client=client)["rows"]] == ["m3", "m2", "m1"]  # newest first


# ── Routes and page files ────────────────────────────────────────────────────

V2_ROUTES = ["/api/v2/filters", "/api/v2/pulse?ide=claude-code&days=30", "/api/v2/friction",
             "/api/v2/friction/tool?tool=Edit", "/api/v2/adoption", "/api/v2/adoption/sessions?key=plan",
             "/api/v2/prompts", "/api/v2/shape", "/api/v2/cost", "/api/v2/sessions?sort=errors&limit=5",
             "/api/v2/tools", "/api/v2/files", "/api/v2/projects?project=alpha", "/api/v2/health"]


@pytest.mark.parametrize("route", V2_ROUTES)
def test_every_v2_route_answers(db, route):
    r = TestClient(app).get(route)
    assert r.status_code == 200, r.text


def test_memory_routes_use_the_injected_store(db, memory_home, monkeypatch):
    from coworker.memory.mem0_client import Mem0Client
    monkeypatch.setattr(Mem0Client, "from_config", classmethod(lambda cls, **kw: FakeMem0([_lesson(1)])))
    monkeypatch.setenv("HOME", str(memory_home))
    client = TestClient(app)
    assert client.get("/api/v2/memory-roi").json()["store"]["total"] == 1
    assert client.get("/api/v2/memories?q=retries").json()["total"] == 1


class TestPageFiles:
    static = resource_files("coworker.dashboard") / "static"

    def sources(self):
        return {f.name: f.read_text() for f in (self.static / "app").iterdir() if f.name.endswith(".js")}

    def test_index_loads_the_module_entry_and_stylesheet(self):
        html = (self.static / "index.html").read_text()
        assert 'type="module" src="/app/main.js' in html and "/app.css" in html
        assert (self.static / "app.css").is_file()

    def test_every_import_resolves(self):
        import re
        src = self.sources()
        for name, text in src.items():
            for target in re.findall(r'from "\./([\w\-]+\.js)"', text):
                assert target in src, f"{name} imports missing {target}"

    def test_pages_never_parse_recorded_text_as_markup(self):
        # Prompts, tool arguments and file paths are shown verbatim.
        for name, text in self.sources().items():
            assert "innerHTML" not in text.replace("never innerHTML", ""), f"{name} uses innerHTML"
            assert "insertAdjacentHTML" not in text and "document.write" not in text

    def test_requests_are_built_from_the_origin(self):
        # A page opened as http://user:password@host/ cannot make relative
        # requests; every fetch must start from location.origin.
        main = self.sources()["main.js"]
        assert 'const API = location.origin + "/api/";' in main
        assert main.count("fetch(") == main.count("fetch(API + ") == 2
        for name, text in self.sources().items():
            if name != "main.js":
                assert "fetch(" not in text, f"{name} must call api() or post(), not fetch()"

    def test_static_files_must_be_revalidated(self):
        r = TestClient(app).get("/app/ui.js")
        assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"
