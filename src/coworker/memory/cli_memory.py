"""Memory CLI — graph and memory management subcommands.

Wired into the main coworker CLI via register_memory_commands(main).
"""

from __future__ import annotations

import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _short_path(path: str) -> str:
    """Show a source path relative to the working directory when it is under it.

    This used to strip a hardcoded absolute checkout prefix, so it only ever
    shortened anything on the machine that prefix named; everywhere else the
    full path was printed instead.
    """
    if not path:
        return ""
    try:
        rel = os.path.relpath(path, Path.cwd())
    except ValueError:  # Windows: path and cwd on different drives
        return path
    return path if rel.startswith("..") else rel


def register_memory_commands(main_group: click.Group) -> None:
    """Register the 'memory' subcommand group on the main CLI."""

    @main_group.group()
    def memory():
        """Manage memory graph and session capture."""
        pass

    @memory.command("init")
    @click.option("--graphify-dir", default=None, help="Path to graphify-out/ directory")
    @click.option(
        "--force",
        is_flag=True,
        help="Rebuild from scratch, discarding the graph already on disk",
    )
    def memory_init(graphify_dir, force):
        """Initialize the memory graph from Graphify output.

        Creates ~/.coworker/memory/graph.json seeded with code/document
        structure from Graphify.

        It will not touch a graph that already holds nodes. This builds a fresh
        graph and saves it over the file, so re-running it erased everything the
        memory platform had accumulated — and it used to claim existing edges
        were preserved, which was never true. `coworker memory sync` is the
        command that merges new Graphify output into an existing graph.
        """
        from pathlib import Path
        from coworker.memory.graphify_sync import init_graph_from_graphify
        from coworker.memory.storage import GRAPH_PATH, load_graph, save_graph

        existing = load_graph()
        if existing.nodes and not force:
            console.print(
                f"[yellow]Graph already holds {len(existing.nodes)} node(s); "
                f"leaving it alone.[/yellow]"
            )
            console.print(
                "  [cyan]coworker memory sync[/cyan] merges new Graphify output into it."
            )
            console.print(
                "  [cyan]--force[/cyan] rebuilds from scratch and discards it."
            )
            return

        gf_path = Path(graphify_dir) if graphify_dir else None
        if gf_path:
            gf_path = gf_path / "graph.json" if gf_path.is_dir() else gf_path

        graph = init_graph_from_graphify(gf_path)
        if existing.nodes:
            from .. import backup

            backup.snapshot([GRAPH_PATH], "memory-init")
        save_graph(graph)
        console.print(
            f"[green]Graph initialized:[/green] {len(graph.nodes)} nodes, "
            f"{len(graph.links)} edges (schema v{graph.schema_version})"
        )

    @memory.command("sync")
    @click.option("--graphify-dir", default=None, help="Path to graphify-out/ directory")
    def memory_sync(graphify_dir):
        """Re-sync Graphify skeleton into the memory graph.

        New code/docs from git pull are imported. Existing edges and
        weights are preserved. Safe to run on-demand or via weekly cron.
        """
        from pathlib import Path
        from coworker.memory.graphify_sync import sync_graphify_skeleton, load_graphify_output
        from coworker.memory.storage import load_graph, save_graph

        gf_path = Path(graphify_dir) if graphify_dir else None
        if gf_path:
            gf_path = gf_path / "graph.json" if gf_path.is_dir() else gf_path

        data = load_graphify_output(gf_path)
        if data is None:
            console.print("[yellow]No Graphify output found. Run 'graphify .' first.[/yellow]")
            return

        graph = load_graph()
        added = sync_graphify_skeleton(graph, data)
        save_graph(graph)
        console.print(
            f"[green]Sync complete:[/green] {added} new items. "
            f"Graph now has {len(graph.nodes)} nodes, {len(graph.links)} edges."
        )

    @memory.command("close")
    @click.argument("session_id", required=False, default=None)
    def memory_close(session_id):
        """Merge a session's pending graph data into graph.json.

        With an id, only that session's dump is merged; with none, every
        pending dump is. Reads pending/<session_id>.json, enriches, dedups and
        merges into graph.json.

        Called by the session-end hook after `memory capture` has written the
        dump. The id used to be required and then ignored — the command always
        processed all of them — so a typo succeeded and closing one session
        drained every other one too.
        """
        from coworker.memory.merge_worker import process_all_pending, process_pending
        from coworker.memory.storage import PENDING_DIR

        if session_id:
            path = PENDING_DIR / f"{session_id}.json"
            if not path.exists():
                raise click.ClickException(
                    f"No pending dump for session {session_id!r}."
                )
            stats = process_pending(path)
            sessions = 1 if stats["status"] == "ok" else 0
        else:
            stats = process_all_pending()
            sessions = stats.get("sessions_processed", 0)

        if sessions:
            console.print(
                f"[green]Session close processed:[/green] "
                f"{sessions} sessions, "
                f"+{stats['added_nodes']} nodes, +{stats['added_edges']} edges, "
                f"{stats['deduped']} deduped, {stats['graph_misses']} misses"
            )
        else:
            console.print("[yellow]No pending sessions to process.[/yellow]")

    @memory.command("query")
    @click.argument("question")
    @click.option("--top-k", "-k", default=50, help="Max results per source (default: 50)")
    @click.option("--budget", default=2000, help="Token budget per section (default: 2000)")
    @click.option("--min-score", default=0.3, type=float, help="Min score for vector results (default: 0.3)")
    @click.option("--mode", default="both", type=click.Choice(["graph", "vector", "both"]),
                  help="Search mode (default: both)")
    def memory_query(question, top_k, mode, budget, min_score):
        """Query the memory graph + vector memory.

        Graph search: graphify seed scoring → BFS traversal (max depth 6)
        with decay-weighted ranking. Results cut by token budget.
        Vector search: mem0 hybrid retrieval with min_score quality filter.
        """
        from coworker.memory.storage import load_graph
        from coworker.memory.query import query as graph_query

        graph = load_graph()
        # Only a graph-only request is blocked by an empty graph. This guard
        # used to run before the mode check, so `--mode vector` — which does not
        # read the graph at all, and is exactly what a user wants when the graph
        # is empty — was refused for a reason that did not apply to it.
        if mode == "graph" and not graph.nodes:
            console.print("[dim]Graph is empty. Run 'coworker memory init' first.[/dim]")
            return

        mem0 = None
        if mode in ("vector", "both"):
            try:
                from coworker.memory.mem0_client import Mem0Client
                mem0 = Mem0Client.from_config()
            except Exception:
                console.print("[dim]mem0 not available — vector search skipped[/dim]")

        result = graph_query(
            graph, question, mode=mode, mem0_client=mem0,
            top_k=top_k, min_score=min_score, budget=budget,
        )

        graph_results = result["graph_results"]
        vector_results = result["vector_results"]

        # Graph results
        if graph_results:
            t = Table(title=f"🔗 Knowledge Graph ({len(graph_results)} results)")
            t.add_column("#", style="dim")
            t.add_column("Label", style="cyan")
            t.add_column("Type")
            t.add_column("File")
            t.add_column("W", justify="right")
            for i, r in enumerate(graph_results, 1):
                label = r.get("label", "")[:120]
                source = _short_path(r.get("source_file") or "")
                t.add_row(
                    str(i), label, r.get("type", ""),
                    source[:50] if source else "",
                    f"{r.get('path_weight', 0):.2f}"
                )
            console.print(t)

        # Vector/mem0 results
        if vector_results:
            console.print()
            t2 = Table(title=f"🧠 Session Memory ({len(vector_results)} results)")
            t2.add_column("#", style="dim")
            t2.add_column("Memory")
            t2.add_column("Type")
            t2.add_column("Score", justify="right")
            for i, r in enumerate(vector_results, 1):
                meta = r.get("metadata", {})
                t2.add_row(
                    str(i), r.get("memory", "")[:120],
                    meta.get("type", ""),
                    f"{r.get('score', 0):.2f}"
                )
            console.print(t2)

        console.print(
            f"[dim]Graph: {result['stats']['graph_hits']} | "
            f"Vector: {result['stats']['vector_hits']} | "
            f"Shown: {len(graph_results)} + {len(vector_results)} (budget: {budget}T, min-score: {min_score})[/dim]"
        )

    @memory.command("metrics")
    def memory_metrics():
        """Show the evolution metrics report — is the agent getting smarter?"""
        from coworker.memory.metrics import get_metrics_report

        console.print(get_metrics_report())

    @memory.command("capture")
    def memory_capture():
        """Session-end capture: read the hook payload on stdin, then reconcile.

        process_session_end is the loop's session-end stage — it back-fills
        missed captures from the transcript and assesses whether a pattern is
        skill-worthy — and nothing called it. The design reserved
        `coworker memory close` for this, but that name went to the graph
        command, so the stage was unreachable rather than missing.

        Reads {"session_id", "transcript_path"} from stdin: the same flat
        payload every Claude Code hook receives.

        Wired to the Stop hook by setup/install.sh. That is one LLM call per
        session — the cheap half of capture. process_turn, the per-PostToolUse
        half, is an LLM call per tool call and stays unwired.

        Exits 0 without a word when mem0 is not configured, so a machine with
        no API key is quiet rather than reporting the same thing after every
        session. A genuine failure still exits non-zero and says why.
        """
        import json as _json
        import sys

        raw = sys.stdin.read()
        if not raw.strip():
            raise click.ClickException("No hook payload on stdin")

        try:
            payload = _json.loads(raw)
        except _json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid JSON on stdin: {exc}")

        session_id = payload.get("session_id") or ""
        transcript_path = payload.get("transcript_path") or ""
        if not session_id:
            raise click.ClickException("Hook payload has no session_id")
        if not transcript_path:
            raise click.ClickException("Hook payload has no transcript_path")

        from coworker.memory.capture import process_session_end
        from coworker.memory.llm import LLMClient
        from coworker.memory.mem0_client import ConfigError, Mem0Client

        try:
            mem0 = Mem0Client.from_config()
        except ConfigError:
            # The Stop hook runs this at the end of every session, so an
            # unconfigured machine must be distinguishable from a broken one.
            # A missing API key is a state to leave alone; repeating it at the
            # user after every session is noise, not a signal.
            return
        except Exception as exc:
            raise click.ClickException(f"mem0 unavailable: {exc}")

        try:
            result = process_session_end(
                mem0_client=mem0,
                llm_client=LLMClient(),
                session_id=session_id,
                transcript_path=transcript_path,
                audit_dir="~/.coworker/memory/",
            )
        except Exception as exc:
            raise click.ClickException(f"{session_id}: {exc}")

        if result.error:
            raise click.ClickException(result.error)

        console.print(
            f"Reconciled: {result.reconciled}, "
            f"Lessons: {len(result.lessons)}, "
            f"Skills staged: {len(result.skills_staged)}"
        )

    @memory.command("stats")
    def memory_stats():
        """Show memory graph statistics."""
        from coworker.memory.storage import load_graph
        from coworker.memory.decay import compute_effective_weight, query_filter
        from datetime import datetime, timezone

        graph = load_graph()
        if not graph.nodes:
            console.print("[dim]Graph is empty.[/dim]")
            return

        now = datetime.now(timezone.utc)

        # Count by type and provenance
        type_counts: dict[str, int] = {}
        prov_counts: dict[str, int] = {}
        for n in graph.nodes:
            type_counts[n.type] = type_counts.get(n.type, 0) + 1
            prov_counts[n.provenance] = prov_counts.get(n.provenance, 0) + 1

        # Edge weight distribution
        normal = stale = suppressed = 0
        for e in graph.links:
            ew = compute_effective_weight(e.base_weight, e.last_traversed_at, now)
            qf = query_filter(ew)
            if qf == "normal":
                normal += 1
            elif qf == "stale":
                stale += 1
            else:
                suppressed += 1

        table = Table(title="Memory Graph Stats")
        table.add_column("Metric", style="cyan")
        table.add_column("Value")

        table.add_row("Schema version", graph.schema_version)
        table.add_row("Total nodes", str(len(graph.nodes)))
        for t, c in sorted(type_counts.items()):
            table.add_row(f"  {t}", str(c))
        table.add_row("Total edges", str(len(graph.links)))
        for p, c in sorted(prov_counts.items()):
            table.add_row(f"  {p}", str(c))
        table.add_row("Edge health", f"{normal} normal, {stale} stale, {suppressed} suppressed")

        console.print(table)


    # ── session capture + mem0 operations ───────────────────────────────
    # Moved here from the orphaned coworker/cli_memory.py, which nothing
    # imported: its `train` was referenced by the dashboard and by
    # memory/metrics.py, so the CLI told users to run a command that did
    # not exist. Its sync/close were dropped - the live ones are different
    # commands with the same names.
    @memory.command("search")
    @click.argument("query")
    @click.option("--project", default=None, help="Filter by project")
    @click.option("--limit", default=10, help="Max results")
    def memory_search(query, project, limit):
        """Search cross-session memory."""
        from coworker.memory.mem0_client import Mem0Client

        try:
            mem0 = Mem0Client.from_config()
        except Exception as e:
            # The search did not happen, so the exit status must not claim it
            # did. This printed the reason and returned 0.
            raise click.ClickException(f"mem0 unavailable: {e}")

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
        import os

        from coworker.memory.inject import build_snapshot, inject_into_local_md
        from coworker.memory.mem0_client import Mem0Client
        from coworker.memory.wrong_history import build_snapshot as build_wh_snapshot, inject_into_local_md as inject_wh

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


    @memory.command("curate")
    @click.option("--if-due", is_flag=True,
                  help="Run only when the 7-day interval (spec §4.3) has elapsed")
    @click.option("--state", "state_path", default=None, help="Override the last-run stamp path")
    @click.option("--export", "export_path", default=None, help="Override the MEMORY.md export path")
    def memory_curate(if_due, state_path, export_path):
        """Run curator maintenance: mark stale, archive, score, export MEMORY.md."""
        from coworker.memory.curator import (
            DEFAULT_EXPORT_PATH,
            is_due,
            mark_ran,
            run_curator,
        )

        if if_due and not is_due(state_path=state_path):
            console.print("[dim]Curator not due (last run within 7 days).[/dim]")
            return

        from coworker.memory.mem0_client import Mem0Client

        try:
            mem0 = Mem0Client.from_config()
        except Exception as e:
            # --if-due is how the Stop hook calls this, once per session; it
            # must stay quiet, or an unconfigured machine reports the same
            # missing key after every session. Invoked by hand, the curator
            # did not run and the exit status should say so.
            if if_due:
                console.print(f"[dim]Curator skipped (mem0 unavailable): {e}[/dim]")
                return
            raise click.ClickException(f"mem0 unavailable: {e}")

        stats = run_curator(mem0, export_path=export_path or DEFAULT_EXPORT_PATH)
        # Only a clean run counts as "ran", so a failing one retries next session.
        if not stats.get("errors"):
            mark_ran(state_path=state_path)

        if stats.get("errors"):
            console.print(f"[yellow]Curator finished with errors: {stats['errors']}[/yellow]")
        console.print(
            f"[green]Curator:[/green] {stats['stale_marked']} stale, "
            f"{stats['archived']} archived, {stats.get('scored', 0)} scored, "
            f"{stats['exported_entries']} exported"
        )

    @memory.command("train")
    @click.option("--limit", default=None, type=int, help="Max sessions to process")
    @click.option("--target-skills", default=10, type=int, help="Target skills to stage")
    @click.option("--target-experiences", default=10, type=int, help="Target experiences to store")
    @click.option("--skip-existing/--no-skip-existing", default=True, help="Skip sessions with existing entries")
    def memory_train(limit, target_skills, target_experiences, skip_existing):
        """Batch-train mem0 from all past sessions in analytics.db."""
        from coworker.memory.train import run_training_pipeline
        from coworker.memory.mem0_client import Mem0Client
        from coworker.memory.llm import LLMClient
        from coworker.analytics.db import get_db

        try:
            mem0 = Mem0Client.from_config()
            llm = LLMClient()
            db = get_db()
        except Exception as e:
            console.print(f"[red]Setup failed: {e}[/red]")
            return

        console.print("[bold]Starting training pipeline...[/bold]")
        stats = run_training_pipeline(
            mem0,
            llm,
            db,
            limit=limit,
            skip_existing=skip_existing,
            target_skills=target_skills,
            target_experiences=target_experiences,
        )
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

        from coworker.memory.validate import run_validation

        console.print("[bold]Running validation harness...[/bold]")
        report = run_validation(task or "", task_file=task_file)
        console.print("\n[bold]Results:[/bold]")
        console.print(f"  Baseline tool calls:     {report['baseline']['tool_calls']}")
        console.print(f"  Memory-augmented calls:  {report['with_memory']['tool_calls']}")
        console.print(f"  Tool call reduction:     {report['tool_call_reduction']}")
        console.print(f"  Baseline assumptions:    {report['baseline']['incorrect_assumptions']} incorrect")
        console.print(f"  Memory assumptions:      {report['with_memory']['incorrect_assumptions']} incorrect")
        console.print(f"  Skills invoked:          {', '.join(report['with_memory']['skills_invoked']) or 'none'}")
        console.print(f"  Experiences retrieved:   {', '.join(report['with_memory']['experiences_retrieved']) or 'none'}")
        console.print(f"  [bold]Verdict: {report['verdict'].upper()}[/bold]")
        console.print(f"  Elapsed: {report['elapsed_seconds']}s")


    @memory.command("wrong-history")
    @click.argument("action", type=click.Choice(["record", "index"]))
    @click.option("--summary", default=None, help="One-line summary of the mistake")
    @click.option("--rule", "prevention_rule", default=None, help="Prevention rule")
    @click.option("--severity", default="high", type=click.Choice(["critical", "high", "medium", "low"]))
    @click.option("--category", default="code-quality", type=click.Choice(["tool-use", "code-quality", "process", "communication", "design"]))
    @click.option("--what", "what_happened", default="", help="What happened")
    @click.option("--why", "root_cause", default="", help="Root cause")
    @click.option("--fix", "fix_desc", default="", help="What was done to fix it")
    def memory_wrong_history(action, summary, prevention_rule, severity, category, what_happened, root_cause, fix_desc):
        """Manage wrong-history entries — record mistakes or rebuild index."""
        from coworker.memory.wrong_history import record_entry, _rebuild_index

        if action == "index":
            count, path = _rebuild_index()
            console.print(
                f"[green]Wrong-history INDEX rebuilt:[/green] {count} entries -> {path}"
            )
            return

        if action == "record":
            if not summary or not prevention_rule:
                console.print("[red]--summary and --rule are required for record[/red]")
                return
            path = record_entry(
                summary=summary,
                prevention_rule=prevention_rule,
                severity=severity,
                category=category,
                what_happened=what_happened,
                root_cause=root_cause,
                fix=fix_desc,
            )
            if path:
                console.print(f"[green]Created wrong-history entry: {path.name}[/green]")
            else:
                console.print("[red]Failed to create entry[/red]")
