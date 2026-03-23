"""Tests for plaud_sync.tui module."""

from unittest.mock import patch

import pytest

from plaud_sync.tui import TuiError, _check_textual, _format_date, _truncate


class TestCheckTextual:
    def test_missing_textual_raises(self):
        with patch.dict("sys.modules", {"textual": None}):
            with pytest.raises(TuiError, match="textual"):
                _check_textual()

    def test_installed_textual_ok(self):
        # Should not raise when textual is importable
        try:
            import textual  # noqa: F401
            _check_textual()
        except ImportError:
            pytest.skip("textual not installed")


class TestFormatDate:
    def test_valid_timestamp(self):
        assert _format_date(1711200000000) == "2024-03-23 13:20"

    def test_zero(self):
        result = _format_date(0)
        assert result  # Should return something, not crash

    def test_invalid(self):
        assert _format_date(-999999999999999) == "unknown"


class TestTruncate:
    def test_short_text(self):
        assert _truncate("Hello", 10) == "Hello"

    def test_exact_width(self):
        assert _truncate("Hello", 5) == "Hello"

    def test_long_text(self):
        assert _truncate("Hello World!", 7) == "Hello.."

    def test_very_short_width(self):
        assert _truncate("Hello", 3) == "H.."
