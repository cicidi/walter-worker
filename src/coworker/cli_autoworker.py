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
    @click.option("--project", default="walter-worker", help="Target project")
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
        import glob
        import os
        from datetime import datetime, timezone


        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = (
            output
            or f"docs/features/self-evolving-agent/state/issues-found-{today}-auto.md"
        )
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        console.print("[bold]Find-Issues — QA inspection[/bold]")
        console.print(f"  Project: {project}")
        console.print(f"  Phases: {phases}")
        console.print(f"  Output: {out_path}")

        findings = []
        phases_list = [p.strip() for p in phases.split(",")]

        # A typo used to produce an empty findings file and exit 0, which is
        # indistinguishable from a clean bill of health.
        _valid_phases = ("prd", "spec", "web", "code", "all")
        _unknown = [p for p in phases_list if p and p not in _valid_phases]
        if _unknown:
            raise click.ClickException(
                f"Unknown phase(s): {', '.join(_unknown)}. "
                f"Valid: {', '.join(_valid_phases)}."
            )

        # Phases that reported something wrong. The command exits non-zero for
        # these: a QA inspector whose exit status is always 0 cannot gate a
        # loop or a CI job, which is the whole point of it.
        problems: list[str] = []

        # Both scans read docs/features/<project>/, which is what --project
        # selects. The paths were hardcoded to the self-evolving-agent feature,
        # so --project was accepted, echoed, and had no effect whatsoever — and
        # the default (walter-worker) did not match the path either.
        docs_dir = os.path.join("docs", "features", project)

        if "all" in phases_list or "prd" in phases_list:
            prd_dir = os.path.join(docs_dir, "prd")
            prd_files = sorted(glob.glob(os.path.join(prd_dir, "*.md")))
            if prd_files:
                reqs = 0
                for prd_path in prd_files:
                    with open(prd_path) as f:
                        reqs += sum(
                            1 for line in f
                            if line.strip().startswith("- R")
                            or "R1" in line or "R2" in line
                        )
                findings.append(
                    f"## PRD Scan: {reqs} requirement references in "
                    f"{len(prd_files)} file(s) under {prd_dir}"
                )
            else:
                findings.append(f"## PRD Scan: no PRD files under {prd_dir}")

        if "all" in phases_list or "spec" in phases_list:
            spec_dir = os.path.join(docs_dir, "spec")
            spec_files = sorted(glob.glob(os.path.join(spec_dir, "*.md")))
            if spec_files:
                sections = 0
                for spec_path in spec_files:
                    with open(spec_path) as f:
                        sections += sum(1 for line in f if line.startswith("## §"))
                findings.append(
                    f"## Spec Scan: {sections} sections in "
                    f"{len(spec_files)} file(s) under {spec_dir}"
                )
            else:
                findings.append(f"## Spec Scan: no spec files under {spec_dir}")

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
                timeout=600,  # full suite takes ~5-6 min
            )
            test_status = "PASS" if r.returncode == 0 else "FAIL"
            # Extract pass/fail counts from pytest output. When pytest cannot
            # even start it writes nothing to stdout and the reason goes to
            # stderr, so reading stdout alone produced "Tests FAIL — " with a
            # blank explanation.
            output = r.stdout.strip() or r.stderr.strip()
            last_line = output.split("\n")[-1] if output else "(no output)"
            findings.append(f"## Code Audit: Tests {test_status} — {last_line}")
            if r.returncode != 0:
                problems.append("tests")
            r = subprocess.run(
                ["git", "status", "--short"], capture_output=True, text=True
            )
            mods = [
                line
                for line in r.stdout.strip().split("\n")
                if line.strip() and not line.startswith("??")
            ]
            findings.append(f"  Uncommitted: {len(mods)} modified files")

        with open(out_path, "w") as f:
            f.write(f"# Issues Found — {today} (auto)\n\n")
            f.write("\n".join(findings) + "\n")

        console.print(f"[green]Findings written to {out_path}[/green]")

        if problems:
            raise click.ClickException(
                f"Inspection reported problems in: {', '.join(problems)}. "
                f"See {out_path}."
            )

    # -----------------------------------------------------------------------
    # run — auto-worker loop
    # -----------------------------------------------------------------------

    @main_group.command()
    @click.option("--loop", is_flag=True, help="Run in continuous loop mode")
    @click.option("--max-hours", default=12, help="Max duration in hours")
    @click.option("--project", default="walter-worker", help="Target project")
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
