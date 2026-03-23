"""Tests for plaud_sync.sync module."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from plaud_sync.sync import (
    run_sync,
    _slugify,
    _make_filename,
    _should_sync_file,
    _read_file_id,
    _find_existing_file,
    _resolve_collision,
    SyncSummary,
)
from plaud_sync.config import Config
from plaud_sync.normalizer import NormalizedDetail


class TestSlugify:
    def test_basic(self):
        assert _slugify("Team Meeting") == "team-meeting"

    def test_special_chars(self):
        assert _slugify("Hello! World?") == "hello-world"

    def test_empty(self):
        assert _slugify("") == "recording"

    def test_collapses_hyphens(self):
        assert _slugify("a  --  b") == "a-b"


class TestMakeFilename:
    def test_default_pattern(self):
        detail = NormalizedDetail(
            id="1", file_id="f1", title="Team Meeting",
            start_at_ms=1700000000000, duration_ms=0,
            summary="", highlights=[], transcript="", raw={},
        )
        name = _make_filename("plaud-{date}-{title}", detail)
        assert name == "plaud-2023-11-14-team-meeting.md"


class TestShouldSyncFile:
    def test_trash_excluded(self):
        assert _should_sync_file({"is_trash": True, "start_time": 999}, 0) is False

    def test_newer_than_checkpoint(self):
        assert _should_sync_file({"start_time": 200}, 100) is True

    def test_older_than_checkpoint(self):
        assert _should_sync_file({"start_time": 50}, 100) is False

    def test_equal_to_checkpoint(self):
        assert _should_sync_file({"start_time": 100}, 100) is False

    def test_missing_start_time(self):
        assert _should_sync_file({}, 100) is True


class TestReadFileId:
    def test_reads_file_id(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("---\nfile_id: abc123\n---\n# Title\n")
        assert _read_file_id(md) == "abc123"

    def test_quoted_file_id(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text('---\nfile_id: "abc123"\n---\n# Title\n')
        assert _read_file_id(md) == "abc123"

    def test_no_frontmatter(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# Just a title\n")
        assert _read_file_id(md) is None

    def test_missing_file(self, tmp_path):
        assert _read_file_id(tmp_path / "missing.md") is None


class TestFindExistingFile:
    def test_finds_by_file_id(self, tmp_path):
        md = tmp_path / "note.md"
        md.write_text("---\nfile_id: xyz\n---\n# Note\n")
        result = _find_existing_file(tmp_path, "xyz")
        assert result == md

    def test_returns_none_when_not_found(self, tmp_path):
        md = tmp_path / "note.md"
        md.write_text("---\nfile_id: xyz\n---\n# Note\n")
        assert _find_existing_file(tmp_path, "abc") is None


class TestResolveCollision:
    def test_no_collision(self, tmp_path):
        assert _resolve_collision(tmp_path, "note.md") == "note.md"

    def test_collision_appends_suffix(self, tmp_path):
        (tmp_path / "note.md").write_text("existing")
        assert _resolve_collision(tmp_path, "note.md") == "note-2.md"

    def test_multiple_collisions(self, tmp_path):
        (tmp_path / "note.md").write_text("existing")
        (tmp_path / "note-2.md").write_text("existing")
        assert _resolve_collision(tmp_path, "note.md") == "note-3.md"


class TestRunSync:
    def test_full_sync(self, tmp_path):
        mock_api = MagicMock()
        mock_api.list_files.return_value = [
            {"id": "f1", "file_id": "f1", "start_time": 1000},
        ]
        mock_api.get_file_detail.return_value = {
            "id": "f1",
            "file_id": "f1",
            "file_name": "Test",
            "start_time": 1000,
            "duration": 60000,
            "summary": "Summary",
            "highlights": ["H1"],
            "trans_result": {"full_text": "Transcript"},
        }

        config = Config(sync_folder="notes")
        summary = run_sync(mock_api, tmp_path, config)

        assert summary.listed == 1
        assert summary.selected == 1
        assert summary.created == 1
        assert summary.failed == 0

        # Verify file was created
        notes_dir = tmp_path / "notes"
        md_files = list(notes_dir.glob("*.md"))
        assert len(md_files) == 1
        content = md_files[0].read_text()
        assert "file_id: f1" in content
        assert "Zusammenfassung" in content

    def test_incremental_sync_skips_old(self, tmp_path):
        # Set up state with checkpoint
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        state_file = notes_dir / ".plaud-sync-state.json"
        state_file.write_text(json.dumps({"lastSyncAtMs": 500}))

        mock_api = MagicMock()
        mock_api.list_files.return_value = [
            {"id": "old", "file_id": "old", "start_time": 400},
            {"id": "new", "file_id": "new", "start_time": 600},
        ]
        mock_api.get_file_detail.return_value = {
            "id": "new", "file_id": "new", "file_name": "New",
            "start_time": 600, "duration": 60000,
        }

        config = Config(sync_folder="notes")
        summary = run_sync(mock_api, tmp_path, config)

        assert summary.listed == 2
        assert summary.selected == 1
        assert summary.created == 1
        mock_api.get_file_detail.assert_called_once_with("new")

    def test_failure_does_not_update_checkpoint(self, tmp_path):
        mock_api = MagicMock()
        mock_api.list_files.return_value = [
            {"id": "f1", "file_id": "f1", "start_time": 1000},
        ]
        mock_api.get_file_detail.side_effect = Exception("API down")

        config = Config(sync_folder="notes")
        summary = run_sync(mock_api, tmp_path, config)

        assert summary.failed == 1
        state_file = tmp_path / "notes" / ".plaud-sync-state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            assert state["lastSyncAtMs"] == 0
