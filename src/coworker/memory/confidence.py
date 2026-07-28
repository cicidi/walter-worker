"""Confidence tier → numeric score mapping.

Single source of truth. Used by BOTH capture merge worker (§4.2) and
Graphify sync (§5.2). Spec requirement: do NOT duplicate this function
under any other name.
"""

from .graph import ConfidenceTier

# Tier rank for comparisons (never compare tier strings lexicographically —
# 'INFERRED' > 'EXTRACTED' and 'WEAK' > 'EXTRACTED' as strings).
TIER_RANK: dict[ConfidenceTier, int] = {
    "EXTRACTED": 4,
    "INFERRED": 3,
    "AMBIGUOUS": 2,
    "WEAK": 1,
}

TIER_SCORE: dict[ConfidenceTier, float] = {
    "EXTRACTED": 0.9,
    "INFERRED": 0.7,
    "AMBIGUOUS": 0.5,
    "WEAK": 0.2,
}


def confidence_to_score(confidence: str) -> float:
    """Map a confidence tier string to its numeric score.

    Unknown/missing → AMBIGUOUS (0.5).

    Spec §1.3: this is the canonical mapper. Both capture merge (§4.2)
    and Graphify sync (§5.2) must call this — do not duplicate.
    """
    return TIER_SCORE.get(confidence, 0.5)


def rank(confidence: str) -> int:
    """Return numeric rank for tier comparison. Higher = more confident."""
    return TIER_RANK.get(confidence, 2)  # unknown → AMBIGUOUS rank
