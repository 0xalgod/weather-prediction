import pytest

from scripts.run_chicago_vertical_slice import select_exact_target_record


def test_select_exact_target_record_returns_the_only_match():
    records = [
        {"valid_time_utc": "2026-09-04T00:00:00Z", "value": 1},
        {"valid_time_utc": "2026-09-05T00:00:00Z", "value": 2},
    ]
    selected = select_exact_target_record(records, "2026-09-05T00:00:00Z")
    assert selected["value"] == 2


@pytest.mark.parametrize("records", [[], [{"valid_time_utc": "x"}, {"valid_time_utc": "x"}]])
def test_select_exact_target_record_rejects_zero_or_multiple(records):
    with pytest.raises(ValueError, match="expected one"):
        select_exact_target_record(records, "x")
