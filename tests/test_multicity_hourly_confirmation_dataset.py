from scripts.build_multicity_hourly_confirmation_dataset import quality_checks


def test_quality_checks_use_cutoff_coverage_and_identity():
    summary = {
        "target_day_count": 730,
        "label_coverage": 0.995,
        "days_with_18_temperature_hours_through_cutoff_rate": 0.96,
        "station_identity_error_count": 0,
        "duplicate_sod_date_count": 0,
        "out_of_range_temperature_count": 0,
        "unique_station_names": ["AIRPORT, STATE US"],
    }
    gates = {
        "minimum_label_coverage": 0.99,
        "minimum_days_with_18_temperature_hours_through_cutoff_rate": 0.95,
        "maximum_station_identity_error_count": 0,
        "maximum_duplicate_sod_date_count": 0,
        "maximum_out_of_range_temperature_count": 0,
    }

    assert all(quality_checks(summary, gates, 730).values())

    summary["station_identity_error_count"] = 1
    assert not quality_checks(summary, gates, 730)["maximum_station_identity_error_count"]


def test_quality_checks_reject_multiple_station_names():
    summary = {
        "target_day_count": 730,
        "label_coverage": 1.0,
        "days_with_18_temperature_hours_through_cutoff_rate": 1.0,
        "station_identity_error_count": 0,
        "duplicate_sod_date_count": 0,
        "out_of_range_temperature_count": 0,
        "unique_station_names": ["OLD NAME", "NEW NAME"],
    }
    gates = {
        "minimum_label_coverage": 0.99,
        "minimum_days_with_18_temperature_hours_through_cutoff_rate": 0.95,
        "maximum_station_identity_error_count": 0,
        "maximum_duplicate_sod_date_count": 0,
        "maximum_out_of_range_temperature_count": 0,
    }

    assert not quality_checks(summary, gates, 730)["single_station_name"]
