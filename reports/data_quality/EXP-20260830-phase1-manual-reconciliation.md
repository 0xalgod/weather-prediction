# Phase 1 Manual Market/Resolution Reconciliation

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Evaluation date:** 2026-08-30  
**Sample:** Fixed-seed 20-event queue selected before source inspection  
**Source snapshots:** Gamma event endpoint and linked Wunderground daily history pages  
**Status:** `PASSED` for the Phase 1 pre-registered gate

## Gate

Phase 1 required at least 10 qualifying reconciled market-events across at least 3 cities, with zero critical identifier mismatches among retained records. All 20 selected records had to receive a disposition; anomalous records were not silently repaired.

## Method

For every sampled event, a fresh public Gamma event snapshot was compared with the stored sample's market ID, condition ID and ordered CLOB token IDs. Rule text was parsed for station name, station code, unit and local rule date. The linked resolution page was retrieved with the event date and its displayed finalized daily high was compared with the sole exact `Yes=1/No=0` terminal bucket.

Displayed whole-degree values were treated as rounding intervals when Celsius-to-Fahrenheit conversion was necessary. Only unambiguous containment counted as a match. Missing source, missing terminal winner, identifier mismatch or source/outcome disagreement produced an explicit non-retained disposition.

## Results

| Result | Events | Interpretation |
|---|---:|---|
| `RECONCILED` | 12 | Identifier, rule/station, terminal bucket and displayed source high agree |
| `NO_TRADE_MISSING_RESOLUTION_SOURCE` | 3 | Outcome cannot be independently tied to a declared source/station |
| `NON_TERMINAL_OR_CANCELLED` | 3 | No sole exact terminal winner; must not be treated as a settled weather label |
| `OUTCOME_SOURCE_MISMATCH_NO_TRADE` | 2 | Terminal bucket conflicts with the linked source day's displayed high |
| Fetch errors | 0 | All requested public Gamma and Wunderground pages were retrieved |

The 12 retained records span Karachi, Munich, Guangzhou, Jakarta, Panama City, Shenzhen, Kuala Lumpur, Buenos Aires, Toronto, Chicago, Mexico City and Milan. This exceeds the registered 10-event/3-city threshold. Live Gamma identity matched the stored identity for all 20 records; the two pre-identified incomplete events remained incomplete in both snapshots and were excluded rather than counted as retained.

## Event dispositions

| Event | City | Station | Terminal winner | Displayed high | Disposition |
|---:|---|---|---|---|---|
| 624485 | Hong Kong | — | 32°C | — | `NO_TRADE_MISSING_RESOLUTION_SOURCE` |
| 668435 | Moscow | — | 20°C | — | `NO_TRADE_MISSING_RESOLUTION_SOURCE` |
| 899793 | Tel Aviv | — | 33°C | — | `NO_TRADE_MISSING_RESOLUTION_SOURCE` |
| 493722 | Karachi | OPKC | 36°C | 36°C | `RECONCILED` |
| 593023 | Munich | EDDM | 22°C | 22°C | `RECONCILED` |
| 515716 | Guangzhou | ZGGG | 36°C | 36°C | `RECONCILED` |
| 493659 | Dallas | KDAL | 73°F or below | 30°C | `OUTCOME_SOURCE_MISMATCH_NO_TRADE` |
| 490270 | Jakarta | WIHH | 34°C | 34°C | `RECONCILED` |
| 493666 | Munich | EDDM | 11°C or below | 19°C | `OUTCOME_SOURCE_MISMATCH_NO_TRADE` |
| 504566 | Jinan | ZSJN | — | 25°C | `NON_TERMINAL_OR_CANCELLED` |
| 504568 | Zhengzhou | ZHCC | — | 26°C | `NON_TERMINAL_OR_CANCELLED` |
| 493696 | Cape Town | FACT | — | 24°C | `NON_TERMINAL_OR_CANCELLED` |
| 497028 | Panama City | MPMG | 31°C or higher | 33°C | `RECONCILED` |
| 515700 | Shenzhen | ZGSZ | 33°C | 33°C | `RECONCILED` |
| 614117 | Kuala Lumpur | WMKK | 33°C | 33°C | `RECONCILED` |
| 132826 | Buenos Aires | SAEZ | 31°C | 31°C | `RECONCILED` |
| 731100 | Toronto | CYYZ | 26°C | 26°C | `RECONCILED` |
| 553903 | Chicago | KORD | 68°F or higher | 27°C | `RECONCILED` |
| 589059 | Mexico City | MMMX | 26°C | 26°C | `RECONCILED` |
| 322484 | Milan | LIMC | 18°C | 18°C | `RECONCILED` |

## Decision and limitations

Phase 1 passes narrowly: public metadata can support a retained identifier/outcome registry, provided invalid records are excluded with hard `NO_TRADE` rules. The sample also falsifies the assumption that exact terminal prices always encode the observed weather result. Dallas and the May 19 Munich event show that a terminal-looking Gamma outcome can disagree materially with the linked source page.

This is a metadata/rule feasibility result, not evidence of forecast edge or tradable EV. The Wunderground HTML is a mutable presentation surface; raw retrievals and checksums are retained locally, but a durable observation source and revision policy are still required.

## Artifacts and verification

- Machine-readable result: `reports/data_quality/EXP-20260830-phase1-manual-reconciliation-v2.json`
- Local immutable raw run: `data/raw/polymarket_reconciliation/run=20260830T-reconciliation-v2`
- 18 unit/contract tests pass.

## Next action

Begin Phase 2 by defining the versioned resolution-rule/station registry schema, including hard exclusion states for missing source, non-terminal/cancelled records and source/outcome mismatches.
