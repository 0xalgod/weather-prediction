import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from weather_quant.ingestion.noaa_gefs import (
    fetch_index_summary,
    local_day_utc,
    member_names,
    object_url,
    parse_index,
    parse_max_window,
    summarize_index,
    window_coverage,
)

FIXTURE = Path(__file__).parent / "fixtures" / "gefs_index.txt"


class NoaaGefsTests(unittest.TestCase):
    def test_member_set_is_control_plus_thirty_perturbed(self):
        members = member_names()
        self.assertEqual(len(members), 31)
        self.assertEqual((members[0], members[1], members[-1]), ("gec00", "gep01", "gep30"))

    def test_url_is_run_member_and_step_specific(self):
        self.assertEqual(
            object_url("20250830", 0, "gep30", 24),
            "https://noaa-gefs-pds.s3.amazonaws.com/gefs.20250830/00/atmos/"
            "pgrb2sp25/gep30.t00z.pgrb2s.0p25.f024",
        )

    def test_index_extracts_exact_surface_temperature_fields_and_ranges(self):
        parsed = parse_index(FIXTURE.read_text(encoding="ascii"), content_length=700)
        self.assertEqual(parsed["required_field_counts"], {"TMP": 1, "TMAX": 1, "TMIN": 1})
        self.assertEqual(parsed["selected_range_bytes"], 400)
        self.assertEqual([row["length"] for row in parsed["selected_rows"]], [120, 130, 150])

    def test_index_summary_does_not_require_full_object_size(self):
        parsed = summarize_index(FIXTURE.read_text(encoding="ascii"))
        self.assertEqual(parsed["required_field_counts"], {"TMP": 1, "TMAX": 1, "TMIN": 1})
        self.assertEqual(parsed["selected_row_count"], 3)

    @patch("weather_quant.ingestion.noaa_gefs.time.sleep")
    @patch(
        "weather_quant.ingestion.noaa_gefs.urlopen",
        side_effect=ConnectionResetError("peer reset"),
    )
    def test_connection_reset_is_bounded_and_recorded(self, _urlopen, _sleep):
        result = fetch_index_summary("https://example.test/object", attempts=3)
        self.assertIsNone(result["inventory"])
        self.assertEqual(result["attempt_count"], 3)
        self.assertEqual([error["kind"] for error in result["errors"]], ["transport"] * 3)

    def test_max_window_parser_rejects_non_maximum_metadata(self):
        self.assertEqual(parse_max_window("18-24 hour max fcst"), (18, 24))
        with self.assertRaises(ValueError):
            parse_max_window("24 hour fcst")

    def test_local_day_uses_real_dst_duration(self):
        start, end = local_day_utc(date(2026, 3, 8), "America/Toronto")
        self.assertEqual((end - start).total_seconds(), 23 * 3600)
        start, end = local_day_utc(date(2026, 11, 1), "America/Toronto")
        self.assertEqual((end - start).total_seconds(), 25 * 3600)

    def test_window_coverage_reports_boundary_contamination(self):
        utc = timezone.utc
        target_start = datetime(2026, 7, 23, 4, tzinfo=utc)
        target_end = datetime(2026, 7, 24, 4, tzinfo=utc)
        windows = [
            (
                datetime(2026, 7, 23, hour, tzinfo=utc),
                datetime(2026, 7, 23, hour, tzinfo=utc) + timedelta(hours=6),
            )
            for hour in (0, 6, 12, 18)
        ] + [(datetime(2026, 7, 24, 0, tzinfo=utc), datetime(2026, 7, 24, 6, tzinfo=utc))]
        result = window_coverage(target_start, target_end, windows)
        self.assertEqual(result["uncovered_seconds"], 0)
        self.assertEqual(result["outside_local_seconds"], 6 * 3600)
        self.assertFalse(result["exact_partition"])


if __name__ == "__main__":
    unittest.main()
