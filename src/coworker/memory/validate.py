"""Claude SDK Validation Harness — spec §12.5.

Spawns two Claude agents (baseline vs memory-augmented) running the
same task, then compares results to measure whether cross-session
memory improves agent performance.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def _run_agent(prompt: str, work_dir: str = ".", timeout_sec: int = 600) -> dict:
    """Run a single Claude agent session. Returns result dict."""
    try:
        result = subprocess.run(
            [
                "claude", "agent",
                "--prompt", prompt,
                "--work-dir", work_dir,
                "--timeout", str(timeout_sec),
                "--output-format", "json",
            ],
            capture_output=True, text=True, timeout=timeout_sec + 30,
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                return {
                    "success": True,
                    "output": data.get("result", result.stdout),
                    "tool_calls": data.get("tool_calls", _estimate_tool_calls(result.stdout)),
                }
            except json.JSONDecodeError:
                return {"success": True, "output": result.stdout,
                        "tool_calls": _estimate_tool_calls(result.stdout)}
        return {"success": False, "output": result.stderr, "tool_calls": 0}
    except FileNotFoundError:
        return {"success": False, "output": "Claude CLI not installed", "tool_calls": 0}
    except Exception as exc:
        return {"success": False, "output": str(exc), "tool_calls": 0}


def _estimate_tool_calls(text: str) -> int:
    """Estimate tool call count from agent output."""
    import re
    return len(re.findall(r'"tool"\s*:', text))


def _count_incorrect_assumptions(text: str) -> int:
    """Count incorrect assumptions in transcript."""
    markers = ["incorrect", "wrong", "error", "mistake", "hallucination", "didn't work", "failed"]
    return sum(1 for m in markers if m in text.lower())


def _extract_skill_calls(text: str) -> list[str]:
    """Extract skill names invoked."""
    import re
    skills = set(re.findall(r'Skill["\']?\s*:\s*["\']?([a-z0-9_-]+)', text, re.IGNORECASE))
    return sorted(skills)


def _extract_memory_searches(text: str) -> list[str]:
    """Extract memory search queries."""
    import re
    queries = set(re.findall(r'memory\s+search\s+["\']?(.+?)["\']?(?:\s|$)', text, re.IGNORECASE))
    return sorted(queries)[:5]


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------


def run_validation(task_definition: str, task_file: str | None = None,
                   work_dir: str = ".") -> dict:
    """Run the A/B validation harness.

    Args:
        task_definition: Natural language task description.
        task_file: Optional path to a file containing the task definition.
        work_dir: Working directory for both agents.

    Returns:
        Comparison report dict.
    """
    if task_file:
        try:
            task_definition = Path(task_file).read_text()
        except Exception:
            pass

    logger.info("Running validation: %s", task_definition[:100])
    start = time.time()

    # Agent A: baseline (no memory)
    prompt_a = (
        f"Complete this task: {task_definition}\n\n"
        "IMPORTANT: You have NO access to cross-session memory. "
        "Do NOT use `coworker memory search` or read CLAUDE.local.md. "
        "Use only your current context and tools."
    )
    result_a = _run_agent(prompt_a, work_dir=work_dir)

    # Small delay between agents
    time.sleep(2)

    # Agent B: with memory
    prompt_b = (
        f"Complete this task: {task_definition}\n\n"
        "IMPORTANT: You HAVE access to cross-session memory. "
        "BEFORE starting, run `coworker memory search <relevant query>` to recall past lessons. "
        "Use past experiences to avoid repeating mistakes and speed up your work."
    )
    result_b = _run_agent(prompt_b, work_dir=work_dir)

    elapsed = time.time() - start
    baseline_tc = result_a["tool_calls"]
    memory_tc = result_b["tool_calls"]

    report = {
        "task": task_definition[:200],
        "elapsed_seconds": round(elapsed, 1),
        "baseline": {
            "tool_calls": baseline_tc,
            "output_len": len(result_a["output"]),
            "incorrect_assumptions": _count_incorrect_assumptions(result_a["output"]),
            "success": result_a["success"],
        },
        "with_memory": {
            "tool_calls": memory_tc,
            "output_len": len(result_b["output"]),
            "incorrect_assumptions": _count_incorrect_assumptions(result_b["output"]),
            "skills_invoked": _extract_skill_calls(result_b["output"]),
            "experiences_retrieved": _extract_memory_searches(result_b["output"]),
            "success": result_b["success"],
        },
        "tool_call_reduction": baseline_tc - memory_tc,
        "verdict": "improved" if memory_tc < baseline_tc else "no_change",
    }

    logger.info(
        "Validation complete: baseline=%d tools, memory=%d tools, verdict=%s",
        baseline_tc, memory_tc, report["verdict"],
    )
    return report
