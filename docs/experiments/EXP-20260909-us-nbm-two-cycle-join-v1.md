# EXP-20260909-us-nbm-two-cycle-join-v1

## Status

`PASSED` — all join gates passed.

## Hypothesis and gates

Every one of the 88 price-usable events joins exactly one terminal winning bucket, a normalized 18-hour market vector, and publication-admissible 07Z f41 and 13Z f35 features for its resolution station. Require 88 rows, 8 dates, 11 cities, exactly 8 rows per city, and zero join error, duplicate, missing outcome, missing cycle feature, or probability normalization error above 1e-9.

Passing freezes model-ready data only. Model form, chronological split, metrics, and acceptance thresholds must be registered before fitting or scoring.

## Result

The join produced 88/88 rows across 8 dates and 11 cities, exactly 8 per city. Join errors, duplicates, missing outcomes, and missing cycle features are zero. Maximum normalized-market sum error is 6.67e-16. Dataset checksum: `b5850b0e86a5a08998dc9e309764edd386719765b0abe59c0802a4ce4b44e49b`.
