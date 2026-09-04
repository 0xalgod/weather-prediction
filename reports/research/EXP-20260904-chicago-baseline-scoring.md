# Chicago baseline scoring — first model evidence

**Experiment:** `EXP-20260904-chicago-baseline-scoring`  
**Split:** first 20 dates validation, last 10 dates single-use test  
**Decision:** `FORECAST_BASELINES_PASS_MARKET_COMPARISON_UNAVAILABLE`  
**Fitting/tuning:** none

## Result

Lower scores are better.

| Split / model | Log loss | Brier | RPS | Winner probability |
|---|---:|---:|---:|---:|
| Validation — uniform | 2.398 | 0.909 | 0.1123 | 9.09% |
| Validation — Gaussian | 1.575 | 0.774 | 0.0586 | 22.72% |
| Validation — quantile | **1.556** | 0.795 | 0.0592 | 22.10% |
| Test — uniform | 2.398 | 0.909 | 0.0964 | 9.09% |
| Test — Gaussian | 1.171 | 0.633 | 0.0369 | 32.96% |
| Test — quantile | **1.085** | **0.600** | **0.0322** | **35.75%** |

Both fixed NBM representations beat the uniform baseline on primary log loss in validation and test. This earns only `PRELIMINARY_BETTER_BASELINE`: no model was trained, and the test segment has ten consecutive summer dates.

Quantile has lower mean log loss than Gaussian in both splits. However, paired date-bootstrap Gaussian-minus-quantile 95% intervals include zero:

- validation: mean `+0.0199`, CI `[-0.1239, +0.1866]`;
- test: mean `+0.0853`, CI `[-0.0960, +0.2673]`.

Therefore the evidence does not establish that quantile is reliably superior.

## Market comparison failed safely

Zero of 30 events had a historical price point timestamped at or before the locked prior-day 11:00 UTC decision time for every bucket. The API's sparse points begin later. We did not pull later prices backward, change the decision time or substitute settlement prices.

Consequently there is no honest model-versus-market score, EV estimate or historical profitability claim from this dataset. This is a data-availability result, not a negative trading-edge result.

## Decision

The fixed forecast baselines are useful enough to justify expanding the labeled weather sample and eventually fitting calibration models. Before that, the f41 NBM-to-Chicago-local-day semantic mapping should be independently resolved. Prospective 14:00 Turkey L2 snapshots remain the execution evidence needed for EV.
