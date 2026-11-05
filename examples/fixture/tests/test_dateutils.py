"""Tests for dateutils (stdlib unittest only)."""

import unittest
from datetime import date, datetime

from src.dateutils import add_business_days, as_utc_date, days_between, parse_rfc3339


class ParseRfc3339Tests(unittest.TestCase):
    def test_z_suffix_is_utc(self) -> None:
        self.assertEqual(parse_rfc3339("2026-01-01T00:00:00Z"), datetime(2026, 1, 1, 0, 0, 0))

    def test_positive_offset_is_converted_to_utc(self) -> None:
        # 2026-01-01T00:30+02:00 == 2025-12-31T22:30Z
        self.assertEqual(as_utc_date("2026-01-01T00:30:00+02:00"), date(2025, 12, 31))

    def test_negative_offset_is_converted_to_utc(self) -> None:
        # 2026-01-01T23:30-02:00 == 2026-01-02T01:30Z
        self.assertEqual(as_utc_date("2026-01-01T23:30:00-02:00"), date(2026, 1, 2))

    def test_days_between(self) -> None:
        self.assertEqual(days_between("2026-01-01T00:00:00Z", "2026-01-11T00:00:00Z"), 10)

    def test_add_business_days_skips_weekend(self) -> None:
        # 2026-01-02 is a Friday; +1 business day -> Monday 2026-01-05
        self.assertEqual(add_business_days(date(2026, 1, 2), 1), date(2026, 1, 5))


if __name__ == "__main__":
    unittest.main()
