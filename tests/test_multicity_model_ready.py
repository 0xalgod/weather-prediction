from weather_quant.features.multicity_model_ready import (
    aggregate_gefs_messages,
    ordered_bucket_thresholds,
)


def test_bucket_thresholds_apply_native_continuity_correction() -> None:
    buckets = [
        {"label": "11°C or below", "market_id": "low"},
        {"label": "12°C", "market_id": "mid"},
        {"label": "13°C or higher", "market_id": "high"},
    ]
    rows = ordered_bucket_thresholds(buckets, "C")
    assert rows[0]["lower_threshold_f"] is None
    assert rows[0]["upper_threshold_f"] == 52.7
    assert rows[1]["lower_threshold_f"] == 52.7
    assert rows[-1]["upper_threshold_f"] is None


def test_gefs_peak_tie_uses_lowest_step() -> None:
    messages = [
        {"step": 6, "product": "geavg", "value_f": 80},
        {"step": 6, "product": "gespr", "value_f": 2},
        {"step": 12, "product": "geavg", "value_f": 80},
        {"step": 12, "product": "gespr", "value_f": 3},
    ]
    result = aggregate_gefs_messages(messages)
    assert result["gefs_overlap_peak_step"] == 6
    assert result["gefs_overlap_spread_at_mean_max_f"] == 2
    assert result["gefs_max_block_spread_f"] == 3
