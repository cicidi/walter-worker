"""Tests for coworker.memory.metrics — evolution metrics collection."""

from __future__ import annotations

import json
from pathlib import Path

from coworker.memory.metrics import compute_evolution_score, record_session_metrics, get_metrics_report, _load_metrics, _save_metrics


class TestMetricsCollection:
    def test_load_metrics_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr("coworker.memory.metrics.METRICS_PATH", str(tmp_path / "metrics.json"))
        data = _load_metrics()
        assert "skill_reuse_rate" in data
        assert "circuit_breaker_trips" in data

    def test_record_and_persist(self, tmp_path, monkeypatch):
        monkeypatch.setattr("coworker.memory.metrics.METRICS_PATH", str(tmp_path / "metrics.json"))
        record_session_metrics("sess_1", {"skill_reuse_rate": 0.5, "memory_hit_rate": 0.8})
        data = _load_metrics()
        assert len(data["skill_reuse_rate"]) == 1
        assert data["skill_reuse_rate"][0]["value"] == 0.5

    def test_compute_score_with_no_data(self, tmp_path, monkeypatch):
        # Use a temp path that doesn't exist yet — clean state
        p = tmp_path / "nonexistent_metrics.json"
        monkeypatch.setattr("coworker.memory.metrics.METRICS_PATH", str(p))
        score = compute_evolution_score()
        assert isinstance(score, int)
        assert 0 <= score <= 100  # Always in valid range


class TestMetricsReport:
    def test_report_generates(self, tmp_path, monkeypatch):
        monkeypatch.setattr("coworker.memory.metrics.METRICS_PATH", str(tmp_path / "metrics.json"))
        record_session_metrics("s1", {"skill_reuse_rate": 0.7, "task_first_pass_rate": 0.8, "memory_hit_rate": 0.9})
        report = get_metrics_report()
        assert "Evolution Score" in report
        assert "Skill Reuse Rate" in report


class TestUnrecognisedKeysAreNotDroppedSilently:
    """record_session_metrics keeps only keys already in the store.

    Its docstring listed `skills_reused`, `user_corrections`, `tasks_completed`
    and six more — not one of which is a storage key (the spec's are the
    *_rate fractions). So a caller who followed the documentation recorded
    nothing at all, and got no error, no warning, and no empty file to
    notice. The suite passed because every test used the real keys.
    """

    def test_docstring_keys_would_record_nothing(self, tmp_path, monkeypatch, caplog):
        import logging

        monkeypatch.setattr(
            "coworker.memory.metrics.METRICS_PATH", str(tmp_path / "metrics.json")
        )
        with caplog.at_level(logging.WARNING):
            record_session_metrics("s1", {"skills_reused": 3, "user_corrections": 1})

        assert "skills_reused" in caplog.text, "a dropped metric must be reported"
        assert _load_metrics()["skill_reuse_rate"] == []

    def test_real_keys_record_without_complaint(self, tmp_path, monkeypatch, caplog):
        import logging

        monkeypatch.setattr(
            "coworker.memory.metrics.METRICS_PATH", str(tmp_path / "metrics.json")
        )
        with caplog.at_level(logging.WARNING):
            record_session_metrics("s1", {"skill_reuse_rate": 0.5})

        assert "skills_reused" not in caplog.text
        assert len(_load_metrics()["skill_reuse_rate"]) == 1

    def test_a_partly_unknown_payload_names_only_the_unknown_keys(
        self, tmp_path, monkeypatch, caplog
    ):
        import logging

        monkeypatch.setattr(
            "coworker.memory.metrics.METRICS_PATH", str(tmp_path / "metrics.json")
        )
        with caplog.at_level(logging.WARNING):
            record_session_metrics("s1", {"skill_reuse_rate": 0.5, "bogus": 1})

        # Named as the dropped one. The message also lists the known keys, so
        # asserting on the bare name would match that list too.
        assert "no storage key: bogus" in caplog.text
        assert len(_load_metrics()["skill_reuse_rate"]) == 1
