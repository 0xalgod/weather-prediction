#!/usr/bin/env python3
"""Fit and validate the preregistered 13Z incremental model."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from scripts.probe_multicity_price_horizons import sha256_path, utc_now
from weather_quant.backtest.scoring import (
    mean_metrics,
    paired_cluster_bootstrap_mean_difference,
    score_probabilities,
)
from weather_quant.forecasting.calibration import quantile_probabilities, select_parameters
from weather_quant.normalization.resolution_rules import parse_bucket_bounds


def event(row, label):
    return {
        "buckets": [
            {**b, **parse_bucket_bounds(b["label"], row["temperature_unit"])}
            for b in row["buckets"]
        ],
        "forecast": row["nbm_features"][label],
        "winning_market_id": row["buckets"][row["winner_bucket_index"]]["market_id"],
    }


def vectors(row, params, weight):
    buckets = event(row, "13Z")["buckets"]
    p07 = quantile_probabilities(
        buckets, row["nbm_features"]["07Z"], params["07Z"]["shift_f"], params["07Z"]["spread_scale"]
    )
    p13 = quantile_probabilities(
        buckets, row["nbm_features"]["13Z"], params["13Z"]["shift_f"], params["13Z"]["spread_scale"]
    )
    market = row["market_probabilities"]
    return {
        "market": market,
        "calibrated_07z": p07,
        "calibrated_13z": p13,
        "challenger": [(1 - weight) * m + weight * n for m, n in zip(market, p13)],
    }


def scores(rows, params, weight, floor):
    out = []
    for row in rows:
        vs = vectors(row, params, weight)
        winner = row["winner_bucket_index"]
        out.append(
            {
                "event_id": row["event_id"],
                "city": row["city"],
                "target_date": row["target_date"],
                "models": {
                    k: {"probabilities": v, "metrics": score_probabilities(v, winner, floor)}
                    for k, v in vs.items()
                },
            }
        )
    return out


def aggregate(rows):
    return {
        name: mean_metrics([r["models"][name]["metrics"] for r in rows])
        for name in rows[0]["models"]
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError("immutable output exists")
    c = json.loads(a.config.read_text())
    source = Path(c["source_dataset"])
    if sha256_path(source) != c["source_dataset_sha256"]:
        raise ValueError("dataset checksum mismatch")
    rows = [json.loads(x) for x in source.read_text().splitlines()]
    split = c["temporal_split"]
    dev = [r for r in rows if r["target_date"] in split["development_dates"]]
    val = [r for r in rows if r["target_date"] in split["validation_dates"]]
    if (
        len(dev) != split["expected_development_count"]
        or len(val) != split["expected_validation_count"]
    ):
        raise ValueError("split count mismatch")
    grid = c["calibration_grid"]
    shifts = list(
        range(grid["shift_f"]["minimum"], grid["shift_f"]["maximum"] + 1, grid["shift_f"]["step"])
    )
    floor = grid["probability_floor"]
    params = {
        label: select_parameters(
            [event(r, label) for r in dev],
            quantile_probabilities,
            shifts,
            grid["spread_scale"],
            floor,
        )
        for label in ("07Z", "13Z")
    }
    candidates = []
    for w in grid["blend_13z_weight"]:
        s = scores(dev, params, w, floor)
        candidates.append(
            {"weight": w, "log_loss": aggregate(s)["challenger"]["multiclass_log_loss"]}
        )
    selected = min(candidates, key=lambda x: (x["log_loss"], x["weight"]))
    validation = scores(val, params, selected["weight"], floor)
    metrics = aggregate(validation)
    l07 = metrics["calibrated_07z"]["multiclass_log_loss"]
    l13 = metrics["calibrated_13z"]["multiclass_log_loss"]
    lm = metrics["market"]["multiclass_log_loss"]
    lc = metrics["challenger"]["multiclass_log_loss"]
    diagnostics = {
        "event_count": len(val),
        "date_count": len({r["target_date"] for r in val}),
        "13z_vs_07z_log_loss_improvement": (l07 - l13) / l07,
        "challenger_vs_market_log_loss_improvement": (lm - lc) / lm,
        "challenger_minus_market_brier": metrics["challenger"]["multiclass_brier_score"]
        - metrics["market"]["multiclass_brier_score"],
        "invalid_probability_vector_count": sum(
            abs(math.fsum(m["probabilities"]) - 1) > 1e-9
            for r in validation
            for m in r["models"].values()
        ),
        "models": metrics,
    }
    g = c["validation_gates"]
    checks = {
        "minimum_13z_vs_07z_log_loss_improvement": diagnostics["13z_vs_07z_log_loss_improvement"]
        >= g["minimum_13z_vs_07z_log_loss_improvement"],
        "minimum_challenger_vs_market_log_loss_improvement": diagnostics[
            "challenger_vs_market_log_loss_improvement"
        ]
        >= g["minimum_challenger_vs_market_log_loss_improvement"],
        "maximum_challenger_minus_market_brier": diagnostics["challenger_minus_market_brier"]
        <= g["maximum_challenger_minus_market_brier"],
        "maximum_invalid_probability_vector_count": diagnostics["invalid_probability_vector_count"]
        <= g["maximum_invalid_probability_vector_count"],
        "exact_validation_date_count": diagnostics["date_count"]
        == g["exact_validation_date_count"],
    }
    uncertainty = paired_cluster_bootstrap_mean_difference(
        [r["models"]["challenger"]["metrics"]["multiclass_log_loss"] for r in validation],
        [r["models"]["market"]["metrics"]["multiclass_log_loss"] for r in validation],
        [r["target_date"] for r in validation],
        10000,
        20260909,
    )
    result = {
        "experiment_id": c["experiment_id"],
        "generated_at_utc": utc_now(),
        "config_sha256": sha256_path(a.config),
        "source_dataset_sha256": sha256_path(source),
        "split_counts": {"development": len(dev), "validation": len(val)},
        "selected_calibration": params,
        "blend_candidates": candidates,
        "selected_blend": selected,
        "validation": {
            "diagnostics": diagnostics,
            "checks": checks,
            "challenger_minus_market_log_loss_bootstrap": uncertainty,
        },
        "decision": "VALIDATION_PASS" if all(checks.values()) else "VALIDATION_REJECT",
        "boundary": c["boundary"],
    }
    a.output.mkdir(parents=True)
    (a.output / "validation-scores.jsonl").write_text(
        "".join(json.dumps(x, sort_keys=True) + "\n" for x in validation)
    )
    (a.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
