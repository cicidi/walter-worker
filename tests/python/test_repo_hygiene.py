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
