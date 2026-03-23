"""Tests for plaud_sync.period module."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from plaud_sync.period import (
    PeriodParseError,
    filter_by_period,
    parse_period,
)


class TestISODay:
    def test_basic(self):
        start, end = parse_period("2026-03-15")
        assert start == datetime(2026, 3, 15, 0, 0, 0)
        assert end == datetime(2026, 3, 16, 0, 0, 0)

    def test_end_of_month(self):
        start, end = parse_period("2026-03-31")
        assert start == datetime(2026, 3, 31)
        assert end == datetime(2026, 4, 1)

    def test_leap_day(self):
        start, end = parse_period("2024-02-29")
        assert start == datetime(2024, 2, 29)
        assert end == datetime(2024, 3, 1)

    def test_invalid_day(self):
        with pytest.raises(PeriodParseError):
            parse_period("2026-02-30")

    def test_year_boundary(self):
        start, end = parse_period("2025-12-31")
        assert start == datetime(2025, 12, 31)
        assert end == datetime(2026, 1, 1)


class TestISOMonth:
    def test_basic(self):
        start, end = parse_period("2026-03")
        assert start == datetime(2026, 3, 1)
        assert end == datetime(2026, 4, 1)

    def test_december(self):
        start, end = parse_period("2025-12")
        assert start == datetime(2025, 12, 1)
        assert end == datetime(2026, 1, 1)

    def test_january(self):
        start, end = parse_period("2026-01")
        assert start == datetime(2026, 1, 1)
        assert end == datetime(2026, 2, 1)

    def test_february_leap_year(self):
        start, end = parse_period("2024-02")
        assert start == datetime(2024, 2, 1)
        assert end == datetime(2024, 3, 1)

    def test_invalid_month(self):
        with pytest.raises(PeriodParseError):
            parse_period("2026-13")


class TestRange:
    def test_basic(self):
        start, end = parse_period("2026-03-01..2026-03-15")
        assert start == datetime(2026, 3, 1)
        assert end == datetime(2026, 3, 16)  # End inclusive

    def test_same_day(self):
        start, end = parse_period("2026-03-15..2026-03-15")
        assert start == datetime(2026, 3, 15)
        assert end == datetime(2026, 3, 16)

    def test_cross_month(self):
        start, end = parse_period("2026-01-28..2026-02-03")
        assert start == datetime(2026, 1, 28)
        assert end == datetime(2026, 2, 4)

    def test_cross_year(self):
        start, end = parse_period("2025-12-25..2026-01-05")
        assert start == datetime(2025, 12, 25)
        assert end == datetime(2026, 1, 6)

    def test_reversed_range(self):
        with pytest.raises(PeriodParseError, match="before"):
            parse_period("2026-03-15..2026-03-01")


class TestRelative:
    FIXED_NOW = datetime(2026, 3, 23, 14, 30, 0)  # Monday

    @patch("plaud_sync.period.datetime")
    def test_today(self, mock_dt):
        mock_dt.now.return_value = self.FIXED_NOW
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("today")
        assert start == datetime(2026, 3, 23)
        assert end == datetime(2026, 3, 24)

    @patch("plaud_sync.period.datetime")
    def test_yesterday(self, mock_dt):
        mock_dt.now.return_value = self.FIXED_NOW
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("yesterday")
        assert start == datetime(2026, 3, 22)
        assert end == datetime(2026, 3, 23)

    @patch("plaud_sync.period.datetime")
    def test_thisweek(self, mock_dt):
        mock_dt.now.return_value = self.FIXED_NOW
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("thisweek")
        assert start == datetime(2026, 3, 23)  # Monday
        assert end == datetime(2026, 3, 30)    # Next Monday

    @patch("plaud_sync.period.datetime")
    def test_thisweek_midweek(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 3, 25, 10, 0)  # Wednesday
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("thisweek")
        assert start == datetime(2026, 3, 23)  # Monday
        assert end == datetime(2026, 3, 30)

    @patch("plaud_sync.period.datetime")
    def test_lastweek(self, mock_dt):
        mock_dt.now.return_value = self.FIXED_NOW
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("lastweek")
        assert start == datetime(2026, 3, 16)
        assert end == datetime(2026, 3, 23)

    @patch("plaud_sync.period.datetime")
    def test_thismonth(self, mock_dt):
        mock_dt.now.return_value = self.FIXED_NOW
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("thismonth")
        assert start == datetime(2026, 3, 1)
        assert end == datetime(2026, 4, 1)

    @patch("plaud_sync.period.datetime")
    def test_lastmonth(self, mock_dt):
        mock_dt.now.return_value = self.FIXED_NOW
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("lastmonth")
        assert start == datetime(2026, 2, 1)
        assert end == datetime(2026, 3, 1)

    @patch("plaud_sync.period.datetime")
    def test_lastmonth_january(self, mock_dt):
        mock_dt.now.return_value = datetime(2026, 1, 15, 10, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("lastmonth")
        assert start == datetime(2025, 12, 1)
        assert end == datetime(2026, 1, 1)

    @patch("plaud_sync.period.datetime")
    def test_thisquarter(self, mock_dt):
        mock_dt.now.return_value = self.FIXED_NOW  # March = Q1
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("thisquarter")
        assert start == datetime(2026, 1, 1)
        assert end == datetime(2026, 4, 1)

    @patch("plaud_sync.period.datetime")
    def test_lastquarter(self, mock_dt):
        mock_dt.now.return_value = self.FIXED_NOW  # Q1 → last = Q4 2025
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("lastquarter")
        assert start == datetime(2025, 10, 1)
        assert end == datetime(2026, 1, 1)

    @patch("plaud_sync.period.datetime")
    def test_last7days(self, mock_dt):
        mock_dt.now.return_value = self.FIXED_NOW
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("last7days")
        assert start == datetime(2026, 3, 16)
        assert end == datetime(2026, 3, 24)

    @patch("plaud_sync.period.datetime")
    def test_last30days(self, mock_dt):
        mock_dt.now.return_value = self.FIXED_NOW
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("last30days")
        assert start == datetime(2026, 2, 21)
        assert end == datetime(2026, 3, 24)

    @patch("plaud_sync.period.datetime")
    def test_last90days(self, mock_dt):
        mock_dt.now.return_value = self.FIXED_NOW
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        start, end = parse_period("last90days")
        assert start == datetime(2025, 12, 23)
        assert end == datetime(2026, 3, 24)

    def test_case_insensitive(self):
        # Just verify it doesn't raise
        parse_period("Today")
        parse_period("THISWEEK")
        parse_period("LastMonth")


class TestEdgeCases:
    def test_empty_string(self):
        with pytest.raises(PeriodParseError, match="Empty"):
            parse_period("")

    def test_whitespace(self):
        with pytest.raises(PeriodParseError, match="Empty"):
            parse_period("   ")

    def test_unknown_keyword(self):
        with pytest.raises(PeriodParseError, match="Unknown"):
            parse_period("nextyear")

    def test_whitespace_around_spec(self):
        start, end = parse_period("  2026-03  ")
        assert start == datetime(2026, 3, 1)


class TestFilterByPeriod:
    def test_basic_filter(self):
        files = [
            {"id": "a", "start_time": 1711100000000},  # 2024-03-22
            {"id": "b", "start_time": 1711200000000},  # 2024-03-23
            {"id": "c", "start_time": 1711300000000},  # 2024-03-24
        ]
        start = datetime(2024, 3, 23)
        end = datetime(2024, 3, 24)
        result = filter_by_period(files, start, end)
        assert len(result) == 1
        assert result[0]["id"] == "b"

    def test_none_start_time_excluded(self):
        files = [{"id": "a", "start_time": None}, {"id": "b"}]
        start = datetime(2024, 1, 1)
        end = datetime(2025, 1, 1)
        assert filter_by_period(files, start, end) == []

    def test_empty_list(self):
        assert filter_by_period([], datetime(2024, 1, 1), datetime(2025, 1, 1)) == []
