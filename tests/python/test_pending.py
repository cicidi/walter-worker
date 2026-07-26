"""Tests for coworker.memory.pending — staged skill review queue."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import patch

from coworker.memory import pending


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
        old_date = (datetime.utcnow() - timedelta(days=31)).strftime("%Y-%m-%dT%H:%M:%SZ")
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
        old_date = (datetime.utcnow() - timedelta(days=31)).strftime("%Y-%m-%dT%H:%M:%SZ")
        data["staged_at"] = old_date
        data["status"] = "approved"
        item_path.write_text(json.dumps(data))

        count = pending.expire_old_items(days=30)
        assert count == 0  # Already approved, skip
