from __future__ import annotations
import os
import re
from pathlib import Path
import yaml
from .models import CoworkerConfig

GLOBAL_DIR = Path.home() / ".coworker"
GLOBAL_CONFIG = GLOBAL_DIR / "coworker.yaml"
PROJECT_CONFIG_NAME = ".coworker/coworker.yaml"


def find_project_config() -> Path | None:
    """Walk up from cwd to find .coworker/coworker.yaml"""
    current = Path.cwd()
    while current != current.parent:
        candidate = current / PROJECT_CONFIG_NAME
        if candidate.exists():
            return candidate
        current = current.parent
    return None


def load_config(path: Path) -> CoworkerConfig:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return CoworkerConfig(**data)


def load_global_config() -> CoworkerConfig | None:
    if GLOBAL_CONFIG.exists():
        return load_config(GLOBAL_CONFIG)
    return None


def load_project_config() -> CoworkerConfig | None:
    path = find_project_config()
    if path:
        return load_config(path)
    return None


def merged_config() -> CoworkerConfig:
    """Project config overrides global config."""
    base = load_global_config() or CoworkerConfig()
    project = load_project_config()
    if not project:
        return base

    # merge: project MCP + skills append to global, project permissions override
    merged = base.model_copy(deep=True)

    # add project MCP servers (deduplicate by name)
    existing_names = {s.name for s in merged.mcp}
    for server in project.mcp:
        if server.name not in existing_names:
            merged.mcp.append(server)
        else:
            # project overrides global for same-name server
            merged.mcp = [server if s.name == server.name else s for s in merged.mcp]

    # add project skills (deduplicate by name)
    existing_skills = {s.name for s in merged.skills}
    for skill in project.skills:
        if skill.name not in existing_skills:
            merged.skills.append(skill)

    # project permissions override global
    if project.permissions.allow:
        merged.permissions.allow = project.permissions.allow
    if project.permissions.deny:
        merged.permissions.deny = project.permissions.deny

    return merged


def save_config(config: CoworkerConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(exclude_none=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


# ── Project Catalog ─────────────────────────────────────────────────────────

from .models import ProjectCatalog

PROJECT_CATALOG_PATH = GLOBAL_DIR / "project.yaml"


def load_project_catalog() -> ProjectCatalog:
    if not PROJECT_CATALOG_PATH.exists():
        return ProjectCatalog()
    with open(PROJECT_CATALOG_PATH) as f:
        data = yaml.safe_load(f) or {}
    return ProjectCatalog(**data)


def save_project_catalog(catalog: ProjectCatalog) -> None:
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    data = catalog.model_dump(exclude_none=True)
    with open(PROJECT_CATALOG_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


# ── Initiative (global) ──────────────────────────────────────────────────────

from .models import InitiativeConfig

INITIATIVES_DIR = GLOBAL_DIR / "initiatives"
_INITIATIVE_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _initiatives_dir() -> Path:
    INITIATIVES_DIR.mkdir(parents=True, exist_ok=True)
    return INITIATIVES_DIR


def _validate_initiative_name(name: str) -> str:
    if not name or not _INITIATIVE_NAME_RE.match(name):
        raise ValueError(
            f"Invalid initiative name: {name!r}. "
            f"Must be kebab-case (e.g. 'my-project')."
        )
    return name


def _safe_initiative_path(name: str) -> Path:
    return _initiatives_dir() / f"{_validate_initiative_name(name)}.yaml"


def list_initiatives() -> list[InitiativeConfig]:
    d = _initiatives_dir()
    results = []
    for f in sorted(d.glob("*.yaml")):
        try:
            with open(f) as fh:
                data = yaml.safe_load(fh) or {}
            results.append(InitiativeConfig(**data))
        except Exception as e:
            results.append(
                InitiativeConfig(name=f.stem, description=f"[error: {e}]")
            )
    return results


def load_initiative(name: str) -> InitiativeConfig | None:
    path = _safe_initiative_path(name)
    if not path.exists():
        return None
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return InitiativeConfig(**data)


def save_initiative(config: InitiativeConfig) -> None:
    path = _safe_initiative_path(config.name)
    data = config.model_dump(exclude_none=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def initiative_path(name: str) -> Path:
    return _safe_initiative_path(name)


def initiative_exists(name: str) -> bool:
    return _safe_initiative_path(name).exists()
