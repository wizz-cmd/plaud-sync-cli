"""Tests for plaud_sync.api module."""

import json
import pytest
from unittest.mock import patch, MagicMock

from plaud_sync.api import (
    PlaudApiClient,
    normalize_domain,
    normalize_token,
    _is_success_status,
    _extract_list_payload,
    _extract_detail_payload,
)
from plaud_sync.retry import PlaudApiError, RetryPolicy


class TestNormalizeDomain:
    def test_strips_trailing_slash(self):
        assert normalize_domain("https://api.plaud.ai/") == "https://api.plaud.ai"

    def test_strips_multiple_slashes(self):
        assert normalize_domain("https://api.plaud.ai///") == "https://api.plaud.ai"

    def test_no_slash_unchanged(self):
        assert normalize_domain("https://api.plaud.ai") == "https://api.plaud.ai"


class TestNormalizeToken:
    def test_strips_bearer_prefix(self):
        assert normalize_token("Bearer mytoken123") == "mytoken123"

    def test_case_insensitive(self):
        assert normalize_token("bearer mytoken123") == "mytoken123"

    def test_strips_whitespace(self):
        assert normalize_token("  mytoken123  ") == "mytoken123"

    def test_plain_token(self):
        assert normalize_token("mytoken123") == "mytoken123"


class TestIsSuccessStatus:
    def test_int_0(self):
        assert _is_success_status(0) is True

    def test_int_200(self):
        assert _is_success_status(200) is True

    def test_int_500(self):
        assert _is_success_status(500) is False

    def test_str_ok(self):
        assert _is_success_status("ok") is True

    def test_str_success(self):
        assert _is_success_status("success") is True


class TestExtractListPayload:
    def test_from_payload(self):
        assert _extract_list_payload({"payload": [{"id": "1"}]}) == [{"id": "1"}]

    def test_from_data_file_list(self):
        assert _extract_list_payload({"data_file_list": [{"id": "2"}]}) == [{"id": "2"}]

    def test_from_data(self):
        assert _extract_list_payload({"data": [{"id": "3"}]}) == [{"id": "3"}]

    def test_empty(self):
        assert _extract_list_payload({}) == []


class TestExtractDetailPayload:
    def test_from_payload(self):
        assert _extract_detail_payload({"payload": {"id": "1"}}) == {"id": "1"}

    def test_from_data(self):
        assert _extract_detail_payload({"data": {"id": "2"}}) == {"id": "2"}

    def test_fallback_to_envelope(self):
        envelope = {"id": "3", "status": 0}
        assert _extract_detail_payload(envelope) == envelope


class TestPlaudApiClient:
    def test_init_normalizes(self):
        client = PlaudApiClient("Bearer tok123", "https://api.plaud.ai/")
        assert client.token == "tok123"
        assert client.api_domain == "https://api.plaud.ai"

    @patch("plaud_sync.api.urlopen")
    def test_list_files_success(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({
            "status": 0,
            "payload": [{"id": "file1"}, {"id": "file2"}],
        }).encode()
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = response

        client = PlaudApiClient("token", retry_policy=RetryPolicy(base_delay_ms=1))
        files = client.list_files()
        assert len(files) == 2
        assert files[0]["id"] == "file1"

    @patch("plaud_sync.api.urlopen")
    def test_get_file_detail_success(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({
            "status": 0,
            "payload": {"id": "f1", "file_id": "f1", "file_name": "Test"},
        }).encode()
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = response

        client = PlaudApiClient("token", retry_policy=RetryPolicy(base_delay_ms=1))
        detail = client.get_file_detail("f1")
        assert detail["file_name"] == "Test"
