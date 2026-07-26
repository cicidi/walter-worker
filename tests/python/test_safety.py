"""Tests for coworker.memory.safety — circuit breaker and safety gates."""

from __future__ import annotations

import json
from unittest.mock import patch

from coworker.memory.safety import (
    CIRCUIT_BREAKER_LIMIT,
    check_circuit_breaker,
    record_auto_evolution,
    reset_circuit_breaker,
)


class TestCircuitBreaker:
    def test_initial_state_allows(self, tmp_path, monkeypatch):
        state_path = tmp_path / "circuit_state.json"
        monkeypatch.setattr("coworker.memory.safety._circuit_state_path", lambda: state_path)
        result = check_circuit_breaker()
        assert result["allowed"] is True
        assert result["count"] == 0

    def test_records_evolution(self, tmp_path, monkeypatch):
        state_path = tmp_path / "circuit_state.json"
        monkeypatch.setattr("coworker.memory.safety._circuit_state_path", lambda: state_path)
        assert record_auto_evolution("create", "test-skill") is True
        data = json.loads(state_path.read_text())
        assert data["count"] == 1
        assert data["history"][0]["skill"] == "test-skill"

    def test_trips_after_limit(self, tmp_path, monkeypatch):
        state_path = tmp_path / "circuit_state.json"
        monkeypatch.setattr("coworker.memory.safety._circuit_state_path", lambda: state_path)
        for i in range(CIRCUIT_BREAKER_LIMIT):
            assert record_auto_evolution("create", f"skill-{i}") is True
        # Next should trip
        assert record_auto_evolution("create", "over-limit") is False
        check = check_circuit_breaker()
        assert check["allowed"] is False

    def test_reset_clears(self, tmp_path, monkeypatch):
        state_path = tmp_path / "circuit_state.json"
        monkeypatch.setattr("coworker.memory.safety._circuit_state_path", lambda: state_path)
        record_auto_evolution("create", "s1")
        reset_circuit_breaker()
        check = check_circuit_breaker()
        assert check["allowed"] is True
        assert check["count"] == 0


class TestCircuitBreakerEdgeCase:
    def test_corrupt_state_file(self, tmp_path, monkeypatch):
        state_path = tmp_path / "circuit_state.json"
        state_path.write_text("not json")
        monkeypatch.setattr("coworker.memory.safety._circuit_state_path", lambda: state_path)
        result = check_circuit_breaker()
        assert result["allowed"] is True
