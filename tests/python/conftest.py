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
def temp_initiatives_dir(monkeypatch, tmp_path):
    """Redirect INITIATIVES_DIR to a temp directory for isolated tests."""
    import coworker.config as cfg
    init_dir = tmp_path / "initiatives"
    init_dir.mkdir()
    monkeypatch.setattr(cfg, "INITIATIVES_DIR", init_dir)
    monkeypatch.setattr(
        "coworker.initiatives.manager.INITIATIVES_DIR", init_dir
    )
    yield init_dir
