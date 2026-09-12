from scripts.correct_multicity_hourly_dataset import correct_hourly_rows, correction_checks


def test_correction_nulls_invalid_temperature_and_dependent_rh():
    source = [
        {"dry_bulb_c": 9.0, "relative_humidity_pct": 70.0},
        {"dry_bulb_c": 80.0, "relative_humidity_pct": 2.0},
    ]

    corrected, count = correct_hourly_rows(source)

    assert count == 1
    assert corrected[0] == source[0]
    assert corrected[1]["dry_bulb_c"] is None
    assert corrected[1]["relative_humidity_pct"] is None
    assert corrected[1]["original_dry_bulb_c"] == 80.0
    assert corrected[1]["original_relative_humidity_pct"] == 2.0
    assert corrected[1]["quality_flags"] == [
        "OUT_OF_RANGE_DRY_BULB_NULLED",
        "DEPENDENT_RH_NULLED",
    ]
    assert source[1]["dry_bulb_c"] == 80.0


def test_correction_checks_enforce_sparse_transform_and_quality():
    summary = {
        "corrected_hourly_row_fraction": 0.00001,
        "label_coverage": 1.0,
        "days_with_18_temperature_hours_through_cutoff_rate": 0.98,
        "out_of_range_temperature_count": 0,
        "station_identity_error_count": 0,
        "duplicate_sod_date_count": 0,
    }
    gates = {
        "maximum_corrected_hourly_row_fraction_per_station": 0.0001,
        "minimum_label_coverage": 0.99,
        "minimum_days_with_18_temperature_hours_through_cutoff_rate": 0.95,
        "maximum_remaining_out_of_range_temperature_count": 0,
        "maximum_station_identity_error_count": 0,
        "maximum_duplicate_sod_date_count": 0,
    }

    assert all(correction_checks(summary, gates).values())
    summary["corrected_hourly_row_fraction"] = 0.001
    assert not correction_checks(summary, gates)[
        "maximum_corrected_hourly_row_fraction_per_station"
    ]
