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
