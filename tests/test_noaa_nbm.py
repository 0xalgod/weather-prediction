import tempfile
import unittest
from pathlib import Path

from weather_quant.ingestion.noaa_nbm import inspect_probabilistic_text, probabilistic_text_url


class NoaaNbmTests(unittest.TestCase):
    def test_probabilistic_text_url_is_run_specific(self):
        self.assertEqual(
            probabilistic_text_url("20260830", 0),
            "https://noaa-nbm-grib2-pds.s3.amazonaws.com/"
            "blend.20260830/00/text/blend_nbptx.t00z",
        )
        with self.assertRaisesRegex(ValueError, "invalid"):
            probabilistic_text_url("2026-08-30", 0)

    def test_inventory_requires_station_and_all_maxt_markers(self):
        content = " KORD    NBM V4.1 NBP GUIDANCE    8/31/2023  0100 UTC\n" + " ".join(
            ("TXNMN", "TXNSD", "TXNP1", "TXNP2", "TXNP5", "TXNP7", "TXNP9")
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nbp.txt"
            path.write_text(content, encoding="ascii")
            inventory = inspect_probabilistic_text(path, "KORD")
        self.assertEqual(inventory["station_occurrence_count"], 1)
        self.assertEqual(inventory["nbm_version"], "4.1")
        self.assertTrue(inventory["contains_probabilistic_maxt_markers"])


if __name__ == "__main__":
    unittest.main()
