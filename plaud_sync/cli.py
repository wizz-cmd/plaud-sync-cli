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
    elif args.command == "validate":
        sys.exit(_handle_validate(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
