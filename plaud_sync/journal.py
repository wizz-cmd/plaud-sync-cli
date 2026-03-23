"""Append-only JSONL meeting journal."""

from __future__ import annotations

import json
import logging
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
