"""Tests for plaud_sync.journal module."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from plaud_sync.journal import (
    build_journal_entry,
    append_or_update,
    read_journal,
    render_obsidian,
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


class TestRenderObsidian:
    def test_empty_entries(self):
        md = render_obsidian([])
        assert "No meetings recorded yet." in md

    def test_groups_by_month(self):
        entries = [
            {"date": "2026-03-20", "title": "A", "file": "a.md",
             "duration_min": 10, "speakers": ["Alice"], "word_count": 50},
            {"date": "2026-03-21", "title": "B", "file": "b.md",
             "duration_min": 15, "speakers": ["Bob"], "word_count": 80},
            {"date": "2026-02-10", "title": "C", "file": "c.md",
             "duration_min": 20, "speakers": ["Alice"], "word_count": 100},
        ]
        md = render_obsidian(entries)
        assert "## 2026-03" in md
        assert "## 2026-02" in md

    def test_wikilinks(self):
        entries = [
            {"date": "2026-03-20", "title": "Test Meeting",
             "file": "2026-03-20-test-meeting.md",
             "duration_min": 10, "speakers": [], "word_count": 0},
        ]
        md = render_obsidian(entries)
        assert "[[2026-03-20-test-meeting|Test Meeting]]" in md

    def test_speaker_index(self):
        entries = [
            {"date": "2026-03-20", "title": "A", "file": "a.md",
             "duration_min": 10, "speakers": ["Alice", "Bob"], "word_count": 0},
            {"date": "2026-03-21", "title": "B", "file": "b.md",
             "duration_min": 15, "speakers": ["Alice"], "word_count": 0},
        ]
        md = render_obsidian(entries)
        assert "## Speakers" in md
        assert "**Alice** (2 meetings)" in md
        assert "**Bob** (1 meetings)" in md

    def test_summary_stats(self):
        entries = [
            {"date": "2026-03-20", "title": "A", "file": "a.md",
             "duration_min": 10, "speakers": [], "word_count": 50},
            {"date": "2026-03-21", "title": "B", "file": "b.md",
             "duration_min": 15, "speakers": [], "word_count": 80},
        ]
        md = render_obsidian(entries)
        assert "2 meetings" in md
        assert "25 min total" in md
        assert "130 words" in md
