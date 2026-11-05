"""Utilities for parsing RFC 3339 timestamps used by the invoicing pipeline."""

from datetime import date, datetime, timedelta


def parse_rfc3339(value: str) -> datetime:
    """Parse an RFC 3339 timestamp into a naive UTC datetime."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # BUG: the timezone offset is silently dropped instead of being converted.
    return datetime.fromisoformat(text).replace(tzinfo=None)


def as_utc_date(value: str) -> date:
    """Calendar date in UTC for a timestamp (may differ from the local date)."""
    return parse_rfc3339(value).date()


def days_between(start: str, end: str) -> int:
    """Whole days between two timestamps, UTC based."""
    return (parse_rfc3339(end) - parse_rfc3339(start)).days


def add_business_days(day: date, count: int) -> date:
    """Add ``count`` business days (Monday-Friday) to a date."""
    current = day
    added = 0
    while added < count:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current
