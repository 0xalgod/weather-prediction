# EXP-20260909-us-nbm-13z-incremental-model-v1

## Status

`FAILED` — validation rejected the incremental-market hypothesis.

## Design

Use the first five dates (55 events) for development and the final three dates (33 events) once for validation. Independently calibrate 07Z and 13Z quantiles using a small common shift/spread grid. Select the fixed 13Z-versus-market blend weight on development only. Validation is never used for tuning.

All gates must pass: calibrated 13Z improves log loss by at least 2% versus calibrated 07Z; the selected challenger improves at least 2% versus market; challenger Brier does not worsen; probability vectors remain valid; and all three validation date clusters are present. Failure closes this branch without post-hoc tuning. Passing only authorizes a new disjoint confirmation cohort because three validation dates are statistically weak and historical prices are not executable fills.

## Result

Development selected shift/spread -2°F/1.25× for 07Z and -2°F/1.5× for 13Z. It selected blend weight 0.0 because every positive NBM weight worsened development log loss versus market.

On 33 validation events, 13Z log loss 2.0404 materially beats 07Z 2.6563 by 23.19%, so forecast freshness helps. Market log loss is nevertheless far better at 1.3399. The selected challenger is market-only and therefore improves market by 0%, below the required 2%. The branch is rejected; validation will not be tuned.
