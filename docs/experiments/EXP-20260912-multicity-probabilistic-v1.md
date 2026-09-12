# EXP-20260912-multicity-probabilistic-v1

## Status

`FAILED` — the frozen Student-t candidate beat both baselines but failed protected interval-calibration gates.

## Why this experiment exists

The expanding Ridge model now has confirmed point-forecast skill, but MAE does not establish calibrated probabilities. Trading temperature buckets requires a full predictive distribution: both its center and its uncertainty must be reliable.

## Development and protected test

KORD, KJFK, KLAX, KDFW, KMIA, and KSEA are consumed and may be used only for probability-model development. Candidate selection will use leave-one-development-station-out CRPS. KBOS, KPHX, and KDEN are frozen protected spatial test stations and may be opened once after data quality and candidate selection are complete.

Every protected station uses the same 2024-08-01–2025-07-31 initial point-model history and 2025-08-01–2026-07-31 probability test. Point predictions remain the frozen station-specific daily expanding Ridge alpha-100 procedure.

## Candidate distributions

- Gaussian development residual distribution.
- Student-t residual distribution with development-only degrees-of-freedom selection.
- Empirical development residual distribution with development-only fixed jitter-bandwidth selection.
- Quantile gradient boosting on residuals, using point prediction, day-of-year and station identity; seven quantiles are monotonically rearranged into a CDF.

The selected candidate is compared with an honestly calibrated probabilistic persistence baseline and day-of-year climatology. Continuous forecasts are scored with CRPS; market-like categorical scores use fixed two-degree-Fahrenheit bins with tails.

## Protected gates

The single frozen candidate must beat the stronger baseline by at least 5% CRPS and 2% categorical log loss; paired CRPS reduction must have a positive date-cluster-bootstrap 95% lower bound; 80%/90% interval coverages must fall in [75%,85%] and [86%,94%]; and at least two of three protected stations must have positive CRPS improvement.

Passing means the weather probability model is eligible for a later market-incremental test. It is not evidence of executable EV or profitability.

## Protected data-quality result

KBOS, KPHX, and KDEN each supplied 730/730 non-null SOD labels. Prior-day cutoff-window coverage was 98.356%, 98.356%, and 98.493%, respectively. Station identity errors, duplicate SOD dates, and out-of-range temperatures were all zero, so the frozen corrective transform was not needed.

No protected probability score was computed. The next permitted operation is development-only candidate selection using KORD, KJFK, KLAX, KDFW, KMIA, and KSEA.

## Development-only candidate selection

Across 2,127 leave-one-development-station-out predictions, Student-t residuals with five degrees of freedom ranked first: 2.982°F CRPS, 2.405 categorical log loss, 78.04% 80% interval coverage, and 88.43% 90% interval coverage. Gaussian CRPS was 3.003°F; the best empirical model was 2.994°F; the best quantile GBT was 2.995°F but had materially worse categorical log loss.

The selected Student-t model artifact is frozen at SHA-256 `7dad352b…a6e8`. Candidate tuning is closed. Development station-level coverage was heterogeneous, so pooled development calibration is not accepted as spatial generalization evidence; the original protected gates remain unchanged.

## Protected probability result

The single-use run scored 1,060 station-days. Student-t CRPS was 3.773°F versus the stronger baseline's 4.378°F, a 13.83% improvement. Categorical log loss improved 9.06%; all three stations had positive CRPS skill; and paired CRPS reduction was 0.606°F with date-cluster-bootstrap 95% interval [0.401, 0.815]. These discrimination/sharpness gates passed.

Calibration failed. The nominal 80% and 90% intervals covered only 69.62% and 81.32%, below the preregistered 75% and 86% minimums. KBOS and KDEN were strongly under-dispersed, while KPHX was over-dispersed. The PIT histogram had excess outer-decile mass and ECE 0.114.

Decision: `PROTECTED_PROBABILITY_FAIL`. KBOS, KPHX, and KDEN are now consumed and cannot be used to confirm a recalibrated model.
