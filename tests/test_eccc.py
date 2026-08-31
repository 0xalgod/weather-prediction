import unittest
from datetime import date

from weather_quant.ingestion.eccc import (
    round_half_up,
    station_civil_day_rows,
    station_local_rows,
)


class EcccTests(unittest.TestCase):
    def test_half_up_matches_source_whole_degree_semantics(self):
        self.assertEqual(round_half_up(8.5), 9)
        self.assertEqual(round_half_up(-1.5), -2)

    def test_station_local_filter_does_not_use_utc_date(self):
        document = {
            "features": [
                {
                    "properties": {
                        "CLIMATE_IDENTIFIER": "6158731",
                        "LOCAL_DATE": "2026-03-08 23:00:00",
                        "UTC_DATE": "2026-03-09T03:00:00",
                    }
                },
                {
                    "properties": {
                        "CLIMATE_IDENTIFIER": "OTHER",
                        "LOCAL_DATE": "2026-03-08 23:00:00",
                        "UTC_DATE": "2026-03-09T03:00:00",
                    }
                },
            ]
        }
        rows = station_local_rows(document, "6158731", "2026-03-08")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["UTC_DATE"], "2026-03-09T03:00:00")

    def test_civil_day_filter_uses_half_open_dst_utc_window(self):
        document = {
            "features": [
                {"properties": {"CLIMATE_IDENTIFIER": "6158731", "UTC_DATE": value}}
                for value in (
                    "2026-03-08T04:00:00",
                    "2026-03-08T05:00:00",
                    "2026-03-09T03:00:00",
                    "2026-03-09T04:00:00",
                )
            ]
        }
        rows = station_civil_day_rows(
            document,
            "6158731",
            date(2026, 3, 8),
            "America/Toronto",
        )
        self.assertEqual(
            [row["UTC_DATE"] for row in rows],
            ["2026-03-08T05:00:00", "2026-03-09T03:00:00"],
        )


if __name__ == "__main__":
    unittest.main()
