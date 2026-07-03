# src/coworker/templates/local_claude_md.py
import re

LOCAL_CLAUDE_MD_TEMPLATE = """# Personal Working Context

This file is NOT committed to git. It contains your personal working context for this project.

## Config Paths

- Project Catalog: ~/.coworker/project.yaml

<!-- INITIATIVE_PLACEHOLDER -->

## Reference Docs

_(initiative reference docs appear here when activated)_

## Current Task State

Active task: _(none)_
Goal: _(what this task is trying to achieve)_
State files: `docs/state/state-{taskname}.md` — use a descriptive task name; auto-timestamp if none given

## Current Workflow

Approach: _(e.g., TDD, direct impl, brainstorming → spec)_
Testing: _(how this task is tested)_
Recommended skills: _(set during initiative activation — user reviewed)_

## Personal Preferences

_(override project-level defaults here)_
"""

INITIATIVE_PLACEHOLDER = "<!-- INITIATIVE_PLACEHOLDER -->"


def generate_local_claude_md() -> str:
    """Return the canonical CLAUDE.local.md template."""
    return LOCAL_CLAUDE_MD_TEMPLATE.strip()


def inject_initiative_into_local_md(content: str, initiative_block: str) -> str:
    """Inject an initiative block into local.md content, replacing existing blocks."""
    cleaned = re.sub(
        r"<!-- INITIATIVE:.*? START -->.*?<!-- INITIATIVE:.*? END -->",
        "",
        content,
        flags=re.DOTALL,
    )
    if INITIATIVE_PLACEHOLDER in cleaned:
        return cleaned.replace(
            INITIATIVE_PLACEHOLDER,
            initiative_block.strip() + "\n\n" + INITIATIVE_PLACEHOLDER,
        )
    return cleaned.strip() + "\n\n" + initiative_block.strip()


def remove_initiative_from_local_md(content: str, name: str) -> str:
    """Remove a specific initiative block from local.md content."""
    pattern = (
        r"<!-- INITIATIVE:" + re.escape(name) + r" START -->.*?"
        r"<!-- INITIATIVE:" + re.escape(name) + r" END -->"
    )
    result = re.sub(pattern, "", content, flags=re.DOTALL)
    return re.sub(r"\n{3,}", "\n\n", result)

