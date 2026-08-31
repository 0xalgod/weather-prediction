import unittest
from datetime import date
from pathlib import Path

from weather_quant.ingestion.wunderground import (
    daily_url,
    date_window_ending,
    parse_daily_page,
)

FIXTURE = Path(__file__).parent / "fixtures" / "wunderground_daily.html"


class WundergroundTests(unittest.TestCase):
    def test_daily_url_uses_unpadded_route_date(self):
        self.assertEqual(
            daily_url("https://example.test/history/daily/us/test/KAAA", "2026-07-03"),
            "https://example.test/history/daily/us/test/KAAA/date/2026-7-3",
        )

    def test_page_parser_preserves_identity_high_and_observations(self):
        result = parse_daily_page(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(result["station_code"], "KAAA")
        self.assertEqual(result["station_name"], "Test Intl Airport Station")
        self.assertEqual(result["timezone"], "America/Test")
        self.assertEqual(result["page_date"], "2026-7-23")
        self.assertEqual(result["daily_high"], 26)
        self.assertEqual(result["temperature_unit"], "C")
        self.assertEqual(result["observation_count"], 2)
        self.assertEqual(result["observation_temperature_max"], 26)

    def test_date_window_is_inclusive_and_locked(self):
        self.assertEqual(
            date_window_ending(date(2026, 1, 2), 3),
            [date(2025, 12, 31), date(2026, 1, 1), date(2026, 1, 2)],
        )
        with self.assertRaises(ValueError):
            date_window_ending(date(2026, 1, 2), 0)


if __name__ == "__main__":
    unittest.main()
