# EXP-20260830 Phase 4 — NOAA NBM initial forecast-as-issued feasibility

**Status:** `CONDITIONAL_PASS` for the initial NBM/KORD spike; Phase 4 remains `IN_PROGRESS`  
**Data cut-off:** 2026-08-30T19:34:37Z  
**Scope:** NBM probabilistic text product, KORD/Chicago, 01Z cycle  
**Cost observed:** no access charge for public NOAA AWS objects; local compute/storage only

## Pre-registered question

Can an exact retained resolution station retrieve timestamped probabilistic daily MaxT guidance as
issued from both a current run and a run at least 365 days old, with immutable bytes, checksums,
run identity and explicit availability limitations?

This spike passes conditionally if actual objects—not only documentation or `HEAD` responses—are
downloaded and the station's own bulletin contains mean, standard deviation and
10/25/50/75/90-percentile MaxT/MinT fields. It does not claim continuous archive coverage from two
successful dates.

## Why KORD and what fields are required

KORD is the verified resolution station for retained Chicago markets and is the only currently
retained US station. NBM is therefore directly applicable to one of 11 retained city mappings; it
cannot be treated as the global provider for the other ten.

For a market-local daily maximum distribution, the minimum useful station product is:

- model run time and forecast hour/valid date;
- QMD mean and standard deviation (`TXNMN`, `TXNSD`);
- QMD 10th, 25th, 50th, 75th and 90th percentiles (`TXNP1/2/5/7/9`); and
- a cycle whose product actually carries those elements.

The [official NBM text-product key](https://vlab.noaa.gov/web/mdl/nbm-textcard-v4.2) defines these
markers, says maximum temperature occupies the 00Z-valid entries and documents that complete NBP
element availability depends on cycle. The [official download page](https://vlab.noaa.gov/web/mdl/nbm-download)
documents run-specific filenames and says the operational NOMADS files are available for only one
to two days; this is distinct from the longer public AWS object history measured here.

## Actual retrieval evidence

Two complete 01Z probabilistic bulletin files were downloaded from NOAA's public AWS bucket:

| Run | Version in KORD block | Bytes | HTTP Last-Modified | SHA-256 |
|---|---:|---:|---|---|
| 2026-08-30 01Z | 5.0 | 34,724,488 | 2026-08-30 02:07:01 GMT | `c109acf07d454bb71baa8ebe83253d7c7ec1dcd3392a25dbe360cf46b3118b41` |
| 2023-08-31 01Z | 4.1 | 34,806,674 | 2023-08-31 02:40:55 GMT | `b8679959fb917cde228fe08808a91d1be398e12c6748544a35f32516499c6f25` |

The dates are 1,095 days apart. Both downloads returned HTTP 200, have different checksums, contain
exactly one KORD NBP station block and contain exactly one of every required temperature marker
inside that block. Checksums were recomputed from the immutable local bytes during the stricter
station-block analysis.

Observed full-file retrieval time was 22.71 seconds for the current 34.72 MB object and 27.18
seconds for the historical 34.81 MB object on this connection. Downloading full national bulletins
for every hourly run would be wasteful; cycle restriction and extraction/storage design remain to
be measured.

## Cycle trap and invalidated interpretation

The first probe compared 00Z products. The 2026 NBM v5.0 KORD block contained the temperature
markers, while the 2023 NBM v4.1 KORD block contained only wind/pressure percentile fields. A naive
interpretation would have called historical MaxT unavailable.

That interpretation is invalidated. The documented full-element cycles differ, and the matched
01Z comparison shows all required KORD temperature markers in both 2023 and 2026. Cycle must
therefore be part of the dataset key and availability contract; `date + provider` is insufficient.

## Timestamp and version semantics

- `model_run_time_utc` is parsed from the immutable filename/header: 01Z on each run date.
- HTTP `Last-Modified` is preserved as object-store evidence. It was 67 minutes after run time for
  the 2026 object and 100 minutes after run time for the 2023 object.
- Historical `Last-Modified` is not assumed to be the first public availability time, and this
  retrospective retrieval cannot measure historical `first_seen_at`.
- Local request/receipt timestamps are separately preserved; they describe this ingestion, not
  original publication.
- The KORD blocks directly expose a material regime boundary: NBM v4.1 versus v5.0. The
  [official version history](https://vlab.noaa.gov/web/mdl/nbm-versions) records v4.2 on
  2024-05-15, v4.3 in 2025 and v5.0 on 2026-05-05, including a temperature update on 2026-07-28.

## Decision

The initial NBM/KORD source spike is `CONDITIONAL_PASS`:

- actual as-issued files 1,095 days apart are retrievable;
- the exact resolution station is present;
- the required probabilistic MaxT markers exist in matched 01Z station blocks; and
- provenance, version and checksum evidence is reproducible.

It is not yet a source-level `PASS`. Two endpoints do not prove daily continuity, missing-run rate,
earliest retention, value-parser correctness or the actual historical first-availability timestamp.
NBM also covers only Chicago among the current retained cities.

## Next smallest experiment

Probe a deterministic monthly-plus-boundary date grid across the AWS archive for the 01Z NBP
object, download/re-verify samples around documented model upgrades, and implement a fixed-width
KORD bulletin parser that produces run/valid-time/mean/SD/percentile records. Report missingness,
cycle availability, version boundaries and estimated annual storage before selecting NBM as the
Chicago baseline.
