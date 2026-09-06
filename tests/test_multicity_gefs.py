from weather_quant.backtest.scoring import paired_cluster_bootstrap_mean_difference
from weather_quant.features.multicity_gefs import longitude_stratified_sample


def test_longitude_stratified_sample_uses_even_order_statistics() -> None:
    rows = [
        {
            "event_id": str(index),
            "longitude": float(index),
            "latitude": 0.0,
            "target_date": "2026-01-01",
        }
        for index in range(12)
    ]
    assert [row["event_id"] for row in longitude_stratified_sample(rows, 4)] == [
        "0",
        "4",
        "7",
        "11",
    ]


def test_cluster_bootstrap_preserves_paired_mean_direction() -> None:
    result = paired_cluster_bootstrap_mean_difference(
        [1.0, 2.0, 4.0], [2.0, 3.0, 5.0], ["a", "a", "b"], 100, 7
    )
    assert result["mean_difference"] == -1.0
    assert result["ci95_upper"] == -1.0
    assert result["cluster_count"] == 2
