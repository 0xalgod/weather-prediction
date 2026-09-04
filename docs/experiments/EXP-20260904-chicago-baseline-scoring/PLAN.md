# EXP-20260904 — Chicago baseline scoring

**Status:** `IN_PROGRESS`
**Pre-registration:** 2026-09-04, before calculating model scores

## Question and hypothesis

On the exact 30 joined Chicago dates, do the locked NBM Gaussian and quantile-preserving distributions assign better probabilities to resolved temperature buckets than an equal-probability baseline, and does either NBM representation consistently dominate the other on the last 10-date holdout?

This is a baseline comparison without fitting or hyperparameter tuning. It is not a strategy backtest.

## Locked split

- Sort target local dates ascending.
- First 20 dates: validation/diagnostic segment.
- Last 10 dates: test segment.
- Models and transformations are already fixed; test is evaluated once and will not be used for tuning.

## Locked probability models

- Uniform: `1 / bucket_count` for each event bucket.
- Gaussian: NBM mean/standard deviation with the existing whole-degree continuity-corrected normal CDF.
- Quantile preserving: existing preregistered p10/p25/p50/p75/p90 piecewise-linear finite-tail CDF.

## Metrics

Primary is mean multiclass log loss. Secondary metrics are multiclass Brier score, ranked probability score and probability assigned to the winning bucket. Every event remains the cluster unit. Paired date bootstrap uses 10,000 resamples and seed `20260904` for Gaussian-minus-quantile uncertainty intervals.

The quality gate requires probability sums within `1e-9`, finite metrics for every model-event row, one-hot winners for every event and exactly 10 test events.

## Indicative market benchmark

For each YES token, select only the latest history point timestamped at or before the locked decision time. Future points are forbidden. Require all event tokens and maximum 18-hour staleness, then normalize positive cross-bucket YES prices to sum to one for scoring. Report raw sum and staleness.

At least 8/10 test events are required for any model-versus-market statement. If fewer qualify, market comparison is `INSUFFICIENT_POINT_IN_TIME_COVERAGE`; timestamps are not shifted and later prices are not substituted.

## Interpretation

- A model may be labelled `PRELIMINARY_BETTER_BASELINE` only if it beats uniform on both validation and test primary metric.
- Gaussian versus quantile ordering is descriptive at 30 dates; bootstrap intervals are reported but do not establish a durable edge.
- No model-versus-market, EV or trading claim is allowed without the market coverage gate.
- The sample is one city, one NBM version and one summer month; expansion and walk-forward training remain required.
