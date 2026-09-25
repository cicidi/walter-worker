"""Knowledge CLI — summarise sessions into knowledge cards.

Wired into the main coworker CLI via register_knowledge_commands(main).

skills/knowledge documents `coworker knowledge summarize` and
`coworker knowledge analyze`; the module behind them existed and was tested,
but nothing ever exposed it, so the skill instructed users to run commands
that did not exist.
"""

from __future__ import annotations

import click

from .knowledge import get_all_sessions_since, summarize_session


def _run(session_ids: list[str], llm) -> tuple[int, int, list[str]]:
    """Summarise each session. Returns (done, card_count, failures).

    One bad session must not abandon the rest of the batch — a run over a
    month of sessions is exactly when a single unreadable one is likely.
    """
    done = 0
    cards = 0
    failures: list[str] = []
    for session_id in session_ids:
        try:
            result = summarize_session(session_id, llm=llm)
        except Exception as exc:  # one session, not the batch
            failures.append(f"{session_id}: {exc}")
            continue
        if result is None:
            failures.append(f"{session_id}: no such session")
            continue
        done += 1
        cards += result["cards"]
    return done, cards, failures


def register_knowledge_commands(main_group: click.Group) -> None:
    """Register the 'knowledge' subcommand group on the main CLI."""

    @main_group.group()
    def knowledge():
        """Summarise sessions into session summaries and knowledge cards."""

    @knowledge.command("summarize")
    @click.argument("session_id")
    def knowledge_summarize(session_id):
        """Summarise one session from analytics.db."""
        from ..memory.llm import LLMClient

        try:
            result = summarize_session(session_id, llm=LLMClient())
        except RuntimeError as exc:
            raise click.ClickException(str(exc))
        except Exception as exc:
            raise click.ClickException(f"{session_id}: {exc}")

        if result is None:
            raise click.ClickException(f"No session with id {session_id!r}")

        click.echo(f"summarized {result['session_id']} ({result['cards']} cards)")

    @knowledge.command("analyze")
    @click.option(
        "--since",
        default=None,
        help="'yesterday' (default), 'today', 'N days ago', an ISO date, or 'all'.",
    )
    @click.option("--all", "all_sessions", is_flag=True, help="Every session on record.")
    def knowledge_analyze(since, all_sessions):
        """Summarise every session in the window."""
        from ..memory.llm import LLMClient

        window = "all" if all_sessions else (since or "yesterday")

        try:
            session_ids = get_all_sessions_since(window)
        except ValueError as exc:
            raise click.ClickException(str(exc))

        if not session_ids:
            click.echo(f"No sessions found since {window}.")
            return

        # One client for the batch: constructing it per session rebuilds the
        # provider list every time for no gain.
        done, cards, failures = _run(session_ids, LLMClient())

        click.echo(f"summarized {done}/{len(session_ids)} sessions ({cards} cards)")
        for failure in failures:
            click.echo(f"  skipped {failure}", err=True)

        if done == 0:
            raise click.ClickException("No session could be summarised.")
