# EXP-20260912-multicity-hourly-data-correction-v2

## Status

`PASSED` — all corrective data-quality gates passed; no confirmation model had been scored at this decision point.

## Hypothesis

The multi-city V1 failure is a sparse structured-field anomaly that can be handled without inventing a replacement value. Across every station, any non-null `dry_bulb_c` outside inclusive [-60, 60]°C will trigger the same deterministic rule: preserve original temperature and RH as provenance, set model-input temperature and dependent RH to missing, and add explicit quality flags.

## Locked gates

- Corrected rows must be no more than 0.01% of hourly rows at each station.
- Every station must retain at least 99% label coverage and 95% eligible cutoff-window coverage.
- Remaining out-of-range temperature, station identity errors, and duplicate SOD dates must be zero.
- No METAR-derived replacement, interpolation, station removal, date removal, model fit, or outcome score is permitted in this step.

Pass freezes corrected V2 artifacts and permits the original five-station confirmation to run once. Fail stops scoring.

## Result

Exactly one of 152,589 cohort hourly rows was corrected: KSEA 2024-12-26 02:53 LST. Its station-level correction fraction was 0.00310%, below the preregistered 0.01% maximum. No other station required correction.

All five stations retained label coverage between 99.863% and 100%, cutoff-window coverage between 98.082% and 98.767%, and zero remaining invalid temperature, station identity error, or duplicate SOD date. Decision: `CORRECTED_DATASET_PASS`.
