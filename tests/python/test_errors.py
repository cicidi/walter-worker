"""Tests for coworker.memory.errors — error code registry."""

from __future__ import annotations

from coworker.memory.errors import (
    MEM_E001, MEM_E002, MEM_E003, MEM_E004, MEM_E005,
    SYNC_E001, SYNC_E002, SYNC_E003, SYNC_E004, SYNC_E005,
    SKILL_E001, SKILL_E002, SKILL_E003, SKILL_E004, SKILL_E005,
    AUTO_E001, AUTO_E002, AUTO_E003,
    ALL_ERROR_CODES,
)


class TestErrorCodes:
    def test_all_codes_registered(self):
        assert len(ALL_ERROR_CODES) == 18

    def test_mem_codes_format(self):
        msg = MEM_E001.format(detail="test failure")
        assert msg.startswith("[MEM_E001]")
        assert "test failure" in msg

    def test_sync_codes_format(self):
        msg = SYNC_E004.format(session_id="s1", gap_minutes=10.5)
        assert "[SYNC_E004]" in msg
        assert "s1" in msg
        assert "10.5" in msg or "10" in msg

    def test_skill_codes_format(self):
        msg = SKILL_E001.format(count=5, limit=3)
        assert "[SKILL_E001]" in msg
        assert "5" in msg
        assert "3" in msg

    def test_auto_codes_format(self):
        msg = AUTO_E001.format(detail="agent crash")
        assert "[AUTO_E001]" in msg
        assert "agent crash" in msg

    def test_code_objects_have_code_and_message(self):
        for code in ALL_ERROR_CODES.values():
            assert code.code
            assert code.message
