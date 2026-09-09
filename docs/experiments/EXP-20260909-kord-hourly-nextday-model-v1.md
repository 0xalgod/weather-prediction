# EXP-20260909-kord-hourly-nextday-model-v1

## Status

`PREREGISTERED` — features, fit, validation, and test scores have not run.

## Design

Predict KORD's target-day NOAA SOD maximum temperature using only information available by 18:00 local standard time on the preceding day. Chronological splits are train 2024-08-01–2025-07-31 (365), validation 2025-08-01–2026-01-31 (184), and protected test 2026-02-01–2026-07-31 (181).

Features include calendar harmonics, hourly weather aggregates and hour-of-day temperatures through the cutoff, and SOD label lags starting at two days. Target-day data and the preceding day's incomplete SOD label are forbidden. Missing values are imputed from train-fold medians with missing indicators.

Compare persistence and train-fitted harmonic climatology against Ridge and histogram gradient boosting. Hyperparameters and the champion are selected using five expanding time-series folds inside train only. Validation passes only if the champion improves MAE by at least 5% against both baselines and absolute bias is at most 1°C. Test is opened once only after a full validation pass and uses identical gates.
