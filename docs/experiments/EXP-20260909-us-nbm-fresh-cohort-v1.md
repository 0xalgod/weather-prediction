# EXP-20260909-us-nbm-fresh-cohort-v1

## Status

`PREREGISTERED` — fresh cohort selection has not been run.

## Hypothesis and exclusions

Ten dates disjoint from every prior pilot/model date and the three 13Z probe dates can produce exactly 110 balanced US events at bounded acquisition cost. The machine-readable config freezes the deduplicated union of 22 excluded dates before selection.

Within January 1 through August 15, 2026, retain remaining dates with exactly one event for every locked city. Sort ascending and choose ten evenly spaced indices `round(i*(n-1)/9)`. Selection uses identity metadata only; buckets, winners, prices, forecast values, and scores are forbidden.

## Gates and cost

Require ten dates, 110 events, 11 cities, ten events per city, zero overlap with excluded dates, and zero duplicate city-date. Planned acquisition is 1,210-ish bucket requests measured exactly after freezing IDs and 20 full NBM objects—07Z and 13Z for ten dates. Conservative NBM transfer must remain within 750 MiB.

Passing freezes a fresh research cohort but is not automatically a confirmatory test. Price/NBM collection and temporal model evaluation require separate preregistered gates.

Pre-run clarification: conservative transfer uses the larger per-object byte count observed across the checksum-tracked 07Z and 13Z probe results, multiplied by 20. Selection and thresholds are unchanged.
