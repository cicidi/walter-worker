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

    # A runnable command, not an internal function name. The old hint told
    # users to call backup.restore(...) from a Python prompt, and there was no
    # CLI entry point for it at all.
    hint = f"backup: {n} path(s) -> {dest}  (restore: coworker restore {dest.name})"
    print(hint)

    # Self-maintaining: every snapshot trims what has accumulated, so the
    # directory stays bounded without anyone remembering to run a cleanup.
    # The directory just written is the newest of its label and is kept.
    dropped = prune()
    if dropped:
        print(f"  pruned {len(dropped)} older backup(s)")

    return dest


#: Timestamped backups kept per label. Only labels that exceed this are
#: trimmed, so a deliberate one-off snapshot survives however many runs happen.
KEEP_PER_LABEL = 20


def prune(keep_per_label: int = KEEP_PER_LABEL) -> list[Path]:
    """Delete older timestamped backups, keeping the newest per label.

    Nothing pruned this directory, so it grew without bound: 1623 directories
    and 137MB on the development machine, 894 of them `json-sync` and 714
    `upgrade` — one per changed write, over months. The rest are deliberate
    snapshots with one or two directories each.

    A label with no more than `keep_per_label` directories is left entirely
    alone, which is what separates the two: mechanical churn accumulates and
    gets trimmed, a considered snapshot does not. `pristine`, which uninstall
    restores from, carries no timestamp and is never a candidate.
    """
    if not BACKUP_ROOT.is_dir():
        return []

    by_label: dict[str, list[Path]] = {}
    for entry in BACKUP_ROOT.iterdir():
        m = re.match(r"^\d{8}-\d{6}-(.+)$", entry.name)
        if m and entry.is_dir():
            by_label.setdefault(m.group(1), []).append(entry)

    removed: list[Path] = []
    for dirs in by_label.values():
        if len(dirs) <= keep_per_label:
            continue
        for old in sorted(dirs, key=lambda p: p.name)[:-keep_per_label]:
            try:
                shutil.rmtree(old)
                removed.append(old)
            except OSError:
                pass  # in use or permission issue — leave it
    return removed


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
