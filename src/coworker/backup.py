"""Backup layer — the mechanical safety net for every user-file mutation.

snapshot(paths, label) copies files/dirs into ~/.coworker/backups/<ts>-<label>/
mirroring their absolute paths, so restore() knows exactly where they go back.
Modeled on the intuit port's setup/lib/backup.py; stdlib only.
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

BACKUP_ROOT = Path.home() / ".coworker" / "backups"


def _safe_label(label: str) -> str:
    label = (label or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", label):
        raise ValueError(f"Invalid backup label (use [A-Za-z0-9_.-]): {label!r}")
    return label


def _mirror(p: Path) -> Path:
    """Absolute path -> its in-backup mirror (drop leading '/')."""
    return Path(str(p.resolve()).lstrip("/"))


def snapshot(paths, label: str) -> Path:
    """Copy each existing path into a fresh timestamped backup dir.

    Nonexistent paths are skipped silently (snapshot what IS there).
    Returns the backup directory; prints a restore hint.
    """
    label = _safe_label(label or "snapshot")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_ROOT / f"{ts}-{label}"
    dest.mkdir(parents=True, exist_ok=True)

    n = 0
    for p in paths:
        p = Path(p).expanduser()
        if not p.exists():
            continue
        target = dest / _mirror(p)
        target.parent.mkdir(parents=True, exist_ok=True)
        if p.is_dir():
            shutil.copytree(p, target, dirs_exist_ok=True)
        else:
            shutil.copy2(p, target)
        n += 1

    hint = f"backup: {n} path(s) -> {dest}  (restore: backup.restore({str(dest)!r}))"
    print(hint)
    return dest


def restore(backup_dir) -> list[Path]:
    """Restore every file under backup_dir to its mirrored absolute path.

    Accepts either an absolute backup dir path or a bare label (newest match).
    Returns the list of restored paths.
    """
    bd = Path(backup_dir).expanduser()
    if not bd.is_absolute() and not bd.exists():
        # bare label: pick newest matching *-<label>
        matches = sorted(BACKUP_ROOT.glob(f"*-{bd}"))
        if not matches:
            raise FileNotFoundError(f"No backup matching label {bd!r} under {BACKUP_ROOT}")
        bd = matches[-1]
    if not bd.is_dir():
        raise FileNotFoundError(f"Backup dir not found: {bd}")

    restored: list[Path] = []
    for f in bd.rglob("*"):
        if f.is_dir():
            continue
        # mirror back: prepend '/' to the path relative to the backup dir
        orig = Path("/") / f.relative_to(bd)
        orig.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, orig)
        restored.append(orig)

    print(f"restore: {len(restored)} path(s) from {bd}")
    return restored
