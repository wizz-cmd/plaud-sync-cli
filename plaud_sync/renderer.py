"""Render normalized Plaud recording data to markdown."""

from __future__ import annotations

from datetime import datetime, timezone

from plaud_sync.normalizer import NormalizedDetail


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


def render_markdown(detail: NormalizedDetail) -> str:
    """Render a normalized recording detail to markdown with YAML frontmatter.

    Args:
        detail: Normalized recording detail.

    Returns:
        Markdown string with frontmatter, summary, highlights, and transcript.
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
        "---",
        "",
        f"# {title}",
        "",
        "## Summary",
        "",
        detail.summary if detail.summary else "No summary available.",
        "",
        "## Highlights",
        "",
    ]

    if detail.highlights:
        for h in detail.highlights:
            lines.append(f"- {h}")
    else:
        lines.append("- No highlights extracted.")

    lines.append("")
    lines.append("## Transcript")
    lines.append("")
    lines.append(detail.transcript if detail.transcript else "No transcript available.")
    lines.append("")

    return "\n".join(lines)
