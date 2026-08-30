import unittest
from pathlib import Path

from weather_quant.ingestion.noaa_gefs import member_names, object_url, parse_index

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


if __name__ == "__main__":
    unittest.main()
