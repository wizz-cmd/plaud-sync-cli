"""Tests for plaud_sync.renderer module."""

import pytest
from plaud_sync.normalizer import NormalizedDetail
from plaud_sync.renderer import (
    render_markdown, _format_date, _format_duration, _format_timestamp,
    _flatten_summary, _summary_preview, _render_transcript_from_segments,
)


class TestFormatDate:
    def test_valid_timestamp(self):
        # 2023-11-14 in UTC
        assert _format_date(1700000000000) == "2023-11-14"

    def test_zero_timestamp(self):
        assert _format_date(0) == "1970-01-01"

    def test_negative_timestamp(self):
        assert _format_date(-1) == "1970-01-01"


class TestFormatDuration:
    def test_one_hour(self):
        assert _format_duration(3600000) == "60 min"

    def test_zero(self):
        assert _format_duration(0) == "0 min"

    def test_negative(self):
        assert _format_duration(-1) == "0 min"

    def test_short(self):
        assert _format_duration(90000) == "2 min"


class TestFormatTimestamp:
    def test_zero(self):
        assert _format_timestamp(0) == "00:00"

    def test_one_minute(self):
        assert _format_timestamp(60000) == "01:00"

    def test_mixed(self):
        assert _format_timestamp(75000) == "01:15"

    def test_negative(self):
        assert _format_timestamp(-1) == "00:00"


class TestFlattenSummary:
    def test_strips_headings(self):
        text = "## Heading\nSome text\n### Another\nMore"
        assert "##" not in _flatten_summary(text)
        assert "Heading" in _flatten_summary(text)

    def test_plain_text_unchanged(self):
        assert _flatten_summary("Hello world.") == "Hello world."


class TestSummaryPreview:
    def test_limits_sentences(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        preview = _summary_preview(text, sentences=2)
        assert "Fourth" not in preview

    def test_empty(self):
        assert _summary_preview("") == ""


class TestRenderTranscriptFromSegments:
    def test_groups_same_speaker(self):
        segments = [
            {"speaker": "Alice", "content": "Hello.", "start_time": 0},
            {"speaker": "Alice", "content": "How are you?", "start_time": 5000},
            {"speaker": "Bob", "content": "Fine.", "start_time": 12000},
        ]
        result = _render_transcript_from_segments(segments)
        assert "**Alice** (00:00)" in result
        assert "Hello. How are you?" in result
        assert "**Bob** (00:12)" in result

    def test_empty_segments(self):
        assert _render_transcript_from_segments([]) == "Kein Transcript verfügbar."


class TestRenderMarkdown:
    def _make_detail(self, **kwargs) -> NormalizedDetail:
        defaults = {
            "id": "abc",
            "file_id": "file_abc",
            "title": "Test Recording",
            "start_at_ms": 1700000000000,
            "duration_ms": 3600000,
            "summary": "A test summary.",
            "highlights": ["Point 1", "Point 2"],
            "transcript": "Speaker: Hello world.",
            "raw": {},
            "speakers": ["Alice", "Bob"],
            "segments": [
                {"speaker": "Alice", "content": "Hello world.", "start_time": 0},
                {"speaker": "Bob", "content": "Hi there.", "start_time": 5000},
            ],
        }
        defaults.update(kwargs)
        return NormalizedDetail(**defaults)

    def test_contains_frontmatter(self):
        md = render_markdown(self._make_detail())
        assert "---" in md
        assert "source: plaud" in md
        assert "type: recording" in md
        assert "file_id: file_abc" in md
        assert 'title: "Test Recording"' in md
        assert "date: 2023-11-14" in md
        assert "duration: 60 min" in md

    def test_speakers_in_frontmatter(self):
        md = render_markdown(self._make_detail())
        assert "speakers:" in md
        assert "  - Alice" in md
        assert "  - Bob" in md

    def test_no_speakers_omits_field(self):
        md = render_markdown(self._make_detail(speakers=[]))
        assert "speakers:" not in md

    def test_summary_as_blockquote(self):
        md = render_markdown(self._make_detail())
        assert "> **Zusammenfassung:**" in md
        assert "A test summary." in md

    def test_no_summary_omits_blockquote(self):
        md = render_markdown(self._make_detail(summary=""))
        assert "Zusammenfassung" not in md

    def test_no_highlights_section(self):
        md = render_markdown(self._make_detail())
        assert "## Highlights" not in md

    def test_contains_transcript(self):
        md = render_markdown(self._make_detail())
        assert "## Transcript" in md
        assert "**Alice** (00:00)" in md
        assert "**Bob** (00:05)" in md

    def test_no_segments_falls_back_to_transcript(self):
        md = render_markdown(self._make_detail(segments=[], transcript="Plain text transcript."))
        assert "Plain text transcript." in md

    def test_no_transcript_fallback(self):
        md = render_markdown(self._make_detail(segments=[], transcript=""))
        assert "Kein Transcript verfügbar." in md

    def test_title_with_quotes_escaped(self):
        md = render_markdown(self._make_detail(title='Say "hello"'))
        assert 'title: "Say \\"hello\\""' in md

    def test_summary_headings_stripped(self):
        md = render_markdown(self._make_detail(
            summary="## Gesprächszusammenfassung\n### Die Stimmung\nNachdenklich."
        ))
        assert "##" not in md.split("## Transcript")[0].split("---")[-1]
        assert "Nachdenklich" in md
