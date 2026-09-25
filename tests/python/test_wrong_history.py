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


class TestWrappedPreventionRules:
    """A multi-line prevention rule was cut off at the first newline.

    The parser took only the text after the marker on the same line, so a rule
    that wrapped was severed mid-sentence. The shipped adversarial-review rule
    came out as "In any adversarial review (devil-advocate, con/pro/judge)," —
    ending on a comma and preventing nothing. It was the severity:high entry,
    and the dropped text was the entire instruction.
    """

    def _entry(self, tmp_path, rule_body: str):
        entries = tmp_path / "entries"
        entries.mkdir(parents=True, exist_ok=True)
        (entries / "2026-01-01-wrapped.md").write_text(
            "---\ndate: 2026-01-01\nseverity: high\ncategory: testing\n---\n\n"
            "# A wrapped rule\n\n"
            "**What happened:** something\n\n"
            f"**Prevention rule:** {rule_body}\n\n"
            "**Anti-pattern:** not following it\n"
        )
        return str(tmp_path)

    def test_the_continuation_is_kept(self, tmp_path):
        from coworker.memory.wrong_history import extract_rules

        d = self._entry(
            tmp_path,
            "In any adversarial review,\n"
            "the PRO agent MUST search for counter-evidence\n"
            "and attempt to REFUTE each finding.",
        )
        rules = extract_rules(d)

        assert len(rules) == 1
        rule = rules[0]["rule"]
        assert "REFUTE each finding" in rule, f"rule truncated: {rule!r}"
        assert rule.startswith("In any adversarial review,")

    def test_it_stops_at_the_next_field(self, tmp_path):
        from coworker.memory.wrong_history import extract_rules

        d = self._entry(tmp_path, "Do the thing.\nThen stop.")
        rule = extract_rules(d)[0]["rule"]

        assert "Then stop." in rule
        assert "Anti-pattern" not in rule, "must not swallow the next field"


class TestIndexKeepsTheWholeRule:
    """The index rebuild had its own copy of the single-line rule read.

    Both it and extract_rules took only the text after the marker on one line,
    so a wrapped rule was severed in the index too — and fixing one would have
    left the other severing rules. They now share one extractor.
    """

    def _entry(self, tmp_path):
        entries = tmp_path / "entries"
        entries.mkdir(parents=True, exist_ok=True)
        (entries / "2026-01-01-wrapped.md").write_text(
            "---\ndate: 2026-01-01\nseverity: high\ncategory: testing\n---\n\n"
            "# Wrapped\n\n"
            "**Prevention rule:** Start here,\nand the rest of the rule follows.\n\n"
            "**Anti-pattern:** ignoring it\n"
        )

    def test_the_continuation_reaches_the_index(self, tmp_path, monkeypatch):
        from coworker.memory import wrong_history as w

        self._entry(tmp_path)
        monkeypatch.setattr(w, "WH_DIR", str(tmp_path))

        count, path = w._rebuild_index()

        assert count == 1
        assert path.exists()
        text = path.read_text()
        assert "the rest of the rule follows" in text, "index kept only line one"
        assert "Anti-pattern" not in text
