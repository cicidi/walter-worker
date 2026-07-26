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
