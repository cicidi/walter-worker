from __future__ import annotations
import logging
import re
from pathlib import Path
import yaml
from .models import CoworkerConfig, FeatureConfig, ProjectCatalog

logger = logging.getLogger(__name__)

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


# ── Skill Discovery ──────────────────────────────────────────────────────────


def discover_project_skills(project_root: Path) -> list:
    """Scan project_root/skills/*/SKILL.md and return Skill objects."""
    from .models import Skill

    skills_dir = project_root / "skills"
    if not skills_dir.is_dir():
        return []

    found: list[Skill] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            name, description = _parse_skill_frontmatter(skill_md)
            if name:
                found.append(Skill(
                    name=name,
                    path=f"skills/{skill_dir.name}",
                    description=description or f"Project skill: {name}",
                    enabled=True,
                ))
        except Exception:
            logger.warning("Failed to parse skill: %s", skill_md, exc_info=True)

    return found


def _parse_skill_frontmatter(skill_md: Path) -> tuple[str | None, str | None]:
    """Parse name and description from SKILL.md YAML frontmatter."""
    content = skill_md.read_text()
    # Extract YAML frontmatter between --- markers
    if not content.startswith("---"):
        return None, None
    end = content.find("---", 3)
    if end == -1:
        return None, None
    try:
        fm = yaml.safe_load(content[3:end])
    except yaml.YAMLError:
        return None, None
    if not isinstance(fm, dict):
        return None, None
    return fm.get("name"), fm.get("description")


# The two IDE command directories install.sh keeps identical in project mode —
# its step 11 mirrors the first into the second. Writing to only the first left
# OpenCode, and anything else reading that directory, without the project's
# skills.
PROJECT_IDE_COMMAND_DIRS = (".claude/commands", ".opencode/instructions")


def install_project_skills(project_root: Path) -> int:
    """Install project skills into both IDE command directories.

    Returns the number of skills installed.
    """
    skills = discover_project_skills(project_root)
    if not skills:
        return 0

    installed = 0
    for skill in skills:
        src = project_root / skill.path / "SKILL.md"
        if not src.exists():
            continue

        targets = [
            project_root / rel / f"{skill.name}.md"
            for rel in PROJECT_IDE_COMMAND_DIRS
        ]
        # Skip only when every target already has it, so a skill installed
        # before the second directory existed still gets mirrored.
        pending = [dst for dst in targets if not dst.exists()]
        if not pending:
            continue

        content = src.read_text()
        for dst in pending:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content)
        installed += 1
        logger.info(
            "Installed skill: %s -> %s",
            skill.name,
            ", ".join(str(d.parent.relative_to(project_root)) for d in pending),
        )

    return installed


# ── Project Catalog ─────────────────────────────────────────────────────────

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


# ── Feature (global) ──────────────────────────────────────────────────────

FEATURES_DIR = GLOBAL_DIR / "features"
# Pre-rename location. Still resolved so that upgrading the tool does not orphan
# an existing data directory; `coworker feature migrate` moves it across.
LEGACY_FEATURES_DIR = GLOBAL_DIR / "initiatives"
#: Kebab-case feature names. The one definition: features/manager.py
#: imported its own copy of this pattern, so the rule that decides what a
#: feature may be called existed twice and could drift.
FEATURE_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _features_dir() -> Path:
    """Feature config directory, honouring the pre-rename location.

    Reads *and* writes follow the legacy directory while it is the only one
    present, so an unmigrated machine neither loses data nor splits it across
    two trees. Once features/ exists, it wins.
    """
    if not FEATURES_DIR.exists() and LEGACY_FEATURES_DIR.exists():
        return LEGACY_FEATURES_DIR
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    return FEATURES_DIR


def _validate_feature_name(name: str) -> str:
    if not name or not FEATURE_NAME_RE.match(name):
        raise ValueError(
            f"Invalid feature name: {name!r}. "
            f"Must be kebab-case (e.g. 'my-project')."
        )
    return name


def _safe_feature_path(name: str) -> Path:
    return _features_dir() / f"{_validate_feature_name(name)}.yaml"


def list_features() -> list[FeatureConfig]:
    d = _features_dir()
    results = []
    for f in sorted(d.glob("*.yaml")):
        try:
            with open(f) as fh:
                data = yaml.safe_load(fh) or {}
            results.append(FeatureConfig(**data))
        except Exception as e:
            results.append(
                FeatureConfig(name=f.stem, description=f"[error: {e}]")
            )
    return results


def load_feature(name: str) -> FeatureConfig | None:
    path = _safe_feature_path(name)
    if not path.exists():
        return None
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return FeatureConfig(**data)


def save_feature(config: FeatureConfig) -> None:
    path = _safe_feature_path(config.name)
    data = config.model_dump(exclude_none=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def feature_path(name: str) -> Path:
    return _safe_feature_path(name)


def feature_exists(name: str) -> bool:
    return _safe_feature_path(name).exists()
