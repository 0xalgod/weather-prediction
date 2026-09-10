# EXP-20260909-kord-hourly-nextday-model-v2

## Status

`FAILED` — validation passed, but the one-time test failed the bias gate.

V1 is technically invalid because dataset coverage counted the whole input day while features stop at 18:00 LST. Days with no pre-cutoff observations caused out-of-distribution `hour_count=0` and predictions near 74°C. Test was not consumed.

V2 excludes, without consulting outcomes, every date with fewer than 18 distinct prior-day temperature hours through 18:00 LST. Eleven dates become `NO_PREDICT`; chronological train/validation/test counts are 365/176/178. Features, candidate models, train-only CV, validation thresholds, and test policy remain identical to V1.

## Result

Five expanding train-only folds selected Ridge with alpha 100. On 176 validation days, MAE was 2.798°C versus persistence 3.317°C and harmonic climatology 4.967°C; improvements were 15.64% and 43.66%, and bias was +0.483°C. Every validation gate passed, so the protected test was consumed once.

On 178 test days, model MAE was 3.921°C versus persistence 4.329°C and climatology 5.186°C—improvements of 9.43% and 24.39%. Test bias was -2.169°C, exceeding the locked absolute 1°C ceiling. The final decision is `TEST_REJECT`: useful incremental MAE skill exists, but it did not generalize with acceptable calibration. No test-period tuning is allowed.
