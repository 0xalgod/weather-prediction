# Chicago vertical slice — live attempt 1

**Decision:** `VERTICAL_SLICE_INCOMPLETE`  
**Reason:** fee parameter reconciliation failed safely  
**Orders/outcome lookup:** none

The first real NBM-to-Chicago-book join ran successfully through forecast, identity, probability and executable-depth stages. NOAA's 07Z NBM run supplied one KORD record with mean 90°F and standard deviation 4°F. All 11 buckets parsed, probabilities summed to exactly 1, all 11 YES books supported an independent `$10` ask-depth VWAP, no request failed, and forecast-to-last-book retrieval skew was 0.913 seconds.

The run did not pass. The runner treated legacy `/fee-rate` `base_fee=1000 bps` as if it should equal Gamma's weather curve `rate=0.05`. They are different V2 fields. The official condition-level CLOB response reports `tbf=1000` and `fd={r:0.05,e:1,to:true}`; `fd.r` matches Gamma in all 11 markets. Because the preregistered fee reconciliation check failed, attempt 1 emitted no net EV. This is the desired fail-closed behavior.

Gross edge ranged from approximately +8.72 percentage points for `86-87°F` to −38.38 points for `94-95°F`. These values are explicitly non-actionable: one uncalibrated Gaussian forecast, one timestamp and unresolved fee treatment cannot support a trade or edge claim.

The corrective run will use the official `/clob-markets/{condition_id}` `fd` object, require `e=1`, `to=true`, and exact agreement with Gamma's schedule. All other cohort, probability, `$10` VWAP, temporal-skew and coverage thresholds remain unchanged.
