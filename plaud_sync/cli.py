"""CLI entry point for Plaud Sync."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from plaud_sync import __version__
from plaud_sync.api import PlaudApiClient
from plaud_sync.config import Config, load_config, load_token
from plaud_sync.period import PeriodParseError, filter_by_period, parse_period
from plaud_sync.retry import PlaudApiError
from plaud_sync.sync import run_sync


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plaud-sync",
        description="Sync Plaud.ai voice recordings to local markdown files.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync recordings to markdown files")
    sync_parser.add_argument("--vault", type=str, default=".",
                             help="Base directory for output (default: current directory)")
    sync_parser.add_argument("--folder", type=str, default=None,
                             help="Subfolder for notes (overrides config)")
    sync_parser.add_argument("--token-file", type=str, default=None,
                             help="Path to token file (default: ~/.secrets/plaud.txt)")
    sync_parser.add_argument("--config", type=str, default=None,
                             help="Path to config file (default: ~/.config/plaud-sync/config.json)")
    sync_parser.add_argument("-p", "--period", type=str, default=None,
                             help="Filter by period (e.g. 2026-03, thisweek, last7days)")
    sync_parser.add_argument("--verbose", action="store_true",
                             help="Enable verbose debug output")

    # list command
    list_parser = subparsers.add_parser("list", help="List recordings (without syncing)")
    list_parser.add_argument("--token-file", type=str, default=None,
                             help="Path to token file (default: ~/.secrets/plaud.txt)")
    list_parser.add_argument("--config", type=str, default=None,
                             help="Path to config file (default: ~/.config/plaud-sync/config.json)")
    list_parser.add_argument("-p", "--period", type=str, default=None,
                             help="Filter by period (e.g. 2026-03, thisweek, last7days)")
    list_parser.add_argument("--verbose", action="store_true",
                             help="Enable verbose debug output")

    # tui command
    tui_parser = subparsers.add_parser("tui", help="Interactive recording browser")
    tui_parser.add_argument("--vault", type=str, default=".",
                            help="Base directory for output (default: current directory)")
    tui_parser.add_argument("--folder", type=str, default=None,
                            help="Subfolder for notes (overrides config)")
    tui_parser.add_argument("--token-file", type=str, default=None,
                            help="Path to token file (default: ~/.secrets/plaud.txt)")
    tui_parser.add_argument("--config", type=str, default=None,
                            help="Path to config file (default: ~/.config/plaud-sync/config.json)")
    tui_parser.add_argument("-p", "--period", type=str, default=None,
                            help="Filter by period (e.g. 2026-03, thisweek, last7days)")
    tui_parser.add_argument("--verbose", action="store_true",
                            help="Enable verbose debug output")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a transcript with LLM")
    analyze_parser.add_argument("file", type=str,
                                help="Path to markdown file or recording ID")
    analyze_parser.add_argument("--template", "-t", type=str, default=None,
                                help="Template name (default: 'default')")
    analyze_parser.add_argument("--prompt", type=str, default=None,
                                help="Additional prompt / ad-hoc instructions")
    analyze_parser.add_argument("--config", type=str, default=None,
                                help="Path to config file")
    analyze_parser.add_argument("--verbose", action="store_true",
                                help="Enable verbose debug output")

    # templates command
    templates_parser = subparsers.add_parser("templates", help="Manage analysis templates")
    templates_sub = templates_parser.add_subparsers(dest="templates_command",
                                                     help="Template commands")
    templates_sub.add_parser("list", help="List available templates")
    show_parser = templates_sub.add_parser("show", help="Show a template")
    show_parser.add_argument("name", type=str, help="Template name")

    # journal command
    journal_parser = subparsers.add_parser("journal", help="View meeting journal")
    journal_parser.add_argument("--vault", type=str, default=".",
                                help="Base directory for output (default: current directory)")
    journal_parser.add_argument("--folder", type=str, default=None,
                                help="Subfolder for notes (overrides config)")
    journal_parser.add_argument("--config", type=str, default=None,
                                help="Path to config file")
    journal_parser.add_argument("-p", "--period", type=str, default=None,
                                help="Filter by period (e.g. 2026-03, thisweek, last7days)")
    journal_parser.add_argument("--format", type=str, default="pretty", choices=["pretty", "json"],
                                help="Output format (default: pretty)")
    journal_parser.add_argument("--stats", action="store_true",
                                help="Show speaker stats and meeting counts by month")
    journal_parser.add_argument("--render-obsidian", type=str, default=None, metavar="PATH",
                                help="Generate Obsidian Meeting-Journal.md at PATH")
    journal_parser.add_argument("--verbose", action="store_true",
                                help="Enable verbose debug output")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate API token")
    validate_parser.add_argument("--token-file", type=str, default=None,
                                 help="Path to token file (default: ~/.secrets/plaud.txt)")
    validate_parser.add_argument("--config", type=str, default=None,
                                 help="Path to config file (default: ~/.config/plaud-sync/config.json)")
    validate_parser.add_argument("--verbose", action="store_true",
                                 help="Enable verbose debug output")

    return parser


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def _handle_sync(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)

    config = load_config(args.config)
    if args.folder:
        config.sync_folder = args.folder

    token = load_token(args.token_file)
    api = PlaudApiClient(token=token, api_domain=config.api_domain)

    vault_path = Path(args.vault).resolve()
    if not vault_path.is_dir():
        print(f"Error: vault path does not exist: {vault_path}", file=sys.stderr)
        return 1

    period_range = _resolve_period(args)
    if period_range is None and hasattr(args, "_period_error"):
        return 1

    try:
        summary = run_sync(api, vault_path, config, verbose=args.verbose,
                           period=period_range)
    except PlaudApiError as e:
        return _handle_api_error(e)

    if args.verbose or summary.created or summary.updated or summary.failed:
        print(f"Sync complete: {summary.created} created, {summary.updated} updated, "
              f"{summary.skipped} skipped, {summary.failed} failed")

    if summary.failures:
        for f in summary.failures:
            print(f"  Failed: {f['fileId']}: {f['message']}", file=sys.stderr)

    return 1 if summary.failed else 0


def _handle_validate(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)

    config = load_config(args.config)
    token = load_token(args.token_file)
    api = PlaudApiClient(token=token, api_domain=config.api_domain)

    try:
        api.validate_token()
        print("Token is valid.")
        return 0
    except PlaudApiError as e:
        return _handle_api_error(e)


def _resolve_period(args: argparse.Namespace) -> tuple | None:
    """Parse --period flag if present. Returns (start, end) or None."""
    if not getattr(args, "period", None):
        return None
    try:
        return parse_period(args.period)
    except PeriodParseError as e:
        print(f"Invalid period: {e}", file=sys.stderr)
        args._period_error = True
        return None


def _handle_list(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)

    config = load_config(args.config)
    token = load_token(args.token_file)
    api = PlaudApiClient(token=token, api_domain=config.api_domain)

    period_range = _resolve_period(args)
    if period_range is None and hasattr(args, "_period_error"):
        return 1

    try:
        files = api.list_files()
    except PlaudApiError as e:
        return _handle_api_error(e)

    # Filter by period if specified
    if period_range:
        files = filter_by_period(files, period_range[0], period_range[1])

    # Filter out trash
    files = [f for f in files if not f.get("is_trash")]

    # Sort by start_time descending
    files.sort(key=lambda f: f.get("start_time", 0), reverse=True)

    if not files:
        print("No recordings found.")
        return 0

    print(f"Found {len(files)} recording(s):\n")
    for f in files:
        file_id = f.get("file_id") or f.get("id", "?")
        title = f.get("file_name") or f.get("title") or "Untitled"
        ts = f.get("start_time")
        if isinstance(ts, (int, float)) and ts > 0:
            from datetime import datetime as dt
            date_str = dt.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
        else:
            date_str = "unknown"
        print(f"  {date_str}  {title}  [{file_id}]")

    return 0


def _handle_tui(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)

    from plaud_sync.tui import TuiError, run_tui

    try:
        config = load_config(args.config)
        if args.folder:
            config.sync_folder = args.folder

        token = load_token(args.token_file)
        api = PlaudApiClient(token=token, api_domain=config.api_domain)

        vault_path = Path(args.vault).resolve()
        sync_folder = vault_path / config.sync_folder

        period_range = _resolve_period(args)
        if period_range is None and hasattr(args, "_period_error"):
            return 1

        files = api.list_files()

        if period_range:
            files = filter_by_period(files, period_range[0], period_range[1])

        files = [f for f in files if not f.get("is_trash")]

        run_tui(files, sync_folder=sync_folder, api=api)
        return 0
    except TuiError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except PlaudApiError as e:
        return _handle_api_error(e)


def _handle_analyze(args: argparse.Namespace) -> int:
    _setup_logging(getattr(args, "verbose", False))

    from plaud_sync.analyze import AnalyzeError, NoLlmConfigError, run_analysis

    # Read transcript from file or treat as recording ID
    file_arg = args.file
    transcript = ""

    path = Path(file_arg)
    if path.is_file():
        content = path.read_text()
        # Extract transcript section from markdown
        if "## Transcript" in content:
            transcript = content.split("## Transcript", 1)[1].strip()
        else:
            transcript = content
    else:
        print(f"File not found: {file_arg}", file=sys.stderr)
        return 1

    if not transcript.strip():
        print("No transcript content found.", file=sys.stderr)
        return 1

    try:
        result = run_analysis(
            transcript=transcript,
            template_name=args.template,
            extra_prompt=args.prompt,
            config_path=args.config,
        )
        print(result)
        return 0
    except NoLlmConfigError as e:
        print(f"LLM not configured: {e}", file=sys.stderr)
        return 1
    except AnalyzeError as e:
        print(f"Analysis failed: {e}", file=sys.stderr)
        return 1


def _handle_templates(args: argparse.Namespace) -> int:
    from plaud_sync.analyze import AnalyzeError, list_templates, load_template

    cmd = getattr(args, "templates_command", None)
    if cmd == "list":
        templates = list_templates()
        if not templates:
            print("No templates found.")
            return 0
        for t in templates:
            print(f"  {t['name']:20s}  ({t['source']})")
        return 0
    elif cmd == "show":
        try:
            content = load_template(args.name)
            print(content)
            return 0
        except AnalyzeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        print("Usage: plaud-sync templates {list|show <name>}", file=sys.stderr)
        return 1


def _handle_journal(args: argparse.Namespace) -> int:
    _setup_logging(getattr(args, "verbose", False))

    import json
    from collections import Counter
    from plaud_sync.journal import read_journal, render_obsidian, JOURNAL_FILENAME

    config = load_config(args.config)
    if args.folder:
        config.sync_folder = args.folder

    vault_path = Path(args.vault).resolve()
    journal_path = vault_path / config.sync_folder / JOURNAL_FILENAME

    entries = read_journal(journal_path)
    if not entries:
        print("No journal entries found.")
        return 0

    # Filter by period
    period_range = _resolve_period(args)
    if period_range is None and hasattr(args, "_period_error"):
        return 1

    if period_range:
        from datetime import datetime
        start, end = period_range
        filtered = []
        for e in entries:
            date_str = e.get("date", "")
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d")
                if start <= d < end:
                    filtered.append(e)
            except ValueError:
                continue
        entries = filtered

    if args.render_obsidian:
        obsidian_path = Path(args.render_obsidian)
        md = render_obsidian(entries)
        obsidian_path.write_text(md)
        print(f"Written {len(entries)} entries to {obsidian_path}")
        return 0

    if args.stats:
        return _print_journal_stats(entries)

    if args.format == "json":
        for e in entries:
            print(json.dumps(e, ensure_ascii=False))
        return 0

    # Pretty print last 20
    for e in entries[-20:]:
        date = e.get("date", "?")
        title = e.get("title", "Untitled")
        dur = e.get("duration_min", 0)
        speakers = ", ".join(e.get("speakers", []))
        words = e.get("word_count", 0)
        print(f"  {date}  {title} ({dur} min, {words} words)")
        if speakers:
            print(f"           Speakers: {speakers}")

    print(f"\n{len(entries)} entries total.")
    return 0


def _print_journal_stats(entries: list[dict]) -> int:
    """Print speaker stats and meeting counts by month."""
    from collections import Counter

    if not entries:
        print("No entries.")
        return 0

    # Meetings by month
    month_counts: Counter[str] = Counter()
    speaker_counts: Counter[str] = Counter()
    total_words = 0
    total_duration = 0

    for e in entries:
        date = e.get("date", "")
        if len(date) >= 7:
            month_counts[date[:7]] += 1
        for s in e.get("speakers", []):
            speaker_counts[s] += 1
        total_words += e.get("word_count", 0)
        total_duration += e.get("duration_min", 0)

    print(f"Total: {len(entries)} meetings, {total_duration} min, {total_words} words\n")

    print("Meetings by month:")
    for month, count in sorted(month_counts.items()):
        print(f"  {month}: {count}")

    if speaker_counts:
        print("\nSpeaker frequency:")
        for speaker, count in speaker_counts.most_common():
            print(f"  {speaker}: {count}")

    return 0


def _handle_api_error(e: PlaudApiError) -> int:
    if e.category == "auth":
        print(f"Authentication failed: {e}. Check your token.", file=sys.stderr)
        return 2
    if e.category == "rate_limit":
        print(f"Rate limited: {e}. Wait and retry.", file=sys.stderr)
        return 1
    if e.category == "network":
        print(f"Network error: {e}. Check your connection.", file=sys.stderr)
        return 1
    print(f"API error: {e}. Try again shortly.", file=sys.stderr)
    return 1


def main() -> None:
    """Main entry point for the CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "sync":
        sys.exit(_handle_sync(args))
    elif args.command == "list":
        sys.exit(_handle_list(args))
    elif args.command == "tui":
        sys.exit(_handle_tui(args))
    elif args.command == "analyze":
        sys.exit(_handle_analyze(args))
    elif args.command == "templates":
        sys.exit(_handle_templates(args))
    elif args.command == "journal":
        sys.exit(_handle_journal(args))
    elif args.command == "validate":
        sys.exit(_handle_validate(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
