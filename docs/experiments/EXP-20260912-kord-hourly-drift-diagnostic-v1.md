# EXP-20260912-kord-hourly-drift-diagnostic-v1

## Status

`PREREGISTERED` — residual diagnostic has not run.

Reproduce the locked Ridge alpha-100 model without changing features, training rows, or parameters. Measure validation/test residuals by calendar month, 30-day rolling test bias, prediction/target means, and standardized train-to-test feature mean shifts. Classify persistent drift only if at least three test months have bias at or below -1°C. This is post-failure diagnosis on a consumed test, never new validation evidence.
