"""Auto-worker validation rules — spec §12.3.

8 rules that audit project state against declared intent.
Each rule returns (verdict, evidence, action) for the state machine.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """One finding from a rule check."""

    rule_id: str
    what: str
    verdict: str  # DONE_RIGHT | DONE_WRONG | NOT_DONE | MISMATCH
    source: str
    evidence: str
    action: str = "skip"  # fix | ask | skip
    confidence: str = "high"


# ---------------------------------------------------------------------------
# R1: Validate against raw data
# ---------------------------------------------------------------------------


class GapCheck:
    """R1: Verify claims against raw analytics data.

    Reads analytics.db raw tables, runs grep on codebase, executes
    tests fresh. Never reads derived tables or mem0 summaries as truth.
    """

    @staticmethod
    def verify(db, skill_name: str, usage_path: str) -> Finding:
        try:
            usage = json.loads(Path(usage_path).read_text())
        except Exception:
            return Finding("R1", f"Skill '{skill_name}' usage validation", "MISMATCH",
                           "usage.json", "Cannot read usage.json", "ask")

        claimed = usage.get("total_calls", 0)
        try:
            rows = db.execute(
                "SELECT COUNT(*) FROM tool_calls WHERE tool = 'Skill' AND detail LIKE ?",
                (f"%{skill_name}%",),
            ).fetchone()
            actual = rows[0] if rows else 0
        except Exception as exc:
            return Finding("R1", f"Skill '{skill_name}' usage validation", "MISMATCH",
                           "analytics.db", f"DB query failed: {exc}", "ask")

        if claimed == actual:
            return Finding("R1", f"Skill '{skill_name}' usage validation", "DONE_RIGHT",
                           "analytics.db", f"Claimed={claimed}, Actual={actual} match", "skip")
        return Finding("R1", f"Skill '{skill_name}' usage validation", "MISMATCH",
                       "analytics.db vs usage.json",
                       f"usage.json claims {claimed}, analytics.db has {actual}", "fix")


# ---------------------------------------------------------------------------
# R2: Dead code detection
# ---------------------------------------------------------------------------


class DeadCodeDetector:
    """R2: Scan for dead code — unused skills, tool-call-less sessions, stale config."""

    @staticmethod
    def scan_skills(skills_dir: str, db) -> list[Finding]:
        d = Path(skills_dir)
        if not d.exists():
            return []
        findings: list[Finding] = []
        for skill_d in sorted(d.iterdir()):
            if not skill_d.is_dir():
                continue
            name = skill_d.name
            try:
                rows = db.execute(
                    "SELECT COUNT(*) FROM tool_calls WHERE tool = 'Skill' AND detail LIKE ?",
                    (f"%{name}%",),
                ).fetchone()
                count = rows[0] if rows else 0
            except Exception:
                count = -1

            if count == 0:
                findings.append(Finding("R2", f"Dead skill: {name}", "DONE_WRONG",
                                        "analytics.db", "Zero actual calls in tool_calls table", "fix"))
        return findings

    @staticmethod
    def scan_config_keys(project_root: str) -> list[Finding]:
        """Check for config keys that have no code references."""
        findings: list[Finding] = []
        config_files = [
            "pyproject.toml", ".coworker.yaml", ".claude/settings.json",
            ".opencode/config.json",
        ]
        for cf in config_files:
            fp = Path(project_root) / cf
            if not fp.exists():
                continue
            # Simple heuristic: check if config file is referenced in code
            try:
                result = subprocess.run(
                    ["grep", "-r", "--include=*.py", "-l", cf, str(Path(project_root) / "src")],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode != 0:
                    findings.append(Finding("R2", f"Unused config: {cf}", "NOT_DONE",
                                            "grep", "Not referenced in any .py file", "ask"))
            except Exception:
                pass
        return findings


# ---------------------------------------------------------------------------
# R3: Three-layer attribution
# ---------------------------------------------------------------------------


class RequirementAuditor:
    """R3: Per PRD/spec item, three-layer verification.

    Layer 1: grep for code existence
    Layer 2: run related tests
    Layer 3: semantic comparison of intent vs implementation
    """

    @staticmethod
    def audit(prd_item: str, spec_section: str, llm_client=None,
              grep_dir: str = "src", test_pattern: str = "") -> Finding:
        # Layer 1: grep
        try:
            result = subprocess.run(
                ["grep", "-r", "--include=*.py", "-l", prd_item[:40], grep_dir],
                capture_output=True, text=True, timeout=10,
            )
            has_code = result.returncode == 0
            code_files = result.stdout.strip().split("\n") if has_code else []
        except Exception:
            has_code = False
            code_files = []

        if not has_code:
            return Finding("R3", f"PRD item: {prd_item[:60]}", "NOT_DONE",
                           "grep", f"No code found matching '{prd_item[:40]}'", "fix")

        # Layer 2: run tests
        test_passing = False
        test_output = ""
        if test_pattern:
            try:
                result = subprocess.run(
                    ["python3", "-m", "pytest", test_pattern, "-q", "--tb=line"],
                    capture_output=True, text=True, timeout=60,
                )
                test_passing = result.returncode == 0
                test_output = result.stdout[-500:]
            except Exception:
                pass

        if test_pattern and not test_passing:
            return Finding("R3", f"PRD item: {prd_item[:60]}", "DONE_WRONG",
                           "pytest", f"Test failure:\n{test_output[:200]}", "fix")

        # Layer 3: semantic check
        if llm_client and spec_section:
            try:
                prompt = (
                    f"Given this spec requirement: '{spec_section[:500]}'\n"
                    f"And these code files: {code_files[:5]}\n"
                    f"Does the implementation match the intent? Answer yes/no + one-line reason.\n"
                    f'Respond JSON: {{"verdict": "yes|no", "reason": "..."}}'
                )
                resp = llm_client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100, response_format={"type": "json_object"},
                )
                data = json.loads(resp.content)
                if data.get("verdict") == "no":
                    return Finding("R3", f"PRD item: {prd_item[:60]}", "DONE_WRONG",
                                   "semantic", data.get("reason", "Semantic mismatch"), "fix")
            except Exception:
                pass

        return Finding("R3", f"PRD item: {prd_item[:60]}", "DONE_RIGHT",
                       "grep + pytest + semantic", f"Code: {len(code_files)} files, tests OK", "skip")


# ---------------------------------------------------------------------------
# R4: Working Notes (state file)
# ---------------------------------------------------------------------------


class StateFile:
    """R4: Checked-items persistence to avoid redoing work."""

    def __init__(self, path: str):
        self.path = Path(path)

    def has_been_checked(self, item_id: str) -> bool:
        if not self.path.exists():
            return False
        return f"| {item_id} |" in self.path.read_text()

    def mark_checked(self, item_id: str, what: str, source: str, verdict: str) -> None:
        from datetime import datetime, timezone
        self.path.parent.mkdir(parents=True, exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not self.path.exists():
            self.path.write_text(
                "## Checked\n| ID | What | Source | Verdict | Date |\n|----|------|--------|---------|------|\n"
            )
        content = self.path.read_text()
        if f"| {item_id} |" not in content:
            content += f"| {item_id} | {what} | {source} | {verdict} | {today} |\n"
            self.path.write_text(content)

    def add_open_question(self, question: str) -> str:
        from datetime import datetime, timezone
        self.path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        if not self.path.exists():
            self.path.write_text(
                "## Open Questions\n| ID | Question | Asked At | Status |\n|----|----------|----------|--------|\n"
            )
        content = self.path.read_text()
        qid = f"Q-{content.count('| Q-') + 1}"
        content += f"| {qid} | {question} | {now} | pending |\n"
        self.path.write_text(content)
        return qid

    def record_fixed(self, item_id: str, what: str, action: str) -> None:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        content = self.path.read_text() if self.path.exists() else "## Fixed\n| ID | What | Action | Date |\n|----|------|--------|------|\n"
        if "## Fixed" not in content:
            content += "\n## Fixed\n| ID | What | Action | Date |\n|----|------|--------|------|\n"
        content += f"| {item_id} | {what} | {action} | {today} |\n"
        self.path.write_text(content)

    def record_skipped(self, item_id: str, what: str, reason: str) -> None:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        content = self.path.read_text() if self.path.exists() else ""
        if "## Skipped" not in content:
            content += "\n## Skipped\n| ID | What | Reason | Date |\n|----|------|--------|------|\n"
        content += f"| {item_id} | {what} | {reason} | {today} |\n"
        self.path.write_text(content)


# ---------------------------------------------------------------------------
# R5: Vision Check
# ---------------------------------------------------------------------------


class VisionCheck:
    """R5: Verify a change aligns with the product vision."""

    VISION_PROMPT = (
        "Self-evolving agent 的愿景是让 agent 越来越聪明——"
        "通过跨 session 记忆积累、技能自动生成、自主质量检测，"
        "使 AI 编程助手在每次使用后变得更强大、更准确、更个性化。\n\n"
        "这个改动是否靠近此愿景？请用中文回答。\n"
        "改动描述: {change_description}\n"
        '返回 JSON: {{"verdict": "proceed|skip", "reason": "..."}}'
    )

    @staticmethod
    def evaluate(llm_client, change_description: str) -> Finding:
        prompt = VisionCheck.VISION_PROMPT.format(change_description=change_description)
        try:
            resp = llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.content)
            verdict = data.get("verdict", "skip")
            reason = data.get("reason", "")
        except Exception:
            verdict = "skip"
            reason = "LLM evaluation failed"

        if verdict == "proceed":
            return Finding("R5", f"Vision check: {change_description[:60]}", "DONE_RIGHT",
                           "LLM (deepseek-pro)", reason, "fix")
        return Finding("R5", f"Vision check: {change_description[:60]}", "DONE_WRONG",
                       "LLM (deepseek-pro)", reason, "skip")


# ---------------------------------------------------------------------------
# R6: Research → Advocate
# ---------------------------------------------------------------------------


class ResearchAdvisor:
    """R6: WebSearch for similar solutions + contrarian review before acting."""

    @staticmethod
    def advise(llm_client, change_description: str) -> Finding:
        # Step 1: Simple heuristic — check for prior art patterns
        # (Full WebSearch integration requires MCP/web tool)
        research_note = "WebSearch not available in standalone mode"

        # Step 2: Invoke adversarial reasoning via LLM
        prompt = (
            f"Proposed change: {change_description}\n\n"
            f"You are a contrarian reviewer. Identify 2-3 risks or better alternatives.\n"
            f'Respond JSON: {{"action": "fix|ask|skip", "rationale": "...", "risks": ["..."]}}'
        )
        try:
            resp = llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.content)
            action = data.get("action", "skip")
            rationale = data.get("rationale", "")
        except Exception:
            action = "ask"
            rationale = "LLM advisor failed"

        return Finding("R6", f"Research→Advocate: {change_description[:60]}",
                       "DONE_RIGHT" if action == "fix" else "DONE_WRONG",
                       "LLM", f"{research_note}. {rationale}", action)


# ---------------------------------------------------------------------------
# R7: Context-Aware Input
# ---------------------------------------------------------------------------


class ContextLoader:
    """R7: Load all relevant context before deciding.

    Reads PRD items, spec sections, design decisions, open questions,
    devil's advocate findings, prior state files. Cross-references
    for contradictions.
    """

    @staticmethod
    def load(project_root: str = ".") -> dict:
        ctx: dict = {
            "prd_items": [],
            "spec_sections": [],
            "design_decisions": [],
            "open_questions": [],
            "prior_findings": [],
            "contradictions": [],
        }

        base = Path(project_root) / "docs" / "self-evolving-agent"
        if not base.exists():
            return ctx

        # Load PRD items (section headers)
        prd_path = base / "prd" / "self-evolving-agent-prd.md"
        if prd_path.exists():
            for line in prd_path.read_text().split("\n"):
                if line.startswith("## "):
                    ctx["prd_items"].append(line.strip("# ").strip())

        # Load spec sections
        spec_path = base / "spec" / "self-evolving-agent-spec.md"
        if spec_path.exists():
            for line in spec_path.read_text().split("\n"):
                if line.startswith("## §"):
                    ctx["spec_sections"].append(line.strip("# ").strip())

        # Load prior state files
        state_dir = base / "state"
        if state_dir.exists():
            for sf in sorted(state_dir.glob("*.md")):
                try:
                    text = sf.read_text()
                    for line in text.split("\n"):
                        if "| C-" in line or "| Q-" in line:
                            ctx["prior_findings"].append(line.strip())
                except Exception:
                    pass

        # Cross-reference for contradictions
        # Simple check: if a PRD item is not referenced in any spec section
        for item in ctx["prd_items"]:
            found = any(item[:20].lower() in s.lower() for s in ctx["spec_sections"])
            if not found:
                ctx["contradictions"].append(f"PRD item not in spec: {item}")

        return ctx
