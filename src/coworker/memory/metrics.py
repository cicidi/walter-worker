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
        metrics: Dict with any of: skills_reused, user_corrections,
                 tasks_completed, tasks_reworked, memory_searches,
                 memory_hits, unsafe_outputs, refusals, circuit_trips.
    """
    data = _load_metrics()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {"session_id": session_id, "ts": ts, **metrics}

    for key in data:
        if key in metrics:
            data[key].append({"ts": ts, "value": metrics[key]})

    _save_metrics(data)
    logger.debug("Recorded metrics for session %s: %s", session_id,
                 {k: v for k, v in metrics.items()})


def compute_evolution_score() -> int:
    """Compute a 0-100 evolution score from collected metrics.

    Higher = agent is getting smarter over time.
    """
    data = _load_metrics()

    def recent_trend(key: str) -> float:
        values = [e["value"] for e in data.get(key, [])[-10:]]
        if not values:
            return 0.0
        return sum(values) / len(values)

    reuse = recent_trend("skill_reuse_rate")
    first_pass = recent_trend("task_first_pass_rate")
    memory_hit = recent_trend("memory_hit_rate")
    correction = recent_trend("user_correction_rate")
    trips = sum(e["value"] for e in data.get("circuit_breaker_trips", [])[-30:])

    # Weighted score
    score = (
        reuse * 30 +
        first_pass * 25 +
        memory_hit * 25 +
        (1.0 - correction) * 15 +
        (1.0 if trips == 0 else 0.0) * 5
    )
    return max(0, min(100, int(score)))


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
