"""Safety gates — spec §6 + §9.

Circuit breaker, sandbox dry-run, and rollback for skill
auto-creation/evolution. Prevents runaway autonomous behavior.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

CIRCUIT_BREAKER_LIMIT = 3  # max skill create/patch per 24h
CIRCUIT_BREAKER_WINDOW_HOURS = 24


def _circuit_state_path() -> Path:
    return Path.home() / ".coworker" / "safety" / "circuit_state.json"


def check_circuit_breaker() -> dict:
    """Check if auto-evolution should be halted.

    Returns {"allowed": bool, "reason": str, "count": int, "resets_at": str}
    """
    path = _circuit_state_path()
    if not path.exists():
        return {"allowed": True, "reason": "", "count": 0, "resets_at": ""}

    try:
        data = json.loads(path.read_text())
    except Exception:
        return {"allowed": True, "reason": "", "count": 0, "resets_at": ""}

    count = data.get("count", 0)
    last_reset = data.get("last_reset", "")
    now = datetime.now(timezone.utc)

    # Check if window has passed — reset if so
    if last_reset:
        try:
            reset_time = datetime.strptime(last_reset, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if now - reset_time > timedelta(hours=CIRCUIT_BREAKER_WINDOW_HOURS):
                data = {"count": 0, "last_reset": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "history": []}
                path.write_text(json.dumps(data, indent=2))
                return {"allowed": True, "reason": "Window reset", "count": 0,
                        "resets_at": (now + timedelta(hours=CIRCUIT_BREAKER_WINDOW_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")}
        except ValueError:
            pass

    if count >= CIRCUIT_BREAKER_LIMIT:
        resets_at = ""
        if last_reset:
            try:
                rt = datetime.strptime(last_reset, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                resets_at = (rt + timedelta(hours=CIRCUIT_BREAKER_WINDOW_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                pass
        return {"allowed": False,
                "reason": f"Circuit breaker: {count}/{CIRCUIT_BREAKER_LIMIT} auto-evolutions in 24h",
                "count": count, "resets_at": resets_at}

    return {"allowed": True, "reason": "", "count": count,
            "resets_at": (now + timedelta(hours=CIRCUIT_BREAKER_WINDOW_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")}


def record_auto_evolution(action: str, skill_name: str = "", detail: str = "") -> bool:
    """Record an auto-evolution action (create/patch).

    Returns True if the action was allowed, False if circuit breaker tripped.
    """
    check = check_circuit_breaker()
    if not check["allowed"]:
        logger.warning("Circuit breaker tripped: %s", check["reason"])
        return False

    path = _circuit_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except Exception:
            data = {"count": 0, "last_reset": now, "history": []}
    else:
        data = {"count": 0, "last_reset": now, "history": []}

    data["count"] = data.get("count", 0) + 1
    data.setdefault("history", []).append({
        "action": action,
        "skill": skill_name,
        "detail": detail,
        "timestamp": now,
    })
    path.write_text(json.dumps(data, indent=2))
    logger.info("Auto-evolution recorded: %s %s (%d/%d)", action, skill_name, data["count"], CIRCUIT_BREAKER_LIMIT)
    return True


def reset_circuit_breaker() -> None:
    """Manually reset the circuit breaker."""
    path = _circuit_state_path()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {"count": 0, "last_reset": now, "history": []}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    logger.info("Circuit breaker reset")
