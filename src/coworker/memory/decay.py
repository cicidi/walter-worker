"""Passive decay computation for graph edges.

Spec §2: exponential decay on edge effective_weight.
Computed at query time — no daemon, no background process.
Only the queried edges are evaluated.

Decay model boundary (spec §2.1): this exponential decay applies to GRAPH
EDGES only. mem0 memory cards use a DIFFERENT, step-function decay already
implemented in memory/curator.py. The two coexist by design.
"""

from datetime import datetime, timezone, timedelta


# Protection window: no decay for first 20 days after last traversal
PROTECTION_DAYS = 20

# Decay rate: 0.99 per day after protection window
DECAY_RATE = 0.99

# Query filter thresholds (spec §2.2)
STALE_THRESHOLD = 0.5   # below this → flagged stale
SUPPRESS_THRESHOLD = 0.3  # below this → suppressed from results


def compute_effective_weight(
    base_weight: float,
    last_traversed_at: str | None,
    now: datetime | None = None,
) -> float:
    """Compute the decay-adjusted effective_weight of an edge.

    Spec §2.1 formula:
        effective_weight = base_weight   if days_since(last_traversed_at) < 20
                         = base_weight × 0.99^(days - 20)   if days ≥ 20

    Edge cases (spec §2.3):
        - last_traversed_at = None → effective_weight = base_weight (no decay)
        - last_traversed_at in the future → clamp to now(), compute normally
        - base_weight ≤ 0 → treat as 0.2 (WEAK floor)

    Args:
        base_weight: The edge's current base_weight.
        last_traversed_at: ISO timestamp of last traversal, or None.
        now: Current time (injectable for testing). Defaults to utcnow().

    Returns:
        Effective weight as a float in [0.0, 1.0].
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Never-traversed edge: no decay (spec §2.3)
    if last_traversed_at is None:
        return base_weight

    # Floor for zero/negative base_weight (spec §2.3)
    if base_weight <= 0:
        base_weight = 0.2

    # Parse timestamp
    try:
        traversed = datetime.fromisoformat(last_traversed_at)
    except (ValueError, TypeError):
        # Unparseable timestamp → treat as never traversed
        return base_weight

    # Ensure timezone-aware comparison
    if traversed.tzinfo is None:
        traversed = traversed.replace(tzinfo=timezone.utc)

    # Future timestamp → clamp to now (spec §2.3)
    if traversed > now:
        traversed = now

    days_since = (now - traversed).days

    # Within protection window → no decay
    if days_since < PROTECTION_DAYS:
        return base_weight

    # Exponential decay after protection window
    decay_days = days_since - PROTECTION_DAYS
    effective = base_weight * (DECAY_RATE ** decay_days)

    return round(effective, 4)


def query_filter(effective_weight: float) -> str:
    """Classify an edge's effective_weight for query filtering.

    Spec §2.2:
        ≥ 0.5 → "normal" (included in navigation)
        0.3–0.5 → "stale" (returned with flag)
        < 0.3 → "suppressed" (excluded from results)
    """
    if effective_weight >= STALE_THRESHOLD:
        return "normal"
    elif effective_weight >= SUPPRESS_THRESHOLD:
        return "stale"
    else:
        return "suppressed"
