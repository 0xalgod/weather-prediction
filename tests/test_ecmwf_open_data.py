import unittest
from pathlib import Path

from weather_quant.ingestion.ecmwf_open_data import index_url, inventory_index

FIXTURE = Path(__file__).parent / "fixtures" / "ecmwf_open_index.jsonl"


class EcmwfOpenDataTests(unittest.TestCase):
    def test_index_url_is_run_stream_and_step_specific(self):
        self.assertEqual(
            index_url("20260830", 0, "oper", 24),
            "https://data.ecmwf.int/forecasts/20260830/00z/ifs/0p25/oper/"
            "20260830000000-24h-oper-fc.index",
        )

    def test_inventory_counts_only_required_temperature_fields(self):
        inventory = inventory_index(FIXTURE)
        self.assertEqual(inventory["selected_row_count"], 3)
        self.assertEqual(inventory["selected_range_bytes"], 33)
        self.assertEqual(inventory["type_parameter_counts"]["fc:mx2t3"], 1)
        self.assertTrue(inventory["all_selected_have_ranges"])


if __name__ == "__main__":
    unittest.main()
