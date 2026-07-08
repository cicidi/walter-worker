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

Approach: _(e.g., TDD, direct impl, brainstorming -> spec)_
Testing: _(how this task is tested)_
Recommended skills: _(set during initiative activation — user reviewed)_

## Personal Preferences

_(override project-level defaults here)_
"""

INITIATIVE_PLACEHOLDER = "<!-- INITIATIVE_PLACEHOLDER -->"

_INITIATIVE_ANY_RE = re.compile(
    r"<!--\s*INITIATIVE:\S+\s+START\s*-->.*?"
    r"<!--\s*INITIATIVE:\S+\s+END\s*-->\n?",
    re.DOTALL,
)


def generate_local_claude_md() -> str:
    return LOCAL_CLAUDE_MD_TEMPLATE.strip()


def inject_initiative_into_local_md(content: str, initiative_block: str) -> str:
    """Idempotently inject an initiative block. Removes any existing
    initiative block (consuming its trailing newline), collapses excess
    blank lines only around the removal site."""
    cleaned = _INITIATIVE_ANY_RE.sub("", content)
    # Scoped collapse: replace \n{3,} with \n\n only around the injection point
    if INITIATIVE_PLACEHOLDER in cleaned:
        cleaned = cleaned.replace(
            INITIATIVE_PLACEHOLDER,
            initiative_block.strip() + "\n\n" + INITIATIVE_PLACEHOLDER,
        )
    else:
        cleaned = cleaned.rstrip() + "\n\n" + initiative_block.strip() + "\n"
    return cleaned


def remove_initiative_from_local_md(content: str, name: str) -> str:
    """Remove a specific initiative block. Consumes trailing newline.
    Idempotent: repeated calls produce the same result."""
    escaped = re.escape(name)
    pattern = re.compile(
        r"<!--\s*INITIATIVE:" + escaped + r"\s+START\s*-->.*?"
        r"<!--\s*INITIATIVE:" + escaped + r"\s+END\s*-->\n?",
        re.DOTALL,
    )
    result = pattern.sub("", content)
    return result.rstrip() + "\n"
