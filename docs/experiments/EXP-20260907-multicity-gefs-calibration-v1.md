# EXP-20260907 Multi-city GEFS Calibration v1

## Status

`PREREGISTERED` — calibration candidates and validation metrics have not been calculated.

## Purpose

Determine whether the poor raw GEFS Gaussian result is a simple global bias/spread problem or whether aggregate GEFS should be removed from the current strategy branch.

## Data policy

Only 34 events through 2026-07-11 select calibration parameters. The 16 events from 2026-07-12 through 2026-07-18 are evaluated once. Rows from 2026-07-20 onward belong to the already consumed fixed-benchmark test and will not be scored or used here.

## Locked calibration

Search 13 additive Fahrenheit biases, six spread multipliers, and four standard-deviation floors: 312 candidates. Minimize development multiclass log loss. Ties prefer lower absolute bias, then lower multiplier, then lower floor. This candidate count and selection bias are disclosed explicitly.

The only incremental challenger is still a fixed 50/50 blend of normalized market and calibrated GEFS. The blend weight is not tuned.

## Decision gate

Validation must contain exactly 16 events and at least five target-date clusters. The blend must improve validation log loss over market by at least 2%, not worsen Brier, and produce no invalid probability vector. This is only a signal to justify nested/prospective work, never live promotion.

## Boundary

The test period is excluded and already consumed. Market histories remain indicative rather than executable. With only 34 development and 16 validation events, any successful result would require new future confirmation.
