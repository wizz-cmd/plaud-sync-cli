"""hledger-inspired period parser for date range filtering."""

from __future__ import annotations

import re
from datetime import datetime, timedelta


class PeriodParseError(Exception):
    """Raised when a period spec cannot be parsed."""


_RANGE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})$")


def parse_period(spec: str) -> tuple[datetime, datetime]:
    """Parse a period spec into (start, end) datetime range.

    Supported formats:
        - ISO month: "2026-03" → 1 Mar 00:00 to 1 Apr 00:00
        - ISO day: "2026-03-15" → whole day
        - Range: "2026-03-01..2026-03-15" → start to end (end inclusive)
        - Relative: "today", "yesterday", "thisweek", "lastweek",
          "thismonth", "lastmonth", "thisquarter", "lastquarter",
          "last7days", "last30days", "last90days"

    Returns:
        Tuple of (start, end) datetimes. Start is inclusive, end is exclusive.

    Raises:
        PeriodParseError: If the spec cannot be parsed.
    """
    spec = spec.strip()
    if not spec:
        raise PeriodParseError("Empty period spec")

    # Try range first: "2026-03-01..2026-03-15"
    m = _RANGE_RE.match(spec)
    if m:
        return _parse_range(m.group(1), m.group(2))

    # Try ISO day: "2026-03-15"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", spec):
        return _parse_day(spec)

    # Try ISO month: "2026-03"
    if re.match(r"^\d{4}-\d{2}$", spec):
        return _parse_month(spec)

    # Try relative keywords
    lower = spec.lower()
    if lower in _RELATIVE_PARSERS:
        return _RELATIVE_PARSERS[lower]()

    raise PeriodParseError(f"Unknown period format: {spec!r}")


def _parse_day(spec: str) -> tuple[datetime, datetime]:
    """Parse an ISO day spec like '2026-03-15'."""
    try:
        day = datetime.strptime(spec, "%Y-%m-%d")
    except ValueError as e:
        raise PeriodParseError(f"Invalid date: {spec!r}") from e
    return day, day + timedelta(days=1)


def _parse_month(spec: str) -> tuple[datetime, datetime]:
    """Parse an ISO month spec like '2026-03'."""
    try:
        start = datetime.strptime(spec, "%Y-%m")
    except ValueError as e:
        raise PeriodParseError(f"Invalid month: {spec!r}") from e
    # First day of next month
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def _parse_range(start_str: str, end_str: str) -> tuple[datetime, datetime]:
    """Parse a range like '2026-03-01..2026-03-15' (end inclusive)."""
    try:
        start = datetime.strptime(start_str, "%Y-%m-%d")
    except ValueError as e:
        raise PeriodParseError(f"Invalid range start: {start_str!r}") from e
    try:
        end = datetime.strptime(end_str, "%Y-%m-%d")
    except ValueError as e:
        raise PeriodParseError(f"Invalid range end: {end_str!r}") from e
    if end < start:
        raise PeriodParseError(f"Range end {end_str} is before start {start_str}")
    # End is inclusive → add one day
    return start, end + timedelta(days=1)


def _today() -> tuple[datetime, datetime]:
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _yesterday() -> tuple[datetime, datetime]:
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=1), today


def _thisweek() -> tuple[datetime, datetime]:
    """Monday to Sunday (European)."""
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=7)


def _lastweek() -> tuple[datetime, datetime]:
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    return last_monday, this_monday


def _thismonth() -> tuple[datetime, datetime]:
    now = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def _lastmonth() -> tuple[datetime, datetime]:
    now = datetime.now()
    first_of_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if first_of_this.month == 1:
        start = first_of_this.replace(year=first_of_this.year - 1, month=12)
    else:
        start = first_of_this.replace(month=first_of_this.month - 1)
    return start, first_of_this


def _thisquarter() -> tuple[datetime, datetime]:
    now = datetime.now()
    q_start_month = ((now.month - 1) // 3) * 3 + 1
    start = now.replace(month=q_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    q_end_month = q_start_month + 3
    if q_end_month > 12:
        end = start.replace(year=start.year + 1, month=q_end_month - 12)
    else:
        end = start.replace(month=q_end_month)
    return start, end


def _lastquarter() -> tuple[datetime, datetime]:
    now = datetime.now()
    q_start_month = ((now.month - 1) // 3) * 3 + 1
    this_q_start = now.replace(month=q_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    if q_start_month <= 3:
        last_q_start = this_q_start.replace(year=this_q_start.year - 1, month=q_start_month + 9)
    else:
        last_q_start = this_q_start.replace(month=q_start_month - 3)
    return last_q_start, this_q_start


def _last_n_days(n: int) -> tuple[datetime, datetime]:
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=n), today + timedelta(days=1)


_RELATIVE_PARSERS: dict[str, callable] = {
    "today": _today,
    "yesterday": _yesterday,
    "thisweek": _thisweek,
    "lastweek": _lastweek,
    "thismonth": _thismonth,
    "lastmonth": _lastmonth,
    "thisquarter": _thisquarter,
    "lastquarter": _lastquarter,
    "last7days": lambda: _last_n_days(7),
    "last30days": lambda: _last_n_days(30),
    "last90days": lambda: _last_n_days(90),
}


def filter_by_period(
    files: list[dict],
    start: datetime,
    end: datetime,
    time_field: str = "start_time",
) -> list[dict]:
    """Filter file summaries by period range.

    Args:
        files: List of file summary dicts from the API.
        start: Inclusive start datetime.
        end: Exclusive end datetime.
        time_field: Field name containing Unix timestamp in milliseconds.

    Returns:
        Filtered list of files within the period.
    """
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    result = []
    for f in files:
        ts = f.get(time_field)
        if ts is None:
            continue
        if isinstance(ts, (int, float)) and start_ms <= ts < end_ms:
            result.append(f)
    return result
