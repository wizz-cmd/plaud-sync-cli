"""CLI entry point for Plaud Sync."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from plaud_sync import __version__
from plaud_sync.api import PlaudApiClient
from plaud_sync.config import Config, load_config, load_token
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
    sync_parser.add_argument("--verbose", action="store_true",
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

    try:
        summary = run_sync(api, vault_path, config, verbose=args.verbose)
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
    elif args.command == "validate":
        sys.exit(_handle_validate(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
