from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from coworker.initiatives.manager import InitiativeManager, _extract_active_name
from coworker.models import InitiativeConfig


# ── _extract_active_name (pure function) ──────────────────────────────────


class TestExtractActiveName:
    def test_valid_marker(self):
        content = "## Active Initiative: test-init\n\n<!-- INITIATIVE:test-init START -->\nsome content\n<!-- INITIATIVE:test-init END -->\n"
        assert _extract_active_name(content) == "test-init"

    def test_no_marker(self):
        content = "# My Project\n\n## No initiatives here\n"
        assert _extract_active_name(content) is None

    def test_malformed_marker_missing_name(self):
        content = "<!-- INITIATIVE: START -->"
        assert _extract_active_name(content) is None

    def test_malformed_marker_no_start(self):
        content = "<!-- INITIATIVE:test-init -->"
        assert _extract_active_name(content) is None

    def test_minimal_whitespace(self):
        content = "<!--INITIATIVE:test-init  START-->"
        assert _extract_active_name(content) == "test-init"


# ── InitiativeManager.create() ────────────────────────────────────────────


class TestCreate:
    def test_create_valid(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        config = manager.create("test-init", description="A test initiative")
        assert config.name == "test-init"
        assert config.description == "A test initiative"
        assert config.status == "active"
        assert config.created != ""

    def test_create_invalid_name(self, temp_initiatives_dir, temp_project_dir):
        manager = InitiativeManager(project_dir=temp_project_dir)
        with pytest.raises(ValueError, match="kebab-case"):
            manager.create("Invalid Name")

    def test_create_duplicate(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        manager.create("test-init")
        with pytest.raises(FileExistsError, match="already exists"):
            manager.create("test-init")

    def test_create_writes_yaml_file(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        manager.create("my-project")
        yaml_path = temp_initiatives_dir / "my-project.yaml"
        assert yaml_path.exists()


# ── InitiativeManager.edit() ──────────────────────────────────────────────


class TestEdit:
    def test_edit_existing(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        manager.create("edit-test", description="Original")
        updated = manager.edit("edit-test", description="Updated")
        assert updated.description == "Updated"

    def test_edit_non_existent(self, temp_initiatives_dir, temp_project_dir):
        manager = InitiativeManager(project_dir=temp_project_dir)
        with pytest.raises(FileNotFoundError, match="not found"):
            manager.edit("no-such-initiative")

    def test_edit_multiple_fields(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        manager.create("multi-edit", description="Before")
        manager.edit("multi-edit", goal="Old goal")
        updated = manager.edit("multi-edit", description="After", goal="New goal")
        assert updated.description == "After"
        assert updated.goal == "New goal"

    def test_edit_unknown_field_ignored(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        manager.create("field-test", description="Original")
        updated = manager.edit("field-test", nonexistent_field="should be ignored")
        assert updated.description == "Original"
        assert not hasattr(updated, "nonexistent_field")


# ── InitiativeManager.show() / list_all() ────────────────────────────────


class TestShow:
    def test_show_existing(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        manager.create("show-test", description="Visible")
        config = manager.show("show-test")
        assert config is not None
        assert config.name == "show-test"
        assert config.description == "Visible"

    def test_show_non_existent(self, temp_initiatives_dir, temp_project_dir):
        manager = InitiativeManager(project_dir=temp_project_dir)
        assert manager.show("no-such") is None


class TestListAll:
    def test_list_empty(self, temp_initiatives_dir, temp_project_dir):
        manager = InitiativeManager(project_dir=temp_project_dir)
        assert manager.list_all() == []

    def test_list_with_entries(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        manager.create("alpha")
        manager.create("beta")
        manager.create("gamma")
        results = manager.list_all()
        names = [c.name for c in results]
        assert "alpha" in names
        assert "beta" in names
        assert "gamma" in names


# ── InitiativeManager.remove() ────────────────────────────────────────────


class TestRemove:
    def test_remove_existing(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        manager.create("remove-me")
        yaml_path = temp_initiatives_dir / "remove-me.yaml"
        assert yaml_path.exists()
        manager.remove("remove-me")
        assert not yaml_path.exists()

    def test_remove_non_existent(self, temp_initiatives_dir, temp_project_dir):
        manager = InitiativeManager(project_dir=temp_project_dir)
        with pytest.raises(FileNotFoundError, match="not found"):
            manager.remove("no-such")

    def test_remove_deactivates_if_active(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        """When removing the active initiative, deactivate is called first."""
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        manager.create("active-remove")

        # Create CLAUDE.local.md declaring this initiative active
        local_md = temp_project_dir / "CLAUDE.local.md"
        local_md.write_text(
            "## Active Initiative: active-remove\n\n"
            "<!-- INITIATIVE:active-remove START -->\n"
            "content\n"
            "<!-- INITIATIVE:active-remove END -->\n"
        )

        # Mock remove_initiative at the manager level
        deactivated = []
        monkeypatch.setattr(
            "coworker.initiatives.manager.remove_initiative",
            lambda project_dir: deactivated.append("removed") or ["removed initiative 'active-remove'"],
        )

        manager.remove("active-remove")
        assert len(deactivated) == 1
        yaml_path = temp_initiatives_dir / "active-remove.yaml"
        assert not yaml_path.exists()


# ── InitiativeManager.activate() / deactivate() ───────────────────────────


class TestActivate:
    def test_activate_calls_inject_initiative(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        manager.create("activate-test", description="test")

        injected_configs = []
        monkeypatch.setattr(
            "coworker.initiatives.manager.inject_initiative",
            lambda config, project_dir: injected_configs.append(config) or ["injected"],
        )
        monkeypatch.setattr(
            "coworker.initiatives.manager.remove_initiative",
            lambda project_dir: ["no initiative"],
        )

        actions = manager.activate("activate-test")
        assert len(injected_configs) == 1
        assert injected_configs[0].name == "activate-test"
        assert any("Activated" in a for a in actions)

    def test_activate_deactivates_previous_first(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(manager, "_scaffold_docs", lambda name: None)
        manager.create("second-init")

        call_order = []
        monkeypatch.setattr(
            "coworker.initiatives.manager.inject_initiative",
            lambda config, project_dir: call_order.append("inject") or ["injected"],
        )
        monkeypatch.setattr(
            "coworker.initiatives.manager.remove_initiative",
            lambda project_dir: call_order.append("remove") or ["no initiative"],
        )

        manager.activate("second-init")
        assert call_order == ["remove", "inject"]

    def test_activate_non_existent(self, temp_initiatives_dir, temp_project_dir):
        manager = InitiativeManager(project_dir=temp_project_dir)
        with pytest.raises(FileNotFoundError, match="not found"):
            manager.activate("no-such")


class TestDeactivate:
    def test_deactivate_calls_remove_initiative(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)

        remove_calls = []
        monkeypatch.setattr(
            "coworker.initiatives.manager.remove_initiative",
            lambda project_dir: remove_calls.append(project_dir) or ["removed initiative 'test'"],
        )

        actions = manager.deactivate()
        assert len(remove_calls) == 1
        assert remove_calls[0] == temp_project_dir
        assert any("Deactivated" in a for a in actions)

    def test_deactivate_no_active_initiative(self, temp_initiatives_dir, temp_project_dir, monkeypatch):
        manager = InitiativeManager(project_dir=temp_project_dir)
        monkeypatch.setattr(
            "coworker.initiatives.manager.remove_initiative",
            lambda project_dir: ["no initiative in CLAUDE.local.md"],
        )

        actions = manager.deactivate()
        assert any("No active initiative" in a for a in actions)


# ── InitiativeManager.active_name() ───────────────────────────────────────


class TestActiveName:
    def test_active_name_with_initiative(self, temp_initiatives_dir, temp_project_dir):
        manager = InitiativeManager(project_dir=temp_project_dir)
        local_md = temp_project_dir / "CLAUDE.local.md"
        local_md.write_text(
            "## Active Initiative: my-active\n\n"
            "<!-- INITIATIVE:my-active START -->\n"
            "some content\n"
            "<!-- INITIATIVE:my-active END -->\n"
        )
        assert manager.active_name() == "my-active"

    def test_active_name_no_file(self, temp_initiatives_dir, temp_project_dir):
        manager = InitiativeManager(project_dir=temp_project_dir)
        assert manager.active_name() is None

    def test_active_name_no_initiative_in_file(self, temp_initiatives_dir, temp_project_dir):
        manager = InitiativeManager(project_dir=temp_project_dir)
        local_md = temp_project_dir / "CLAUDE.local.md"
        local_md.write_text("# Personal Working Context\n\nNo active initiative\n")
        assert manager.active_name() is None
