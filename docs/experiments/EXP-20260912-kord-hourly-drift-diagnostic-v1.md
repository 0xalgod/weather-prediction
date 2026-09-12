# EXP-20260912-kord-hourly-drift-diagnostic-v1

## Status

`PASSED` — preregistered persistent-drift classification threshold was met.

Reproduce the locked Ridge alpha-100 model without changing features, training rows, or parameters. Measure validation/test residuals by calendar month, 30-day rolling test bias, prediction/target means, and standardized train-to-test feature mean shifts. Classify persistent drift only if at least three test months have bias at or below -1°C. This is post-failure diagnosis on a consumed test, never new validation evidence.

## Result

Five of six test calendar months had bias at or below -1°C (March through July 2026), exceeding the preregistered minimum of three. The worst eligible 30-day rolling bias was -3.697°C. Seven features shifted by at least 0.5 train standard deviations; the largest was `observation_count` at +2.367 standard deviations. Decision: `PERSISTENT_REGIME_DRIFT_CONFIRMED`.

This result permits an expanding-window retrain experiment. It does not repair the rejected model and is not a new protected test because the outcome period has already been consumed.
