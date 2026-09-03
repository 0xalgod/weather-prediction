# Chicago paper cohort — Day 1

**Scheduled time:** 2026-09-03 11:00 UTC ±15 minutes  
**Actual completion:** 10:57:52 UTC  
**Target:** Chicago/KORD, 2026-09-04, event `952456`  
**Status:** `CAPTURE_ELIGIBLE_PENDING_OUTCOME`  
**Real order:** none

## Data-quality result

The corrected immutable attempt passed every mechanics check. It used NOAA NBM 07Z after the 09Z and 08Z objects were unavailable. All 11 market identities and probabilities reconciled, all 11 YES books supported an independent `$10` ask-depth VWAP, 10 books were two-sided, fees reconciled 11/11 and no request failed. Forecast retrieval to final book receipt skew was 0.944 seconds.

The two models differed materially: total variation `0.2672`.

## Paper decisions

Both models' best threshold-comparison bucket was `86-87°F`, with executable VWAP `0.11`. A hypothetical `$10` purchase corresponds to 90.909 shares and a documented taker fee of `$0.445`.

- Gaussian probability: 16.30%. Adjusted edge after fee and 2pp haircut: **+2.81pp**, below the locked +3pp threshold → `NO_TRADE`.
- Quantile probability: 26.25%. Adjusted edge: **+12.76pp** → `PAPER_TRADE`.

No order was sent. The paper record is now frozen; outcome and P&L remain null until eligible settlement evidence is appended. One observation cannot support an edge claim, and the NBM valid-time-to-local-day semantic mapping remains a tracked validation dependency.
