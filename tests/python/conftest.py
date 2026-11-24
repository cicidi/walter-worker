from __future__ import annotations
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest


@pytest.fixture
def temp_coworker_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        coworker_dir = Path(tmp) / ".coworker"
        coworker_dir.mkdir()
        monkeypatch.setattr(
            "coworker.config.GLOBAL_DIR", coworker_dir
        )
        monkeypatch.setattr(
            "coworker.cli.GLOBAL_DIR", coworker_dir
        )
        monkeypatch.setattr(
            "coworker.config.PROJECT_CATALOG_PATH",
            coworker_dir / "project.yaml",
        )
        yield coworker_dir


@pytest.fixture
def temp_claude_md():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "CLAUDE.md"
        path.write_text("# Test Project\n\n## Original content\n")
        yield path


@pytest.fixture
def temp_project_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def temp_features_dir(monkeypatch, tmp_path):
    """Redirect FEATURES_DIR to a temp directory for isolated tests."""
    import coworker.config as cfg
    init_dir = tmp_path / "features"
    init_dir.mkdir()
    monkeypatch.setattr(cfg, "FEATURES_DIR", init_dir)
    monkeypatch.setattr(
        "coworker.features.manager.FEATURES_DIR", init_dir
    )
    yield init_dir


# ---------------------------------------------------------------------------
# mem0 test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def _mem0_session_dir(tmp_path_factory):
    """Session-scoped temp directory for mem0 global state.

    MEM0_DIR must be set before mem0 is first imported (it's evaluated
    at module load time in mem0.configs.base).  We create one temp dir
    for the entire test session and set the env var once.
    """
    import os
    mem0_dir = tmp_path_factory.mktemp("mem0_session")
    os.environ["MEM0_DIR"] = str(mem0_dir)
    return mem0_dir


@pytest.fixture
def clean_mem0(tmp_path, _mem0_session_dir):
    """Empty mem0 client pointed at a temporary vector store.

    Uses a session-scoped MEM0_DIR to avoid Qdrant file-lock conflicts
    between tests.  Each test still gets its own vector store on disk.
    """
    import os
    from coworker.memory.mem0_client import Mem0Client

    # mem0 first, then the key. A venv built with `pip install -e ".[test]"`
    # has no mem0 even when the shell exports DEEPSEEK_API_KEY, and checking
    # the key first sent every consumer of this fixture into from_config and
    # out with ModuleNotFoundError — 47 errors that said nothing about the
    # code, on the machine most likely to run them.
    pytest.importorskip("mem0", reason="mem0ai is in the optional [memory] extra")
    if "DEEPSEEK_API_KEY" not in os.environ:
        pytest.skip("DEEPSEEK_API_KEY not set — required for real mem0 tests")

    client = Mem0Client.from_config(
        vector_store_path=str(tmp_path / "mem0_test"),
    )
    yield client
    # Cleanup: reset the store
    try:
        client.delete_all()
    except Exception:
        pass


@pytest.fixture
def populated_mem0(clean_mem0):
    """mem0 client pre-loaded with 5 test entries across 2 projects."""
    client = clean_mem0
    entries = [
        {
            "memory": "MCP first request 403-times-out; retry once before failing.",
            "metadata": {
                "type": "lesson", "project": "walter-worker", "topic": "mcp",
                "problem": "first-request-403", "provenance": "agent", "state": "active",
            },
        },
        {
            "memory": "Use ruff for linting with E501 ignored for this project.",
            "metadata": {
                "type": "convention", "project": "walter-worker", "topic": "linting",
                "provenance": "agent", "state": "active",
            },
        },
        {
            "memory": "Prefer Chinese for communication; discuss before implementing.",
            "metadata": {
                "type": "preference", "project": "walter-worker", "topic": "communication",
                "provenance": "hand-written", "state": "active",
            },
        },
        {
            "memory": "Docker compose must use v2 syntax; v1 is deprecated.",
            "metadata": {
                "type": "lesson", "project": "skill-factory", "topic": "docker",
                "problem": "v1-deprecation", "provenance": "agent", "state": "active",
            },
        },
        {
            "memory": "Test fixtures should be clean and isolated per test module.",
            "metadata": {
                "type": "lesson", "project": "skill-factory", "topic": "testing",
                "problem": "fixture-isolation", "provenance": "agent", "state": "stale",
            },
        },
    ]
    for entry in entries:
        client.add(
            memory=entry["memory"],
            user_id="default",
            run_id="sess_populated_001",
            metadata=entry["metadata"],
        )
    return client


@pytest.fixture
def real_llm():
    """Real DeepSeek Flash LLMClient. Requires DEEPSEEK_API_KEY."""
    import os
    from coworker.memory.llm import LLMClient

    if "DEEPSEEK_API_KEY" not in os.environ:
        pytest.skip("DEEPSEEK_API_KEY not set")
    return LLMClient()


@pytest.fixture(autouse=True)
def _isolate_managed_mcp_store(tmp_path, monkeypatch):
    """Keep adapter syncs out of the real ~/.coworker.

    _sync_mcp records which MCP entries it wrote, keyed by the absolute path of
    the file it wrote them to, so it can retire its own later without touching
    the user's. That record lives in the real home, so without this every test
    that calls an adapter's sync — including ones written long before the store
    existed — deposits temp paths into the user's own state file. Autouse
    rather than per-test: the next adapter to sync will need it too, and this
    is the kind of side effect nobody notices until their home directory has
    a hundred stale keys in it.
    """
    monkeypatch.setattr(
        "coworker.adapters.claude._managed_mcp_path",
        lambda: tmp_path / "mcp-managed.json",
    )


@pytest.fixture(autouse=True)
def _isolate_backup_root(tmp_path, monkeypatch):
    """Keep snapshots out of the real ~/.coworker/backups.

    snapshot() mirrors files into the user's own backup directory, and several
    commands take one as ordinary operation — `init`, `upgrade`, `sync`, and
    `memory init --force`. So any test that runs one deposits a real,
    timestamped directory in the user's home: a memory-init test left one
    behind before this existed.

    Tests that assert on backups patch coworker.backup.BACKUP_ROOT or
    coworker.backup.snapshot themselves; their patch runs after this one and
    wins, so they are unaffected.
    """
    monkeypatch.setattr("coworker.backup.BACKUP_ROOT", tmp_path / "backups")


@pytest.fixture(autouse=True)
def _isolate_analytics_db(tmp_path, monkeypatch):
    """Point the analytics database at a temp file for every test.

    get_db() resolves COWORKER_ANALYTICS_DB, and several code paths read the
    user's real analytics.db when it is unset — the evolution score does, now
    that it computes from the database rather than a JSON store. Without this a
    test asserting "no data scores zero" reads whatever the developer has
    accumulated and fails on their machine only.
    """
    monkeypatch.setenv("COWORKER_ANALYTICS_DB", str(tmp_path / "analytics.db"))
