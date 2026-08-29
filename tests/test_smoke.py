from pathlib import Path
import unittest

from weather_quant.pipeline import (
    brier_score,
    celsius_to_fahrenheit,
    ensemble_mean,
    run_smoke_pipeline,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PipelineSmokeTest(unittest.TestCase):
    def test_repository_pipeline_is_reproducible(self) -> None:
        result = run_smoke_pipeline(PROJECT_ROOT / "configs" / "base.json")

        self.assertEqual(result["project_name"], "weather-quant")
        self.assertFalse(result["live_trading_enabled"])
        self.assertEqual(result["ensemble_mean_celsius"], 21.0)
        self.assertAlmostEqual(result["ensemble_mean_fahrenheit"], 69.8)
        self.assertAlmostEqual(result["brier_score"], 1.0 / 9.0)

    def test_critical_transform_guards(self) -> None:
        self.assertEqual(celsius_to_fahrenheit(0.0), 32.0)
        self.assertEqual(ensemble_mean([1.0, 2.0, 3.0]), 2.0)
        self.assertEqual(brier_score(1.0, 1), 0.0)

        with self.assertRaises(ValueError):
            ensemble_mean([])
        with self.assertRaises(ValueError):
            brier_score(1.01, 1)
        with self.assertRaises(ValueError):
            brier_score(0.5, 2)


if __name__ == "__main__":
    unittest.main()
