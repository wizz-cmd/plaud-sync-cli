"""Tests for plaud_sync.normalizer module."""

import json
import pytest
from plaud_sync.normalizer import normalize, NormalizedDetail


class TestNormalize:
    def test_basic_normalization(self):
        detail = {
            "id": "abc123",
            "file_id": "file_abc123",
            "file_name": "Team Meeting",
            "start_time": 1700000000000,
            "duration": 3600000,
            "summary": "A meeting about stuff.",
            "highlights": ["Point 1", "Point 2"],
            "trans_result": {"full_text": "Speaker A: Hello"},
        }
        result = normalize(detail)
        assert result.id == "abc123"
        assert result.file_id == "file_abc123"
        assert result.title == "Team Meeting"
        assert result.start_at_ms == 1700000000000
        assert result.duration_ms == 3600000
        assert result.summary == "A meeting about stuff."
        assert result.highlights == ["Point 1", "Point 2"]
        assert result.transcript == "Speaker A: Hello"

    def test_title_fallback_chain(self):
        assert normalize({"file_name": "A"}).title == "A"
        assert normalize({"filename": "B"}).title == "B"
        assert normalize({"title": "C"}).title == "C"
        assert normalize({}).title == "Untitled recording"

    def test_id_fallback(self):
        result = normalize({"id": "x"})
        assert result.id == "x"
        assert result.file_id == "x"

    def test_file_id_preferred(self):
        result = normalize({"id": "x", "file_id": "y"})
        assert result.file_id == "y"

    def test_strips_html_from_title(self):
        result = normalize({"file_name": "Hello <b>World</b>"})
        assert result.title == "Hello World"

    def test_strips_markdown_images(self):
        result = normalize({"file_name": "Note ![img](http://example.com/img.png) here"})
        assert result.title == "Note here"

    def test_summary_from_ai_content(self):
        detail = {"ai_content": {"summary": "AI summary text"}}
        assert normalize(detail).summary == "AI summary text"

    def test_summary_from_ai_notes(self):
        detail = {"ai_notes": {"abstract": "Abstract text"}}
        assert normalize(detail).summary == "Abstract text"

    def test_highlights_from_json_string(self):
        detail = {"highlights": json.dumps(["H1", "H2"])}
        result = normalize(detail)
        assert result.highlights == ["H1", "H2"]

    def test_highlights_from_newline_string(self):
        detail = {"highlights": "- Point A\n- Point B\nPoint C"}
        result = normalize(detail)
        assert result.highlights == ["Point A", "Point B", "Point C"]

    def test_transcript_from_paragraphs(self):
        detail = {
            "trans_result": {
                "paragraphs": [
                    {"speaker": "Alice", "text": "Hello"},
                    {"speaker": "Bob", "text": "Hi there"},
                ]
            }
        }
        result = normalize(detail)
        assert "Alice: Hello" in result.transcript
        assert "Bob: Hi there" in result.transcript

    def test_transcript_from_direct_field(self):
        detail = {"full_text": "Full transcript text here."}
        assert normalize(detail).transcript == "Full transcript text here."

    def test_empty_detail(self):
        result = normalize({})
        assert result.id == "unknown"
        assert result.file_id == "unknown"
        assert result.title == "Untitled recording"
        assert result.start_at_ms == 0
        assert result.duration_ms == 0
        assert result.summary == ""
        assert result.highlights == []
        assert result.transcript == ""
        assert result.speakers == []
        assert result.segments == []

    def test_segments_from_trans_result_list(self):
        detail = {
            "trans_result": [
                {"content": "Hello", "speaker": "Alice", "start_time": 0, "end_time": 5000},
                {"content": "Hi", "speaker": "Bob", "start_time": 5000, "end_time": 10000},
            ]
        }
        result = normalize(detail)
        assert len(result.segments) == 2
        assert result.segments[0]["speaker"] == "Alice"
        assert result.segments[1]["content"] == "Hi"

    def test_speakers_extracted_from_segments(self):
        detail = {
            "trans_result": [
                {"content": "Hello", "speaker": "Alice", "start_time": 0, "end_time": 5000},
                {"content": "Hi", "speaker": "Bob", "start_time": 5000, "end_time": 10000},
                {"content": "Yes", "speaker": "Alice", "start_time": 10000, "end_time": 15000},
            ]
        }
        result = normalize(detail)
        assert result.speakers == ["Alice", "Bob"]

    def test_speakers_generic_sorted_last(self):
        detail = {
            "trans_result": [
                {"content": "A", "speaker": "Speaker 1", "start_time": 0, "end_time": 1},
                {"content": "B", "speaker": "Alice", "start_time": 1, "end_time": 2},
                {"content": "C", "speaker": "Speaker 2", "start_time": 2, "end_time": 3},
            ]
        }
        result = normalize(detail)
        assert result.speakers == ["Alice", "Speaker 1", "Speaker 2"]
