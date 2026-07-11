# src/coworker/templates/local_claude_md.py
import re

LOCAL_CLAUDE_MD_TEMPLATE = """# Personal Working Context

This file is NOT committed to git. Your personal working context for this project.

## Config

- Project Catalog: ~/.coworker/project.yaml

## Project Info

_(auto-discovered by `coworker init`)_

<!-- INITIATIVE_PLACEHOLDER -->

## Reference Docs

_(initiative reference docs appear here when activated)_

## Current Task

Active task: _(none)_
Goal: _(what this task is trying to achieve)_
State: `docs/state/state-{taskname}.md`

## Current Workflow

Approach: _(e.g., TDD, direct impl, brainstorming → spec)_
Testing: _(how this task is tested)_
Skills: _(set during initiative activation)_
"""

INITIATIVE_PLACEHOLDER = "<!-- INITIATIVE_PLACEHOLDER -->"

_INITIATIVE_ANY_RE = re.compile(
    r"<!--\s*INITIATIVE:\S+\s+START\s*-->.*?"
    r"<!--\s*INITIATIVE:\S+\s+END\s*-->\n?",
    re.DOTALL,
)


def generate_local_claude_md() -> str:
    return LOCAL_CLAUDE_MD_TEMPLATE.strip()


def update_project_info(content: str, project_info: dict) -> str:
    lines = []
    if project_info.get("repo_url"):
        lines.append(f"- Repo: {project_info['repo_url']}")
    if project_info.get("language") and project_info["language"] != "unknown":
        lines.append(f"- Language: {project_info['language']}")
    if project_info.get("framework"):
        fw = project_info["framework"] if isinstance(project_info["framework"], str) else ", ".join(project_info["framework"])
        lines.append(f"- Framework: {fw}")
    if project_info.get("deps"):
        deps_show = project_info["deps"][:5]
        deps_str = ", ".join(deps_show)
        if len(project_info["deps"]) > 5:
            deps_str += f" (+{len(project_info['deps']) - 5} more)"
        lines.append(f"- Dependencies: {deps_str}")
    if project_info.get("ides"):
        lines.append(f"- IDEs: {', '.join(project_info['ides'])}")
    if project_info.get("test_command"):
        lines.append(f"- Test: {project_info['test_command']}")
    if project_info.get("lint_command"):
        lines.append(f"- Lint: {project_info['lint_command']}")

    if not project_info.get("repo_url") and not lines:
        return content

    if lines:
        new_section = "## Project Info\n\n" + "\n".join(lines) + "\n"
    else:
        new_section = "## Project Info\n\n_(auto-discovered by `coworker init`)_\n"

    pattern = re.compile(
        r"## Project Info\n.*?(?=\n(?:<!-- INITIATIVE_PLACEHOLDER-->|## ))",
        re.DOTALL,
    )
    if pattern.search(content):
        return pattern.sub(new_section, content)
    else:
        return content.replace(
            "<!-- INITIATIVE_PLACEHOLDER -->",
            new_section + "\n<!-- INITIATIVE_PLACEHOLDER -->",
        )


def inject_initiative_into_local_md(content: str, initiative_block: str) -> str:
    cleaned = _INITIATIVE_ANY_RE.sub("", content)
    if INITIATIVE_PLACEHOLDER in cleaned:
        cleaned = cleaned.replace(
            INITIATIVE_PLACEHOLDER,
            initiative_block.strip() + "\n\n" + INITIATIVE_PLACEHOLDER,
        )
    else:
        cleaned = cleaned.rstrip() + "\n\n" + initiative_block.strip() + "\n"
    return cleaned


def remove_initiative_from_local_md(content: str, name: str) -> str:
    escaped = re.escape(name)
    pattern = re.compile(
        r"<!--\s*INITIATIVE:" + escaped + r"\s+START\s*-->.*?"
        r"<!--\s*INITIATIVE:" + escaped + r"\s+END\s*-->\n?",
        re.DOTALL,
    )
    result = pattern.sub("", content)
    return result.rstrip() + "\n"
