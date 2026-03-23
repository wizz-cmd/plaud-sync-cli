"""Append-only JSONL meeting journal."""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from plaud_sync.normalizer import NormalizedDetail
from plaud_sync.renderer import _flatten_summary

logger = logging.getLogger(__name__)

JOURNAL_FILENAME = "meeting-journal.jsonl"


def _word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split()) if text.strip() else 0


def _summary_preview(summary: str, max_chars: int = 150) -> str:
    """First max_chars characters of flattened summary."""
    flat = _flatten_summary(summary)
    if len(flat) <= max_chars:
        return flat
    return flat[:max_chars].rsplit(" ", 1)[0] + "..."


def build_journal_entry(
    detail: NormalizedDetail,
    filename: str,
) -> dict[str, Any]:
    """Build a journal entry dict from a normalized detail.

    Args:
        detail: Normalized recording detail.
        filename: The .md filename written to disk.

    Returns:
        Dict ready to be serialized as a JSONL line.
    """
    from plaud_sync.renderer import _format_date, _format_duration

    duration_min = round(detail.duration_ms / 60000) if detail.duration_ms > 0 else 0

    return {
        "meeting_id": detail.file_id,
        "date": _format_date(detail.start_at_ms),
        "title": detail.title,
        "duration_min": duration_min,
        "speakers": detail.speakers,
        "has_transcript": bool(detail.transcript or detail.segments),
        "has_summary": bool(detail.summary),
        "summary_preview": _summary_preview(detail.summary) if detail.summary else "",
        "file": filename,
        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "word_count": _word_count(detail.transcript),
    }


def append_or_update(journal_path: Path, entry: dict[str, Any]) -> None:
    """Append a new entry or update existing entry by meeting_id.

    Args:
        journal_path: Path to the JSONL file.
        entry: Journal entry dict.
    """
    meeting_id = entry["meeting_id"]
    entries: list[dict[str, Any]] = []
    found = False

    if journal_path.exists():
        for line in journal_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing = json.loads(line)
                if existing.get("meeting_id") == meeting_id:
                    entries.append(entry)
                    found = True
                else:
                    entries.append(existing)
            except json.JSONDecodeError:
                entries.append(json.loads(line) if line else {})

    if not found:
        entries.append(entry)

    lines = [json.dumps(e, ensure_ascii=False) for e in entries]
    journal_path.write_text("\n".join(lines) + "\n")


def read_journal(journal_path: Path) -> list[dict[str, Any]]:
    """Read all entries from a JSONL journal file.

    Args:
        journal_path: Path to the JSONL file.

    Returns:
        List of journal entry dicts.
    """
    if not journal_path.exists():
        return []

    entries: list[dict[str, Any]] = []
    for line in journal_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("Skipping invalid JSONL line: %s", line[:80])
    return entries


def _slugify_filename(filename: str) -> str:
    """Convert filename to wikilink-safe name (strip .md extension)."""
    return filename.removesuffix(".md")


def render_obsidian(entries: list[dict[str, Any]]) -> str:
    """Render journal entries as an Obsidian-compatible Meeting-Journal.md.

    Groups meetings by month, includes speaker index and wikilinks.

    Args:
        entries: List of journal entry dicts.

    Returns:
        Markdown string for the Obsidian meeting journal.
    """
    if not entries:
        return "# Meeting Journal\n\nNo meetings recorded yet.\n"

    # Sort by date descending
    sorted_entries = sorted(entries, key=lambda e: e.get("date", ""), reverse=True)

    # Group by month
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in sorted_entries:
        date = e.get("date", "")
        month = date[:7] if len(date) >= 7 else "Unknown"
        by_month[month].append(e)

    # Collect all speakers
    speaker_counts: dict[str, int] = defaultdict(int)
    for e in sorted_entries:
        for s in e.get("speakers", []):
            speaker_counts[s] += 1

    lines = ["# Meeting Journal", ""]

    # Speaker index
    if speaker_counts:
        lines.append("## Speakers")
        lines.append("")
        for speaker, count in sorted(speaker_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- **{speaker}** ({count} meetings)")
        lines.append("")

    # Meetings by month
    for month in sorted(by_month.keys(), reverse=True):
        month_entries = by_month[month]
        lines.append(f"## {month}")
        lines.append("")
        lines.append("| Date | Title | Duration | Speakers |")
        lines.append("|------|-------|----------|----------|")
        for e in month_entries:
            date = e.get("date", "?")
            title = e.get("title", "Untitled")
            filename = e.get("file", "")
            if filename:
                link = f"[[{_slugify_filename(filename)}|{title}]]"
            else:
                link = title
            dur = f"{e.get('duration_min', 0)} min"
            speakers = ", ".join(e.get("speakers", []))
            lines.append(f"| {date} | {link} | {dur} | {speakers} |")
        lines.append("")

    # Summary stats
    total = len(sorted_entries)
    total_dur = sum(e.get("duration_min", 0) for e in sorted_entries)
    total_words = sum(e.get("word_count", 0) for e in sorted_entries)
    lines.append("---")
    lines.append(f"*{total} meetings, {total_dur} min total, {total_words} words transcribed*")
    lines.append("")

    return "\n".join(lines)
