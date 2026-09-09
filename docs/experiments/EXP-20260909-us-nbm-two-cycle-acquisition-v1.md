# EXP-20260909-us-nbm-two-cycle-acquisition-v1

## Status

`PASSED` — all preregistered acquisition gates passed.

## Hypothesis and frozen cohort

Prior-day 07Z f41 and the six-hour-fresher 13Z f35 NBM probabilistic MaxT products are both published before the prior-day 18:00Z market cutoff and feature-complete on the eight dates where all 11 cities passed the market-price gate: March 25, April 27, May 12, May 29, June 13, June 29, July 15, and August 14, 2026.

Extract 12 station regimes because Denver events can resolve against either KBKF or KDEN. Required fields are mean, standard deviation, and P10/P25/P50/P75/P90 in Fahrenheit. A complete byte-identical duplicate station block may be canonicalized; a conflicting duplicate fails.

## Gates

Require exactly 8 dates, 2 cycles, 12 stations, and 16 full objects; 192/192 station-cycle-date feature rows; zero retrieval failure, station error, late publication, or conflicting duplicate; and total transfer no more than 600 MiB.

A pass only freezes model inputs. Forecast accuracy and incremental value against the market require a later temporal evaluation preregistration. A failure forbids fitting this branch.

## Result

All 16 objects were retrieved and all 192 station-cycle-date rows contain the required features. Retrieval failures, station errors, late publications, and conflicting duplicates are zero. Transfer was 555,793,550 bytes, below the 600 MiB cap. The two-cycle inputs are now frozen for temporal scoring.
