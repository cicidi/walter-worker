"""Evolution metrics collection — spec §7.

Collects effectiveness and safety metrics to track whether the
agent is actually getting "smarter over time."
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

METRICS_PATH = "~/.coworker/memory/metrics.json"


def _load_metrics() -> dict:
    path = Path(METRICS_PATH).expanduser()
    if not path.exists():
        logger.debug("Metrics file not found at %s; returning defaults. Run 'coworker memory train' to populate.", path)
        return {
            "skill_reuse_rate": [],
            "user_correction_rate": [],
            "task_first_pass_rate": [],
            "memory_hit_rate": [],
            "refusal_rate": [],
            "unsafe_output_rate": [],
            "circuit_breaker_trips": [],
        }
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _save_metrics(data: dict) -> None:
    path = Path(METRICS_PATH).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def record_session_metrics(session_id: str, metrics: dict) -> None:
    """Record per-session evolution metrics.

    Args:
        session_id: Session identifier.
        metrics: Dict with any of: skill_reuse_rate, user_correction_rate,
                 task_first_pass_rate, memory_hit_rate, refusal_rate,
                 unsafe_output_rate, circuit_breaker_trips. These are the
                 spec §7 keys and the fractions compute_evolution_score reads;
                 a name that is not one of them is reported, not dropped.

    The previous docstring named counts instead — skills_reused,
    user_corrections, tasks_completed and six more — none of which exist in
    the store. Values under those names were discarded by the loop below with
    no error, no warning, and no other trace, so a caller who followed the
    documentation recorded nothing and had no way to find out.
    """
    data = _load_metrics()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    recorded = 0
    unknown = []
    for key, value in metrics.items():
        if key not in data:
            unknown.append(key)
            continue
        data[key].append({"ts": ts, "value": value})
        recorded += 1

    if unknown:
        logger.warning(
            "Ignoring %d metric(s) with no storage key: %s. Known keys: %s",
            len(unknown), ", ".join(sorted(unknown)), ", ".join(sorted(data)),
        )

    _save_metrics(data)
    logger.debug("Recorded %d metric(s) for session %s", recorded, session_id)


def compute_evolution_score() -> int:
    """The evolution score, from the same place the dashboard gets it.

    Higher = agent is getting smarter over time.

    This used to be a second implementation with its own formula, reading
    metrics.json — a store nothing ever wrote, so `coworker memory metrics`
    reported 0 for ever while the dashboard reported a real number under the
    same name. Spec §7 settles which is which: "Collection: logged to
    analytics.db per session ... Exact formulas + dashboard -> impl detail, not
    spec." analytics.db is the source, so this delegates rather than keeping a
    parallel sum.
    """
    try:
        from coworker.dashboard.queries_evolution import evolution_inputs, evolution_score
    except Exception:
        return 0
    try:
        skills, sessions_with_auto, total_sessions = evolution_inputs()
    except Exception:
        return 0
    return evolution_score(skills, sessions_with_auto, total_sessions)


def get_metrics_report() -> str:
    """Generate a human-readable metrics report."""
    data = _load_metrics()
    score = compute_evolution_score()

    def latest(key: str) -> str:
        entries = data.get(key, [])
        if not entries:
            return "N/A"
        return f"{entries[-1]['value']:.2f}"

    return (
        f"# Evolution Metrics Report\n"
        f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
        f"**Evolution Score:** {score}/100\n\n"
        f"| Metric | Latest | Trend |\n|--------|--------|-------|\n"
        f"| Skill Reuse Rate | {latest('skill_reuse_rate')} | — |\n"
        f"| Task First-Pass Rate | {latest('task_first_pass_rate')} | — |\n"
        f"| Memory Hit Rate | {latest('memory_hit_rate')} | — |\n"
        f"| User Correction Rate | {latest('user_correction_rate')} | — |\n"
        f"| Refusal Rate | {latest('refusal_rate')} | — |\n"
        f"| Unsafe Output Rate | {latest('unsafe_output_rate')} | — |\n"
        f"| Circuit Breaker Trips | {latest('circuit_breaker_trips')} | — |\n"
    )
