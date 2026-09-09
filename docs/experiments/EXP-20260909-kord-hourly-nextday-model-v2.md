# EXP-20260909-kord-hourly-nextday-model-v2

## Status

`PREREGISTERED` — corrective V2 has not been fit or scored.

V1 is technically invalid because dataset coverage counted the whole input day while features stop at 18:00 LST. Days with no pre-cutoff observations caused out-of-distribution `hour_count=0` and predictions near 74°C. Test was not consumed.

V2 excludes, without consulting outcomes, every date with fewer than 18 distinct prior-day temperature hours through 18:00 LST. Eleven dates become `NO_PREDICT`; chronological train/validation/test counts are 365/176/178. Features, candidate models, train-only CV, validation thresholds, and test policy remain identical to V1.
