import tempfile
import unittest
from pathlib import Path

from scripts.probe_us_nbm_station_coverage import target_date
from weather_quant.ingestion.noaa_nbm import (
    extract_station_block,
    inspect_probabilistic_text,
    parse_station_maxt,
    probabilistic_text_url,
    publication_is_admissible,
)


class NoaaNbmTests(unittest.TestCase):
    def test_probe_target_date_is_day_after_run(self):
        self.assertEqual(target_date("20260114"), "2026-01-15")

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

    def test_parses_only_00z_valid_maximum_rows(self):
        content = """ KORD    NBM V5.0 NBP GUIDANCE    8/30/2026  0100 UTC
 UTC    00  12| 00  12
 FHR    23  35| 47  59
 TXNMN  85  74| 88  76
 TXNSD   3   2|  4   3
 TXNP1  81  71| 84  73
 TXNP2  83  73| 86  74
 TXNP5  85  74| 87  75
 TXNP7  86  75| 89  77
 TXNP9  88  77| 95  80
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nbp.txt"
            path.write_text(content, encoding="ascii")
            parsed = parse_station_maxt(path, "KORD", "2026-08-30T01:00:00Z")
        self.assertEqual(len(parsed["records"]), 2)
        self.assertEqual(parsed["records"][0]["valid_time_utc"], "2026-08-31T00:00:00Z")
        self.assertEqual(parsed["records"][0]["p90_f"], 88)

    def test_extracts_exact_station_block_from_range_payload(self):
        payload = b"""partial preceding bytes
 KORD    NBM V5.0 NBP GUIDANCE    8/30/2026  0700 UTC
 FHR    17  29| 41  53
 TXNMN  85  74| 88  76
 TXNSD   3   2|  4   3
 TXNP1  81  71| 84  73
 TXNP2  83  73| 86  74
 TXNP5  85  74| 87  75
 TXNP7  86  75| 89  77
 TXNP9  88  77| 95  80
 KORE    NBM V5.0 NBP GUIDANCE    8/30/2026  0700 UTC
 trailing bytes
"""
        block = extract_station_block(payload, "KORD")
        self.assertTrue(block.startswith(b" KORD"))
        self.assertIn(b"TXNP9", block)
        self.assertNotIn(b"KORE", block)

    def test_station_block_extraction_fails_when_next_header_is_not_in_range(self):
        payload = b" KORD    NBM V5.0 NBP GUIDANCE    8/30/2026  0700 UTC\n"
        # A truncated range cannot be distinguished from a complete final block,
        # so required markers provide the fail-closed content contract.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "block.txt"
            path.write_bytes(extract_station_block(payload, "KORD"))
            with self.assertRaisesRegex(ValueError, "missing FHR"):
                parse_station_maxt(path, "KORD", "2026-08-30T07:00:00Z")

    def test_publication_admission_uses_decision_timestamp(self):
        self.assertTrue(
            publication_is_admissible(
                "Sun, 30 Aug 2026 08:15:00 GMT", "2026-08-30T11:00:00Z"
            )
        )
        self.assertFalse(
            publication_is_admissible(
                "Sun, 30 Aug 2026 11:00:01 GMT", "2026-08-30T11:00:00Z"
            )
        )


if __name__ == "__main__":
    unittest.main()
