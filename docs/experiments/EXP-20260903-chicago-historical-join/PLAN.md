# EXP-20260903 — Chicago historical forecast/outcome join

**Status:** `IN_PROGRESS`
**Pre-registration:** 2026-09-03, before retrieval/parsing of experiment-specific NBM forecast values

## Hypothesis

At least 29 of the exact 30 locked Chicago events can be joined to a KORD NBM probabilistic forecast that was published by the fixed prior-day 11:00 UTC decision time, while all 30 have one unambiguous resolved winner and a valid exhaustive Fahrenheit bucket partition.

## Locked identities and timing

- Events are exactly the 30 identities in the checksum-locked historical price experiment selection; no event/date replacement is allowed.
- Target local date is parsed from the event title and cross-checked against `endDate`.
- Decision time is target local date minus one calendar day at 11:00 UTC, matching the prospective cohort schedule.
- Forecast run is fixed to NBM 07Z on the prior calendar date, with no fallback in this experiment.
- Target forecast record is the single MaxT record valid at 00:00 UTC on the day after the target local date, matching the currently implemented prospective mapping.
- HTTP `Last-Modified` is retained as a retrospective publication proxy and must be no later than decision time. It is not treated as independently observed first-seen time.

## Outcome and bucket contract

- Frozen Gamma metadata is the outcome source.
- Exactly one market must have final `[Yes, No]` prices `[1, 0]`; every other bucket must be `[0, 1]`.
- All bucket labels must parse as whole-degree Fahrenheit and form one exhaustive, gap-free partition.
- Any ambiguous winner, unresolved price, identity mismatch or partition defect makes that event ineligible; it is never imputed.

## Pre-registered gates

- event identity match = 30/30;
- NBM 07Z object coverage ≥29/30;
- parse success = 100% of retrieved objects;
- publication-proxy leakage count = 0;
- exact target MaxT record = 100% of parsed objects;
- exact winner and valid bucket partition = 30/30;
- final joined event rate ≥29/30.

Decision is `HISTORICAL_JOIN_PASS`, `HISTORICAL_JOIN_FAIL` or `INCOMPLETE`.

## Interpretation boundary

Passing creates a leakage-controlled baseline dataset, not a trained model and not an executable P&L backtest. The NBM valid-time/local-day mapping remains provisional until independently reconciled against product semantics. Historical CLOB prices remain indicative and sparse.

## Execution log

### 2026-09-03/04 — Attempt 1 failed the locked coverage gate due to transport

- Exact event identities, winners and bucket partitions passed 30/30. Twenty-three NBM objects downloaded, parsed and matched the exact target record; publication-proxy leakage was zero.
- Seven downloads ended in five read timeouts and two connection resets. Raw partial files remain in the immutable attempt and are not accepted as source objects.
- Observed join rate was 23/30 (76.67%), below the locked 29/30 gate; raw runner decision remains `HISTORICAL_JOIN_FAIL`.
- Corrective experiment does not change identities, forecast cycle/mapping, values, outcomes, thresholds or gates. It checksum-verifies/reuses the 23 complete objects and retries only the seven transport failures in a new run, using two workers and a 300-second per-request timeout.
