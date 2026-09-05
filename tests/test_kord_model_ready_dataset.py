from datetime import date

from scripts.build_kord_model_ready_dataset import (
    calendar_features,
    canonical_sha256,
    decision_time,
)


def test_calendar_features_capture_dst_and_are_finite() -> None:
    winter = calendar_features(date(2026, 1, 1))
    summer = calendar_features(date(2026, 7, 1))
    assert winter["dst_offset_hours"] == -6
    assert summer["dst_offset_hours"] == -5
    assert -1 <= summer["day_of_year_sin"] <= 1
    assert -1 <= summer["day_of_year_cos"] <= 1


def test_decision_time_is_prior_day_at_11z() -> None:
    assert decision_time(date(2026, 7, 1)).isoformat() == "2026-06-30T11:00:00+00:00"


def test_canonical_checksum_ignores_mapping_order() -> None:
    assert canonical_sha256({"a": 1, "b": 2}) == canonical_sha256({"b": 2, "a": 1})
