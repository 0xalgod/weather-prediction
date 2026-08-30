import unittest

from scripts.probe_noaa_nbm_daily_coverage import dates_inclusive


class NoaaNbmDailyCoverageTests(unittest.TestCase):
    def test_date_window_is_inclusive_and_leap_safe(self):
        self.assertEqual(
            dates_inclusive("2024-02-28", "2024-03-01"),
            ["20240228", "20240229", "20240301"],
        )

    def test_rejects_reversed_window(self):
        with self.assertRaisesRegex(ValueError, "precedes"):
            dates_inclusive("2026-01-02", "2026-01-01")


if __name__ == "__main__":
    unittest.main()
