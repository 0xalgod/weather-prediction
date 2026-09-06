# EXP-20260907 Multi-city GEFS Calibration v1

## Status

`FAILED` — the development-selected calibration failed its one-time validation on 2026-09-07.

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

## Result

Development selected `+2°F` bias, `2×` spread multiplier, and `3°F` standard-deviation floor from 312 candidates. This reduced development GEFS log loss from 3.2858 to 1.7510, but market remained better at 1.2836.

On the one-time 16-event/five-date validation:

| Model | Log loss | Brier |
|---|---:|---:|
| Normalized market | 1.1694 | 0.6127 |
| Raw GEFS | 4.4654 | 1.0294 |
| Calibrated GEFS | 2.5415 | 0.9593 |
| Fixed calibrated blend | 1.4932 | 0.7300 |

The calibrated blend worsened market log loss by 27.70% and Brier by 0.1173. Both incremental gates failed. Raw GEFS mean fell inside the winning bucket interval in only 16% of development-plus-validation events.

The preregistered slices were consistently adverse. In validation, market/calibrated-GEFS/blend log loss was 1.202/2.666/1.519 for Celsius, 1.027/2.003/1.381 for Fahrenheit, 1.218/2.615/1.538 for overlap proxy, and 0.436/1.445/0.818 for the single exact event.

## Decision

Reject global calibration and drop aggregate GEFS from this dataset's strategy branch. Do not run a larger grid or tune the blend against the consumed test. A better-quality probabilistic forecast source or new prospective data is required.
