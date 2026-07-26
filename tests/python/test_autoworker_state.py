"""Tests for coworker.autoworker.state — state file management."""

from __future__ import annotations

from coworker.autoworker.state import (
    add_open_question,
    get_open_questions,
    has_been_checked,
    load_checked_ids,
    mark_checked,
)


class TestHasBeenChecked:
    def test_no_file_returns_false(self, tmp_path):
        assert has_been_checked(str(tmp_path / "nonexistent.md"), "test item") is False

    def test_item_present_returns_true(self, tmp_path):
        p = tmp_path / "state.md"
        p.write_text("checked: test item")
        assert has_been_checked(str(p), "test item") is True

    def test_item_absent_returns_false(self, tmp_path):
        p = tmp_path / "state.md"
        p.write_text("checked: other item")
        assert has_been_checked(str(p), "test item") is False


class TestMarkChecked:
    def test_creates_file_with_table(self, tmp_path):
        p = tmp_path / "state.md"
        mark_checked(str(p), "C-001", "mem0 ok", "DONE_RIGHT")
        content = p.read_text()
        assert "C-001" in content
        assert "mem0 ok" in content
        assert "DONE_RIGHT" in content

    def test_appends_to_existing_table(self, tmp_path):
        p = tmp_path / "state.md"
        mark_checked(str(p), "C-001", "first", "OK")
        mark_checked(str(p), "C-002", "second", "MISMATCH")
        content = p.read_text()
        assert "C-001" in content
        assert "C-002" in content

    def test_no_duplicate_ids(self, tmp_path):
        p = tmp_path / "state.md"
        mark_checked(str(p), "C-001", "first", "OK")
        mark_checked(str(p), "C-001", "first", "OK")
        assert p.read_text().count("C-001") == 1


class TestOpenQuestions:
    def test_add_and_get(self, tmp_path):
        p = tmp_path / "state.md"
        qid = add_open_question(str(p), "Is mem0 running?")
        assert qid == "Q-1"

        questions = get_open_questions(str(p))
        assert len(questions) == 1
        assert questions[0]["id"] == "Q-1"
        assert questions[0]["status"] == "pending"

    def test_multiple_questions(self, tmp_path):
        p = tmp_path / "state.md"
        add_open_question(str(p), "Question A")
        add_open_question(str(p), "Question B")
        add_open_question(str(p), "Question C")
        assert len(get_open_questions(str(p))) == 3

    def test_no_file_returns_empty(self, tmp_path):
        assert get_open_questions(str(tmp_path / "nope.md")) == []


class TestLoadCheckedIds:
    def test_empty_file(self, tmp_path):
        p = tmp_path / "state.md"
        p.write_text("## Checked\n")
        assert load_checked_ids(str(p)) == set()

    def test_loads_ids(self, tmp_path):
        p = tmp_path / "state.md"
        p.write_text("## Checked\n| C-001 | ... |\n| C-002 | ... |\n")
        ids = load_checked_ids(str(p))
        assert "C-001" in ids
        assert "C-002" in ids

    def test_no_file(self, tmp_path):
        assert load_checked_ids(str(tmp_path / "no.md")) == set()
