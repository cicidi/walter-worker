#!/usr/bin/env python3
"""Move ~/.coworker/initiatives/ to ~/.coworker/features/.

The initiative->feature rename changed the directory name only: no YAML key
ever mentioned "initiative", so file contents move verbatim. Raw filesystem
moves are used rather than a FeatureConfig load/save round-trip, because the
model does not define every key in the wild (for example `llm_effort`) and a
round-trip would silently drop the ones it does not know.

Dry-run by default; pass --apply to perform the move.

Usage:  python3 scripts/migrate_features.py [--apply]
"""
import argparse
import shutil
import sys
from pathlib import Path

GLOBAL_DIR = Path.home() / ".coworker"
LEGACY = GLOBAL_DIR / "initiatives"
TARGET = GLOBAL_DIR / "features"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--apply",
        action="store_true",
        help="perform the move (default is a dry run)",
    )
    args = ap.parse_args()

    if not LEGACY.exists():
        print(f"nothing to do: {LEGACY} does not exist")
        return 0

    if TARGET.exists():
        print(f"refusing to move: {TARGET} already exists.")
        print("Resolve manually so the two trees are not silently merged.")
        return 1

    entries = sorted(LEGACY.iterdir())
    verb = "MOVING" if args.apply else "WOULD MOVE"
    print(f"{verb} {LEGACY} -> {TARGET}\n")
    for p in entries:
        kind = "dir" if p.is_dir() else "file"
        print(f"  [{kind}] {p.name}")

    if not args.apply:
        print(f"\n{len(entries)} entries. Re-run with --apply to perform the move.")
        return 0

    shutil.move(str(LEGACY), str(TARGET))
    print(f"\nmoved {len(entries)} entries to {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
