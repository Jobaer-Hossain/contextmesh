"""
ContextMesh CLI
Command-line interface to index, query, and manage local developer context.
"""

import sys
import io
import argparse
from pathlib import Path

# Windows UTF-8
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from contextmesh.core.store import LocalContextStore
from contextmesh.core.collector import ContextCollector
from contextmesh.core.models import EventSource

console = Console(force_terminal=True)
store = LocalContextStore()
collector = ContextCollector(store)


def show_banner():
    console.print(
        Panel.fit(
            "[bold violet]⚡ ContextMesh[/bold violet] — [bold white]Local-First Personal Context API[/bold white]\n"
            "[dim]SQLite & FTS5 Privacy-Preserving Developer Memory Daemon[/dim]",
            border_style="violet"
        )
    )


def command_search(args):
    show_banner()
    query = args.query
    source = EventSource(args.source) if args.source else None
    results = store.query_context(query=query, source=source, limit=args.limit)

    table = Table(title=f"Context Search: '{query}'", header_style="bold violet")
    table.add_column("Source", style="bold cyan")
    table.add_column("Title", style="bold white")
    table.add_column("Timestamp", style="dim")
    table.add_column("Snippet")

    for r in results:
        table.add_row(
            r.source.value.upper(),
            r.title,
            r.timestamp.strftime("%Y-%m-%d %H:%M"),
            r.snippet[:120] + "..."
        )
    console.print(table)


def command_sync(args):
    show_banner()
    target_path = Path(args.path or ".").resolve()
    console.print(f"[bold cyan]Indexing context for:[/bold cyan] {target_path}\n")

    git_events = collector.collect_git_activity(target_path)
    notes_count = collector.index_markdown_notes(target_path)

    console.print(f"[bold green]✔ Git repository indexed:[/bold green] {len(git_events)} events")
    console.print(f"[bold green]✔ Markdown notes indexed:[/bold green] {notes_count} documents\n")


def command_stats(args):
    show_banner()
    stats = store.get_stats()
    table = Table(title="Local Context Store Statistics", header_style="bold green")
    table.add_column("Metric")
    table.add_column("Value", style="bold yellow")

    table.add_row("Total Indexed Events", str(stats["total_events"]))
    table.add_row("Redacted Secrets Intercepted", str(stats["redacted_events_count"]))
    table.add_row("Database Disk Size", f"{stats['db_size_kb']} KB")
    for k, v in stats["sources_breakdown"].items():
        table.add_row(f"  Source: {k}", str(v))

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="ContextMesh CLI")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand")

    search_p = subparsers.add_parser("search", help="Query local developer context")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--source", choices=["terminal", "git", "notes"], help="Filter by source")
    search_p.add_argument("--limit", type=int, default=5, help="Result limit")

    sync_p = subparsers.add_parser("sync", help="Index current folder git and notes")
    sync_p.add_argument("path", nargs="?", default=".", help="Directory to index")

    subparsers.add_parser("stats", help="Display store statistics")

    args = parser.parse_args()
    if args.subcommand == "search":
        command_search(args)
    elif args.subcommand == "sync":
        command_sync(args)
    elif args.subcommand == "stats":
        command_stats(args)
    else:
        show_banner()
        parser.print_help()


if __name__ == "__main__":
    main()
