# KORD prospective trigger capture — pre-registration

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Prospective run:** `EXP-20260904-phase5-kord-prospective-capture`  
**Pre-registered:** 2026-09-02 14:08:40 UTC  
**Status:** `PREREGISTERED`

## Locked hypothesis

A bounded browser session at the market rule's trigger can preserve an immutable NOAA WRH KORD snapshot containing the Sep 3 target-day rows and the first Sep 4 local observation before event 946566's outcome is used.

This tests collection and provenance, not trading profitability.

## Event selection

Event `946566`, **Highest temperature in Chicago on September 3?**, is locked. It was the earliest `end_at` among the two observed-future, identity-complete Chicago records using NOAA WRH KORD as the primary source in the checksum-locked discovery artifact. Selection occurred while the target date was still in the future.

- Event end: `2026-09-03T12:00:00Z`
- Rule SHA-256: `15ce309df35d3bb6f1f3eb7988adb87b3ff8d1fb831b775a3642f4cba75158ec`
- Identity inventory: 11 markets, 11 condition IDs, 22 token IDs
- Source artifact SHA-256: `e003e77b7f0083e4f3d1322512f8731de1f49fc4463f843c2079348cd82c7da0`

The complete market/condition/token identities remain locked by the source checksum and JSON pointer `/chicago_audits/1/token_identities`; they must match before capture is admitted.

## Trigger and bounded execution

The target local date is Sep 3 and following local date is Sep 4 in `America/Chicago`. The trigger row is defined before observation as the minimum rendered KORD timestamp belonging to Sep 4—not as a hard-coded `00:51` row.

The session must not start before Sep 4 00:00 Chicago / `05:00 UTC`. Preferred start is `05:45 UTC`; hard stop is `06:30 UTC`. At most 10 page renders are allowed, at least 240 seconds apart, within a maximum 45-minute foreground session. There is no 24-hour collector, background process or automatic schedule.

## Pre-registered acceptance gate

A capture passes only when all conditions hold:

- exact KORD/O'Hare identity and Fahrenheit header;
- capture at or after following-date local midnight;
- at least 20 timestamped numeric target-date rows and at least one following-date row;
- zero duplicate timestamps;
- first following row selected by minimum timestamp;
- locked rule and identity-source checksum match;
- rendered table payload and canonical manifest checksums are present;
- append-only replay verification passes.

Missing the window, failing to observe a following-date row, identity/unit/schema mismatch, insufficient target coverage, duplicate timestamps, lock mismatch, browser failure or append-only verification failure is a fail-closed result. No threshold will be changed after seeing the data.

## Interpretation boundary

A successful capture becomes `PROSPECTIVE_TRIGGER_CAPTURE_PASS_PENDING_SETTLEMENT`; it is not yet a label. After Polymarket terminal settlement, the captured maximum/bucket and terminal winner must be reconciled. One match is pipeline evidence, not statistical edge evidence. A divergence quarantines the event and rejects the label pipeline pending root-cause analysis.

No order, wallet, credential, cookie/local-storage capture, network-token inspection or outcome lookup is permitted during the capture.

Machine-readable locked configuration: `configs/EXP-20260904-kord-prospective-capture.json`.
