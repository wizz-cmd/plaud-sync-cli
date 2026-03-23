"""Normalize raw Plaud API detail into a clean data structure."""

from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]*>")
_MD_IMAGE_RE = re.compile(r"!\[.*?\]\(.*?\)")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class NormalizedDetail:
    """Normalized recording detail."""
    id: str
    file_id: str
    title: str
    start_at_ms: int
    duration_ms: int
    summary: str
    highlights: list[str]
    transcript: str
    raw: dict[str, Any]
    speakers: list[str] = field(default_factory=list)
    segments: list[dict[str, Any]] = field(default_factory=list)


def _strip_markup(text: str) -> str:
    """Remove HTML tags, markdown images, and collapse whitespace."""
    text = _HTML_TAG_RE.sub("", text)
    text = _MD_IMAGE_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _extract_str(detail: dict, *keys: str) -> str:
    """Return first non-empty string value from the given keys."""
    for key in keys:
        val = detail.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _extract_int(detail: dict, *keys: str) -> int:
    """Return first valid integer value from the given keys."""
    for key in keys:
        val = detail.get(key)
        if isinstance(val, (int, float)) and val == val:  # exclude NaN
            return int(val)
        if isinstance(val, str):
            try:
                return int(val)
            except ValueError:
                continue
    return 0


def _extract_title(detail: dict) -> str:
    """Extract recording title from detail."""
    title = _extract_str(detail, "file_name", "filename", "title")
    if title:
        return _strip_markup(title)
    return "Untitled recording"


def _extract_id(detail: dict) -> str:
    """Extract the primary ID."""
    return _extract_str(detail, "id") or "unknown"


def _extract_file_id(detail: dict) -> str:
    """Extract the file ID (preferred) or fall back to id."""
    return _extract_str(detail, "file_id", "id") or "unknown"


def _parse_highlights(value: Any) -> list[str]:
    """Parse highlights from various formats."""
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        # Try JSON parse first
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return _parse_highlights(parsed)
        except (json.JSONDecodeError, ValueError):
            pass
        # Split by newlines
        lines = value.split("\n")
        result = []
        for line in lines:
            line = line.strip()
            line = re.sub(r"^[-*]\s*", "", line)
            if line:
                result.append(_strip_markup(line))
        return result

    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(_strip_markup(item.strip()))
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("value", "")
                if isinstance(text, str) and text.strip():
                    result.append(_strip_markup(text.strip()))
        return result

    return []


def _extract_highlights(detail: dict) -> list[str]:
    """Extract highlights from various locations in detail."""
    sources = [
        detail.get("highlights"),
        (detail.get("ai_content") or {}).get("highlights") if isinstance(detail.get("ai_content"), dict) else None,
        (detail.get("ai_notes") or {}).get("key_points") if isinstance(detail.get("ai_notes"), dict) else None,
    ]
    for source in sources:
        if source is not None:
            result = _parse_highlights(source)
            if result:
                return result

    # Check pre_download_content_list
    content_list = detail.get("pre_download_content_list")
    if isinstance(content_list, list):
        for item in content_list:
            if not isinstance(item, dict):
                continue
            data_id = str(item.get("data_id", ""))
            if data_id.startswith("note:"):
                text = item.get("content") or item.get("text", "")
                if isinstance(text, str) and text.strip():
                    return _parse_highlights(text)

    return []


def _extract_summary(detail: dict) -> str:
    """Extract summary from various locations in detail."""
    # Direct summary
    summary = _extract_str(detail, "summary")
    if summary:
        return _strip_markup(summary)

    # Nested in ai_content
    ai_content = detail.get("ai_content")
    if isinstance(ai_content, dict):
        s = _extract_str(ai_content, "summary")
        if s:
            return _strip_markup(s)

    # Nested in ai_notes
    ai_notes = detail.get("ai_notes")
    if isinstance(ai_notes, dict):
        s = _extract_str(ai_notes, "summary", "abstract")
        if s:
            return _strip_markup(s)

    # From pre_download_content_list
    content_list = detail.get("pre_download_content_list")
    if isinstance(content_list, list):
        for item in content_list:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type", "")).lower()
            data_id = str(item.get("data_id", "")).lower()
            if "summary" in item_type or "abstract" in item_type or \
               data_id.startswith("auto_sum:") or "summary" in data_id:
                text = item.get("content") or item.get("text", "")
                if isinstance(text, str) and text.strip():
                    return _strip_markup(text.strip())

    return ""


def _format_speaker_line(speaker: Any, text: str) -> str:
    """Format a single speaker line."""
    if speaker:
        return f"{speaker}: {text}"
    return text


