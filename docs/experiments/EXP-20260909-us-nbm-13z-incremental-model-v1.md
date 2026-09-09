# EXP-20260909-us-nbm-13z-incremental-model-v1

## Status

`PREREGISTERED` — no model fit or score has run.

## Design

Use the first five dates (55 events) for development and the final three dates (33 events) once for validation. Independently calibrate 07Z and 13Z quantiles using a small common shift/spread grid. Select the fixed 13Z-versus-market blend weight on development only. Validation is never used for tuning.

All gates must pass: calibrated 13Z improves log loss by at least 2% versus calibrated 07Z; the selected challenger improves at least 2% versus market; challenger Brier does not worsen; probability vectors remain valid; and all three validation date clusters are present. Failure closes this branch without post-hoc tuning. Passing only authorizes a new disjoint confirmation cohort because three validation dates are statistically weak and historical prices are not executable fills.
