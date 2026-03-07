"""Tests for plaud_sync.hydrator module."""

import json
from unittest.mock import patch

import pytest
from plaud_sync.hydrator import hydrate, _find_content_url


class TestFindContentUrl:
    def test_finds_url_by_type(self):
        detail = {
            "content_list": [
                {"type": "auto_sum_note", "url": "https://example.com/summary"},
                {"type": "transaction", "url": "https://example.com/transcript"},
            ]
        }
        assert _find_content_url(detail, "auto_sum_note") == "https://example.com/summary"
        assert _find_content_url(detail, "transaction") == "https://example.com/transcript"

    def test_returns_none_when_not_found(self):
        assert _find_content_url({"content_list": []}, "auto_sum_note") is None
        assert _find_content_url({}, "auto_sum_note") is None

    def test_prefers_url_field(self):
        detail = {"content_list": [{"type": "auto_sum_note", "url": "a", "signed_url": "b"}]}
        assert _find_content_url(detail, "auto_sum_note") == "a"

    def test_falls_back_to_signed_url(self):
        detail = {"content_list": [{"type": "auto_sum_note", "signed_url": "b"}]}
        assert _find_content_url(detail, "auto_sum_note") == "b"


class TestHydrate:
    def test_returns_copy(self):
        detail = {"id": "1"}
        result = hydrate(detail)
        assert result is not detail
        assert result["id"] == "1"

    def test_no_content_list_unchanged(self):
        detail = {"id": "1", "summary": "existing"}
        result = hydrate(detail)
        assert result["summary"] == "existing"

    @patch("plaud_sync.hydrator._fetch_url")
    def test_hydrates_summary_from_json(self, mock_fetch):
        mock_fetch.return_value = json.dumps({"summary": "Fetched summary"})
        detail = {
            "content_list": [{"type": "auto_sum_note", "url": "https://example.com/s"}]
        }
        result = hydrate(detail)
        assert result["summary"] == "Fetched summary"

    @patch("plaud_sync.hydrator._fetch_url")
    def test_hydrates_transcript_from_json(self, mock_fetch):
        mock_fetch.return_value = json.dumps({"full_text": "Hello world"})
        detail = {
            "content_list": [{"type": "transaction", "url": "https://example.com/t"}]
        }
        result = hydrate(detail)
        assert result["full_text"] == "Hello world"

    @patch("plaud_sync.hydrator._fetch_url")
    def test_does_not_overwrite_existing(self, mock_fetch):
        mock_fetch.return_value = json.dumps({"summary": "New"})
        detail = {
            "summary": "Existing",
            "content_list": [{"type": "auto_sum_note", "url": "https://example.com/s"}],
        }
        result = hydrate(detail)
        assert result["summary"] == "Existing"

    @patch("plaud_sync.hydrator._fetch_url")
    def test_fetch_failure_graceful(self, mock_fetch):
        mock_fetch.return_value = ""
        detail = {
            "content_list": [{"type": "auto_sum_note", "url": "https://example.com/s"}]
        }
        result = hydrate(detail)
        assert "summary" not in result
