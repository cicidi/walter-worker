"""Normalization shared by every importer, so all sources land in one shape.

Before this, each importer wrote its own form: OpenCode stored local wall-clock
time without an offset, the hooks wrote ``-0800``, Claude JSONL wrote ``Z``.
Sorting those strings mixed sessions from different days, and one project
showed up under both ``walter-worker`` and ``-home-cicidi-project-walter-worker``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

#: OpenCode names its built-in tools in lower case; Claude Code capitalises
#: them. Without this, ``Bash`` and ``bash`` were two rows on every tools chart.
_TOOL_NAMES = {
    "bash": "Bash", "read": "Read", "edit": "Edit", "write": "Write",
    "glob": "Glob", "grep": "Grep", "webfetch": "WebFetch",
    "websearch": "WebSearch", "todowrite": "TodoWrite", "task": "Task",
    "skill": "Skill", "question": "Question",
}


def canonical_tool(name: str) -> str:
    return _TOOL_NAMES.get(name, name) if name else name


def utc_iso(ts) -> str:
    """Any timestamp as ``YYYY-MM-DDTHH:MM:SS.mmmZ`` in UTC, or "".

    Accepts ISO strings (``Z``, ``+08:00``, ``-0800`` or naive) and epoch
    milliseconds. A naive string is taken as local time, which is how the old
    OpenCode importer wrote it.
    """
    if ts is None or ts == "":
        return ""
    try:
        if isinstance(ts, (int, float)) or str(ts).isdigit():
            dt = datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.astimezone()  # naive → local
    except (ValueError, OSError, OverflowError):
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def project_from_cwd(cwd: str, home: Path | None = None) -> str:
    """``~/project/<repo>/sub`` → ``<repo>``; ``~`` → ``home``; else the last
    path component."""
    cwd = (cwd or "").rstrip("/")
    if not cwd:
        return ""
    home_s = str(home or Path.home()).rstrip("/")
    if cwd == home_s:
        return "home"
    if "/project/" in cwd:
        return cwd.split("/project/", 1)[1].split("/")[0]
    return cwd.rsplit("/", 1)[-1]


def project_from_slug(slug: str, home: Path | None = None) -> str:
    """Name a project from a Claude Code transcript folder.

    Claude Code stores transcripts under a folder named after the cwd with
    every "/" turned into "-": ``/home/u/project/repo`` → ``-home-u-project-repo``.
    When no cwd is recorded, that folder name is all there is to go on. Used
    raw, one project appears twice: once as ``repo``, once as the slug.
    """
    slug = slug or ""
    if not slug.startswith("-"):
        return slug  # already a name
    if "-project-" in slug:
        return slug.split("-project-", 1)[1]
    home_slug = "-" + str(home or Path.home()).strip("/").replace("/", "-")
    if slug == home_slug:
        return "home"
    return slug.lstrip("-")


def minutes_between(start: str, end: str) -> int | None:
    try:
        a = datetime.fromisoformat(start.replace("Z", "+00:00"))
        b = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return max(0, int((b - a).total_seconds() // 60))
