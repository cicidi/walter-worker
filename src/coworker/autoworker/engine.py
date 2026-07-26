"""Auto-worker loop engine — spec §12.

Spawns Claude Code SDK sessions as autonomous agents. The agent
uses its full tool suite (Grep, Bash, Read, Edit, WebSearch, etc.)
to investigate issues, decide fixes, and self-improve.

This is NOT a deterministic script. It spawns an LLM agent that
reasons about what to do and takes action.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Claude SDK agent spawn
# ---------------------------------------------------------------------------


def _spawn_agent(prompt: str, work_dir: str = ".", timeout_sec: int = 300) -> dict:
    """Spawn a Claude Code agent session to perform a task.

    Uses `claude` CLI in SDK mode (pip install @anthropic-ai/claude-code).
    Falls back to using the LLMClient directly if CLI unavailable.

    Returns {"success": bool, "output": str, "tool_calls": int}
    """
    # Try Claude Code CLI first
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
                return {"success": True, "output": data.get("result", result.stdout),
                        "tool_calls": data.get("tool_calls", 0)}
            except json.JSONDecodeError:
                return {"success": True, "output": result.stdout, "tool_calls": 0}
        return {"success": False, "output": result.stderr, "tool_calls": 0}
    except FileNotFoundError:
        pass  # Claude CLI not installed, fall back
    except Exception:
        pass

    # Fallback: use LLMClient directly (limited — no tool calling)
    try:
        from coworker.memory.llm import LLMClient
        llm = LLMClient()
        resp = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        return {"success": True, "output": resp.content, "tool_calls": 0}
    except Exception as exc:
        return {"success": False, "output": str(exc), "tool_calls": 0}


# ---------------------------------------------------------------------------
# Auto-worker agent implementation
# ---------------------------------------------------------------------------


class AutoWorkerAgent:
    """Spawns Claude SDK agents to run the auto-worker loop.

    Each iteration is a fresh Claude agent session with the auto-worker
    skill loaded as context. The agent reads state files, investigates
    gaps, and takes action — just like a human engineer would.
    """

    def __init__(
        self,
        mem0_client=None,
        db=None,
        project: str = "ai-coworker",
        state_dir: str = "docs/self-evolving-agent/state",
        work_dir: str = ".",
    ):
        self.mem0 = mem0_client
        self.db = db
        self.project = project
        self.state_dir = Path(state_dir)
        self.work_dir = work_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _inject_wrong_history(self) -> None:
        """Inject wrong-history prevention rules into CLAUDE.local.md."""
        try:
            from coworker.memory.wrong_history import extract_rules, inject_into_local_md, build_snapshot
            rules = extract_rules()
            critical = [r for r in rules if r["severity"] == "critical"]
            if critical:
                import os
                local_md = os.path.expanduser("~/CLAUDE.local.md")
                snapshot = build_snapshot()
                inject_into_local_md(local_md, snapshot)
                logger.info("Injected %d critical wrong-history rules into CLAUDE.local.md", len(critical))
            else:
                logger.debug("No critical wrong-history rules to inject")
        except Exception as exc:
            logger.warning("Wrong-history injection failed: %s", exc)

    # ------------------------------------------------------------------
    # Agent execution
    # ------------------------------------------------------------------

    def run(self, max_hours: int = 12, task: str | None = None) -> dict:
        """Run the auto-worker as a series of Claude agent sessions.

        Each round spawns one agent. Between rounds, state files are
        updated so the next agent picks up where the last left off.
        """
        start = time.time()
        deadline = start + (max_hours * 3600)
        round_num = 0
        total_fixed = total_asked = 0
        session_log: list[dict] = []

        # Inject wrong-history rules into Claude context BEFORE anything else
        self._inject_wrong_history()

        # Build the initial agent prompt from context
        base_prompt = self._build_base_prompt(task)

        while time.time() < deadline:
            round_num += 1
            logger.info("=== Agent round %d ===", round_num)

            # Check what was done in prior rounds
            prior_context = self._read_prior_state()

            # Build round-specific prompt
            if round_num == 1:
                prompt = base_prompt + "\n\n" + prior_context + "\n\nBegin your investigation. Use grep, Read, and Bash to explore the codebase. Identify gaps and fix them."
            else:
                prompt = (
                    f"Round {round_num} of the auto-worker loop.\n\n"
                    f"Here is what was done in previous rounds:\n{prior_context}\n\n"
                    f"Continue investigating remaining gaps. "
                    f"Use tools to explore, analyze, and fix. "
                    f"Focus on items not yet checked."
                )

            # Spawn the agent
            result = _spawn_agent(prompt, work_dir=self.work_dir, timeout_sec=600)
            session_log.append({"round": round_num, "success": result["success"],
                                "output_len": len(result["output"])})

            if result["success"]:
                # Extract what the agent did
                self._process_agent_output(result["output"], round_num)
                # Count fixes from output
                if "fixed" in result["output"].lower() or "DONE_RIGHT" in result["output"]:
                    total_fixed += 1

            # Check for stall
            if round_num >= 50:
                logger.info("Max rounds (50) reached")
                break

            # Sleep between rounds (agent needs time to think)
            remaining = deadline - time.time()
            if remaining > 60:
                time.sleep(60)

        # Generate summary
        self._write_summary(round_num, total_fixed, total_asked, start)
        elapsed = (time.time() - start) / 60
        return {
            "rounds": round_num,
            "fixed": total_fixed,
            "asked": total_asked,
            "session_log": session_log,
            "elapsed_minutes": round(elapsed, 1),
        }

    def _build_base_prompt(self, task: str | None = None) -> str:
        """Build the initial agent prompt with full context."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        lines = [
            "You are the ai-coworker Auto-Worker — an autonomous QA agent.",
            f"Project: {self.project}",
            f"Date: {today}",
            "",
            "## Your Mission",
            "",
            "Audit the project against its declared intent (specs, PRD, design docs).",
            "Find gaps between what was promised and what was built.",
            "Fix what you can. Ask about what you cannot. Skip what is intentional.",
            "",
            "## Rules (guidelines, not hardcoded checks)",
            "",
            "1. Verify claims against raw data — check analytics.db, run grep, execute tests.",
            "2. Find dead code — unused skills, stale config, dead branches.",
            "3. Three-layer audit — grep for code → run tests → semantic comparison.",
            "4. Use state files — don't redo work. Check what was already done.",
            "5. Vision check — does each change move toward a smarter agent?",
            "6. Research before acting — search for similar solutions, consider alternatives.",
            "7. Load all context — read PRD, spec, design docs, prior state files.",
            "8. Ask, don't block — if unsure, ask the user (log to state file + notify).",
            "",
            "## Available Tools",
            "",
            "- `coworker memory search <query>` — search cross-session memory",
            "- `coworker memory refresh` — refresh CLAUDE.local.md snapshot",
            "- `python3 -m pytest tests/ -v` — run tests",
            "- grep, find, git log — code exploration",
            "- Read file, Edit file — code changes",
            "",
            "## Current State",
            f"State directory: {self.state_dir}",
            f"Check files matching: auto-worker-{today}-state.md",
            "",
            "## How to Report",
            "",
            "After investigating, write findings to the state file:",
            "- DONE_RIGHT: item is implemented correctly",
            "- DONE_WRONG: implemented but incorrect → try to fix",
            "- NOT_DONE: not implemented → implement or ask for help",
            "- MISMATCH: data mismatch → fix the data",
            "",
            "IMPORTANT: Use your tools. grep the code. Run tests. Read files.",
            "Do not just think — act. Fix real problems. Generate real code.",
        ]

        if task:
            lines.insert(3, f"**Specific task:** {task}")
            lines.insert(4, "")

        return "\n".join(lines)

    def _read_prior_state(self) -> str:
        """Read prior state files to give the agent context."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state_path = self.state_dir / f"auto-worker-{today}-state.md"

        if state_path.exists():
            content = state_path.read_text()
            # Summarize for prompt
            checked = []
            open_qs = []
            for line in content.split("\n"):
                if "| C-" in line:
                    checked.append(line.strip())
                elif "| Q-" in line:
                    open_qs.append(line.strip())

            return (
                f"Prior state file exists ({len(checked)} checked, {len(open_qs)} open questions).\n"
                f"State file: {state_path}\n"
                f"Read it for full details before starting new work.\n"
                f"Open questions needing answers: {len([q for q in open_qs if 'pending' in q])}"
            )

        return "No prior state file for today. This is the first round."

    def _process_agent_output(self, output: str, round_num: int) -> None:
        """Extract findings from agent output and update state file."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state_path = self.state_dir / f"auto-worker-{today}-state.md"

        # Append a round summary
        summary = (
            f"\n## Round {round_num} Agent Output\n\n"
            f"```\n{output[:5000]}\n```\n"
        )

        if state_path.exists():
            content = state_path.read_text()
            if f"## Round {round_num}" not in content:
                state_path.write_text(content + summary)
        else:
            state_path.write_text(
                f"# Auto-Worker Run State\n\n"
                f"**Started:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
                f"**Status:** in_progress\n\n"
                + summary
            )

    def _write_summary(self, rounds: int, fixed: int, asked: int, start: float) -> None:
        """Write final summary to state file."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state_path = self.state_dir / f"auto-worker-{today}-state.md"
        elapsed = (time.time() - start) / 60

        summary = (
            f"\n## Summary\n\n"
            f"- **Rounds:** {rounds}\n"
            f"- **Fixed:** {fixed}\n"
            f"- **Asked:** {asked}\n"
            f"- **Elapsed:** {elapsed:.1f} min\n"
            f"- **Completed:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
        )

        if state_path.exists():
            content = state_path.read_text()
            content = content.replace("in_progress", "completed")
            state_path.write_text(content + summary)
        else:
            state_path.write_text(f"# Auto-Worker Run State\n\n**Status:** completed\n\n{summary}")


# ---------------------------------------------------------------------------
# Validation harness — spec §12.5
# ---------------------------------------------------------------------------


def run_validation_harness(task_definition: str, task_file: str | None = None) -> dict:
    """Run A/B comparison of baseline vs memory-augmented agent.

    Spec §12.5: Spawns Agent A (no mem0) and Agent B (with mem0),
    compares results to measure whether memory improves performance.
    """
    if task_file:
        try:
            task_definition = Path(task_file).read_text()
        except Exception:
            pass

    logger.info("Running validation harness for task: %s", task_definition[:100])

    # Agent A: no memory
    prompt_a = (
        f"Complete this task: {task_definition}\n\n"
        "You have NO access to cross-session memory. Use only your current context."
    )
    result_a = _spawn_agent(prompt_a)

    # Agent B: with memory
    prompt_b = (
        f"Complete this task: {task_definition}\n\n"
        "You HAVE access to cross-session memory via `coworker memory search`.\n"
        "Before starting, run `coworker memory search <relevant query>` to recall past lessons.\n"
        "Use past experiences to avoid repeating mistakes."
    )
    result_b = _spawn_agent(prompt_b)

    return {
        "task": task_definition[:200],
        "baseline": {"success": result_a["success"], "tool_calls": result_a["tool_calls"],
                     "output_len": len(result_a["output"])},
        "with_memory": {"success": result_b["success"], "tool_calls": result_b["tool_calls"],
                        "output_len": len(result_b["output"])},
        "verdict": "improved" if result_b["tool_calls"] < result_a["tool_calls"] else "no_change",
    }


# ---------------------------------------------------------------------------
# CLI entry point (backward-compatible)
# ---------------------------------------------------------------------------


def run_autoworker_loop(
    mem0_client=None,
    llm_client=None,
    db=None,
    max_hours: int = 12,
    project: str = "ai-coworker",
    state_dir: str | None = None,
    task: str | None = None,
) -> dict:
    """Run the auto-worker loop as Claude SDK agents — spec §12.1.

    Spawns one agent per round. Each agent has full tool access
    (grep, bash, read, edit) and autonomously investigates and fixes.
    """
    sd = state_dir or "docs/self-evolving-agent/state"
    agent = AutoWorkerAgent(
        mem0_client=mem0_client,
        db=db,
        project=project,
        state_dir=sd,
    )
    return agent.run(max_hours=max_hours, task=task)
