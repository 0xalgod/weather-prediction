import copy
import json
import unittest
from pathlib import Path

from weather_quant.normalization.resolution_rules import (
    ResolutionRegistryError,
    build_bucket_records,
    parse_bucket_bounds,
    rule_sha256,
    validate_resolution_record,
)


FIXTURE = Path(__file__).parent / "fixtures" / "resolution_registry_record.json"


class ResolutionRegistryTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_reconciled_fixture_passes_contract(self):
        self.assertEqual(rule_sha256(self.record["rule"]["rule_text"]), self.record["rule"]["rule_text_sha256"])
        self.assertEqual(validate_resolution_record(self.record), [])

    def test_gap_or_overlap_is_rejected(self):
        broken = copy.deepcopy(self.record)
        broken["buckets"][1]["lower_bound"] = 71
        with self.assertRaisesRegex(ResolutionRegistryError, "gap or overlap"):
            validate_resolution_record(broken)

    def test_rule_revision_requires_new_hash(self):
        broken = copy.deepcopy(self.record)
        broken["rule"]["rule_text"] += " changed"
        with self.assertRaisesRegex(ResolutionRegistryError, "rule hash"):
            validate_resolution_record(broken)

    def test_invalid_timezone_is_rejected(self):
        broken = copy.deepcopy(self.record)
        broken["rule"]["timezone"] = "Invalid/Nowhere"
        with self.assertRaisesRegex(ResolutionRegistryError, "IANA"):
            validate_resolution_record(broken)

    def test_no_trade_preserves_missing_fields_with_reason(self):
        excluded = copy.deepcopy(self.record)
        excluded["disposition"] = "NO_TRADE_MISSING_RESOLUTION_SOURCE"
        excluded["exclusion_reasons"] = ["MISSING_RESOLUTION_SOURCE"]
        excluded["rule"]["source_url"] = None
        self.assertEqual(validate_resolution_record(excluded), ["MISSING_RESOLUTION_SOURCE"])

    def test_parses_celsius_and_fahrenheit_bucket_boundaries(self):
        self.assertEqual(parse_bucket_bounds("27°C or below", "C")["lower_bound"], None)
        self.assertEqual(parse_bucket_bounds("74-75°F", "F")["upper_bound"], 75)
        self.assertEqual(parse_bucket_bounds("37°C or higher", "C")["upper_bound"], None)

    def test_incomplete_token_identity_cannot_build_bucket(self):
        with self.assertRaisesRegex(ResolutionRegistryError, "incomplete identifiers"):
            build_bucket_records([{"id": "1", "conditionId": None, "clobTokenIds": "[]", "groupItemTitle": "20°C"}], "C")

    def test_station_candidate_runs_full_contract_but_remains_excluded(self):
        candidate = copy.deepcopy(self.record)
        candidate["disposition"] = "CANDIDATE_STATION_UNVERIFIED"
        candidate["exclusion_reasons"] = ["STATION_TIMEZONE_UNVERIFIED"]
        self.assertEqual(validate_resolution_record(candidate), ["STATION_TIMEZONE_UNVERIFIED"])
        candidate["buckets"][1]["lower_bound"] = 71
        with self.assertRaisesRegex(ResolutionRegistryError, "gap or overlap"):
            validate_resolution_record(candidate)


if __name__ == "__main__":
    unittest.main()