def _extract_transcript(detail: dict) -> str:
    """Extract transcript from various locations in detail."""
    trans = detail.get("trans_result")
    if isinstance(trans, dict):
        full = trans.get("full_text")
        if isinstance(full, str) and full.strip():
            return full.strip()

        # Paragraphs
        paras = trans.get("paragraphs")
        if isinstance(paras, list) and paras:
            lines = []
            for p in paras:
                if isinstance(p, dict):
                    text = p.get("text", "")
                    speaker = p.get("speaker", "")
                    if text:
                        lines.append(_format_speaker_line(speaker, text))
                elif isinstance(p, str):
                    lines.append(p)
            if lines:
                return "\n\n".join(lines)

        # Sentences
        sents = trans.get("sentences")
        if isinstance(sents, list) and sents:
            lines = []
            for s in sents:
                if isinstance(s, dict):
                    text = s.get("text", "")
                    speaker = s.get("speaker", "")
                    if text:
                        lines.append(_format_speaker_line(speaker, text))
                elif isinstance(s, str):
                    lines.append(s)
            if lines:
                return "\n\n".join(lines)

    # Direct fields
    for key in ("full_text", "transcript_text"):
        val = detail.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    # Transcript array
    transcript = detail.get("transcript")
    if isinstance(transcript, list) and transcript:
        lines = []
        for item in transcript:
            if isinstance(item, dict):
                text = item.get("text", "")
                speaker = item.get("speaker", "")
                if text:
                    lines.append(_format_speaker_line(speaker, text))
            elif isinstance(item, str):
                lines.append(item)
        if lines:
            return "\n\n".join(lines)

    # Paragraphs at top level
    paras = detail.get("paragraphs")
    if isinstance(paras, list) and paras:
        lines = []
        for p in paras:
            if isinstance(p, dict):
                text = p.get("text", "")
                speaker = p.get("speaker", "")
                if text:
                    lines.append(_format_speaker_line(speaker, text))
            elif isinstance(p, str):
                lines.append(p)
        if lines:
            return "\n\n".join(lines)

    return ""


def _extract_segments(detail: dict) -> list[dict[str, Any]]:
    """Extract raw transcript segments with timestamps.

    Returns list of dicts with keys: content, speaker, start_time, end_time.
    """
    # trans_result may be a list of segments directly (from hydrator)
    trans = detail.get("trans_result")
    if isinstance(trans, list):
        segments = []
        for seg in trans:
            if isinstance(seg, dict) and seg.get("content", "").strip():
                segments.append({
                    "content": seg.get("content", "").strip(),
                    "speaker": seg.get("speaker", "").strip(),
                    "original_speaker": seg.get("original_speaker", "").strip(),
                    "start_time": seg.get("start_time", 0),
                    "end_time": seg.get("end_time", 0),
                })
        return segments

    # trans_result as dict with paragraphs/sentences
    if isinstance(trans, dict):
        for key in ("paragraphs", "sentences"):
            items = trans.get(key)
            if isinstance(items, list) and items:
                segments = []
                for item in items:
                    if isinstance(item, dict) and item.get("text", "").strip():
                        segments.append({
                            "content": item.get("text", "").strip(),
                            "speaker": item.get("speaker", "").strip(),
                            "original_speaker": item.get("original_speaker", "").strip(),
                            "start_time": item.get("start_time", 0),
                            "end_time": item.get("end_time", 0),
                        })
                if segments:
                    return segments

    # Top-level transcript array
    transcript = detail.get("transcript")
    if isinstance(transcript, list) and transcript:
        segments = []
        for item in transcript:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content", "")
                if text.strip():
                    segments.append({
                        "content": text.strip(),
                        "speaker": (item.get("speaker") or "").strip(),
                        "original_speaker": (item.get("original_speaker") or "").strip(),
                        "start_time": item.get("start_time", 0),
                        "end_time": item.get("end_time", 0),
                    })
        if segments:
            return segments

    return []


def _extract_speakers(segments: list[dict[str, Any]]) -> list[str]:
    """Extract deduplicated speaker list from segments.

    Named speakers first, then 'Speaker N' style at the end.
    """
    seen: set[str] = set()
    named: list[str] = []
    generic: list[str] = []

    for seg in segments:
        speaker = seg.get("speaker", "").strip()
        if not speaker or speaker in seen:
            continue
        seen.add(speaker)
        if re.match(r"^Speaker\s+\d+$", speaker, re.IGNORECASE):
            generic.append(speaker)
        else:
            named.append(speaker)

    return named + generic


def normalize(detail: dict) -> NormalizedDetail:
    """Normalize a raw Plaud API file detail into a clean structure.

    Args:
        detail: Raw detail dict from the Plaud API.

    Returns:
        NormalizedDetail with extracted and cleaned fields.
    """
    segments = _extract_segments(detail)
    speakers = _extract_speakers(segments)
    return NormalizedDetail(
        id=_extract_id(detail),
        file_id=_extract_file_id(detail),
        title=_extract_title(detail),
        start_at_ms=_extract_int(detail, "start_time"),
        duration_ms=_extract_int(detail, "duration"),
        summary=_extract_summary(detail),
        highlights=_extract_highlights(detail),
        transcript=_extract_transcript(detail),
        raw=detail,
        speakers=speakers,
        segments=segments,
    )
