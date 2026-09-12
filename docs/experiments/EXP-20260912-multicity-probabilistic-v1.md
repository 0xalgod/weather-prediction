# EXP-20260912-multicity-probabilistic-v1

## Status

`IN_PROGRESS` — protected station data quality passed; protected probability outcomes remain unscored while development-only candidate selection is pending.

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
