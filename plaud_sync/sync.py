"""Incremental sync orchestration for Plaud recordings."""

from __future__ import annotations

import re
import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from plaud_sync.api import PlaudApiClient
from plaud_sync.hydrator import hydrate
from plaud_sync.normalizer import normalize, NormalizedDetail
from plaud_sync.renderer import render_markdown
from plaud_sync.config import Config, load_state, save_state, STATE_FILENAME
from plaud_sync.journal import JOURNAL_FILENAME, append_or_update, build_journal_entry
from plaud_sync.period import filter_by_period

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_FILE_ID_RE = re.compile(r"file_id:\s*[\"']?([^\"'\n]+)[\"']?")


@dataclass
class SyncSummary:
    """Summary of a sync operation."""
    listed: int = 0
    selected: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    last_sync_at_ms_before: int = 0
    last_sync_at_ms_after: int = 0
    failures: list[dict[str, str]] = field(default_factory=list)


def _slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    # Collapse consecutive hyphens
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "recording"


def _make_filename(pattern: str, detail: NormalizedDetail) -> str:
    """Generate a filename from the pattern and detail."""
    from plaud_sync.renderer import _format_date
    date = _format_date(detail.start_at_ms)
    title_slug = _slugify(detail.title)
    name = pattern.replace("{date}", date).replace("{title}", title_slug)
    return f"{name}.md"


def _read_file_id(filepath: Path) -> str | None:
    """Read file_id from YAML frontmatter of a markdown file."""
    try:
        with open(filepath) as f:
            content = f.read(1024)  # Only need frontmatter
    except OSError:
        return None

    if not content.startswith("---"):
        return None

    end = content.find("---", 3)
    if end == -1:
        return None

    frontmatter = content[3:end]
    match = _FILE_ID_RE.search(frontmatter)
    if match:
        return match.group(1).strip()
    return None


def _find_existing_file(folder: Path, file_id: str) -> Path | None:
    """Find an existing markdown file with the given file_id."""
    if not folder.exists():
        return None
    for md_file in folder.glob("*.md"):
        existing_id = _read_file_id(md_file)
        if existing_id == file_id:
            return md_file
    return None


def _resolve_collision(folder: Path, filename: str) -> str:
    """If filename already exists, append -2, -3, etc."""
    path = folder / filename
    if not path.exists():
        return filename

    base = filename.rsplit(".md", 1)[0]
    counter = 2
    while True:
        candidate = f"{base}-{counter}.md"
        if not (folder / candidate).exists():
            return candidate
        counter += 1


def _should_sync_file(file_summary: dict, checkpoint: int) -> bool:
    """Determine if a file should be synced based on checkpoint."""
    if file_summary.get("is_trash"):
        return False
    start_time = file_summary.get("start_time")
    if start_time is None:
        return True  # Always sync files with missing start_time
    if isinstance(start_time, (int, float)) and start_time > checkpoint:
        return True
    return False


def run_sync(
    api: PlaudApiClient,
    vault_path: Path,
    config: Config,
    verbose: bool = False,
    period: tuple | None = None,
) -> SyncSummary:
    """Run incremental sync of Plaud recordings to local markdown files.

    Args:
        api: Authenticated Plaud API client.
        vault_path: Base path for the vault.
        config: Sync configuration.
        verbose: Enable verbose logging.

    Returns:
        SyncSummary with counts and any failures.
    """
    sync_folder = vault_path / config.sync_folder
    sync_folder.mkdir(parents=True, exist_ok=True)

    state_path = sync_folder / STATE_FILENAME
    state = load_state(state_path)
    checkpoint = state.get("lastSyncAtMs", 0)

    summary = SyncSummary(last_sync_at_ms_before=checkpoint)

    # List all files
    all_files = api.list_files()
    summary.listed = len(all_files)

    # Filter by period if specified
    if period:
        all_files = filter_by_period(all_files, period[0], period[1])

    # Filter by checkpoint and trash
    selected = [f for f in all_files if _should_sync_file(f, checkpoint)]
    summary.selected = len(selected)

    if verbose:
        logger.info("Listed %d files, selected %d for sync (checkpoint=%d)",
                     summary.listed, summary.selected, checkpoint)

    max_start_time = checkpoint
    any_failure = False

    for file_summary in selected:
        file_id = file_summary.get("file_id") or file_summary.get("id", "unknown")
        try:
            # Fetch detail
            detail = api.get_file_detail(file_id)

            # Hydrate content from signed URLs
            detail = hydrate(detail)

            # Normalize
            normalized = normalize(detail)

            # Render markdown
            markdown = render_markdown(normalized)

            # Check for existing file with same file_id
            existing = _find_existing_file(sync_folder, normalized.file_id)

            journal_path = sync_folder / JOURNAL_FILENAME

            if existing:
                if config.update_existing:
                    existing.write_text(markdown)
                    summary.updated += 1
                    if verbose:
                        logger.info("Updated: %s", existing.name)
                    entry = build_journal_entry(normalized, existing.name)
                    append_or_update(journal_path, entry)
                else:
                    summary.skipped += 1
                    if verbose:
                        logger.info("Skipped (exists): %s", existing.name)
            else:
                filename = _make_filename(config.filename_pattern, normalized)
                filename = _resolve_collision(sync_folder, filename)
                filepath = sync_folder / filename
                filepath.write_text(markdown)
                summary.created += 1
                if verbose:
                    logger.info("Created: %s", filename)
                entry = build_journal_entry(normalized, filename)
                append_or_update(journal_path, entry)

            # Track max start_time
            start_time = file_summary.get("start_time")
            if isinstance(start_time, (int, float)) and start_time > max_start_time:
                max_start_time = int(start_time)

        except Exception as e:
            summary.failed += 1
            summary.failures.append({"fileId": file_id, "message": str(e)})
            any_failure = True
            logger.error("Failed to sync %s: %s", file_id, e)

    # Only update checkpoint if no failures
    if not any_failure and max_start_time > checkpoint:
        state["lastSyncAtMs"] = max_start_time
        save_state(state_path, state)

    summary.last_sync_at_ms_after = state.get("lastSyncAtMs", checkpoint)
    return summary
