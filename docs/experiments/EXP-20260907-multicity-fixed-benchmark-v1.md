# EXP-20260907 Multi-city Fixed Benchmark v1

## Status

`FAILED` — the fixed blend promotion gate was evaluated once and rejected on 2026-09-07.

## Question

Does a fixed combination of global GEFS information and the 18-hour Polymarket distribution improve probabilistic accuracy over the market alone on an untouched chronological test period?

## Chronological split

- development: through 2026-07-11, expected 34 events;
- validation: 2026-07-12 through 2026-07-18, expected 16 events;
- untouched test: from 2026-07-20, expected 20 events.

Events sharing a target date cannot cross splits. Test data is not used for model or weight selection.

## Fixed models

1. Uniform: 1/11 per bucket.
2. Normalized market: frozen 18-hour indicative vector.
3. Raw GEFS Gaussian: overlap-peak mean and `max(spread_at_peak, 1°F)`, evaluated on frozen continuity-corrected bucket edges.
4. Fixed blend: 50% normalized market plus 50% raw GEFS Gaussian. The weight is not fitted.

The GEFS Gaussian is intentionally simple and its block spread is not assumed to be a calibrated daily-maximum uncertainty distribution.

## Metrics and decision

Primary metric is multiclass log loss with probability floor 1e-6. Brier and ranked probability scores are secondary. Uncertainty uses 10,000 target-date cluster bootstrap repetitions so same-day cities are not treated as independent.

The fixed blend produces a research promotion signal only if the untouched test contains at least 15 events, improves log loss over market by at least 2%, does not worsen Brier, and the paired clustered log-loss difference has a 95% CI upper bound below zero.

## Boundary

The sample is small, city coverage is sparse, market prices are non-executable historical indications, and no order-book fill is reconstructed. Even a pass would authorize further prospective research, not live trading.

## Result

All split counts and probability-vector checks passed. Untouched-test log loss was:

| Model | Test log loss | Test Brier |
|---|---:|---:|
| Uniform | 2.3979 | 0.9091 |
| Normalized market | 1.2567 | 0.6643 |
| Raw GEFS Gaussian | 6.2400 | 1.2320 |
| Fixed 50/50 blend | 1.7168 | 0.8464 |

The blend's relative log-loss improvement versus market was −36.61%; it made the score worse. Paired target-date cluster-bootstrap blend-minus-market log loss was `+0.4601`, with 95% CI `[+0.3321, +0.6149]`. Brier worsened by `+0.1821`. Every promotion criterion related to incremental skill failed.

The preregistered slices tell the same directional story. Market/GEFS log loss was 1.327/5.079 for Celsius events, 0.988/2.105 for Fahrenheit events, 0.476/3.746 for exact partitions, and 1.309/4.450 for overlap proxies. The poor GEFS result is therefore not explained solely by Celsius conversion or overlap contamination, though these estimates remain small-sample diagnostics.

## Decision

Reject the raw GEFS Gaussian and fixed blend. Keep normalized market as the current 18-hour probabilistic benchmark. The test period is consumed and must not be reused to select a blend weight or spread adjustment.

The next admissible modeling work is a preregistered development-only calibration diagnostic followed by nested chronological evaluation or genuinely future data. It cannot retroactively promote a model on this consumed test.
