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
    for grp in ("analytics", "project", "skill", "initiative"):
        for m in _CMD_NAME_RE.finditer(runner.invoke(main, [grp, "--help"]).output):
            cmds.add(f"{grp} {m.group(1)}")
    return cmds


def test_all_script_skill_refs_resolve_in_cli():
    root = Path(__file__).resolve().parents[2]
    refs = _collect_refs(root)
    assert refs, "No coworker command references found"

    known = _cli_commands()
    known.add("state-update")  # top-level, may appear differently
    known.add("initiative")    # group
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
