"""Tests for plaud_sync.renderer module."""

import pytest
from plaud_sync.normalizer import NormalizedDetail
from plaud_sync.renderer import render_markdown, _format_date, _format_duration


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

    def test_contains_summary(self):
        md = render_markdown(self._make_detail())
        assert "## Summary" in md
        assert "A test summary." in md

    def test_contains_highlights(self):
        md = render_markdown(self._make_detail())
        assert "## Highlights" in md
        assert "- Point 1" in md
        assert "- Point 2" in md

    def test_contains_transcript(self):
        md = render_markdown(self._make_detail())
        assert "## Transcript" in md
        assert "Speaker: Hello world." in md

    def test_no_summary_fallback(self):
        md = render_markdown(self._make_detail(summary=""))
        assert "No summary available." in md

    def test_no_highlights_fallback(self):
        md = render_markdown(self._make_detail(highlights=[]))
        assert "- No highlights extracted." in md

    def test_no_transcript_fallback(self):
        md = render_markdown(self._make_detail(transcript=""))
        assert "No transcript available." in md

    def test_title_with_quotes_escaped(self):
        md = render_markdown(self._make_detail(title='Say "hello"'))
        assert 'title: "Say \\"hello\\""' in md
