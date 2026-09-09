# EXP-20260908-us-nbm-failure-diagnostic-v1

## Status

`FAILED` — diagnostic returned `NBM_BRANCH_NO_GO`; test remains untouched.

## Question and data boundary

Does the rejected NBM blend have a stable, actionable city-bias mechanism, or is its underperformance diffuse? Use only the 99 development and 44 validation events. The final four test dates remain unread and unscored. Reuse the locked -1°F/1.5× calibration; fit no new parameter.

The exact development and validation date lists are copied unchanged from the parent experiment config into the machine-readable diagnostic config before calculation; no dynamic split inference is allowed.

## Diagnostics

For each city and split, measure the signed distance from calibrated NBM median to the winning bucket interval, winner-interval containment, raw/calibrated NBM losses, forecast spread, and challenger-minus-market loss. Also report loss by 16/17/18-hour proxy overlap.

A city has stable material bias only when development and validation mean signed distances share a nonzero direction and development absolute mean is at least 1°F. Loss concentration is the three largest positive city validation excess-loss totals divided by total positive city excess-loss.

## Go/no-go rule

All cities must have at least nine development and four validation events. A city-offset model is permitted only if at least six of 11 cities show stable material bias and top-three positive excess-loss concentration is at least 50%. Both conditions are required. Otherwise stop this NBM modeling branch and keep test untouched.

This is an exploratory mechanism diagnostic with disclosed multiple city slices, not confirmatory evidence, EV, or permission to trade.

## Result

Zero of 11 cities met the stable material-bias rule, versus the required six. The top three positive excess-loss cities—Los Angeles, Dallas, and San Francisco—accounted for 42.26% of positive validation excess loss, below the 50% threshold. All per-city sample-count checks passed.

Bias was unstable rather than consistently city-specific; Los Angeles, for example, changed from a positive development median residual to a large negative validation residual. The 16/17/18-hour overlap slices showed no clean monotonic failure pattern. A city-offset model is not justified, and the final test remains untouched.
