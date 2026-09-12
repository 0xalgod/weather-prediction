# EXP-20260912-kord-hourly-expanding-walkforward-v1

## Status

`PREREGISTERED` — expanding walk-forward run has not started.

## Hypothesis

A locked Ridge alpha-100 model, refitted daily on every eligible historical row available before the prediction date, will reduce the static model's persistent bias without sacrificing its MAE advantage. Over both the complete 2025-08-01–2026-07-31 evaluation period and the 2026-02-01–2026-07-31 former-test segment, it must have absolute bias at or below 1°C and improve MAE versus persistence by at least 5%.

## Protocol

- Begin with 365 eligible training targets from 2024-08-01 through 2025-07-31.
- Predict the next eligible target date, then add its now-observed row to the training history before predicting the following eligible date.
- Refit median imputation, missing indicators, scaling, Ridge alpha-100, and harmonic climatology using past rows only at every step.
- Keep the parent experiment's 48 features, prior-day 18:00 LST weather cutoff, and minimum 18-hour eligibility rule unchanged.
- Compare against prior-day observed maximum and an expanding harmonic day-of-year regression.
- Report the full evaluation, former-validation, former-test, and calendar-month metrics.
- Perform no model selection, hyperparameter tuning, feature selection, recalibration, or threshold changes.

## Interpretation boundary

The evaluation outcomes were exposed by earlier work. This is therefore a post-test exploratory diagnostic even though the walk-forward calculation itself is leakage-safe. Passing the gates would justify freezing a candidate for a new disjoint confirmation cohort; it would not constitute confirmation or trading evidence.
