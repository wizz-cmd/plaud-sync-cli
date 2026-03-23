"""Tests for journal CLI subcommand."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from plaud_sync.cli import _handle_journal


def _make_args(**kwargs):
    """Create a mock args namespace."""
    from argparse import Namespace
    defaults = {
        "vault": ".",
        "folder": None,
        "config": None,
        "period": None,
        "format": "pretty",
        "stats": False,
        "verbose": False,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


def _write_journal(path: Path, entries: list[dict]) -> None:
    lines = [json.dumps(e, ensure_ascii=False) for e in entries]
    path.write_text("\n".join(lines) + "\n")


class TestHandleJournal:
    def test_no_entries(self, tmp_path, capsys):
        args = _make_args(vault=str(tmp_path), folder="notes")
        (tmp_path / "notes").mkdir()
        result = _handle_journal(args)
        assert result == 0
        assert "No journal entries" in capsys.readouterr().out

    def test_pretty_output(self, tmp_path, capsys):
        notes = tmp_path / "Plaud"
        notes.mkdir()
        _write_journal(notes / "meeting-journal.jsonl", [
            {"meeting_id": "m1", "date": "2026-03-20", "title": "Test Meeting",
             "duration_min": 25, "speakers": ["Alice"], "word_count": 100},
        ])
        args = _make_args(vault=str(tmp_path))
        result = _handle_journal(args)
        assert result == 0
        out = capsys.readouterr().out
        assert "Test Meeting" in out
        assert "25 min" in out

    def test_json_format(self, tmp_path, capsys):
        notes = tmp_path / "Plaud"
        notes.mkdir()
        _write_journal(notes / "meeting-journal.jsonl", [
            {"meeting_id": "m1", "date": "2026-03-20", "title": "Test"},
        ])
        args = _make_args(vault=str(tmp_path), format="json")
        result = _handle_journal(args)
        assert result == 0
        out = capsys.readouterr().out
        parsed = json.loads(out.strip())
        assert parsed["meeting_id"] == "m1"

    def test_stats_output(self, tmp_path, capsys):
        notes = tmp_path / "Plaud"
        notes.mkdir()
        _write_journal(notes / "meeting-journal.jsonl", [
            {"meeting_id": "m1", "date": "2026-03-20", "title": "A",
             "duration_min": 10, "speakers": ["Alice", "Bob"], "word_count": 50},
            {"meeting_id": "m2", "date": "2026-03-21", "title": "B",
             "duration_min": 15, "speakers": ["Alice"], "word_count": 80},
        ])
        args = _make_args(vault=str(tmp_path), stats=True)
        result = _handle_journal(args)
        assert result == 0
        out = capsys.readouterr().out
        assert "2 meetings" in out
        assert "2026-03" in out
        assert "Alice" in out

    def test_period_filter(self, tmp_path, capsys):
        notes = tmp_path / "Plaud"
        notes.mkdir()
        _write_journal(notes / "meeting-journal.jsonl", [
            {"meeting_id": "m1", "date": "2026-03-20", "title": "March"},
            {"meeting_id": "m2", "date": "2026-02-15", "title": "February"},
        ])
        args = _make_args(vault=str(tmp_path), period="2026-03")
        result = _handle_journal(args)
        assert result == 0
        out = capsys.readouterr().out
        assert "March" in out
        assert "February" not in out
