from __future__ import annotations
import importlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import yaml

from coworker.models import (
    CoworkerConfig,
    McpServer,
    Permissions,
    ProjectEntry,
    ProjectCatalog,
    FeatureConfig,
    Skill,
)
import coworker.config as cfg


class TestProjectCatalogConfig:
    def test_load_empty(self, temp_coworker_dir):
        catalog = cfg.load_project_catalog()
        assert catalog.projects == []

    def test_save_and_load(self, temp_coworker_dir):
        catalog = ProjectCatalog(
            projects=[ProjectEntry(name="svc", local_path="/tmp/svc")]
        )
        cfg.save_project_catalog(catalog)
        loaded = cfg.load_project_catalog()
        assert len(loaded.projects) == 1
        assert loaded.projects[0].name == "svc"

    def test_overwrite(self, temp_coworker_dir):
        catalog = ProjectCatalog(
            projects=[ProjectEntry(name="old", local_path="/tmp/old")]
        )
        cfg.save_project_catalog(catalog)
        catalog.projects = [
            ProjectEntry(name="new", local_path="/tmp/new")
        ]
        cfg.save_project_catalog(catalog)
        loaded = cfg.load_project_catalog()
        assert loaded.projects[0].name == "new"


class TestFeatureConfig:
    def test_save_and_load(self, temp_features_dir):
        cfg.save_feature(
            FeatureConfig(name="test-init", description="Test"),
        )
        loaded = cfg.load_feature("test-init")
        assert loaded is not None
        assert loaded.name == "test-init"
        assert loaded.description == "Test"

    def test_feature_exists(self, temp_features_dir):
        assert not cfg.feature_exists("test-init")
        cfg.save_feature(FeatureConfig(name="test-init"))
        assert cfg.feature_exists("test-init")

    def test_list_features(self, temp_features_dir):
        cfg.save_feature(FeatureConfig(name="init-a"))
        cfg.save_feature(FeatureConfig(name="init-b"))
        results = cfg.list_features()
        assert len(results) == 2
        names = {i.name for i in results}
        assert names == {"init-a", "init-b"}

    def test_load_nonexistent(self, temp_features_dir):
        assert cfg.load_feature("does-not-exist") is None

    def test_load_save_preserves_unknown_keys(self, temp_features_dir):
        """Keys the model does not define must survive a load/save cycle.

        Feature YAML is user-editable and save_feature() writes model_dump()
        straight back to disk, so Pydantic's default extra="ignore" would
        silently delete anything unmodelled on any edit.
        """
        path = cfg.feature_path("extras")
        path.write_text(
            "name: extras\ndescription: d\nllm_effort: high\n", encoding="utf-8"
        )

        loaded = cfg.load_feature("extras")
        assert loaded is not None
        cfg.save_feature(loaded)

        saved = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert saved["llm_effort"] == "high", "unmodelled key was dropped"

    def test_edit_preserves_unknown_keys(self, temp_features_dir):
        """The same must hold when a modelled field actually changes."""
        path = cfg.feature_path("extras2")
        path.write_text(
            "name: extras2\ndescription: before\nllm_effort: high\n",
            encoding="utf-8",
        )

        loaded = cfg.load_feature("extras2")
        loaded.description = "after"
        cfg.save_feature(loaded)

        saved = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert saved["description"] == "after"
        assert saved["llm_effort"] == "high"


