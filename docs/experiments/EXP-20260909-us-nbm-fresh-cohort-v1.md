# EXP-20260909-us-nbm-fresh-cohort-v1

## Status

`PASSED` — the disjoint balanced cohort and acquisition volumes are frozen.

## Hypothesis and exclusions

Ten dates disjoint from every prior pilot/model date and the three 13Z probe dates can produce exactly 110 balanced US events at bounded acquisition cost. The machine-readable config freezes the deduplicated union of 22 excluded dates before selection.

Within January 1 through August 15, 2026, retain remaining dates with exactly one event for every locked city. Sort ascending and choose ten evenly spaced indices `round(i*(n-1)/9)`. Selection uses identity metadata only; buckets, winners, prices, forecast values, and scores are forbidden.

## Gates and cost

Require ten dates, 110 events, 11 cities, ten events per city, zero overlap with excluded dates, and zero duplicate city-date. Planned acquisition is 1,210-ish bucket requests measured exactly after freezing IDs and 20 full NBM objects—07Z and 13Z for ten dates. Conservative NBM transfer must remain within 750 MiB.

Pre-run clarification: the conservative object-size estimate uses the maximum byte count across the checksum-tracked 07Z and 13Z three-date probe results. No cohort or threshold changed.

Passing freezes a fresh research cohort but is not automatically a confirmatory test. Price/NBM collection and temporal model evaluation require separate preregistered gates.

Pre-run clarification: conservative transfer uses the larger per-object byte count observed across the checksum-tracked 07Z and 13Z probe results, multiplied by 20. Selection and thresholds are unchanged.

## Result

Selection passed every preregistered gate: 10 dates, 110 events, 11 cities, and exactly 10 events per city. Excluded-date overlap and duplicate city-date counts are both zero. The selected dates are 2026-03-25, 2026-04-10, 2026-04-27, 2026-05-12, 2026-05-29, 2026-06-13, 2026-06-29, 2026-07-15, 2026-07-30, and 2026-08-14.

The frozen cohort contains 1,210 market token requests. Twenty planned NBM objects have a conservative estimated transfer of 696,133,480 bytes, below the 786,432,000-byte cap. The tracked selection report records input and output checksums.

Known serialization issue: the frozen config text contains the identical `source_07z_probe_result` key twice. Because both values are identical, selection semantics are unchanged. The file remains untouched so its preregistered checksum stays reproducible.

Next, collect only the frozen cohort's 18-hour market histories under a separately preregistered coverage gate. No forecast values or outcomes are used in that gate.
