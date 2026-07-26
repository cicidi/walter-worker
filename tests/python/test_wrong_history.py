from coworker.memory.wrong_history import extract_rules, build_snapshot, inject_into_local_md, MARKER_START, MARKER_END

class TestExtractRules:
    def test_no_entries_dir(self, tmp_path):
        rules = extract_rules(str(tmp_path / "nonexistent"))
        assert rules == []

class TestBuildSnapshot:
    def test_no_rules(self, tmp_path):
        snapshot = build_snapshot(str(tmp_path / "nonexistent"))
        assert MARKER_START in snapshot
        assert "No wrong-history entries yet" in snapshot

    def test_with_rules(self, tmp_path):
        d = tmp_path / "entries"
        d.mkdir(parents=True)
        (d / "test.md").write_text("---\ndate: 2026-01-01\nseverity: critical\ncategory: test\n---\n# Test\n**Prevention rule:** Always test before commit\n")
        snapshot = build_snapshot(str(tmp_path))
        assert "Always test before commit" in snapshot

class TestInjectLocalMd:
    def test_creates_file(self, tmp_path):
        p = tmp_path / "test.md"
        inject_into_local_md(str(p), "<!-- WRONG-HISTORY START -->\ntest\n<!-- WRONG-HISTORY END -->")
        assert p.exists()
        assert "test" in p.read_text()

    def test_replaces_existing(self, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("old<!-- WRONG-HISTORY START -->old-body<!-- WRONG-HISTORY END -->end")
        inject_into_local_md(str(p), "<!-- WRONG-HISTORY START -->new-body<!-- WRONG-HISTORY END -->")
        assert "new-body" in p.read_text()
        assert "old-body" not in p.read_text()
