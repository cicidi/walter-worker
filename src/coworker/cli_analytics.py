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
    @click.option("--db", default=None, help="Path to analytics database")
    def analytics_dashboard(port, db):
        """Start the analytics dashboard."""
        import os
        if db:
            os.environ["COWORKER_ANALYTICS_DB"] = db
        import uvicorn
        from .dashboard.app import app
        console.print(f"[green]Dashboard: http://localhost:{port}[/green]")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
