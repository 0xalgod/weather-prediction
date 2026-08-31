import unittest

from weather_quant.ingestion.eccc import round_half_up, station_local_rows


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


if __name__ == "__main__":
    unittest.main()
