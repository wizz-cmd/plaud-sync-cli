"""Tests for plaud_sync.journal module."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from plaud_sync.journal import (
    build_journal_entry,
    append_or_update,
    read_journal,
    _word_count,
    _summary_preview,
    JOURNAL_FILENAME,
)
from plaud_sync.normalizer import NormalizedDetail


def _make_detail(**kwargs) -> NormalizedDetail:
    defaults = {
        "id": "abc",
        "file_id": "file_abc",
        "title": "Test Meeting",
        "start_at_ms": 1700000000000,
        "duration_ms": 1500000,  # 25 min
        "summary": "A test summary about the meeting.",
        "highlights": [],
        "transcript": "Alice said hello. Bob said hi.",
        "raw": {},
        "speakers": ["Alice", "Bob"],
        "segments": [
            {"speaker": "Alice", "content": "Hello", "start_time": 0},
            {"speaker": "Bob", "content": "Hi", "start_time": 5000},
        ],
    }
    defaults.update(kwargs)
    return NormalizedDetail(**defaults)


class TestWordCount:
    def test_normal_text(self):
        assert _word_count("hello world foo") == 3

    def test_empty(self):
        assert _word_count("") == 0

    def test_whitespace(self):
        assert _word_count("   ") == 0


class TestSummaryPreview:
    def test_short_text(self):
        assert _summary_preview("Short text.") == "Short text."

    def test_long_text_truncated(self):
        long_text = "A " * 100
        result = _summary_preview(long_text.strip(), max_chars=20)
        assert len(result) <= 25  # word boundary + "..."
        assert result.endswith("...")


class TestBuildJournalEntry:
    def test_basic_entry(self):
        detail = _make_detail()
        entry = build_journal_entry(detail, "2023-11-14-test-meeting.md")
        assert entry["meeting_id"] == "file_abc"
        assert entry["date"] == "2023-11-14"
        assert entry["title"] == "Test Meeting"
        assert entry["duration_min"] == 25
        assert entry["speakers"] == ["Alice", "Bob"]
        assert entry["has_transcript"] is True
        assert entry["has_summary"] is True
        assert entry["file"] == "2023-11-14-test-meeting.md"
        assert "synced_at" in entry
        assert entry["word_count"] == 6  # "Alice said hello. Bob said hi."

    def test_no_transcript(self):
        detail = _make_detail(transcript="", segments=[])
        entry = build_journal_entry(detail, "test.md")
        assert entry["has_transcript"] is False
        assert entry["word_count"] == 0

    def test_no_summary(self):
        detail = _make_detail(summary="")
        entry = build_journal_entry(detail, "test.md")
        assert entry["has_summary"] is False
        assert entry["summary_preview"] == ""


class TestAppendOrUpdate:
    def test_append_new_entry(self, tmp_path):
        journal = tmp_path / JOURNAL_FILENAME
        entry = {"meeting_id": "m1", "title": "Meeting 1"}
        append_or_update(journal, entry)

        entries = read_journal(journal)
        assert len(entries) == 1
        assert entries[0]["meeting_id"] == "m1"

    def test_append_multiple(self, tmp_path):
        journal = tmp_path / JOURNAL_FILENAME
        append_or_update(journal, {"meeting_id": "m1", "title": "Meeting 1"})
        append_or_update(journal, {"meeting_id": "m2", "title": "Meeting 2"})

        entries = read_journal(journal)
        assert len(entries) == 2

    def test_update_existing(self, tmp_path):
        journal = tmp_path / JOURNAL_FILENAME
        append_or_update(journal, {"meeting_id": "m1", "title": "Original"})
        append_or_update(journal, {"meeting_id": "m1", "title": "Updated"})

        entries = read_journal(journal)
        assert len(entries) == 1
        assert entries[0]["title"] == "Updated"

    def test_update_preserves_other_entries(self, tmp_path):
        journal = tmp_path / JOURNAL_FILENAME
        append_or_update(journal, {"meeting_id": "m1", "title": "Meeting 1"})
        append_or_update(journal, {"meeting_id": "m2", "title": "Meeting 2"})
        append_or_update(journal, {"meeting_id": "m1", "title": "Updated 1"})

        entries = read_journal(journal)
        assert len(entries) == 2
        assert entries[0]["title"] == "Updated 1"
        assert entries[1]["title"] == "Meeting 2"


class TestReadJournal:
    def test_missing_file(self, tmp_path):
        assert read_journal(tmp_path / "missing.jsonl") == []

    def test_empty_file(self, tmp_path):
        journal = tmp_path / JOURNAL_FILENAME
        journal.write_text("")
        assert read_journal(journal) == []

    def test_reads_valid_entries(self, tmp_path):
        journal = tmp_path / JOURNAL_FILENAME
        lines = [
            json.dumps({"meeting_id": "m1"}),
            json.dumps({"meeting_id": "m2"}),
        ]
        journal.write_text("\n".join(lines) + "\n")
        entries = read_journal(journal)
        assert len(entries) == 2

    def test_skips_invalid_json(self, tmp_path):
        journal = tmp_path / JOURNAL_FILENAME
        journal.write_text('{"meeting_id": "m1"}\nnot json\n{"meeting_id": "m2"}\n')
        entries = read_journal(journal)
        assert len(entries) == 2
