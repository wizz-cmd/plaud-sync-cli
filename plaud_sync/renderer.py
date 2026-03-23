"""Render normalized Plaud recording data to markdown."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from plaud_sync.normalizer import NormalizedDetail

_MD_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _format_date(timestamp_ms: int) -> str:
    """Format millisecond timestamp to YYYY-MM-DD."""
    try:
        if timestamp_ms <= 0:
            return "1970-01-01"
        dt = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except (OSError, OverflowError, ValueError):
        return "1970-01-01"


def _format_duration(duration_ms: int) -> str:
    """Format millisecond duration to 'N min'."""
    if duration_ms <= 0:
        return "0 min"
    minutes = round(duration_ms / 60000)
    return f"{minutes} min"


def _escape_title(title: str) -> str:
    """Escape double quotes in title for YAML frontmatter."""
    return title.replace('"', '\\"')


def _format_timestamp(ms: int | float) -> str:
    """Convert milliseconds to MM:SS format."""
    if not isinstance(ms, (int, float)) or ms < 0:
        return "00:00"
    total_seconds = int(ms / 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def _flatten_summary(summary: str) -> str:
    """Strip markdown headings from summary and return plain text."""
    text = _MD_HEADING_RE.sub("", summary)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _summary_preview(summary: str, sentences: int = 3) -> str:
    """Return first N sentences of flattened summary."""
    flat = _flatten_summary(summary)
    if not flat:
        return ""
    parts = _SENTENCE_RE.split(flat)
    preview = ". ".join(p.rstrip(".") for p in parts[:sentences])
    if not preview.endswith((".", "!", "?")):
        preview += "."
    return preview


def _render_transcript_from_segments(segments: list[dict[str, Any]]) -> str:
    """Render transcript with speaker attribution and timestamps.

    Groups consecutive segments by same speaker into one paragraph.
    """
    if not segments:
        return "Kein Transcript verfügbar."

    blocks: list[str] = []
    current_speaker: str | None = None
    current_texts: list[str] = []
    current_ts: str = "00:00"

    for seg in segments:
        speaker = seg.get("speaker", "").strip()
        content = seg.get("content", "").strip()
        if not content:
            continue

        if speaker == current_speaker:
            current_texts.append(content)
        else:
            # Flush previous block
            if current_texts:
                header = f"**{current_speaker}** ({current_ts})" if current_speaker else f"({current_ts})"
                blocks.append(f"{header}\n{' '.join(current_texts)}")
            current_speaker = speaker
            current_texts = [content]
            current_ts = _format_timestamp(seg.get("start_time", 0))

    # Flush last block
    if current_texts:
        header = f"**{current_speaker}** ({current_ts})" if current_speaker else f"({current_ts})"
        blocks.append(f"{header}\n{' '.join(current_texts)}")

    return "\n\n".join(blocks)


def render_markdown(detail: NormalizedDetail) -> str:
    """Render a normalized recording detail to markdown with YAML frontmatter.

    Args:
        detail: Normalized recording detail.

    Returns:
        Markdown string with frontmatter, summary blockquote, and transcript.
    """
    title = detail.title or "Untitled recording"
    date = _format_date(detail.start_at_ms)
    duration = _format_duration(detail.duration_ms)

    lines = [
        "---",
        "source: plaud",
        "type: recording",
        f"file_id: {detail.file_id}",
        f'title: "{_escape_title(title)}"',
        f"date: {date}",
        f"duration: {duration}",
    ]

    # Speakers in frontmatter
    if detail.speakers:
        lines.append("speakers:")
        for s in detail.speakers:
            lines.append(f"  - {s}")

    lines.extend([
        "---",
        "",
        f"# {title}",
        "",
    ])

    # Summary as blockquote (plain text, first 2-3 sentences)
    if detail.summary:
        preview = _summary_preview(detail.summary)
        if preview:
            lines.append(f"> **Zusammenfassung:** {preview}")
            lines.append("")

    # Transcript
    lines.append("## Transcript")
    lines.append("")

    if detail.segments:
        lines.append(_render_transcript_from_segments(detail.segments))
    elif detail.transcript:
        lines.append(detail.transcript)
    else:
        lines.append("Kein Transcript verfügbar.")

    lines.append("")

    return "\n".join(lines)