class TestMergedConfig:
    """Tests for merged_config() — project config overrides global config."""

    def test_no_global_no_project(self, monkeypatch):
        """When neither global nor project config exists, returns a default CoworkerConfig."""
        monkeypatch.setattr(cfg, "load_global_config", lambda: None)
        monkeypatch.setattr(cfg, "load_project_config", lambda: None)

        result = cfg.merged_config()
        assert isinstance(result, CoworkerConfig)
        assert result.scope == "global"
        assert result.mcp == []
        assert result.skills == []
        assert result.permissions.allow == []
        assert result.permissions.deny == []

    def test_global_only_no_project(self, monkeypatch):
        """When only a global config exists and no project config, return global as-is."""
        global_cfg = CoworkerConfig(
            scope="global",
            mcp=[McpServer(name="server1", command="cmd1")],
            permissions=Permissions(allow=["read"], deny=["write"]),
        )
        monkeypatch.setattr(cfg, "load_global_config", lambda: global_cfg)
        monkeypatch.setattr(cfg, "load_project_config", lambda: None)

        result = cfg.merged_config()
        assert len(result.mcp) == 1
        assert result.mcp[0].name == "server1"
        assert result.permissions.allow == ["read"]

    def test_project_overrides_global_mcp_same_name(self, monkeypatch):
        """A project MCP server with the same name as a global one overrides it."""
        global_cfg = CoworkerConfig(
            mcp=[McpServer(name="shared", command="global-cmd", args=["--old"])],
        )
        project_cfg = CoworkerConfig(
            scope="project",
            mcp=[McpServer(name="shared", command="project-cmd", args=["--new"])],
        )
        monkeypatch.setattr(cfg, "load_global_config", lambda: global_cfg)
        monkeypatch.setattr(cfg, "load_project_config", lambda: project_cfg)

        result = cfg.merged_config()
        shared = [s for s in result.mcp if s.name == "shared"]
        assert len(shared) == 1
        assert shared[0].command == "project-cmd"
        assert shared[0].args == ["--new"]

    def test_project_appends_new_mcp_servers(self, monkeypatch):
        """Project MCP servers with new names are appended to global ones."""
        global_cfg = CoworkerConfig(
            mcp=[McpServer(name="global-only", command="g-cmd")],
        )
        project_cfg = CoworkerConfig(
            scope="project",
            mcp=[McpServer(name="project-only", command="p-cmd")],
        )
        monkeypatch.setattr(cfg, "load_global_config", lambda: global_cfg)
        monkeypatch.setattr(cfg, "load_project_config", lambda: project_cfg)

        result = cfg.merged_config()
        names = {s.name for s in result.mcp}
        assert names == {"global-only", "project-only"}

    def test_project_skills_dedup_by_name(self, monkeypatch):
        """Duplicate skill names from project are not added; global version is kept."""
        global_cfg = CoworkerConfig(
            skills=[Skill(name="shared-skill", path="/global/path")],
        )
        project_cfg = CoworkerConfig(
            scope="project",
            skills=[Skill(name="shared-skill", path="/project/path")],
        )
        monkeypatch.setattr(cfg, "load_global_config", lambda: global_cfg)
        monkeypatch.setattr(cfg, "load_project_config", lambda: project_cfg)

        result = cfg.merged_config()
        # shared-skill appears only once (skills dedup by name, project only appends new)
        matching = [s for s in result.skills if s.name == "shared-skill"]
        assert len(matching) == 1
        assert matching[0].path == "/global/path"

    def test_project_new_skills_appended(self, monkeypatch):
        """Project skills with new names are appended to global skills."""
        global_cfg = CoworkerConfig(
            skills=[Skill(name="global-skill", path="/g")],
        )
        project_cfg = CoworkerConfig(
            scope="project",
            skills=[Skill(name="project-skill", path="/p")],
        )
        monkeypatch.setattr(cfg, "load_global_config", lambda: global_cfg)
        monkeypatch.setattr(cfg, "load_project_config", lambda: project_cfg)

        result = cfg.merged_config()
        names = {s.name for s in result.skills}
        assert names == {"global-skill", "project-skill"}

    def test_project_permissions_override_global(self, monkeypatch):
        """Non-empty project permissions override global permissions entirely."""
        global_cfg = CoworkerConfig(
            permissions=Permissions(allow=["read"], deny=["write"]),
        )
        project_cfg = CoworkerConfig(
            scope="project",
            permissions=Permissions(allow=["execute"], deny=["delete"]),
        )
        monkeypatch.setattr(cfg, "load_global_config", lambda: global_cfg)
        monkeypatch.setattr(cfg, "load_project_config", lambda: project_cfg)

        result = cfg.merged_config()
        assert result.permissions.allow == ["execute"]
        assert result.permissions.deny == ["delete"]

    def test_project_empty_permissions_do_not_override(self, monkeypatch):
        """Empty project permission lists do not override global permissions."""
        global_cfg = CoworkerConfig(
            permissions=Permissions(allow=["read"], deny=["write"]),
        )
        project_cfg = CoworkerConfig(
            scope="project",
            permissions=Permissions(allow=[], deny=[]),
        )
        monkeypatch.setattr(cfg, "load_global_config", lambda: global_cfg)
        monkeypatch.setattr(cfg, "load_project_config", lambda: project_cfg)

        result = cfg.merged_config()
        # Empty lists are falsy so global permissions should remain
        assert result.permissions.allow == ["read"]
        assert result.permissions.deny == ["write"]


class TestSaveConfig:
    """Tests for save_config() — write CoworkerConfig to YAML on disk."""

    def test_save_and_reload_config(self, tmp_path):
        """Save a config to a YAML file and verify it can be read back."""
        config = CoworkerConfig(
            scope="project",
            mcp=[McpServer(name="test-server", command="echo", args=["hello"])],
            skills=[Skill(name="test-skill", path="/tmp/test", description="A test skill")],
            permissions=Permissions(allow=["read"], deny=["write"]),
        )
        path = tmp_path / "subdir" / "coworker.yaml"
        cfg.save_config(config, path)

        assert path.exists()
        with open(path) as f:
            data = yaml.safe_load(f)

        assert data["scope"] == "project"
        assert data["mcp"][0]["name"] == "test-server"
        assert data["skills"][0]["name"] == "test-skill"
        assert data["permissions"]["allow"] == ["read"]


class TestProjectSkillInstallation:
    """Project skills must reach both IDE command directories.

    install.sh mirrors <project>/.claude/commands/ into
    <project>/.opencode/instructions/ (step 11). This installed to the first
    only, so OpenCode never received a project's skills — the second directory
    was not even created.
    """

    def _project_with_skill(self, root):
        skill = root / "skills" / "my-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: Use when testing.\n---\n# my-skill\n",
            encoding="utf-8",
        )
        return root

    def test_installs_into_both_directories(self, tmp_path):
        project = self._project_with_skill(tmp_path / "proj")

        installed = cfg.install_project_skills(project)
        assert installed == 1

        for rel in (".claude/commands", ".opencode/instructions"):
            assert (project / rel / "my-skill.md").is_file(), f"missing in {rel}"

    def test_second_run_is_idempotent(self, tmp_path):
        project = self._project_with_skill(tmp_path / "proj")

        cfg.install_project_skills(project)
        assert cfg.install_project_skills(project) == 0
