from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path

from ..config import (
    GLOBAL_DIR,
    FEATURES_DIR,
    load_feature,
    save_feature,
    list_features,
    feature_exists,
)
from ..models import (
    FeatureConfig,
    FeatureProjectRef,
)
from ..adapters.claude import inject_feature, remove_feature

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _local_md_path(project_dir: Path) -> Path:
    return project_dir / "CLAUDE.local.md"


def _extract_active_name(content: str) -> str | None:
    m = re.search(r"<!--\s*FEATURE:(\S+)\s+START\s*-->", content)
    if m:
        return m.group(1)
    return None


class FeatureManager:

    def __init__(self, project_dir: Path | None = None):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()

    # ── CRUD ────────────────────────────────────────────────────────────

    def create(self, name: str, description: str = "") -> FeatureConfig:
        if feature_exists(name):
            raise FileExistsError(f"Feature '{name}' already exists.")
        if not KEBAB_RE.match(name):
            raise ValueError(f"Name '{name}' must be kebab-case (e.g. 'auth-migration').")

        config = FeatureConfig(
            name=name,
            description=description,
            status="active",
            created=datetime.now().strftime("%Y-%m-%d"),
        )
        save_feature(config)

        self._scaffold_docs(name)
        return config

    def _scaffold_docs(self, name: str) -> None:
        """Create docs/features/<feature>/<doc-type>/ directories."""
        try:
            from ...constants import DOCS_DISCIPLINES
        except ImportError:
            from ..constants import DOCS_DISCIPLINES
        for discipline in DOCS_DISCIPLINES:
            (self.project_dir / "docs" / "features" / name / discipline).mkdir(
                parents=True, exist_ok=True
            )


    def edit(self, name: str, **updates) -> FeatureConfig:
        config = load_feature(name)
        if config is None:
            raise FileNotFoundError(f"Feature '{name}' not found.")

        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        save_feature(config)
        return config

    def show(self, name: str) -> FeatureConfig | None:
        return load_feature(name)

    def list_all(self) -> list[FeatureConfig]:
        return list_features()

    def remove(self, name: str) -> None:
        if not feature_exists(name):
            raise FileNotFoundError(f"Feature '{name}' not found.")

        if self.active_name() == name:
            self.deactivate()

        path = FEATURES_DIR / f"{name}.yaml"
        path.unlink()

    # ── Activation ──────────────────────────────────────────────────────

    def activate(self, name: str) -> list[str]:
        config = load_feature(name)
        if config is None:
            raise FileNotFoundError(f"Feature '{name}' not found.")

        actions = []
        self.deactivate()

        # Claude injects into CLAUDE.local.md; OpenCode reads the same file.
        actions += inject_feature(config, project_dir=self.project_dir)
        actions.append(f"Activated feature '{name}'")
        return actions

    def deactivate(self) -> list[str]:
        actions = []
        had_effect = False

        result = remove_feature(project_dir=self.project_dir)
        for r in result:
            if "removed" in r:
                had_effect = True
            actions.append(r)

        if had_effect:
            actions.append("Deactivated current feature")
        else:
            actions.append("No active feature")
        return actions

    def active_name(self) -> str | None:
        """Derive the active feature from the project's CLAUDE.local.md
        FEATURE block.  No global .active marker — single source of truth."""
        local_md = _local_md_path(self.project_dir)
        if not local_md.exists():
            return None
        return _extract_active_name(local_md.read_text(encoding="utf-8"))

    def archive(self, name: str) -> FeatureConfig:
        return self.edit(name, status="archived")

    def inject_static_context(self) -> list[str]:
        from ..config import load_project_catalog
        from ..adapters.claude import inject_static_context

        catalog = load_project_catalog()
        return inject_static_context(catalog, project_dir=self.project_dir)
