"""Auto-worker QA and loop commands for the Coworker CLI."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


def register_autoworker(main_group: click.Group) -> None:
    """Register find-issues group and run command on the main CLI group."""

    # -----------------------------------------------------------------------
    # find-issues — QA inspector
    # -----------------------------------------------------------------------

    @main_group.group()
    def find_issues():
        """QA inspector — find gaps between PRD/spec and implementation."""
        pass

    @find_issues.command("run")
    @click.option("--project", default="ai-coworker", help="Target project")
    @click.option(
        "--phases",
        default="all",
        help="Comma-separated phases: prd,spec,web,code,all",
    )
    @click.option(
        "--output", default=None, help="Output file path (default: auto-generated)"
    )
    def find_issues_run(project, phases, output):
        """Run a full QA inspection and write findings."""
        import os
        from datetime import datetime, timezone

        from .memory.wrong_history import extract_rules

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = (
            output
            or f"docs/self-evolving-agent/state/issues-found-{today}-auto.md"
        )
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        console.print("[bold]Find-Issues — QA inspection[/bold]")
        console.print(f"  Project: {project}")
        console.print(f"  Phases: {phases}")
        console.print(f"  Output: {out_path}")

        findings = []
        phases_list = [p.strip() for p in phases.split(",")]

        if "all" in phases_list or "prd" in phases_list:
            prd_path = "docs/self-evolving-agent/prd/self-evolving-agent-prd.md"
            if os.path.exists(prd_path):
                lines = open(prd_path).readlines()
                reqs = [
                    l
                    for l in lines
                    if l.strip().startswith("- R") or "R1" in l or "R2" in l
                ]
                findings.append(
                    f"## PRD Scan: {len(reqs)} requirement references found in {prd_path}"
                )
            else:
                findings.append(f"## PRD Scan: {prd_path} not found")

        if "all" in phases_list or "spec" in phases_list:
            spec_path = "docs/self-evolving-agent/spec/self-evolving-agent-spec.md"
            if os.path.exists(spec_path):
                sections = [
                    l for l in open(spec_path).readlines() if l.startswith("## §")
                ]
                findings.append(
                    f"## Spec Scan: {len(sections)} sections in {spec_path}"
                )
            else:
                findings.append(f"## Spec Scan: {spec_path} not found")

        if "all" in phases_list or "web" in phases_list:
            findings.append(
                "## Web Research: Use WebSearch tool interactively for best practices"
            )
            findings.append(
                "  (WebSearch requires interactive Claude session)"
            )

        if "all" in phases_list or "code" in phases_list:
            import subprocess

            r = subprocess.run(
                ["python3", "-m", "pytest", "tests/python/", "-q", "--tb=no"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            test_status = "PASS" if r.returncode == 0 else "FAIL"
            findings.append(f"## Code Audit: Tests {test_status}")
            r = subprocess.run(
                ["git", "status", "--short"], capture_output=True, text=True
            )
            mods = [
                l
                for l in r.stdout.strip().split("\n")
                if l.strip() and not l.startswith("??")
            ]
            findings.append(f"  Uncommitted: {len(mods)} modified files")

        with open(out_path, "w") as f:
            f.write(f"# Issues Found — {today} (auto)\n\n")
            f.write("\n".join(findings) + "\n")

        console.print(f"[green]Findings written to {out_path}[/green]")

    # -----------------------------------------------------------------------
    # run — auto-worker loop
    # -----------------------------------------------------------------------

    @main_group.command()
    @click.option("--loop", is_flag=True, help="Run in continuous loop mode")
    @click.option("--max-hours", default=12, help="Max duration in hours")
    @click.option("--project", default="ai-coworker", help="Target project")
    def run(loop, max_hours, project):
        """Run an auto-worker validation loop."""
        if not loop:
            console.print("Use --loop for continuous auto-worker mode")
            return

        from .memory.mem0_client import Mem0Client
        from .memory.llm import LLMClient
        from .analytics.db import get_db
        from .autoworker.engine import run_autoworker_loop

        try:
            mem0 = Mem0Client.from_config()
            llm = LLMClient()
            db = get_db()
        except Exception as e:
            console.print(
                f"[yellow]Running in reduced mode (some services unavailable): {e}[/yellow]"
            )
            mem0 = None
            llm = None
            db = None

        console.print(
            f"[bold]Starting auto-worker loop (max {max_hours}h)...[/bold]"
        )
        stats = run_autoworker_loop(
            mem0, llm, db, max_hours=max_hours, project=project
        )
        console.print(
            f"[green]Auto-worker complete: {stats['rounds']} rounds, "
            f"{stats['fixed']} fixed, {stats['elapsed_minutes']} min[/green]"
        )
