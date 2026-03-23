"""Content hydration - fetch full content from signed URLs in recording details."""

from __future__ import annotations

import gzip
import json
import logging
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _fetch_url(url: str) -> str:
    """Fetch text content from a URL. Handles gzip. Returns empty string on failure."""
    try:
        req = Request(url, headers={"User-Agent": _USER_AGENT})
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
        # Try gzip decompression (Plaud S3 URLs are .json.gz)
        try:
            return gzip.decompress(raw).decode("utf-8")
        except (gzip.BadGzipFile, OSError):
            return raw.decode("utf-8")
    except Exception as e:
        logger.debug("Failed to fetch %s: %s", url[:80], e)
        return ""


def _find_content_url(detail: dict, content_type: str) -> str | None:
    """Find a signed URL for the given content type in content_list.

    Plaud API uses 'data_type' and 'data_link' as field names.
    Falls back to 'type' and 'url'/'signed_url' for compatibility.
    """
    content_list = detail.get("content_list")
    if not isinstance(content_list, list):
        return None

    for item in content_list:
        if not isinstance(item, dict):
            continue
        # Primary: data_type / data_link (current Plaud API)
        item_type = item.get("data_type") or item.get("type", "")
        if item_type == content_type:
            url = (item.get("data_link") or item.get("url")
                   or item.get("signed_url") or item.get("download_url", ""))
            if url:
                return url
    return None


def _segments_to_text(segments: list[dict]) -> str:
    """Convert transcript segments array to readable text.

    Each segment has: content, speaker (optional), start_time, end_time.
    Groups consecutive segments by speaker.
    """
    lines = []
    current_speaker = None
    for seg in segments:
        content = seg.get("content", "").strip()
        if not content:
            continue
        speaker = seg.get("speaker", "").strip()
        if speaker and speaker != current_speaker:
            lines.append(f"\n**{speaker}:** {content}")
            current_speaker = speaker
        elif speaker:
            lines.append(content)
        else:
            lines.append(content)
    return " ".join(lines).strip()


def hydrate(detail: dict) -> dict:
    """Enrich a file detail by fetching content from signed URLs.

    Fetches summary (auto_sum_note) and transcript (transaction) content
    from signed URLs if present. Failures are silently ignored (best-effort).

    Args:
        detail: Raw detail dict from the API.

    Returns:
        Enriched copy of the detail dict with fetched content merged in.
    """
    result = dict(detail)

    # Try to hydrate summary from signed URL
    summary_url = _find_content_url(detail, "auto_sum_note")
    if summary_url:
        content = _fetch_url(summary_url)
        if content:
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    # Plaud uses 'ai_content' for the summary text
                    if "ai_content" in parsed:
                        result.setdefault("summary", parsed["ai_content"])
                    elif "summary" in parsed:
                        result.setdefault("summary", parsed["summary"])
                    if "highlights" in parsed:
                        result.setdefault("highlights", parsed["highlights"])
                    if "key_points" in parsed:
                        result.setdefault("highlights", parsed["key_points"])
                elif isinstance(parsed, str):
                    result.setdefault("summary", parsed)
            except json.JSONDecodeError:
                result.setdefault("summary", content)

    # Try to hydrate transcript from signed URL
    transcript_url = _find_content_url(detail, "transaction")
    if transcript_url:
        content = _fetch_url(transcript_url)
        if content:
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    # Plaud returns transcript as array of segments
                    # [{content, speaker, start_time, end_time}, ...]
                    result.setdefault("full_text", _segments_to_text(parsed))
                    result.setdefault("trans_result", parsed)
                elif isinstance(parsed, dict):
                    if "full_text" in parsed:
                        result.setdefault("full_text", parsed["full_text"])
                    if "paragraphs" in parsed:
                        result.setdefault("paragraphs", parsed["paragraphs"])
                    if "sentences" in parsed:
                        result.setdefault("sentences", parsed["sentences"])
                    if "trans_result" in parsed:
                        result.setdefault("trans_result", parsed["trans_result"])
                elif isinstance(parsed, str):
                    result.setdefault("full_text", parsed)
            except json.JSONDecodeError:
                result.setdefault("full_text", content)

    return result
