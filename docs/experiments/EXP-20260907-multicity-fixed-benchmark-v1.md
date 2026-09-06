# EXP-20260907 Multi-city Fixed Benchmark v1

## Status

`PREREGISTERED` — no benchmark probability or score has been calculated.

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
