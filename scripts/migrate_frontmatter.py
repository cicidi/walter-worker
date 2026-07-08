#!/usr/bin/env python3
"""Migrate all skills/*/SKILL.md frontmatter to the canonical schema
(one shape: name/version/description/triggers/when-to-use + optional
aliases/license/compatibility).  Dry-run prints what would change;
omit --dry-run to apply.

Usage:  python3 scripts/migrate_frontmatter.py [--dry-run]
"""
import sys
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent.parent


def migrate_frontmatter(raw: str) -> str | None:
    """Parse old frontmatter, return new YAML or None if already compliant."""
    raw = raw.strip()
    if not raw.startswith("---"):
        return None

    # Strip opening/closing ---
    inner = raw[3:].strip()
    if inner.endswith("---"):
        inner = inner[:-3].strip()
    if inner.endswith("---"):
        inner = inner[:-3].strip()

    try:
        old = yaml.safe_load(inner)
    except yaml.YAMLError:
        print(f"  WARN: could not parse YAML, skipping")
        return None
    if not isinstance(old, dict):
        return None

    # Extract known fields
    name = old.get("name", "unknown")
    description = old.get("description", "")
    version = old.get("version", "0.1.0")

    # triggers: from triggers field, or metadata.triggers, or aliases fallback
    triggers = old.get("triggers", None)
    if triggers is None and isinstance(old.get("metadata"), dict):
        triggers = old["metadata"].get("triggers", None)
    if triggers is None:
        triggers = old.get("aliases", [])
    if isinstance(triggers, str):
        triggers = [triggers]
    if not isinstance(triggers, list):
        triggers = []
    # clean: strip, lowercase
    triggers = [t.strip().lower() for t in triggers if isinstance(t, str) and t.strip()]

    # when-to-use
    when = old.get("when-to-use", None)
    if when is None and isinstance(old.get("metadata"), dict):
        when = old["metadata"].get("when_to_use", None)
    if when is None:
        when = old.get("when_to_use", "")
    if isinstance(when, str):
        when = when.strip()
    else:
        when = ""

    # optional
    aliases = old.get("aliases", None)
    if isinstance(aliases, list):
        aliases = [a.strip() for a in aliases if isinstance(a, str) and a.strip()]
    else:
        aliases = None
    license_ = old.get("license", None)
    compat = old.get("compatibility", None)

    # Build new frontmatter as ordered dict
    new = {"name": name, "version": version, "description": description}
    if triggers:
        new["triggers"] = triggers
    else:
        new["triggers"] = [name]
    if when:
        new["when-to-use"] = when
    else:
        new["when-to-use"] = description if isinstance(description, str) else str(description)

    if aliases:
        new["aliases"] = aliases
    if license_:
        new["license"] = license_
    if compat:
        new["compatibility"] = compat

    return new


def main(dry_run: bool = True):
    root = HERE / "skills"
    count = 0
    for skill_file in sorted(root.glob("*/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8")
        # Find frontmatter between first set of ---
        if not text.startswith("---"):
            continue
        # find closing ---
        closing = text.find("---", 3)
        if closing == -1:
            continue
        raw_fm = text[:closing + 3]
        rest = text[closing + 3:]

        new_fm = migrate_frontmatter(raw_fm)
        if new_fm is None:
            print(f"  SKIP {skill_file.relative_to(root)} — could not parse")
            continue

        new_yaml = yaml.dump(new_fm, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120).strip()
        new_text = f"---\n{new_yaml}\n---{rest}"

        if new_text == text:
            continue

        count += 1
        rel = skill_file.relative_to(root)
        print(f"  {'(dry) ' if dry_run else ''}UP   {rel}")
        if not dry_run:
            skill_file.write_text(new_text, encoding="utf-8")

    print(f"\n{'Would migrate' if dry_run else 'Migrated'} {count} skills.")
    return count


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
