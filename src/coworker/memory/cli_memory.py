"""Memory CLI — graph and memory management subcommands.

Wired into the main coworker CLI via register_memory_commands(main).
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

console = Console()


def register_memory_commands(main_group: click.Group) -> None:
    """Register the 'memory' subcommand group on the main CLI."""

    @main_group.group()
    def memory():
        """Manage memory graph and session capture."""
        pass

    @memory.command("init")
    @click.option("--graphify-dir", default=None, help="Path to graphify-out/ directory")
    def memory_init(graphify_dir):
        """Initialize the memory graph from Graphify output.

        Creates ~/.coworker/memory/graph.json seeded with code/document
        structure from Graphify. Safe to re-run — existing edges are preserved.
        """
        from pathlib import Path
        from coworker.memory.graphify_sync import init_graph_from_graphify, load_graphify_output
        from coworker.memory.storage import save_graph

        gf_path = Path(graphify_dir) if graphify_dir else None
        if gf_path:
            gf_path = gf_path / "graph.json" if gf_path.is_dir() else gf_path

        graph = init_graph_from_graphify(gf_path)
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
    @click.argument("session_id")
    def memory_close(session_id):
        """Process a session's pending graph data into graph.json.

        Called by the session-end hook (Claude Code Stop / OpenCode session.end).
        Reads pending/<session_id>.json, enriches + dedups + merges into graph.json.
        """
        from coworker.memory.merge_worker import process_all_pending

        stats = process_all_pending()
        if stats["status"] == "ok":
            console.print(
                f"[green]Session close processed:[/green] "
                f"{stats['sessions_processed']} sessions, "
                f"+{stats['added_nodes']} nodes, +{stats['added_edges']} edges, "
                f"{stats['deduped']} deduped, {stats['graph_misses']} misses"
            )
        else:
            console.print(f"[yellow]No pending sessions to process.[/yellow]")

    @memory.command("query")
    @click.argument("question")
    @click.option("--top-k", "-k", default=50, help="Max results per source (default: 50, cut by token budget)")
    @click.option("--budget", default=2000, help="Token budget per section (default: 2000)")
    @click.option("--mode", default="both", type=click.Choice(["graph", "vector", "both"]),
                  help="Search mode (default: both)")
    def memory_query(question, top_k, mode, budget):
        """Query the memory graph.

        Searches nodes and traverses edges (BFS max depth 3).
        Results are ranked by path weight with decay applied.
        """
        from pathlib import Path
        from coworker.memory.storage import load_graph
        from coworker.memory.query import query as graph_query

        graph = load_graph()
        if not graph.nodes:
            console.print("[dim]Graph is empty. Run 'coworker memory init' first.[/dim]")
            return

        mem0 = None
        if mode in ("vector", "both"):
            try:
                from coworker.memory.mem0_client import Mem0Client
                mem0 = Mem0Client.from_config()
            except Exception:
                console.print("[dim]mem0 not available — vector search skipped[/dim]")

        result = graph_query(graph, question, mode=mode, mem0_client=mem0, top_k=top_k)

        graph_results = result.get("graph_results", [r for r in result["results"] if r.get("source") == "graph"])
        vector_results = result.get("vector_results", [r for r in result["results"] if r.get("source") == "vector"])

        # Full-text search in session messages
        message_results = []
        try:
            import sqlite3
            db = sqlite3.connect(str(Path.home() / '.coworker' / 'analytics' / 'analytics.db'))
            terms = question.lower().split()
            like_clauses = ' OR '.join(['m.content LIKE ?' for _ in terms])
            params = ['%' + t + '%' for t in terms]
            rows = db.execute(
                f'SELECT m.type, substr(m.content, 1, 500) as snippet, s.id, s.initiative, s.created_at '
                f'FROM messages m JOIN sessions s ON m.session_id = s.id '
                f'WHERE ({like_clauses}) AND m.content != \"\" '
                f'ORDER BY s.created_at DESC LIMIT 10',
                params
            ).fetchall()
            for row in rows:
                message_results.append({
                    'type': row[0], 'content': row[1], 'session_id': row[2],
                    'initiative': row[3] or '', 'date': (row[4] or '')[:10]
                })
            db.close()
        except Exception:
            pass

        def _cut_by_budget(items, budget_tokens):
            """Cut items to fit within budget_tokens (~3 chars per token)."""
            char_budget = budget_tokens * 3
            used = 0
            out = []
            for item in items:
                text = str(item.get("label") or item.get("memory", ""))
                used += len(text) + 50  # 50 chars for metadata (type, score, file)
                if used > char_budget:
                    break
                out.append(item)
            return out

        graph_results = _cut_by_budget(graph_results, budget)
        vector_results = _cut_by_budget(vector_results, budget)

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
                # If it's a document node, include its content
                source = (r.get("source_file") or "").replace("/home/cicidi/project/ai-coworker/", "")
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

        # Message results (full-text search in session transcripts)
        if message_results:
            console.print()
            t3 = Table(title=f"💬 Session Messages ({len(message_results)} results)")
            t3.add_column("#", style="dim")
            t3.add_column("Session")
            t3.add_column("Type")
            t3.add_column("Content")
            for i, m in enumerate(message_results, 1):
                role_icon = '👤' if m['type'] == 'user' else '🤖'
                t3.add_row(
                    str(i),
                    f"{m['session_id'][:20]}...\n{m['date']}",
                    role_icon,
                    m['content'][:300]
                )
            console.print(t3)

        console.print(
            f"[dim]Graph: {result['stats']['graph_hits']} | "
            f"Vector: {result['stats']['vector_hits']} | "
            f"Messages: {len(message_results)} | "
            f"Shown: {len(graph_results)} + {len(vector_results)} + {len(message_results)} (budget: {budget}T)[/dim]"
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
