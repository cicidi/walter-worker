"""Analytics commands for the Coworker CLI."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


def register_analytics(main_group: click.Group) -> None:
    """Register analytics subcommands on the main CLI group."""

    @main_group.group()
    def analytics():
        """Analytics database and dashboard commands."""
        pass

    @analytics.command("create-db")
    def analytics_create_db():
        """Initialize analytics SQLite database."""
        from .analytics.db import init_db
        init_db()
        console.print("[green]Analytics database initialized.[/green]")

    @analytics.command("import")
    def analytics_import():
        """Import raw JSONL sessions into SQLite."""
        from .analytics.import_data import import_all
        import_all()

    @analytics.command("daemon")
    def analytics_daemon():
        """Run auto-import daemon — polls every 30 minutes for new sessions."""
        from .analytics.auto_import import run_daemon
        run_daemon()

    @analytics.command("once")
    def analytics_once():
        """Import new sessions once (no daemon)."""
        from .analytics.auto_import import run_once
        stats = run_once(verbose=True)
        console.print(
            f"[green]Imported:[/green] claude_jsonl={stats['claude_jsonl']} "
            f"claude_hooks={stats['claude_hooks']} opencode={stats['opencode']} "
            f"skipped={stats['skipped']}"
        )

    @analytics.command("dashboard")
    @click.option("--port", default=8080, help="Port to listen on")
    @click.option(
        "--host",
        default="127.0.0.1",
        show_default=True,
        help="Interface to bind. Loopback by default; use 0.0.0.0 to expose it.",
    )
    @click.option("--db", default=None, help="Path to analytics database")
    def analytics_dashboard(port, host, db):
        """Start the analytics dashboard."""
        import os
        # COWORKER_ANALYTICS_DB is process-global and _default_db_path() reads it,
        # so leaving it set would silently redirect every later analytics call in
        # this process — and every subprocess it spawns — at this database.
        previous = os.environ.get("COWORKER_ANALYTICS_DB")
        if db:
            os.environ["COWORKER_ANALYTICS_DB"] = db
        try:
            import uvicorn
            from .dashboard.app import app
            # Loopback unless asked otherwise. This bound 0.0.0.0 and announced
            # itself as localhost, so it was listening on every interface while
            # saying it was not — reachable from the local network, with no
            # auth, serving session prompts, file paths and tool arguments, and
            # offering endpoints that rewrite ~/CLAUDE.local.md and skill state.
            shown = "localhost" if host in ("127.0.0.1", "::1") else host
            console.print(f"[green]Dashboard: http://{shown}:{port}[/green]")
            if host not in ("127.0.0.1", "::1"):
                console.print(
                    f"[yellow]Listening on {host} — anyone who can reach this "
                    f"port can read your sessions and change memory state.[/yellow]"
                )
            uvicorn.run(app, host=host, port=port, log_level="info")
        finally:
            if db:
                if previous is None:
                    os.environ.pop("COWORKER_ANALYTICS_DB", None)
                else:
                    os.environ["COWORKER_ANALYTICS_DB"] = previous
