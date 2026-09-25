"""Tests for coworker.memory.pending — staged skill review queue."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from coworker.memory import pending
from coworker.memory import safety


@pytest.fixture(autouse=True)
def _isolate_circuit_breaker(tmp_path, monkeypatch):
    """Keep stage_skill's circuit-breaker state out of the real HOME.

    stage_skill consults memory.safety, whose state file lives under
    ~/.coworker/safety/. Without this, staged test skills are recorded there -
    and after three of them the breaker trips and every later test fails.
    """
    monkeypatch.setattr(
        safety, "_circuit_state_path", lambda: tmp_path / "circuit_state.json"
    )


class TestStageListApproveReject:
    def test_stage_and_list(self, tmp_path, monkeypatch):
        pending_dir = tmp_path / "pending_skills"
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(pending_dir))

        sid = pending.stage_skill("Test Skill", "A test skill", 15, "sess_001")
        assert len(sid) > 0

        items = pending.list_pending()
        assert len(items) == 1
        assert items[0]["name"] == "Test Skill"
        assert items[0]["status"] == "pending"

    def test_approve(self, tmp_path, monkeypatch):
        pending_dir = tmp_path / "pending_skills"
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(pending_dir))

        sid = pending.stage_skill("Approve Me", "desc", 10, "sess_x")
        assert pending.approve(sid) is True
        items = pending.list_pending()
        assert items[0]["status"] == "approved"

    def test_reject(self, tmp_path, monkeypatch):
        pending_dir = tmp_path / "pending_skills"
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(pending_dir))

        sid = pending.stage_skill("Reject Me", "desc", 10, "sess_x")
        assert pending.reject(sid) is True
        items = pending.list_pending()
        assert items[0]["status"] == "rejected"

    def test_approve_nonexistent(self, tmp_path, monkeypatch):
        pending_dir = tmp_path / "pending_skills"
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(pending_dir))
        assert pending.approve("nonexistent") is False

    def test_reject_nonexistent(self, tmp_path, monkeypatch):
        pending_dir = tmp_path / "pending_skills"
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(pending_dir))
        assert pending.reject("nonexistent") is False

    def test_list_empty_dir(self, tmp_path, monkeypatch):
        pending_dir = tmp_path / "nonexistent"
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(pending_dir))
        assert pending.list_pending() == []

    def test_batch_approve(self, tmp_path, monkeypatch):
        pending_dir = tmp_path / "pending_skills"
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(pending_dir))

        pending.stage_skill("Skill A", "", 10, "s1")
        pending.stage_skill("Skill B", "", 12, "s1")
        count = pending.batch_approve()
        assert count == 2


class TestExpire:
    def test_expire_old_items(self, tmp_path, monkeypatch):
        pending_dir = tmp_path / "pending_skills"
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(pending_dir))

        sid = pending.stage_skill("Old Skill", "", 10, "s1")

        # Manually backdate the file
        item_path = pending_dir / f"{sid}.json"
        data = json.loads(item_path.read_text())
        old_date = (datetime.now(timezone.utc) - timedelta(days=31)).strftime("%Y-%m-%dT%H:%M:%SZ")
        data["staged_at"] = old_date
        item_path.write_text(json.dumps(data))

        count = pending.expire_old_items(days=30)
        assert count == 1

    def test_recent_items_not_expired(self, tmp_path, monkeypatch):
        pending_dir = tmp_path / "pending_skills"
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(pending_dir))

        pending.stage_skill("Recent Skill", "", 10, "s1")
        count = pending.expire_old_items(days=30)
        assert count == 0

    def test_already_approved_not_expired(self, tmp_path, monkeypatch):
        pending_dir = tmp_path / "pending_skills"
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(pending_dir))

        sid = pending.stage_skill("Approved Old", "", 10, "s1")
        pending.approve(sid)

        # Backdate
        item_path = pending_dir / f"{sid}.json"
        data = json.loads(item_path.read_text())
        old_date = (datetime.now(timezone.utc) - timedelta(days=31)).strftime("%Y-%m-%dT%H:%M:%SZ")
        data["staged_at"] = old_date
        data["status"] = "approved"
        item_path.write_text(json.dumps(data))

        count = pending.expire_old_items(days=30)
        assert count == 0  # Already approved, skip


class TestStageSkillIsGated:
    """The circuit breaker must actually gate staging.

    memory/safety.py implements a limit of 3 auto-evolutions per 24h and says it
    "prevents runaway autonomous behavior", and the spec repeats the cap - but
    nothing consulted it. This function staged unconditionally, and
    capture._stage_skill wrote the pending file itself without calling here.
    """

    def test_staging_stops_after_the_limit(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(tmp_path / "p"))
        from coworker.memory import safety

        for i in range(safety.CIRCUIT_BREAKER_LIMIT):
            pending.stage_skill(f"skill-{i}", "d", 10, "s")

        with pytest.raises(RuntimeError, match="Circuit breaker"):
            pending.stage_skill("one-too-many", "d", 10, "s")

    def test_a_staged_skill_is_recorded(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(tmp_path / "p"))
        from coworker.memory import safety

        pending.stage_skill("recorded", "d", 10, "s")

        state = json.loads(safety._circuit_state_path().read_text())
        assert state["count"] == 1
        assert state["history"][0]["skill"] == "recorded"

    def test_capture_no_longer_writes_around_the_gate(self):
        """capture._stage_skill must delegate, not write the JSON itself."""
        import inspect

        from coworker.memory import capture

        src = inspect.getsource(capture._stage_skill)
        assert "from coworker.memory.pending import stage_skill" in src
        assert "write_text" not in src, (
            "capture._stage_skill is writing the pending file itself again, "
            "which skips the circuit breaker"
        )
