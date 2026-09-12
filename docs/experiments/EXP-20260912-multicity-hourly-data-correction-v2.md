# EXP-20260912-multicity-hourly-data-correction-v2

## Status

`PREREGISTERED` — corrective transform has not run and no confirmation model has been scored.

## Hypothesis

The multi-city V1 failure is a sparse structured-field anomaly that can be handled without inventing a replacement value. Across every station, any non-null `dry_bulb_c` outside inclusive [-60, 60]°C will trigger the same deterministic rule: preserve original temperature and RH as provenance, set model-input temperature and dependent RH to missing, and add explicit quality flags.

## Locked gates

- Corrected rows must be no more than 0.01% of hourly rows at each station.
- Every station must retain at least 99% label coverage and 95% eligible cutoff-window coverage.
- Remaining out-of-range temperature, station identity errors, and duplicate SOD dates must be zero.
- No METAR-derived replacement, interpolation, station removal, date removal, model fit, or outcome score is permitted in this step.

Pass freezes corrected V2 artifacts and permits the original five-station confirmation to run once. Fail stops scoring.
