"""Reference-integrity test: every 'coworker <cmd>' in setup scripts
must resolve to a CLI command. Guards the G2 class (phantom import-mcp).

Skills are excluded — their prose generates too many false positives;
they're covered by manual review when commands are added/removed.
"""
import re
from pathlib import Path

from click.testing import CliRunner

from coworker.cli import main

_CMD_RE = re.compile(
    r"coworker\s+([a-z][a-z0-9-]*(?:\s+[a-z][a-z0-9-]+){0,2})"
    r"(?=\s|$|--|&&|;|\||[`'\"()])"
)

_CMD_NAME_RE = re.compile(r"^\s{2}([a-z][-a-z0-9]+)\s{2,}", re.MULTILINE)


def _collect_refs(root: Path):
    refs = []
    for src in (root / "setup").glob("*.sh"):
        for i, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
            if re.match(r"^\s*(echo|ok|log|warn|error|#)", line):
                continue
            for m in _CMD_RE.finditer(line):
                cmd = m.group(1).strip()
                if not cmd or cmd in ("state", "watch", "help", "note", "rules", "version"):
                    continue
                refs.append((cmd, f"{src.name}:{i}"))
    return refs


def _cli_commands():
    runner = CliRunner()
    cmds = set()
    for m in _CMD_NAME_RE.finditer(runner.invoke(main, ["--help"]).output):
        cmds.add(m.group(1))
    for grp in ("analytics", "project", "skill", "feature"):
        for m in _CMD_NAME_RE.finditer(runner.invoke(main, [grp, "--help"]).output):
            cmds.add(f"{grp} {m.group(1)}")
    return cmds


def test_all_script_skill_refs_resolve_in_cli():
    root = Path(__file__).resolve().parents[2]
    refs = _collect_refs(root)
    assert refs, "No coworker command references found"

    known = _cli_commands()
    known.add("state-update")  # top-level, may appear differently
    known.add("feature")    # group
    removed = {"import-mcp"}

    missing = []
    for cmd_str, src in refs:
        if cmd_str in removed:
            continue
        if cmd_str in known or cmd_str.split()[0] in known:
            continue
        missing.append(f"  {cmd_str!r}  (from {src})")

    assert not missing, (
        f"Phantom coworker subcommands in setup scripts:\n"
        + "\n".join(missing)
        + f"\n\nKnown ({len(known)}): {sorted(known)}"
    )


_FENCE_RE = re.compile(r"^\s*```")


def _skill_code_commands(skill: Path):
    """Commands inside a skill's fenced code blocks.

    Only fences, not prose: a skill saying "show current coworker config
    status" would otherwise read as an invocation of `coworker config`. The
    blocks are where a skill tells the user to actually run something, and
    where `coworker knowledge summarize` sat for months after the command it
    named had been dropped.
    """
    refs = []
    in_fence = False
    for i, line in enumerate(skill.read_text(encoding="utf-8").splitlines(), 1):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence or line.lstrip().startswith("#"):
            continue
        for m in _CMD_RE.finditer(line):
            refs.append((m.group(1).strip(), f"{skill.parent.name}:{i}"))
    return refs


def test_all_skill_code_refs_resolve_in_cli():
    root = Path(__file__).resolve().parents[2]
    refs = []
    for skill in sorted((root / "skills").glob("*/SKILL.md")):
        refs.extend(_skill_code_commands(skill))
    assert refs, "No coworker command references found in skill code blocks"

    known = _cli_commands()
    known |= {"state-update", "initiative"}  # deprecated alias, still resolves
    removed = {"import-mcp"}

    missing = []
    for cmd_str, src in refs:
        if cmd_str in removed:
            continue
        if cmd_str in known or cmd_str.split()[0] in known:
            continue
        missing.append(f"  {cmd_str!r}  (from {src})")

    assert not missing, (
        "Phantom coworker subcommands in skill code blocks:\n"
        + "\n".join(missing)
        + f"\n\nKnown ({len(known)}): {sorted(known)}"
    )
