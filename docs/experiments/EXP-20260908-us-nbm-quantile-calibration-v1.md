# EXP-20260908-us-nbm-quantile-calibration-v1

## Status

`FAILED` — validation rejected the challenger; test remains untouched.

## Hypothesis and split

A single city-agnostic NBM quantile shift/spread calibration, blended 50/50 with the indicative 18-hour market vector, improves validation log loss by at least 2% without worsening Brier score.

Use only the 187 `PRICE_ELIGIBLE` rows. The first nine date clusters are development (99 events), the next four validation (44), and the final four untouched test (44). No random split or city-specific parameters are permitted.

## Models and training

Benchmarks are uniform, market, and raw NBM quantile distributions. Fit the calibrated distribution on development only over 78 locked combinations: shift -6°F through +6°F by 1°F, and spread scales 0.5, 0.75, 1, 1.25, 1.5, 2. Select minimum development log loss with deterministic simplicity tie-break. The challenger is fixed 50% market plus 50% calibrated NBM.

Use native bucket boundaries with 1°F continuity precision, a quantile-preserving piecewise-linear CDF, 1°F minimum tail width, and probability floor `1e-6`.

## Gates and test policy

Validation must have four date clusters, at least 2% challenger log-loss improvement over market, non-positive challenger-minus-market Brier, and zero invalid vectors. If it fails, do not score test. If it passes, consume test once with the locked model and require the same point-metric gates. Report a 10,000-repetition paired target-date cluster bootstrap using seed 20260908; with only four test clusters, its interval is diagnostic rather than a pass requirement.

## Boundary

Prices are indicative rather than fills, price eligibility came from a disclosed post-hoc corrective, and NBM f41 is a proxy rather than the resolution label. Passing would establish only a research signal, not executable EV or trading authorization.

## Result

Development selected a common -1°F shift and 1.5× spread. This reduced development raw-NBM log loss from 1.9764 to 1.5036, but the market remained better at 1.2600; the fixed blend scored 1.2753.

On validation, market/calibrated-NBM/blend log loss was 1.5341/2.1663/1.6224. The blend was 5.76% worse than market and worsened Brier by 0.00569. Paired date-cluster bootstrap blend-minus-market log loss was +0.0883 with CI95 [+0.0631, +0.1153]. Both economic point gates failed, with zero invalid vectors.

Per policy, the final 44-event test set was not scored. The model is rejected. Before increasing model capacity, diagnostics must determine whether failure is associated with city bias, proxy-window mismatch, forecast distribution shape, or broad lack of incremental information.
