# NOAA WRH snapshot adapter contract result

**Run:** `EXP-20260902-phase5-noaa-wrh-snapshot-adapter`  
**Decision:** `SNAPSHOT_ADAPTER_CONTRACT_PASS`  
**Data:** Synthetic weather rows; event 946566 locked public metadata  
**Live outcome used:** No

## Result

The capture preparation layer passed its preregistered gate. The new adapter accepts a sanitized rendered NOAA table, validates it against the locked event/source contract, selects the minimum following-date local timestamp, and produces deterministic content-addressed manifests.

The focused suite passed 13/13 cases. The repository suite increased from 81 to 94 passing tests. Scoped Ruff returned zero errors.

## Fail-closed coverage

The tests reject pre-midnight capture, wrong station, Celsius/schema drift, wrong source URL, fewer than 20 target rows, no following-date row, duplicate timestamps, non-numeric temperature and source-artifact checksum tampering.

Storage tests establish that:

- the same payload/manifest is an idempotent replay;
- changed content creates a separate revision;
- payload tampering is detected;
- writing payload bytes that do not match the manifest is rejected;
- the same inputs produce the same manifest identity.

The valid synthetic fixture selected Sep 4 `00:51` as the minimum following-date row even though rows were supplied out of order. Chicago midnight was correctly converted to `2026-09-04T05:00:00Z` under the locked `America/Chicago` timezone.

## Interpretation

This removes manual transformation from the upcoming capture and protects provenance. It does not demonstrate that the browser will be available inside the real window, that the first row will arrive before the hard stop, or that the captured value will match settlement.

The next evidence-producing action remains the bounded event 946566 capture on Sep 4 `05:45Z–06:30Z`. No background collector or outcome lookup should occur before that run.
