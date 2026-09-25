#!/usr/bin/env python3
"""G12: Correction detector hook script (runs on UserPromptSubmit).

Reads a Claude Code hook JSON payload from stdin, inspects data.prompt,
and decides whether the user's message indicates a correction. Writes a
trace file with status:draft if it does — the self-heal skill then picks
it up and instructs the AI to either fill in the detail or delete the
file as a false positive.

Precision guards:
- Confidence-weighted patterns (high-weight phrases contribute more).
- Skips slash-commands, one-word prompts, and very long prompts
  unless a high-confidence pattern matches.
- Minimum confidence threshold before writing a trace.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

TRACES_DIR = Path.home() / ".coworker" / "analytics" / "traces"

# (pattern, weight). Higher weight = more likely a real correction.
_PATTERNS: list[tuple[str, float]] = [
    (r"\byou should have\b", 1.0),
    (r"\bwhy didn'?t you\b", 1.0),
    (r"\bi told you\b", 1.0),
    (r"\bnot like that\b", 0.9),
    (r"\bthat'?s wrong\b", 0.9),
    (r"\bdon'?t do that\b", 0.9),
    (r"\bno\W.*that'?s\b", 0.7),
    (r"\bwrong\b", 0.5),
    (r"\bstop\b", 0.3),
    (r"\bno\b", 0.2),
]

_SLASH_CMD_RE = re.compile(r"\A\s*/")
_ONE_WORD_RE = re.compile(r"\A\S+\Z")


def _parse_hook() -> dict | None:
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _score(prompt: str) -> float:
    prompt_lower = prompt.lower()
    score = 0.0
    for pat, weight in _PATTERNS:
        if re.search(pat, prompt_lower):
            score += weight
    return score


def main() -> None:
    payload = _parse_hook()
    if payload is None:
        sys.exit(0)

    prompt = payload.get("data", {}).get("prompt", "")
    if not prompt.strip():
        sys.exit(0)

    # Skip slash commands and one-word prompts
    if _SLASH_CMD_RE.search(prompt) or _ONE_WORD_RE.match(prompt.strip()):
        sys.exit(0)

    # Long prompts (>300 chars) need high confidence
    score = _score(prompt)
    threshold = 0.9 if len(prompt) > 300 else 0.8
    if score < threshold:
        sys.exit(0)

    # Write trace
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    trace = TRACES_DIR / f"correction-{ts}.md"
    trace.write_text(
        f"---\n"
        f"status: draft\n"
        f"score: {score:.2f}\n"
        f"date: {datetime.now().isoformat()}\n"
        f"---\n\n"
        f"## Detected Correction\n\n"
        f"**User prompt:** {prompt[:200]}\n\n"
        f"_(This file is a draft. If this is a real correction, fill in the"
        f" details below. If it was a false positive, delete this file.)_\n\n"
        f"## What was wrong\n\n\n"
        f"## Expected behavior\n\n\n"
        f"## Fix applied\n",
        encoding="utf-8",
    )
    print(f"correction trace written: {trace}")


if __name__ == "__main__":
    main()
