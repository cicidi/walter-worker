from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path

from ..config import (
    GLOBAL_DIR,
    INITIATIVES_DIR,
    load_initiative,
    save_initiative,
    list_initiatives,
    initiative_exists,
)
from ..models import (
    InitiativeConfig,
    InitiativeProjectRef,
)
from ..adapters.claude import inject_initiative, remove_initiative

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _local_md_path(project_dir: Path) -> Path:
    return project_dir / "CLAUDE.local.md"


def _extract_active_name(content: str) -> str | None:
    m = re.search(r"<!--\s*INITIATIVE:(\S+)\s+START\s*-->", content)
    if m:
        return m.group(1)
    return None


class InitiativeManager:

    def __init__(self, project_dir: Path | None = None):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()

    # ── CRUD ────────────────────────────────────────────────────────────

    def create(self, name: str, description: str = "") -> InitiativeConfig:
        if initiative_exists(name):
            raise FileExistsError(f"Initiative '{name}' already exists.")
        if not KEBAB_RE.match(name):
            raise ValueError(f"Name '{name}' must be kebab-case (e.g. 'auth-migration').")

        config = InitiativeConfig(
            name=name,
            description=description,
            status="active",
            created=datetime.now().strftime("%Y-%m-%d"),
        )
        save_initiative(config)
        return config

    def edit(self, name: str, **updates) -> InitiativeConfig:
        config = load_initiative(name)
        if config is None:
            raise FileNotFoundError(f"Initiative '{name}' not found.")

        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        save_initiative(config)
        return config

    def show(self, name: str) -> InitiativeConfig | None:
        return load_initiative(name)

    def list_all(self) -> list[InitiativeConfig]:
        return list_initiatives()

    def remove(self, name: str) -> None:
        if not initiative_exists(name):
            raise FileNotFoundError(f"Initiative '{name}' not found.")

        if self.active_name() == name:
            self.deactivate()

        path = INITIATIVES_DIR / f"{name}.yaml"
        path.unlink()

    # ── Activation ──────────────────────────────────────────────────────

    def activate(self, name: str) -> list[str]:
        config = load_initiative(name)
        if config is None:
            raise FileNotFoundError(f"Initiative '{name}' not found.")

        actions = []
        self.deactivate()

        # Claude injects into CLAUDE.local.md; OpenCode reads the same file.
        actions += inject_initiative(config, project_dir=self.project_dir)
        actions.append(f"Activated initiative '{name}'")
        return actions

    def deactivate(self) -> list[str]:
        actions = []
        had_effect = False

        result = remove_initiative(project_dir=self.project_dir)
        for r in result:
            if "removed" in r:
                had_effect = True
            actions.append(r)

        if had_effect:
            actions.append("Deactivated current initiative")
        else:
            actions.append("No active initiative")
        return actions

    def active_name(self) -> str | None:
        """Derive the active initiative from the project's CLAUDE.local.md
        INITIATIVE block.  No global .active marker — single source of truth."""
        local_md = _local_md_path(self.project_dir)
        if not local_md.exists():
            return None
        return _extract_active_name(local_md.read_text(encoding="utf-8"))

    def archive(self, name: str) -> InitiativeConfig:
        return self.edit(name, status="archived")

    def inject_static_context(self) -> list[str]:
        from ..config import load_project_catalog
        from ..adapters.claude import inject_static_context

        catalog = load_project_catalog()
        return inject_static_context(catalog, project_dir=self.project_dir)
