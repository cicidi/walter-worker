# src/coworker/templates/local_claude_md.py
import re

LOCAL_CLAUDE_MD_TEMPLATE = """# Personal Working Context

This file is NOT committed to git. Your personal working context for this project.

## Config

- Project Catalog: ~/.coworker/project.yaml

## Project Info

_(auto-discovered by `coworker init`)_

<!-- FEATURE_PLACEHOLDER -->

## Reference Docs

_(feature reference docs appear here when activated)_

## Principles

_(project-specific principles — add yours here)_

## Current Task

Active task: _(none)_
Goal: _(what this task is trying to achieve)_
State: `docs/state/state-{taskname}.md`
Docs convention: `docs/<feature>/{prd,plan,spec}/`

## Current Workflow

Approach: _(e.g., TDD, direct impl, brainstorming → spec)_
Testing: _(how this task is tested)_
Skills: _(set during feature activation)_
"""

FEATURE_PLACEHOLDER = "<!-- FEATURE_PLACEHOLDER -->"
# Written before the initiative→feature rename. Still read so an existing
# CLAUDE.local.md keeps working, and upgraded on its next write.
LEGACY_FEATURE_PLACEHOLDER = "<!-- INITIATIVE_PLACEHOLDER -->"

# Marker dialect: FEATURE is what we write, INITIATIVE is what older files carry.
# Shared with the Claude adapter so both agree on what counts as a block.
MARKER_DIALECT = r"(?:FEATURE|INITIATIVE)"

_FEATURE_ANY_RE = re.compile(
    rf"<!--\s*{MARKER_DIALECT}:\S+\s+START\s*-->.*?"
    rf"<!--\s*{MARKER_DIALECT}:\S+\s+END\s*-->\n?",
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
        rf"## Project Info\n.*?(?=\n(?:<!--\s*{MARKER_DIALECT}_PLACEHOLDER\s*-->|## ))",
        re.DOTALL,
    )
    if pattern.search(content):
        return pattern.sub(new_section, content)
    for placeholder in (FEATURE_PLACEHOLDER, LEGACY_FEATURE_PLACEHOLDER):
        if placeholder in content:
            return content.replace(
                placeholder, new_section + "\n" + FEATURE_PLACEHOLDER
            )
    return content


def inject_feature_into_local_md(content: str, feature_block: str) -> str:
    cleaned = _FEATURE_ANY_RE.sub("", content)
    # A legacy placeholder is replaced and upgraded to the current spelling.
    for placeholder in (FEATURE_PLACEHOLDER, LEGACY_FEATURE_PLACEHOLDER):
        if placeholder in cleaned:
            return cleaned.replace(
                placeholder,
                feature_block.strip() + "\n\n" + FEATURE_PLACEHOLDER,
            )
    return cleaned.rstrip() + "\n\n" + feature_block.strip() + "\n"


def remove_feature_from_local_md(content: str, name: str) -> str:
    escaped = re.escape(name)
    pattern = re.compile(
        rf"<!--\s*{MARKER_DIALECT}:" + escaped + r"\s+START\s*-->.*?"
        rf"<!--\s*{MARKER_DIALECT}:" + escaped + r"\s+END\s*-->\n?",
        re.DOTALL,
    )
    result = pattern.sub("", content)
    return result.rstrip() + "\n"
