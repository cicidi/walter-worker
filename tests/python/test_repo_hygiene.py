"""Repository hygiene: scratch stays out of the published tree.

The doc standard (doc-organize, Mode C) says `raw/` content — research
dumps, discussion logs, generated renderings — belongs in gitignored
scratch, or is deleted once it has no continuing value. It is not part of
the six committed doc types.

It had drifted back in: docs/features/*/raw/ held 4.2 MB across 166 tracked
files, including demo-html/ (generated renderings, one file 2.99 MB) and
html-ppt/ (a vendored third-party slide toolkit with no LICENSE or README).
On a public repo that is bloat at best and a licence question at worst. The
files are still on disk as scratch; they are simply no longer shipped.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def test_no_tracked_file_lives_under_a_raw_directory():
    offenders = [f for f in _tracked_files() if "/raw/" in f or f.startswith("raw/")]
    assert offenders == [], (
        "docs/**/raw/ is gitignored scratch and must not be tracked "
        f"({len(offenders)} offending files, e.g. {offenders[:5]})"
    )


def test_raw_scratch_is_gitignored():
    # Untracking alone is not enough: the next `git add -A` would put it
    # straight back. The ignore rule is what keeps it out.
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "docs/features/some-feature/raw/notes.md"],
        cwd=ROOT,
    )
    assert ignored.returncode == 0, "docs/features/*/raw/ must be gitignored"


def test_no_source_file_points_at_the_pre_migration_docs_layout():
    """`docs/<feature>/` became `docs/features/<feature>/`.

    Seven references survived that move, and they fail silently rather than
    loudly: the wrong-history directory, the auto-worker's state dir, and both
    scan paths in `find-issues` all named a directory that no longer exists.
    """
    offenders = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "docs/self-evolving-agent" in line:
                offenders.append(f"{path.relative_to(ROOT)}:{i}")
    assert offenders == [], (
        "source files still name the pre-migration docs layout "
        f"(docs/self-evolving-agent/): {offenders}"
    )


def test_wrong_history_default_dir_holds_the_real_entries():
    """WH_DIR named a directory that does not exist.

    Every read found nothing, so wrong-history looked empty while its entries
    sat under docs/features/. Worse, `index` does mkdir(parents=True) on the
    path — it would have created the phantom directory and written an INDEX
    there, leaving the real one stale.
    """
    from coworker.memory import wrong_history

    base = ROOT / wrong_history.WH_DIR
    assert base.is_dir(), f"WH_DIR {wrong_history.WH_DIR!r} does not exist"
    assert (base / "entries").is_dir(), "wrong-history entries/ is not there"


_DEAD_SUPERLAB_PATHS = (
    "project/skill-factory",
    "skills/skill-factory",
    "SKILL_FACTORY_DIR",
    "walter-worker-skills",
)


def test_no_shipped_skill_names_the_renamed_repo_as_a_path():
    """skill-factory was renamed to the-super-lab.

    The upgrade skill still told the agent to pull from ~/project/skill-factory
    and from $SKILL_FACTORY_DIR, and to scan a `walter-worker-skills/` that has
    never existed — the real ones are `skills/` and `personal-skills/`. Three
    dead paths in a workflow the global CLAUDE.md template sends users to, so
    the upgrade would silently pull nothing.

    Verified against the filesystem, not inferred: ~/project/skill-factory and
    ~/.config/opencode/skills/skill-factory are both absent, the-super-lab and
    its two subdirectories are both present, and setup/install.sh indexes
    exactly those.
    """
    offenders = []
    for path in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            for dead in _DEAD_SUPERLAB_PATHS:
                if dead in line:
                    offenders.append(f"{path.parent.name}:{i} names {dead!r}")
    assert offenders == [], f"dead super-lab paths in shipped skills: {offenders}"


def test_no_bash_substitution_inside_python3_c_blocks():
    """`python3 -c "…"` is a double-quoted bash string.

    Three regressions came out of that one block in install.sh: a backtick pair
    executed the coworker CLI and pasted its usage text into the middle of the
    Python, so no hooks were written at all while the installer still reported
    success. A double quote there is worse than it looks — it ends the string,
    so everything after it is parsed as bash.

    The block ends only at a line whose first non-space character is the closing
    quote. A quote anywhere else is therefore an offender, not a terminator:
    treating it as one is what let a stray quote hide the rest of the block from
    this check.
    """
    offenders = []
    for path in sorted((ROOT / "setup").glob("*.sh")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            marker = 'python3 -c "'
            if marker not in line:
                continue
            rest = line.split(marker, 1)[1]
            if '"' in rest:
                # A one-liner closes on the same line; nothing later belongs.
                body = [(i, rest.split('"', 1)[0])]
            else:
                body = [(i, rest)]
                for j, later in enumerate(lines[i + 1:], i + 1):
                    if later.lstrip().startswith('"'):
                        break
                    body.append((j, later))
            for lineno, text in body:
                for bad, why in (('"', "ends the bash string early"),
                                 ("`", "is a command substitution"),
                                 ("$(", "is a command substitution")):
                    if bad in text:
                        offenders.append(
                            f"{path.name}:{lineno + 1} contains {bad!r} "
                            f"({why}): {text.strip()[:60]}"
                        )
    assert offenders == [], (
        "bash-active characters inside python3 -c blocks:\n  "
        + "\n  ".join(offenders)
    )
