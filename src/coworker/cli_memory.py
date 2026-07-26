"""Memory CLI commands (mem0-based cross-session memory).

Extracted from cli.py to keep file sizes manageable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import click
from rich.console import Console

console = Console()


def register_memory_commands(main_group: click.Group) -> None:
    """Attach the memory command group to the main CLI group."""
    main_group.add_command(memory)


@click.group()
def memory():
    """Memory platform commands (mem0-based cross-session memory)."""


@memory.command("sync")
@click.option("--ide", default="claude", help="IDE triggering the sync")
@click.option("--trigger", default="posttooluse", help="Hook trigger name")
@click.option("--session-id", default=None, help="Session identifier")
@click.option("--tool", default="unknown", help="Tool that triggered the sync")
@click.option("--input", "tool_input", default="{}", help="Tool input (JSON)")
@click.option("--result", "tool_result", default="", help="Tool result")
def memory_sync(ide, trigger, session_id, tool, tool_input, tool_result):
    """Per-turn memory sync (called by PostToolUse/SubagentStop hooks)."""
    from .memory.capture import process_turn
    from .memory.mem0_client import Mem0Client
    from .memory.llm import LLMClient

    try:
        mem0 = Mem0Client.from_config()
        llm = LLMClient()
    except Exception as e:
        console.print(f"[yellow]Memory sync skipped (mem0 unavailable): {e}[/yellow]")
        return

    try:
        input_data = json.loads(tool_input) if tool_input else {}
    except json.JSONDecodeError:
        input_data = {"raw": tool_input}

    tool_event = {
        "tool": tool,
        "input": input_data,
        "result": tool_result,
    }
    session = session_id or os.environ.get("COWORKER_SESSION_ID", "unknown")

    audit_dir = os.path.expanduser("~/.coworker/memory")
    state_dir = os.path.expanduser("~/.coworker/state")

    result = process_turn(mem0, llm, tool_event, [], session, state_dir=state_dir, audit_dir=audit_dir)
    if result.lessons_extracted > 0:
        console.print(f"[green]Extracted {result.lessons_extracted} lesson(s)[/green]")


@memory.command("close")
@click.option("--ide", default="claude", help="IDE triggering the close")
@click.option("--trigger", default="stop", help="Hook trigger name")
@click.option("--session-id", default=None, help="Session identifier")
@click.option("--transcript", default=None, help="Path to session transcript")
def memory_close(ide, trigger, session_id, transcript):
    """Session-end memory reconciliation (called by Stop hook)."""
    from .memory.capture import process_session_end
    from .memory.mem0_client import Mem0Client
    from .memory.llm import LLMClient

    try:
        mem0 = Mem0Client.from_config()
        llm = LLMClient()
    except Exception as e:
        console.print(f"[yellow]Memory close skipped (mem0 unavailable): {e}[/yellow]")
        return

    session = session_id or os.environ.get("COWORKER_SESSION_ID", "unknown")
    transcript_path = transcript or os.path.expanduser("~/.coworker/analytics/latest_transcript.txt")
    audit_dir = os.path.expanduser("~/.coworker/memory")

    result = process_session_end(mem0, llm, session, transcript_path, audit_dir=audit_dir)
    console.print(f"[green]Reconciled: {result.reconciled} lessons, {len(result.skills_staged)} skills staged[/green]")


@memory.command("search")
@click.argument("query")
@click.option("--project", default=None, help="Filter by project")
@click.option("--limit", default=10, help="Max results")
def memory_search(query, project, limit):
    """Search cross-session memory."""
    from .memory.mem0_client import Mem0Client

    try:
        mem0 = Mem0Client.from_config()
    except Exception as e:
        console.print(f"[red]mem0 unavailable: {e}[/red]")
        return

    filters = {}
    if project:
        filters["project"] = project
    results = mem0.search(query=query, filters=filters if filters else None, top_k=limit)
    if not results:
        console.print("[dim]No matching memories found.[/dim]")
        return
    for r in results:
        meta = r.get("metadata", {})
        console.print(
            f"[bold]{meta.get('topic', '?')}[/bold] "
            f"[dim]({meta.get('type', '?')}, {meta.get('state', '?')})[/dim]\n"
            f"  {r.get('memory', '')}\n"
        )


@memory.command("refresh")
def memory_refresh():
    """Refresh the CLAUDE.local.md memory snapshot + wrong-history rules."""
    from .memory.inject import build_snapshot, inject_into_local_md
    from .memory.mem0_client import Mem0Client
    from .memory.wrong_history import build_snapshot as build_wh_snapshot, inject_into_local_md as inject_wh

    local_md = os.path.expanduser("~/CLAUDE.local.md")
    changed = False

    # Memory snapshot
    try:
        mem0 = Mem0Client.from_config()
        snapshot = build_snapshot(mem0)
        if inject_into_local_md(str(local_md), snapshot):
            changed = True
            console.print("[green]Memory snapshot refreshed.[/green]")
    except Exception as e:
        console.print(f"[yellow]Memory snapshot skipped (mem0 unavailable): {e}[/yellow]")

    # Wrong-history rules
    try:
        wh_snapshot = build_wh_snapshot()
        if inject_wh(str(local_md), wh_snapshot):
            changed = True
            console.print("[green]Wrong-history rules injected.[/green]")
    except Exception as e:
        console.print(f"[yellow]Wrong-history injection failed: {e}[/yellow]")

    if not changed:
        console.print("[dim]Both snapshots unchanged.[/dim]")


@memory.command("train")
@click.option("--limit", default=None, type=int, help="Max sessions to process")
@click.option("--target-skills", default=10, type=int, help="Target skills to stage")
@click.option("--target-experiences", default=10, type=int, help="Target experiences to store")
@click.option("--skip-existing/--no-skip-existing", default=True, help="Skip sessions with existing entries")
def memory_train(limit, skip_existing):
    """Batch-train mem0 from all past sessions in analytics.db."""
    from .memory.train import run_training_pipeline
    from .memory.mem0_client import Mem0Client
    from .memory.llm import LLMClient
    from .analytics.db import get_db

    try:
        mem0 = Mem0Client.from_config()
        llm = LLMClient()
        db = get_db()
    except Exception as e:
        console.print(f"[red]Setup failed: {e}[/red]")
        return

    console.print("[bold]Starting training pipeline...[/bold]")
    stats = run_training_pipeline(mem0, llm, db, limit=limit, skip_existing=skip_existing)
    console.print(
        f"[green]Training complete: {stats['sessions_processed']} sessions, "
        f"{stats['lessons_extracted']} lessons[/green]"
    )
    if stats["errors"]:
        console.print(f"[yellow]{len(stats['errors'])} errors[/yellow]")


@memory.command("validate")
@click.argument("task", required=False)
@click.option("--task-file", default=None, type=click.Path(exists=True), help="Path to file containing task definition")
@click.option("--compare-baseline/--no-compare-baseline", is_flag=True, default=False, help="Run A/B comparison")
def memory_validate(task, task_file, compare_baseline):
    """Run Claude SDK validation harness — A/B comparison of baseline vs memory-augmented agent."""
    if not task and not task_file:
        console.print("[red]Provide a task description or --task-file[/red]")
        return

    from .memory.validate import run_validation

    console.print("[bold]Running validation harness...[/bold]")
    report = run_validation(task or "", task_file=task_file)
    console.print(f"\n[bold]Results:[/bold]")
    console.print(f"  Baseline tool calls:     {report['baseline']['tool_calls']}")
    console.print(f"  Memory-augmented calls:  {report['with_memory']['tool_calls']}")
    console.print(f"  Tool call reduction:     {report['tool_call_reduction']}")
    console.print(f"  Baseline assumptions:    {report['baseline']['incorrect_assumptions']} incorrect")
    console.print(f"  Memory assumptions:      {report['with_memory']['incorrect_assumptions']} incorrect")
    console.print(f"  Skills invoked:          {', '.join(report['with_memory']['skills_invoked']) or 'none'}")
    console.print(f"  Experiences retrieved:   {', '.join(report['with_memory']['experiences_retrieved']) or 'none'}")
    console.print(f"  [bold]Verdict: {report['verdict'].upper()}[/bold]")
    console.print(f"  Elapsed: {report['elapsed_seconds']}s")
