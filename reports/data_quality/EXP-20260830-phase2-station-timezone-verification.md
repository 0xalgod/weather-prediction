# Phase 2 Station Identity and Timezone Verification

**Experiment:** `EXP-20260830-data-source-feasibility`  
**Date:** 2026-08-30  
**Registry schema/parser:** `0.2.0`  
**Input:** 12 structurally complete station-unverified candidates  
**Status:** Verification substep passed; Phase 2 remains `IN_PROGRESS`

## Question and gate

Can each candidate's rule/source ICAO identity and proposed IANA timezone be independently supported before the record is admitted as a final research label?

Promotion required all of the following:

1. Source URL station code exists in current public AviationWeather station metadata.
2. Rule station name and official airport identity are not materially contradictory.
3. Official station coordinates fall inside the proposed IANA timezone or its release-declared equivalent zone.
4. Metadata and boundary artifacts are checksummed and versioned.

Any failure remains or becomes hard `NO_TRADE`; syntactic `zoneinfo` validity alone is insufficient.

## Sources and provenance

- Current station metadata: [AviationWeather Data API](https://aviationweather.gov/data/api/), public `stationinfo` response for the 12 ICAO codes. Payload SHA-256: `6b3d4db698a47aa87ad729d2f3e0432017ebaa624dbcfbce98e6b4d759cf121d`.
- Station-history cross-check: [NOAA/NCEI ISD station history](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database). The historical file was retained locally; it is not substituted for current AviationWeather identity.
- Timezone geometry: [Timezone Boundary Builder 2026c](https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2026c), `timezones-1970.geojson.zip`, SHA-256 `c1bd0839c15a94ace5107e84694915fca3ab74907dee7b2ed4e3e5e01acc8f16` (matches the published release digest).
- Merged-name mapping: `timezone-names-1970.json`, SHA-256 `1335ffb54ef1262713b7b7067f44902bab4f07232082fabace73f695d6147a28` (matches the published release digest).
- Timezone rule version: IANA/tzdb `2026c`.

## Results

| Measure | Result |
|---|---:|
| Candidate ICAO codes returned by AviationWeather | 12/12 |
| Coordinate-to-timezone matches after release-declared equivalence | 12/12 |
| Rule-name/source-code identity matches | 11/12 |
| Promoted final `RECONCILED` records | 11 |
| Newly rejected ambiguous station rule | 1 |
| Final registry hard `NO_TRADE` records | 9/20 |
| Final reconciled bucket rows | 117 |

Kuala Lumpur's proposed `Asia/Kuala_Lumpur` mapped geometrically to the boundary feature `Asia/Singapore`. Release file `timezone-names-1970.json` explicitly lists `Asia/Kuala_Lumpur` as an equivalent name under that merged feature, so this is a verified equivalence rather than a mismatch.

Karachi failed identity verification. The Polymarket rule says **Masroor Airbase Station**, while its resolution URL uses ICAO `OPKC`; current AviationWeather identifies `OPKC` as **Karachi/Jinnah Intl**. Correct timezone and a valid ICAO code do not repair this semantic rule/source contradiction. The record was changed from candidate to `NO_TRADE_AMBIGUOUS_RULE` with reason `RULE_STATION_NAME_SOURCE_CODE_MISMATCH`.

## Decision

Eleven records are promoted to final `RECONCILED` under registry schema `0.2.0`; the other nine remain hard exclusions. Phase 2 has enough exact station/timezone mappings to exceed its ≥3-city minimum, but the phase is not closed yet: city-family rule/station changes and DST/date-boundary behavior still require explicit tests.

## Artifacts

- `reports/data_quality/EXP-20260830-phase2-resolution-registry-verified.jsonl`
- `reports/data_quality/EXP-20260830-phase2-station-timezone-evidence.json`
- `configs/station_identity_review.json`
- `scripts/verify_station_registry.py`
- Local external evidence under `data/external/` is excluded from Git; checksums are embedded in committed artifacts.

## Next action

Measure station/rule changes within repeated city families and add DST/local-date boundary tests before evaluating the Phase 2 exit gate.
