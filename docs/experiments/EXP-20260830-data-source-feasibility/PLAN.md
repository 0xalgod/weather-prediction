# EXP-20260830-data-source-feasibility — Point-in-time market and weather data feasibility

**Status:** `IN_PROGRESS`
**Owner:** Abdullah Sezdi
**Created:** 2026-08-30
**Last updated:** 2026-08-31
**Project phase:** Phase 0/G0 feasibility, enabling Phase 1
**Related hypotheses:** H1, H2, H3, H5, H6
**Related experiments:** None
**Data cut-off:** 2026-08-30 documentation and reconciliation retrieval; closed inventory through 2026-08-29
**Decision commit:** This registration commit; resolve with `git log -- PLAN.md`

## 1. Executive summary

This experiment determines whether the project can build a point-in-time-correct research dataset for Polymarket daily maximum-temperature bucket markets before investing in forecasting models or trading logic.

The required joined record is:

```text
market and outcome metadata
+ exact resolution rules and reference station
+ executable order-book state
+ historical forecast as it was issued
+ station observation and final settlement
+ availability and ingestion timestamps
```

The experiment does **not** test trading profitability. It tests whether the evidence needed to test profitability can be acquired, normalized, versioned, and reproduced for at least three cities.

The primary output is a `PASS`, `CONDITIONAL_PASS`, `FAIL`, or `INCONCLUSIVE` feasibility decision. A pass authorizes implementation of the long-running collectors and baseline dataset. It does not authorize live trading.

## 2. Primary hypothesis

> For at least three Polymarket daily maximum-temperature market cities, market metadata, resolution rules, executable order-book snapshots, historical forecasts-as-issued, station observations, and final settlements can be joined with explicit point-in-time semantics at sufficient coverage and legal/operational accessibility to support a future walk-forward backtest.

## 3. Motivation and economic mechanism

### Research motivation

A forecast model can appear profitable because of data leakage, midpoint pricing, revised forecasts, wrong-station observations, or optimistic fill assumptions. Before model development, this experiment must prove that those failure modes can be controlled with available data.

### Expected source of future edge

This experiment does not estimate edge. It enables later tests of:

- station-specific forecast bias,
- probabilistic ensemble calibration,
- market repricing latency after forecast runs,
- bucket probability incoherence,
- maker-versus-taker execution economics.

### Why this feasibility may fail

- Historical L2 order books may not be available.
- Historical forecasts may be revised, missing, or retained only briefly.
- Resolution sources may not expose stable station identifiers.
- Market rules may change across dates without a machine-readable version history.
- Observation sources may not match the exact settlement source.
- Polymarket price history may represent prices rather than executable depth.
- Licences, geographic restrictions, or data costs may make a source unsuitable.

### Expected economic consequence

If executable prices and forecasts-as-issued cannot be reconstructed, retrospective P&L cannot be trusted. The correct response is prospective data collection, a narrower city scope, or project suspension—not a more complex model.

### Capacity constraints

Capacity is out of scope for this experiment, but order-book depth, spread, snapshot frequency, and market frequency will be captured as feasibility indicators for later capacity analysis.

## 4. Scope

### Included

- Polymarket event/market discovery for weather and temperature markets.
- Daily maximum-temperature bucket markets.
- Active markets plus a recent settled sample where accessible.
- Market/outcome/token/condition mappings.
- Resolution text, source, station, timezone, units, local observation window, and bucket rules.
- Public CLOB order-book REST snapshots.
- Public market WebSocket messages for book, price, best bid/ask, last trade, lifecycle, and resolution where available.
- Historical price series only as a benchmark and coverage diagnostic.
- NBM/QMD, GFS/GEFS, HRRR, ECMWF Open Data, and official/local observations as candidate sources.
- Data retention, licences, availability timestamps, costs, and access restrictions.
- Candidate-city scoring and selection of 3–5 cities.

### Excluded

- Placing or signing orders.
- Wallet creation, funding, or live position management.
- Authenticated user trade/order streams.
- Forecast-model training or hyperparameter tuning.
- Profitability backtests.
- Rain, snowfall, hurricane, climate-record, and non-temperature contracts.
- Scraping that violates published terms or bypasses access controls.
- Using weather reanalysis as a substitute for historical forecasts-as-issued.
- Treating displayed/midpoint/last-trade prices as executable fills.

## 5. Unit of analysis and sample

### Units of analysis

1. **Market-event unit:** one city/local-date daily maximum-temperature event.
2. **Outcome unit:** one temperature bucket/token within the event.
3. **Order-book unit:** one token-level timestamped L2 snapshot or delta sequence.
4. **Forecast unit:** one provider/model/run/valid-time/grid-or-station forecast.
5. **Observation unit:** one station/observation-time/revision record.
6. **Settlement unit:** one final outcome with source and resolution timestamp.

### Discovery sample

- All active daily maximum-temperature markets returned by the verified discovery method at execution time.
- Recent settled markets sufficient to sample at least 10 market-events across at least 3 cities, if the API exposes them.
- Manual rule-validation sample: minimum 20 market-events or all available if fewer than 20.
- Public order-book probe: every outcome token for at least 3 simultaneous active market-events.
- Collector stability window: minimum 24 continuous hours after the initial spike succeeds.

### Weather-source sample

- At least 3 candidate reference stations.
- At least 3 forecast initialization cycles per selected product during the live probe.
- Historical archive coverage is measured by earliest and latest retrievable run, not inferred from provider descriptions alone.

### Clustering unit

No inferential model is fit in this experiment. Coverage metrics will nevertheless be grouped by event/local date and city so multiple bucket tokens are not presented as independent markets.

### Exclusion rules

- Markets that are not daily maximum-temperature buckets.
- Markets whose rule text cannot be retrieved or preserved.
- Cancelled/invalid markets, recorded separately rather than silently dropped.
- Sources requiring credentials, payment, or contractual access remain candidates but cannot be classified as operationally usable without explicit approval.

### Survivorship-bias control

The discovery method must attempt to include active, closed, and resolved records. Any API filter that excludes delisted, cancelled, or inactive events must be documented. Candidate-city scores must not be calculated only from currently liquid markets.

## 6. Source inventory and preliminary documentation

This table records pre-execution source expectations. Every row is a hypothesis to verify by a read-only API or archive spike.

| Source | Intended use | Official reference | Preliminary expectation | Unknown to resolve |
|---|---|---|---|---|
| Polymarket Gamma API | Events, markets, tags, slugs, rules, outcomes, token IDs | <https://docs.polymarket.com/api-reference/markets/get-market-tags-by-id> | Public metadata endpoints exist | Reliable weather discovery filter; closed-market history; rule revision history |
| Polymarket CLOB REST `/book` | Current aggregated L2 snapshot | <https://docs.polymarket.com/api-reference/market-data/get-order-book> | Token-level bids, asks, timestamp, hash, tick size and neg-risk fields | Rate limits, timestamp units, empty-book semantics, retention |
| Polymarket market WebSocket | Prospective book/delta/lifecycle capture | <https://docs.polymarket.com/api-reference/wss/market> | Public snapshots, price changes, trades, tick changes and some lifecycle events | Reconnect recovery, sequence integrity, custom feature requirements |
| Polymarket `/prices-history` | Price benchmark and historical coverage | <https://docs.polymarket.com/api-reference/markets/get-prices-history> | Timestamped price history with fidelity control | Exact price semantic; not assumed to be L2 or executable |
| Polymarket fee schedule | Cost metadata | <https://docs.polymarket.com/trading/fees> | Weather taker fee schedule is market-dependent; query market metadata | Historical fee versioning and rebate availability |
| NOAA NBM core/QMD | US blended deterministic/probabilistic forecasts | <https://vlab.noaa.gov/web/mdl/nbm-download> | GRIB2 via NOMADS/AWS; QMD cycles available | Actual historical retention, MaxT quantiles/exceedances, publish latency |
| NOAA NOMADS | Operational model distribution | <https://nomads.ncep.noaa.gov/> | Current/near-current operational model files | Product-specific archive depth and model upgrade boundaries |
| NOAA GEFS/GFS | Global ensemble/deterministic forecast candidate | <https://www.nco.ncep.noaa.gov/pmb/products/gens/> | Operational forecast files and ensemble members | Long-term as-issued archive access, station interpolation cost |
| NOAA HRRR | Short-lead US forecast candidate | <https://rapidrefresh.noaa.gov/hrrr/> | High-frequency US guidance | Archive depth, file volume, MaxT construction |
| ECMWF Open Data | Global IFS/AIFS real-time and ensemble candidate | <https://www.ecmwf.int/en/forecasts/datasets/open-data> | Open subset, CC-BY-4.0, rolling archive | Rolling retention length, historical alternative, required parameters |
| METAR/SYNOP and official climate summaries | Station observations | Provider-specific official source | Near-real-time and final observations may differ | Exact settlement source, revisions, rounding and daily window |

### Preliminary facts that constrain the plan

- Polymarket displayed price may be midpoint or last trade; it is not a guaranteed fill price.
- CLOB `/book` exposes current aggregated bids/asks and book metadata for a token.
- Market WebSocket exposes prospective real-time book and price events.
- Price-history endpoints expose price points, not documented historical L2 depth.
- NBM operational products are available through NOMADS and AWS, but some text products have short retention.
- ECMWF Open Data is a rolling real-time archive; historical suitability must be measured separately.

None of these facts counts as a passed feasibility gate until an endpoint-level artifact is produced.

## 7. Data contract and provenance

### Required logical tables

| Table | Grain | Required identifiers | Critical timestamps |
|---|---|---|---|
| `events` | One city/date event | `event_id`, `slug` | `created_at`, `start_at`, `end_at`, `ingested_at` |
| `markets` | One market/condition | `market_id`, `condition_id`, `event_id` | `created_at`, `closed_at`, `ingested_at` |
| `outcomes` | One outcome token/bucket | `token_id`, `market_id`, `outcome_label` | `active_from`, `active_to`, `ingested_at` |
| `resolution_rules` | One versioned rule | `market_id`, `rule_hash`, `source_station_id` | `effective_from`, `effective_to`, `ingested_at` |
| `orderbook_snapshots` | One token snapshot | `token_id`, `book_hash` | `exchange_timestamp`, `received_at`, `persisted_at` |
| `orderbook_levels` | One side/price level | `book_hash`, `side`, `price` | inherited snapshot timestamps |
| `price_history` | One token price point | `token_id`, `timestamp` | `source_timestamp`, `ingested_at` |
| `forecast_runs` | One provider run | `provider`, `model`, `run_time` | `model_run_time`, `published_at`, `first_seen_at`, `ingested_at` |
| `forecast_values` | One run/valid/location/member-or-quantile | forecast composite key | `valid_time`, run availability timestamps |
| `station_observations` | One station observation revision | `station_id`, `observed_at`, `revision` | `observed_at`, `published_at`, `ingested_at` |
| `settlements` | One market resolution | `market_id`, `winning_token_id` | `proposed_at`, `resolved_at`, `ingested_at` |
| `data_quality_flags` | One entity/check result | `entity_type`, `entity_id`, `check_id` | `checked_at` |

### Immutable raw envelope

Every raw payload must be stored with an envelope containing:

```json
{
  "schema_version": "0.1.0",
  "source": "source-name",
  "endpoint": "canonical-endpoint-without-secret",
  "request_parameters": {},
  "source_timestamp": null,
  "requested_at_utc": "...",
  "received_at_utc": "...",
  "http_status": 200,
  "content_sha256": "...",
  "payload": {}
}
```

Secrets, authorization headers, cookies, wallet details, and personal identifiers must never be stored.

### Timestamp requirements

- All persisted machine timestamps use UTC ISO-8601 plus original raw timestamp.
- Local market date is stored separately with IANA timezone.
- Exchange/provider timestamp and local receipt time are never collapsed.
- Forecast run time, publication/first-seen time, and valid time are distinct.
- Observation time, publication time, ingestion time, and revision are distinct.
- Clock skew and timestamp unit inference must be tested and documented.

### Data-quality gates

- [ ] Market/outcome/token referential integrity is 100% for the retained sample.
- [ ] Every retained market has preserved raw metadata and rule text.
- [ ] Every rule has timezone, unit, daily window, source, station or explicit unresolved flag.
- [ ] Outcome buckets have no unexplained gaps or overlaps.
- [ ] Book sides are sorted and prices are within `[0, 1]`.
- [ ] Book snapshot hash/timestamp semantics are documented.
- [ ] Forecast files are tied to a run and first-availability timestamp.
- [ ] Observation revisions are not overwritten.
- [ ] Settlement matches a defined outcome token or has an explicit anomaly flag.
- [ ] Missingness, duplicates, stale records, reconnect gaps, and parse failures are quantified.

## 8. Experimental design

### Evaluation type

Read-only feasibility study with endpoint/archive spikes, schema validation, manual reconciliation, and a 24-hour prospective collector stability run.

### Train/validation/test periods

Not applicable—no predictive model is trained. Any exploratory coverage data gathered here may later be used for infrastructure design, but not silently promoted to a locked profitability test set.

### Execution order

1. Freeze source inventory, metrics, and gates in this registration commit.
2. Verify Polymarket discovery and one complete market-event mapping.
3. Verify resolution-rule extraction and manual reconciliation.
4. Verify REST book snapshots and WebSocket capture.
5. Verify each weather source with a minimal real file/payload.
6. Measure historical archive depth by actual retrieval.
7. Join at least one end-to-end example per candidate city.
8. Score candidates and issue the G0 decision.

### Missing-data policy

- No silent imputation.
- Missing critical fields cause exclusion or a `BLOCKED` result for that city/source.
- Missing noncritical fields are reported with coverage percentages.
- A provider description is not evidence that a historical file is retrievable.

### Outlier/anomaly policy

- Preserve anomalies in raw data.
- Flag impossible values, timestamp reversals, bucket inconsistencies, station changes, and physical observation spikes.
- Do not repair raw payloads.
- Corrected normalized records must link to raw evidence and transformation version.

### Multiple-testing policy

No trading hypothesis is tested. Candidate-city ranking is descriptive. The chosen cities will require out-of-sample forecasting experiments; their ranking here is not evidence of alpha.

### Reproducibility rule

- All spikes must be executable from versioned code/config.
- Raw responses must have checksums and retrieval timestamps.
- Manual findings must link to saved evidence.
- Commands must run without secrets for public endpoints.
- Dependency versions must be locked before the 24-hour collector run.

## 9. Baselines and counterfactuals

| ID | Baseline/counterfactual | Purpose | Success condition |
|---|---|---|---|
| B1 | Polymarket displayed/price-history series | Show why price-only data is insufficient for fills | Difference from L2 semantics is documented |
| B2 | REST polling only | Compare snapshot continuity with WebSocket | Coverage and gap trade-off quantified |
| B3 | WebSocket only | Test reconnect and full-book recovery requirements | Recovery method is demonstrated |
| B4 | Reanalysis/current forecast archive | Negative control for point-in-time correctness | Explicitly rejected as substitute for as-issued forecasts |
| B5 | City-name observation | Compare with exact resolution station | Station mismatch risk is demonstrated or ruled out |
| B6 | Single provider forecast | Minimum viable forecast source | Archive depth and required parameters pass or fail explicitly |

## 10. Metrics and pre-registered decision gates

### Primary feasibility metric

`complete_city_count`: number of cities for which all six evidence components can be joined:

1. market/outcome metadata,
2. versioned resolution rule and station mapping,
3. prospective executable L2 book capture,
4. historical forecast-as-issued archive,
5. official station observation history,
6. final settlement.

### Primary decision gate

#### `PASS`

All conditions must hold:

- `complete_city_count >= 3`.
- At least 10 manually reconciled market-events across the retained cities.
- 100% critical market/outcome/token referential integrity in the sample.
- 100% of retained sample has rule text preserved and source/timezone/unit/bucket interpretation; unresolved station mapping must be 0 for the final 3 cities.
- A 24-hour collector run achieves at least 99% process uptime and at least 95% expected snapshot/heartbeat intervals after excluding documented provider outages.
- Reconnect recovery is demonstrated without silently losing the current full book.
- At least 365 consecutive days of retrievable forecasts-as-issued **or** a documented reforecast/archive product shown to support the intended calibration protocol for each final city.
- At least 365 days of matching station observations with revision semantics or final daily values.
- Licences and access terms permit research use; estimated data cost fits the approved research budget.

#### `CONDITIONAL_PASS`

All core joins work for at least 3 cities, but one or more of the following holds:

- 180–364 days of historical forecasts/observations are available;
- historical L2 is unavailable but prospective capture is stable;
- one preferred provider requires replacement by a documented open alternative;
- a longer prospective collection window is required before backtesting.

The condition must state the minimum collection period and which later experiments remain prohibited.

#### `FAIL`

Any of the following is sufficient:

- fewer than 3 cities can form the complete join;
- exact resolution station/window cannot be reliably mapped;
- no legally/operationally usable forecasts-as-issued exist for the selected market horizon;
- executable book data cannot be captured with recoverable continuity;
- market/outcome/settlement identifiers cannot be reconciled;
- required recurring data cost exceeds the approved project budget with no acceptable alternative.

#### `INCONCLUSIVE`

- Access outage, insufficient live-market availability, unclear provider terms, or unresolved external dependency prevents applying the gate.
- Inconclusive is not a pass and does not authorize forecasting/backtest claims.

### Secondary metrics

| Metric | Definition | Purpose |
|---|---|---|
| `market_discovery_coverage` | Retained qualifying markets / manually verified qualifying markets | Validate discovery filters |
| `critical_rule_parse_rate` | Rules with all critical fields / retained rules | Measure rule usability |
| `station_mapping_rate` | Exact station mappings / retained markets | Detect city-versus-station ambiguity |
| `book_success_rate` | Successful valid books / attempted books | REST reliability |
| `ws_gap_rate` | Missing/invalid message intervals / expected intervals | Stream continuity |
| `stale_book_rate` | Stale books / valid books | Execution-data quality |
| `forecast_archive_days` | Consecutive retrievable as-issued days | Calibration feasibility |
| `forecast_publish_lag` | First seen minus nominal run time | Point-in-time availability |
| `observation_coverage` | Available expected observations / expected observations | Station history quality |
| `rule_change_count` | Distinct rule hashes per market family | Versioning risk |
| `estimated_monthly_storage` | Raw plus normalized collector bytes/month | Operational cost |
| `estimated_monthly_cost` | Data, compute and storage estimate | Budget feasibility |

### No economic-performance metric

Net EV, ROI, Sharpe, win rate, and model accuracy are explicitly out of scope. No feasibility result may be presented as evidence of profitability.

## 11. Candidate-city scoring

Every candidate city receives a score from 0 to 5 for each factor. Scores require linked evidence; missing evidence scores 0 rather than receiving an assumed average.

| Factor | Weight | Score 0 | Score 5 |
|---|---:|---|---|
| Resolution clarity | 20% | Source/window/station ambiguous | Exact versioned station and rule semantics |
| Forecast archive quality | 20% | No as-issued archive | ≥365 days, ensemble/probabilistic, timestamped |
| Observation reliability | 15% | No exact/final station record | Versioned official station history ≥365 days |
| Order-book liquidity/depth | 15% | Empty or unusable | Repeated two-sided executable depth |
| Spread | 10% | Consistently prohibitive | Consistently narrow relative to plausible edge |
| Market frequency | 10% | Rare/irregular | Daily stable listing pattern |
| Station representativeness | 5% | Severe unresolved grid/site mismatch | Well-defined interpolation/site behavior |
| Anomaly/manipulation risk | 5% | Known uncontrolled anomaly | Stable source with cross-check and QC |

Weighted score:

\[
score_{city}=\sum_i weight_i\times\frac{factor_i}{5}\times100
\]

Selection rule:

- Minimum retained score: 70/100.
- Resolution clarity, forecast archive quality, and observation reliability must each score at least 4/5.
- Select 3–5 highest-scoring cities that pass critical gates.
- Ties are broken by better data provenance, then lower recurring cost—not observed trading performance.

## 12. Risks and invalidation conditions

| Risk | Detection | Mitigation | Invalidation condition |
|---|---|---|---|
| Look-ahead from revised forecasts | Compare run/first-seen/valid timestamps | Preserve raw runs and first-seen records | Historical product cannot be shown as issued |
| Midpoint mistaken for fill | Compare displayed, history and L2 fields | Store full book and executable sides | Only midpoint/last trade available |
| REST polling misses book changes | Compare with WebSocket sequence | WebSocket primary plus REST recovery snapshots | Gaps cannot be detected/recovered |
| WebSocket reconnect loses state | Forced disconnect test | Resubscribe and request fresh full book | State cannot be reconciled after reconnect |
| Wrong resolution station | Manual rule/source reconciliation | Versioned station registry and rule hash | Exact station/window remains ambiguous |
| Rule drift | Compare repeated rule hashes | Effective-date versioning | Historical rule versions cannot be established |
| Forecast archive too short | Retrieve earliest actual files | Alternative archive/reforecast or prospective wait | <180 days with no valid alternative |
| Provider model upgrades | Record product/version boundaries | Treat as regimes | Version boundary cannot be identified |
| Observation revisions overwritten | Compare preliminary/final products | Append revision records | Final settlement source cannot be reconstructed |
| Units/timezone/DST error | Boundary-date contract tests | IANA timezone and raw-unit preservation | Reconciliation fails around boundary cases |
| Fee schedule drift | Persist market fee metadata and docs date | Version fee schedule | Historical fee cannot be reconstructed later |
| Discovery survivorship bias | Query active/closed/resolved and manual sample | Preserve all statuses | Closed/cancelled markets inaccessible |
| API rate limit/outage | Log status/latency/retries | Backoff, caching and provider status log | Required rate is unsustainable |
| Excessive storage/compute cost | Measure 24-hour bytes and CPU | Compress/partition/downsample derived layers | Recurring cost exceeds approved budget |
| Terms/geographic restriction | Primary terms and professional review flag | Read-only public scope; block restricted actions | Research access is prohibited or unclear |
| Secret leakage | Staged-file and log scan | Public endpoints; sanitized envelopes | Any secret enters repository/artifact |

## 13. Phased execution plan

### Phase 0 — Pre-registration and source reconnaissance

**Status:** `PASSED`

#### Objective

Freeze the question, scope, sources, metrics, gates, and execution sequence before endpoint-level results influence the decision.

#### Entry criteria

- Root project charter and experiment-memory protocol exist.
- Repository bootstrap and smoke test pass.

#### Tasks

- [x] Assign experiment ID and owner.
- [x] Define primary feasibility hypothesis.
- [x] Define included/excluded scope.
- [x] Register logical tables and timestamp semantics.
- [x] Register primary and secondary metrics.
- [x] Register pass, conditional-pass, fail, and inconclusive gates.
- [x] Register city-scoring rubric.
- [x] Record preliminary official source inventory.
- [x] Record security, licensing, and no-live-trading constraints.
- [x] Create experiment index entry.
- [x] Update project plan.

#### Outputs

- This `PLAN.md`.
- `docs/experiments/README.md` index entry.
- Project-level registration decision in `PROJECT_PLAN.md`.

#### Verification

- All required `docs/agents.md` template sections are present.
- Primary gate can be applied without inventing thresholds after results.
- No API credentials or live-order permissions are required.

#### Exit criteria

- Plan committed before implementation spike.
- Experiment status set to `READY`.

#### Actual result

Plan completed on 2026-08-30. No endpoint-level feasibility result has been used to pass a data gate.

#### Decision

`PASSED` for plan registration. Begin read-only Polymarket discovery only after the registration commit.

#### Next action

Implement Phase 1 market discovery spike using public Gamma and CLOB metadata endpoints.

### Phase 1 — Polymarket market discovery and identifier reconciliation

**Status:** `PASSED`

#### Objective

Produce a reproducible inventory of qualifying active and recent settled daily maximum-temperature market-events and reconcile event, market, condition, outcome and token identifiers.

#### Entry criteria

- Phase 0 registration commit exists.
- Public endpoints and rate limits are documented.

#### Tasks

- [x] Build read-only Gamma discovery client with raw-envelope persistence.
- [x] Determine reliable weather/temperature discovery filters. (`highest-temperature`, tag ID `104596`, selected provisionally.)
- [x] Query active, closed and resolved records where supported. (Full active/not-closed and closed keyset traversals complete; exceptional status cohorts pending reconciliation.)
- [x] Normalize event/market/outcome/token/condition mappings. (Contract implementation complete; full live inventory pending.)
- [x] Preserve rule text and metadata hashes. (Raw envelope preserves payload and SHA-256; normalized event preserves resolution source.)
- [x] Identify multi-outcome/negative-risk structure. (Event contains binary bucket markets; flags preserved at both levels.)
- [x] Validate at least 20 sampled market-events manually. (12 retained/reconciled; all 20 received explicit disposition.)
- [x] Measure discovery coverage and critical-field missingness. (Closed anomaly cohorts are overlap-aware at event and market level.)
- [x] Add unit/contract tests with sanitized fixtures.
- [x] Produce Phase 1 evidence report.

#### Outputs

- `src/weather_quant/ingestion/polymarket_markets.py`
- versioned market schema and sanitized fixtures
- `reports/data_quality/EXP-20260830-phase1-market-discovery.md`
- immutable local raw payloads excluded from Git

#### Verification

- 100% referential integrity for retained sample.
- Discovery coverage reported against manual verification.
- Raw payload checksums reproduce normalized rows.
- No authenticated endpoint or secret is used.

#### Exit criteria

- At least 10 qualifying market-events across at least 3 cities are reconciled, or the phase is marked `BLOCKED`/`FAILED` with evidence.
- Critical identifier mismatch rate is 0 for retained records.

#### Actual result

Schema reconnaissance completed on 2026-08-30:

- `weather` tag ID `84` is broad and contained multiple weather contract families.
- `temperature` tag ID `104615` returned only 2 active/not-closed events in the probe and did not cover the daily MaxT universe.
- `highest-temperature` tag ID `104596` returned a first keyset page of 100 structurally matching events with a non-null cursor.
- The first broad Weather page contained 36 MaxT events across 33 city labels and 396 nested binary bucket markets.
- All 396 observed MaxT market rows had order books and fees enabled, but 44 rows lacked both `conditionId` and `clobTokenIds`.
- `active=true`/`closed=false` included stale May events on 2026-08-30; lifecycle flags alone are not a tradeability filter.
- An observed NYC event contained 11 binary bucket markets, event/market negative-risk flags, market-specific fee metadata and an event-level `resolutionSource` pointing to station code KLGA.

Evidence: `reports/data_quality/EXP-20260830-phase1-schema-recon.md`.

Production client implementation completed after reconnaissance:

- `GammaDiscoveryClient` uses public HTTPS GET requests and opaque keyset cursors.
- Request URL construction is deterministic; cursor loops and page-safety overruns fail closed.
- Raw envelopes record endpoint, request parameters, request/receipt UTC timestamps, SHA-256 and original payload.
- Raw writes are atomic and reject overwrite.
- Nested `outcomes` and `clobTokenIds` accept native arrays or strict JSON-array strings.
- Event normalization separates temporal relevance, lifecycle state, identifier integrity and book eligibility.
- Explicit reason codes cover stale events, missing IDs/tokens, length mismatch, non-binary markets and disabled books.
- Sanitized fixtures contain one eligible NYC bucket and one stale/incomplete Jinan bucket.
- 9 repository tests pass: 7 Gamma discovery/normalization tests and 2 bootstrap smoke tests.

Full active/not-closed traversal completed with run ID `20260829T214842Z`:

- 2 keyset pages, 136 source events and 0 duplicate event IDs.
- 51 unique city labels and 1,496 nested bucket markets.
- 100 events were temporally relevant at run time; their 1,100 nested markets passed the current identifier/book metadata contract and produced 2,200 normalized outcome-token rows.
- 396 markets were excluded because event end time had passed; 44 also lacked usable condition/token data.
- Two immutable raw envelopes consumed 6.6 MB and were indexed by checksums.
- Evidence: `reports/data_quality/EXP-20260830-phase1-active-inventory.md`.

The first full closed traversal completed with run ID `20260829T215025Z`:

- 83 keyset pages, 8,222 events, 54 city labels, 89,536 nested markets and 0 duplicate events.
- Event end-date coverage spans 2025-12-30 through 2026-08-29.
- 83 immutable raw envelopes consumed approximately 370 MB.
- Page/event/market/date/storage counts are valid.
- The first `outcome_count=0` metric is invalidated: the normalizer incorrectly coupled historical identifier mapping to current book eligibility.
- Contract correction now separates `identifier_complete` from `eligible_for_book_collection` and retains valid historical outcome-token rows.
- Evidence/invalidation record: `reports/data_quality/EXP-20260830-phase1-closed-inventory-attempt.md`.

The corrected closed traversal completed with run ID `20260829T215446Z`:

- Reproduced 83 pages, 8,222 events, 54 cities, 89,536 markets and 0 duplicates.
- 89,514 markets are identifier-complete (99.9754%) and produced 179,028 historical outcome-token rows.
- Resolution-source coverage is 92.2282%; automatic-resolution coverage 98.5892%; event close-time coverage 99.3067%; UMA-resolved market coverage 99.9107%.
- Missing cohorts: 639 no event resolution source, 116 not automatically resolved, 57 no close time, 22 identity-incomplete markets and 80 not UMA-resolved markets; categories may overlap.
- One full closed raw traversal consumes approximately 370 MB.
- Evidence: `reports/data_quality/EXP-20260830-phase1-closed-inventory.md`.

Deterministic anomaly extraction and sampling completed:

- 7,470/8,222 events are clean under the registered metadata/status checks; 752 carry at least one flag.
- Market-level counts of 22 identifier-incomplete and 80 non-UMA-resolved records are concentrated in 2 and 19 events respectively.
- The fixed-seed 20-event queue covers every anomaly type plus clean controls; only two identifier-incomplete events exist, so both were selected and one slot was hash-filled.
- Selection is complete, but none of the 20 events is yet credited as manually reconciled.
- Evidence: `reports/data_quality/EXP-20260830-phase1-closed-anomaly-cohorts.md` and `reports/data_quality/EXP-20260830-phase1-closed-audit-sample.json`.

#### Decision

Phase 1 passes. Twelve retained events across twelve cities reconcile identifier, rule/station, terminal bucket and displayed source high with zero retained identifier mismatches. Eight anomalous events remain preserved but excluded.

#### Next action

Begin Phase 2 with the versioned resolution-rule and station registry schema.

### Phase 2 — Resolution-rule and station registry

**Status:** `PASSED`

#### Objective

Convert market rule text into versioned, manually verified station, source, timezone, unit, daily-window, rounding, and bucket semantics.

#### Entry criteria

- Phase 1 identifier inventory passes.

#### Tasks

- [x] Define resolution registry schema. (`schemas/resolution_registry.schema.json` plus fail-closed Python semantic validator.)
- [x] Parse source URL/provider and station identity. (20 candidate records emitted; independent station verification pending.)
- [x] Parse local date, timezone and observation window. (11 retained records independently timezone-verified against IANA-aligned 2026c boundaries.)
- [x] Parse temperature unit, bucket inclusivity and rounding. (161 buckets parsed; 128 belong to structurally valid candidates.)
- [x] Hash and version rule text. (20 exact SHA-256 rule versions.)
- [x] Detect rule/station changes within a city family. (Corrected full history: Denver and Paris station transitions; 52 multi-template cities.)
- [x] Cross-check source station metadata. (AviationWeather returned 12/12 candidates; 11 identity matches and one Karachi rule/source conflict.)
- [x] Manually reconcile minimum 20 market-events. (All 20 received disposition; 11 now pass full registry verification.)
- [x] Add DST, Celsius/Fahrenheit and boundary tests. (Toronto 23/25-hour DST days, Kuala Lumpur 24-hour day, C/F buckets and partition boundaries.)

#### Outputs

- `src/weather_quant/normalization/resolution_rules.py`
- resolution registry schema and sanitized fixtures
- `reports/data_quality/EXP-20260830-phase2-resolution-registry.md`

#### Verification

- Critical rule parse rate and station mapping rate reported.
- Bucket coverage has no unexplained gap/overlap.
- Manual reconciliation evidence is linked.

#### Exit criteria

- At least 3 cities have exact resolution source/station/window/unit mappings.
- Critical fields are complete for 100% of retained sample.

#### Actual result

Registry schema versions `0.1.0`/`0.2.0` bind event identity, disposition, source/station/timezone, unit/precision/rounding, explicit local-day window, exact rule hash/version, numeric bucket boundaries and source provenance. Candidate population produced 20 deterministic records and 161 buckets. Independent AviationWeather plus IANA-aligned boundary verification promoted 11 records; Karachi was rejected for a rule station-name/source-code contradiction. The verified registry contains 11 final records, 9 hard exclusions and 117 retained buckets; 28 tests pass.

#### Decision

Phase 2 passes: 11 retained cities exceed the ≥3-city gate with 100% critical-field completeness. Full-history diagnostics found two station transitions, no unit transitions, 52 multi-template cities and 901 excluded incomplete parses.

#### Next action

Begin Phase 3 with a point-in-time executable CLOB order-book snapshot contract and public REST coverage test.

### Phase 3 — Executable order-book capture feasibility

**Status:** `IN_PROGRESS`

#### Objective

Demonstrate recoverable prospective L2 order-book capture and quantify why price history alone is insufficient for executable fills.

#### Entry criteria

- Phase 1 token identifiers pass.
- At least 3 active market-events are available.

#### Tasks

- [x] Implement public REST `/book` client.
- [x] Implement public market WebSocket client. (Public initial-book capture and forced reconnect passed.)
- [x] Persist raw timestamps, receipt times, hashes and levels. (66 book + 66 dynamic-tick immutable envelopes.)
- [x] Validate bid/ask sorting, bounds, tick size and empty-book behavior. (48 two-sided, 18 one-sided; 0 dynamic tick violations.)
- [ ] Compare displayed/price-history values with executable book sides.
- [x] Force reconnect and demonstrate full-book recovery. (2/2 assets; REST hash match 2/2.)
- [ ] Run a minimum 24-hour stability capture. (`DEFERRED_UNTIL_MANAGED_HOST`; registered gate unchanged.)
- [ ] Measure uptime, gap, stale-book, retry, bytes and storage metrics.
- [ ] Document historical L2 availability or absence without assumption.

#### Outputs

- `src/weather_quant/ingestion/polymarket_orderbook.py`
- order-book schemas and sanitized fixtures
- `reports/data_quality/EXP-20260830-phase3-orderbook-capture.md`

#### Verification

- REST and WebSocket books reconcile within documented timing tolerance.
- Reconnect creates a fresh authoritative book before deltas resume.
- Full capture can be replayed deterministically.

#### Exit criteria

- 24-hour process uptime ≥99% and expected interval coverage ≥95%, excluding documented provider outage.
- Every retained snapshot passes price/order validation or has a quality flag.

#### Actual result

Fresh active inventory selected three latest-end events and requested all 66 Yes/No token books. Public REST coverage was 66/66 with zero request failures: 48 two-sided and 18 one-sided books, 3,828 validated levels, median latency 147.9 ms and median two-sided spread 0.020. Dynamic ticks were `0.01` for 38 and `0.001` for 28 tokens; 8 differed from Gamma metadata. First-run static-tick violation count was invalidated; corrected v3 persists full normalized levels. A two-token forced-reconnect spike then recovered full books in 0.416/0.341 seconds and matched fresh REST hashes 2/2 with zero base-before-delta violations. The subsequent 35-second/12-token heartbeat shakeout applied 78 real changes from 39 events with zero replay-top mismatch and reconciled final REST hashes 12/12.

#### Decision

REST contract, forced reconnect and live delta replay shakeout passed. The first long run is invalid for the stability gate because verified host sleep contaminated wall-clock uptime; its raw replay also exposed checkpoint bias, fixed-asset lifecycle failure and unresolved advertised-top mismatch. Phase 3 remains `IN_PROGRESS`.

#### Next action

Measure the locked latest 365 completed days of operational GEFS 00Z f024 c00/p01/p30 index coverage and investigate any missing date across full membership/cycles.

### Phase 4 — Forecast-as-issued source feasibility

**Status:** `IN_PROGRESS`

#### Objective

Verify actual retrievability, archive depth, timestamp semantics, parameters, licensing, cost and station applicability for candidate forecast providers.

#### Entry criteria

- Phase 2 final candidate station list exists.

#### Tasks

- [x] Define initial NBM variables and lead times for daily MaxT reconstruction. (KORD 01Z NBP: FHR 24–228, mean/SD and 10/25/50/75/90 percentiles; value parser pending.)
- [ ] Retrieve actual NBM core/QMD files for current and earliest available dates.
- [x] Inspect NBM MaxT probabilistic/quantile fields and run cycles. (Matched 01Z required; 00Z historical counterexample preserved.)
- [x] Probe GFS/GEFS archive depth and ensemble structure. (Initial 31/31 samples plus 365/365 representative daily continuity; full-member daily continuity and local-day semantics pending.)
- [ ] Probe HRRR archive depth and short-lead applicability.
- [x] Probe ECMWF Open Data parameters, ensemble structure and rolling retention.
- [ ] Record nominal run, first-seen, publish and valid timestamps.
- [ ] Record model upgrade/version boundaries.
- [ ] Measure file size, retrieval time, compute and storage cost.
- [ ] Reject reanalysis as a substitute for missing as-issued data.
- [ ] Select minimum viable provider set per candidate city.

#### Outputs

- source-specific spike code under `src/weather_quant/ingestion/`
- `reports/research/EXP-20260830-phase4-forecast-sources.md`
- dataset manifests for every retrieved sample

#### Verification

- Earliest/latest retrievable files are demonstrated with checksums.
- Required MaxT or sufficient sub-daily inputs are verified from file inventory.
- First-availability semantics are measured or explicitly unresolved.

#### Exit criteria

- Each retained city has ≥365 days of suitable as-issued/reforecast data for `PASS`, or ≥180 days plus prospective plan for `CONDITIONAL_PASS`.
- Licence and recurring-cost classification is complete.

#### Actual result

Public AWS delivered complete NBM NBP 01Z objects for 2026-08-30 and 2023-08-31, 1,095 days apart. Immutable downloads were 34.72/34.81 MB with distinct, reverified SHA-256 hashes. The exact KORD station blocks identify NBM v5.0/v4.1 and each contains mean, standard deviation and 10/25/50/75/90 percentile temperature markers. An initial 00Z historical negative result was invalidated as a cycle-availability mismatch, not archive absence. A deterministic 49-date monthly/model-boundary probe found 48 objects (97.959%); only 2026-06-01 01Z was absent while four alternative cycles existed. The parser emitted 18 provenance-bearing KORD MaxT distributions with zero missing values.

#### Decision

NBM/KORD remains `CONDITIONAL_PASS`; Phase 4 remains `IN_PROGRESS`. The locked latest 365-day window has 364/365 primary 01Z objects and one verified 07Z fallback, for 100% object-policy coverage with zero transient failures. ECMWF Open Data is prospective-only. GEFS operational archive remains `CONDITIONAL_PASS`: initial samples had 31/31 membership and the 365-day representative continuity gate passed, but exact local-day TMAX aggregation failed for CYYZ and WMKK because canonical UTC windows add six outside-local hours.

#### Next action

Measure source-matching CYYZ/WMKK station-observation history and revision semantics before comparing contamination-tagged GEFS feature policies against local-day outcomes.

#### Pre-registration — 2026-08-31 — GEFS daily representative coverage

- **Hypothesis:** Operational GEFS 00Z/f024 indexes provide sufficiently continuous as-issued temperature-field coverage for historical calibration.
- **Locked window:** 2025-08-31 through 2026-08-30 inclusive (365 completed UTC run dates).
- **Primary sample:** `gec00`, `gep01`, and `gep30`; exactly one 2 m `TMP`, `TMAX`, and `TMIN` record per index.
- **Acceptance:** At least 99% of the 1,095 representative indexes are complete and zero transport failures remain after three bounded attempts.
- **Mandatory diagnosis:** Any incomplete date triggers probes of all 31 members at 00Z and representative members at 06/12/18Z; missing data is not silently replaced.
- **Interpretation limit:** Passing establishes representative daily continuity only. It does not establish 31/31 daily completeness, local-day MaxT construction, or model-version stability.
- **Artifact:** `reports/data_quality/EXP-20260831-phase4-gefs-daily-coverage-365d.json`.

#### Pre-registration — 2026-08-31 — GEFS local-day TMAX semantics

- **Hypothesis:** GEFS 2 m TMAX metadata forms consecutive three-hour UTC windows that can also partition the selected station-local days without gaps or outside-local contamination.
- **Locked cases:** Toronto/CYYZ on 2026-07-23 (`America/Toronto`, DST active) and Kuala Lumpur/WMKK on 2026-06-22 (`Asia/Kuala_Lumpur`, no DST); both are Phase 2 `RECONCILED` records.
- **Data:** Actual 00Z control-member indexes in three-hour steps through at least f048, plus real TMAX range downloads and GRIB boundary/checksum verification for both cases.
- **Gate A — product semantics:** Every inspected step contains exactly one 2 m TMAX row labeled `(step-3)-step hour max fcst`; consecutive windows have zero gap and overlap.
- **Gate B — local-day identity:** Selected windows exactly equal local `[00:00, next 00:00)` in UTC, with zero uncovered seconds and zero outside-local seconds. DST dates must retain their actual 23/25-hour duration.
- **Failure policy:** Gate B failure forbids treating interval TMAX as the resolution-equivalent daily label. Any boundary-overlap feature must expose contamination duration; an instantaneous-TMP or other explicit alternative requires its own contract.
- **Metrics:** Field/window completeness, gap/overlap seconds, local-day duration, uncovered seconds, outside-local seconds, selected run/step set, actual range integrity and data availability timestamps.
- **Artifacts:** `reports/data_quality/EXP-20260831-phase4-gefs-local-day-semantics.json`, `reports/research/EXP-20260831-phase4-gefs-local-day-semantics.md`.

### Phase 5 — Observation and settlement reconciliation

**Status:** `IN_PROGRESS`

#### Objective

Verify that exact resolution-station observations, revisions/final daily values, and Polymarket settlement outcomes can be reconstructed and joined.

#### Entry criteria

- Phase 2 station mapping passes.

#### Tasks

- [ ] Retrieve official/source-matching observations for candidate stations.
- [ ] Distinguish preliminary, real-time, revised and final observations.
- [ ] Reconstruct the contract's local daily maximum and rounding semantics.
- [ ] Retrieve market settlement/winning outcome.
- [ ] Reconcile observed value to winning bucket for sampled settled markets.
- [ ] Record discrepancies, invalid markets and source anomalies.
- [ ] Measure at least 365 days of observation coverage where available.

#### Outputs

- observation/settlement ingestion modules and schemas
- `reports/data_quality/EXP-20260830-phase5-observation-settlement.md`

#### Verification

- Sample settlement is reproducible from preserved rule and observation evidence.
- Revisions are append-only.
- All mismatches are explained or explicitly flagged.

#### Exit criteria

- Exact observation and settlement join passes for at least 10 sampled market-events across at least 3 cities.
- Final retained cities have sufficient historical observation coverage.

#### Actual result

The locked 24-page spike and 730-page availability coverage passed, but outcome-label validity did not generalize. CYYZ 2026-03-08's current page shows 9°C/two rows while official civil-day ECCC max is 12.1°C and Polymarket settled `10°C or higher`. Page availability and settlement-valid labels are now separate gates.

#### Pre-registration — 2026-08-31 — Wunderground observation retention spike

- **Hypothesis:** The exact Wunderground resolution pages expose parseable station/date/daily-high and observation rows for at least 365 days for CYYZ and WMKK.
- **Locked dates:** Offsets `0,1,7,30,60,90,120,150,180,240,300,364` from each station's reconciled market date; 24 pages total.
- **Acceptance:** 24/24 HTTP 200, exact station code/name, requested-date identity, daily high and non-empty observation table; zero terminal transport failures; deterministic normalized parse.
- **Scaling rule:** Do not issue the 730-page full probe unless the spike passes completely. Classify missing object, parser drift and transport separately.
- **Revision limitation:** A page retrieved now is current/final evidence, not proof of the value visible at the rule's next-day freeze time. Exact historical settlement-as-of remains conditional without a preserved snapshot; prospective capture must be append-only.
- **Metrics:** Coverage by station/date, response bytes/hash/timestamps, parsed identity/high/unit/observation count, missingness class and normalized repeatability.
- **Artifacts:** `reports/data_quality/EXP-20260831-phase5-wunderground-observation-spike.json`, `reports/research/EXP-20260831-phase5-wunderground-observation-spike.md`.

#### Pre-registration — 2026-08-31 — Wunderground 365×2 coverage

- **Locked windows:** CYYZ 2025-07-24–2026-07-23 and WMKK 2025-06-23–2026-06-22, inclusive; 730 pages.
- **Acceptance:** Current/final complete-page coverage ≥99% per station, terminal transport failure 0 after bounded retry, and station/date/timezone identity 100% among HTTP-available pages.
- **Daily contract:** Daily high/unit and non-empty observation table required. `daily_high == max(observation temp)` is reported and must be 100% for direct reconstruction; otherwise discrepancy dates are retained and investigated, not imputed.
- **Missingness:** HTTP absence, transport exhaustion, identity mismatch, missing high and missing observations are separate classes.
- **Evidence limit:** Passing authorizes current/final outcome labels for calibration. It does not upgrade them to historical market-freeze-as-of settlement evidence.
- **Artifact:** `reports/data_quality/EXP-20260831-phase5-wunderground-observation-coverage-365d.json`.

#### Pre-registration — 2026-08-31 — CYYZ 2026-03-08 anomaly diagnostic

- **Hypothesis:** Wunderground's two-row page is intraday-incomplete, while its 9°C daily high remains consistent with the exact-station ECCC hourly local-day maximum.
- **Independent source:** Official ECCC `climate-hourly` OGC API; `TORONTO INTL A`, climate identifier `6158731`, with station coordinates checked against CYYZ evidence.
- **Acceptance:** Exactly 23 unique local-hour rows on the DST spring-forward date, 23 non-null temperatures, exact local date/station identity, and half-up whole-degree maximum equal to Wunderground's 9°C high.
- **Time contract:** Filter ECCC hourly `LOCAL_DATE`; do not use ECCC daily aggregates because official climatological-day boundaries need not equal the Polymarket local calendar day.
- **Settlement check:** Scan the complete preserved 8,222-event closed inventory for the exact Toronto/date event. No event yields `NOT_APPLICABLE`, not a passed settlement reconciliation.
- **Artifact:** `reports/data_quality/EXP-20260831-phase5-cyyz-20260308-anomaly.json`.

#### Corrective registration — 2026-08-31 — CYYZ civil-time and settlement v2

- **Trigger:** v1 failed: ECCC `LOCAL_DATE` returned 24 standard-time-labelled rows, official max was 12.1°C rather than Wunderground's 9°C, and structured inventory scanning found Polymarket event 249630 with winner `10°C or higher`.
- **Correction:** Filter ECCC `UTC_DATE` by IANA `America/Toronto` civil `[00:00,next 00:00)` boundaries; require 23 rows on the spring-forward date and no duplicate UTC timestamps.
- **Forensic comparison:** Report raw/half-up ECCC maximum, Wunderground current-page high and terminal Polymarket bucket. No source is silently overwritten or promoted to historical freeze evidence.
- **Decision rule:** If civil ECCC maximum belongs to the terminal bucket while current Wunderground high does not, mark the current Wunderground label `HISTORICAL_PAGE_DIVERGED_FROM_SETTLEMENT` and exclude it from outcome training.
- **Artifact:** `reports/data_quality/EXP-20260831-phase5-cyyz-20260308-anomaly.json`; v1 remains `-attempt1.json`.

#### Pre-registration — 2026-08-31 — Fixed Wunderground/settlement divergence audit

- **Cohort:** The pre-existing 20-event Phase 1 stratified sample plus CYYZ event 249630 as the anomaly sentinel. No outcome-selected replacement events.
- **Eligibility:** Exact terminal winner, identifier match and parsed Wunderground daily high. All other records remain `INELIGIBLE` with their original reason.
- **Primary metrics:** Eligible, match, diverged and ineligible events/cities; divergence rate with Wilson 95% interval; explicit event-level evidence class and quarantine.
- **Gate:** At least 10 current-page/winner `MATCH` records across at least three cities, every divergence set `NO_TRAIN_NO_BACKTEST`, and zero unresolved eligible records.
- **Interpretation:** A match is current-page/terminal-bucket consistency, not proof of freeze-time page identity. A divergence invalidates the current page as an outcome label.
- **Artifacts:** `reports/data_quality/EXP-20260831-phase5-wunderground-settlement-audit.json`, `reports/research/EXP-20260831-phase5-wunderground-settlement-audit.md`.

#### Decision

The registered fixed-sample observation/settlement subgate `PASSED`: 12 current-page/terminal-bucket matches across 12 cities, two divergences quarantined, and zero unresolved eligible records. The primary fixed-sample divergence was 2/14 (14.29%, Wilson 95% CI 4.01%–39.94%). Adding the anomaly-selected CYYZ sentinel gives 3/15 (20.00%, sensitivity only).

This does not validate current Wunderground historical pages as exact-temperature labels. Terminal Polymarket bucket labels were available for 14/14 eligible fixed-sample events, while exact-temperature label eligibility was 0/14 because no preserved freeze-time page/version exists. Phase 5 remains `IN_PROGRESS`.

The locked KORD/LCDv2 latest-365 package subsequently `FAILED` coverage: 356/365 dates (97.53%) versus the registered ≥99% threshold. The nine missing dates are the trailing 2026-08-22–2026-08-30 block, consistent with publication lag. Identity, duplicates and transport checks passed; event 553903 was forensically bucket-consistent. LCDv2 remains an independent final diagnostic, not settlement-as-of evidence.

The separately preregistered 40-day-buffer window then `PASSED` final archive coverage at 365/365 dates and non-null maxima with zero duplicates, identity failures or transport failures. This establishes KORD LCDv2 final archive completeness for that cohort, while leaving decision-time and Wunderground freeze-time reconstruction unresolved.

The prospective two-page freeze snapshot fixture contract `PASSED` 12/12 qualification, replay, immutability, idempotency, revision and tamper-detection cases. This validates storage semantics only; no live event or collector uptime evidence exists yet.

Current read-only discovery returned `NOT_AVAILABLE` for the preregistered Wunderground-primary KORD cohort: 0/3 Chicago events used Wunderground as primary. Two events were observed-future and identity-complete, but all current Chicago rules named NOAA WRH KORD as primary and Wunderground only as fallback, establishing a provider-regime boundary.

#### Next action

Inspect the current NOAA WRH KORD primary surface read-only and preregister its timestamp/timezone/unit, hourly-row, next-day-trigger and revision gate before any prospective capture.

#### Pre-registration — 2026-08-31 — KORD/NOAA LCDv2 365-day observation package

- **Hypothesis:** NOAA NCEI LCDv2 can provide an independently sourced daily-maximum observation for at least 99% of the locked 2025-08-31–2026-08-30 KORD dates, with exact station identity and explicit revision limitations.
- **Locked source:** Annual LCDv2 CSV objects `LCD_USW00094846_2025.csv` and `LCD_USW00094846_2026.csv`. Preserve URL, retrieval timestamp, HTTP Last-Modified/ETag, byte count and SHA-256. NOAA documentation and station metadata are provenance inputs.
- **Identity:** KORD / Chicago O'Hare, WBAN 94846 / GHCN `USW00094846`, station name and coordinates. Identity mismatch is a hard failure, not a nearest-station substitution.
- **Coverage acceptance:** All 365 dates represented; ≥99% exact-date coverage and non-null daily maximum; zero duplicate daily summaries; 100% identity among admitted rows; zero terminal transport failures. No imputation.
- **Semantic acceptance:** Record the LCDv2 daily field, units, report/source type and known quality flags. Unless NOAA's daily window and version time are proven identical to the Wunderground rule, classify observations only as `INDEPENDENT_FINAL_DIAGNOSTIC_ONLY`.
- **Settlement sentinel:** Fixed event 553903 / 2026-06-05 / terminal winner `68°F or higher`. Preserve LCDv2 maximum, current Wunderground high and terminal winner separately. Agreement is forensic consistency, not exact settlement-as-of proof.
- **Revision decision:** Object Last-Modified proves only the observed object version. Without immutable historical snapshots/version history, set `HISTORICAL_FREEZE_AS_OF_UNRESOLVED` and require prospective append-only capture.
- **Artifacts:** `reports/data_quality/EXP-20260831-phase5-kord-lcdv2-observation-coverage.json` and `reports/research/EXP-20260831-phase5-kord-lcdv2-observation-coverage.md`.

#### Pre-registration — 2026-08-31 — KORD/LCDv2 lag-safe final archive coverage

- **Hypothesis:** If the latest-window failure is a trailing publication-lag effect, the unchanged KORD/LCDv2 contract will provide ≥99% exact-date and non-null daily-maximum coverage in the fixed 2025-07-23–2026-07-22 window, which has a 40-day buffer at analysis time.
- **Cohort:** Exactly 365 dates; no outcome-selected replacements. Use the same `USW00094846`, `REPORT_TYPE=SOD`, `DailyMaximumDryBulbTemperature`, name/coordinate identity and annual objects.
- **Acceptance:** Exact-date coverage ≥99%, non-null maximum coverage ≥99%, zero duplicate dates, zero identity failures and zero terminal transport failures. No imputation or provider mixing.
- **Lag metric:** Preserve observed annual-object Last-Modified and final SOD date; report their calendar-day difference for the current 2026 object as a publication-lag proxy, not a revision history.
- **Interpretation:** Passing means only `FINAL_ARCHIVE_COVERAGE_PASS`. It does not establish historical decision-time availability, Wunderground equivalence or freeze-time reconstruction. Failure weakens LCDv2 even for final research labels.
- **Artifacts:** `reports/data_quality/EXP-20260831-phase5-kord-lcdv2-lag-safe-coverage.json` and research report.

#### Pre-registration — 2026-09-02 — Prospective Wunderground freeze snapshot contract

- **Hypothesis:** A single capture containing the KORD target-date page and a non-empty following-date page can preserve replayable evidence that collection happened after the rule's next-day trigger, while immutable content addressing prevents silent revision overwrite.
- **Fixture scope:** Synthetic KORD target `2026-09-01`, following date `2026-09-02`, `America/Chicago`, whole °F, event ID and rule hash. Fixture success is not live settlement evidence.
- **Qualification:** Both raw responses present; exact station/name/timezone/page-date identity; target high and F unit; following page has ≥1 observation; capture at/after following local midnight; raw SHA-256 and rule hash present. Any failure yields `NOT_FREEZE_ELIGIBLE`.
- **Append-only record:** Content-addressed raw target/trigger files plus canonical snapshot manifest containing event/date/rule/parser versions, requested/received times, parsed values, checks and checksums. Existing different bytes cannot be overwritten.
- **Idempotency/revisions:** Identical canonical payload returns the same snapshot without adding a manifest. Changed content for the same event/date appends a new revision and preserves earlier evidence.
- **Acceptance:** Valid fixture qualifies; pre-midnight, empty trigger, identity/date/unit/rule mismatch fail closed; tamper verification fails; replay is deterministic; duplicate and changed-content behavior passes. Ruff and full tests pass.
- **Boundary:** This tests the storage/evidence contract, not live page behavior or collector uptime. Do not launch a persistent process in this step.
- **Artifacts:** `reports/data_quality/EXP-20260902-phase5-wunderground-freeze-snapshot-contract.json` and research report.

#### Pre-registration — 2026-09-02 — Upcoming exact-rule KORD event discovery

- **Hypothesis:** One complete public Gamma `highest-temperature`, `closed=false` keyset traversal contains at least one observed-future, active/not-closed Chicago event with an exact Wunderground `/KORD` next-day-first-datapoint rule and complete nested market/token identities.
- **Universe:** One checksum/timestamp-preserved traversal. Do not substitute broad-weather or closed events if the cohort is empty.
- **Eligibility:** Exact Chicago title family; active true, closed false, endDate at/after discovery observed-at; Wunderground KORD station/source and following-date first-datapoint freeze semantics in the rule; event/end and every bucket's market, condition and two-token identity complete.
- **Selection:** Earliest endDate, then numeric event ID. Zero candidates yields `NOT_AVAILABLE`, not a fabricated pass or outcome-selected city replacement.
- **Metrics:** Page/source/duplicate/event/city counts; Chicago raw, future, exact-rule and qualified counts; reason codes; selected event/date/rule hash and token identities.
- **Safety:** Public GET only; no wallet, credential, order or background collector.
- **Artifacts:** `reports/data_quality/EXP-20260902-phase5-kord-upcoming-event-discovery.json`, research report and ignored immutable raw envelopes.

#### Pre-registration — 2026-09-02 — NOAA WRH KORD source-surface discovery

- **Hypothesis:** The declared `weather.gov/wrh/timeseries?site=kord` primary source or its first-party NOAA/NWS data calls expose exact KORD identity, observation timestamps, explicit temperature values/units and hourly rows in a machine-reconcilable form.
- **Scope:** Official `weather.gov`/NOAA/NWS origins and first-party resources referenced by the page; GET/HEAD only, no third-party weather provider.
- **Provenance:** Preserve URL, request/receive UTC, status/headers, bytes, SHA-256, content type, referenced scripts/data calls, candidate endpoint and sample schema. Report credentials/access constraints.
- **Semantic acceptance:** Exact KORD; at least one observation timestamp with explicit/documented timezone semantics; temperature value and unit; at least one hourly row; deterministic conversion to `America/Chicago` local date.
- **Trigger acceptance:** The first observation belonging to the following local date can be deterministically selected from timestamped rows. Page presence alone is insufficient.
- **Revision boundary:** Without a version/revision surface, current retrieval stays `HISTORICAL_FREEZE_AS_OF_UNRESOLVED` and requires prospective raw capture.
- **Stability:** Two bounded consecutive requests must agree on HTTP/schema/identity. Dynamic data/checksum differences are preserved, not failures. No persistent polling.
- **Decision:** `PASSED`, `CONDITIONAL_PASS` or `FAILED` without post-result threshold edits.
- **Artifacts:** `reports/data_quality/EXP-20260902-phase5-noaa-wrh-kord-source-discovery.json` and research report.

### Phase 6 — End-to-end join, city scoring and cost model

**Status:** `NOT_STARTED`

#### Objective

Build one point-in-time end-to-end record per candidate city, score cities using the registered rubric, and quantify recurring data/storage/compute costs.

#### Entry criteria

- Phases 1–5 have passed or have documented conditional results.

#### Tasks

- [ ] Join all six evidence components without forward-looking fields.
- [ ] Produce field-level completeness report.
- [ ] Apply candidate-city score with linked evidence.
- [ ] Estimate monthly API, data, storage and compute cost.
- [ ] Estimate time required to accumulate prospective L2 history.
- [ ] Select 3–5 candidate cities or declare failure.
- [ ] Review licensing/access/geographic blockers.
- [ ] Stress test source outage and provider replacement scenarios.

#### Outputs

- `reports/research/data_source_feasibility.md`
- candidate-city scorecard
- source/cost matrix
- point-in-time join examples with sanitized evidence

#### Verification

- No selected city has a critical factor below 4/5.
- Scores reproduce from documented inputs.
- End-to-end rows trace back to raw checksums.

#### Exit criteria

- Primary `complete_city_count` is known.
- Cost and retention conditions are quantified.
- A preliminary gate outcome can be applied without changing thresholds.

#### Actual result

Pending.

#### Decision

Pending.

#### Next action

Pending Phase 6 result.

### Phase 7 — Final G0 decision and handoff

**Status:** `NOT_STARTED`

#### Objective

Apply the pre-registered gate, close the experiment, and define exactly which downstream work is authorized.

#### Entry criteria

- Phase 6 evidence and scorecard complete.

#### Tasks

- [ ] Apply `PASS`, `CONDITIONAL_PASS`, `FAIL`, or `INCONCLUSIVE` criteria.
- [ ] Separate observed facts, inference and unknowns.
- [ ] Record deviations and invalidated assumptions.
- [ ] Update experiment index and project Decision Log.
- [ ] Update Phase 0/G0 and Phase 1 statuses.
- [ ] Define approved collectors and retention schedule.
- [ ] Define prohibited downstream claims/work.
- [ ] Register follow-up baseline experiment if authorized.

#### Outputs

- completed result, interpretation and decision sections in this plan
- final feasibility report
- updated `PROJECT_PLAN.md`
- follow-up experiment ID if applicable

#### Verification

- Final status follows the gate exactly.
- Evidence paths and final commit are linked.
- No profitability claim is made.

#### Exit criteria

- Experiment has a terminal status.
- Project roadmap reflects the decision.
- Final commit and remote branch state are recorded.

#### Actual result

Pending.

#### Decision

Pending.

#### Next action

Pending final decision.

## 14. Deliverable map

| Phase | Primary deliverable | Commit message |
|---|---|---|
| 0 | Registered experiment plan and index | `experiment(EXP-20260830-data-source-feasibility): register plan` |
| 1 | Market discovery inventory and report | `experiment(EXP-20260830-data-source-feasibility): complete phase 1 market discovery` |
| 2 | Resolution/station registry | `experiment(EXP-20260830-data-source-feasibility): complete phase 2 resolution registry` |
| 3 | 24-hour order-book capture evidence | `experiment(EXP-20260830-data-source-feasibility): complete phase 3 orderbook capture` |
| 4 | Forecast-source archive matrix | `experiment(EXP-20260830-data-source-feasibility): complete phase 4 forecast sources` |
| 5 | Observation/settlement reconciliation | `experiment(EXP-20260830-data-source-feasibility): complete phase 5 settlement reconciliation` |
| 6 | End-to-end join and city scorecard | `experiment(EXP-20260830-data-source-feasibility): complete phase 6 city scoring` |
| 7 | Final G0 decision | `experiment(EXP-20260830-data-source-feasibility): close feasibility decision` |

## 15. Results

### Primary result

Pending. No endpoint-level feasibility gate has been evaluated.

### Coverage results

Pending.

### Candidate-city results

Pending.

### Cost and retention results

Pending.

### Robustness and failure-mode tests

Pending.

### Deviations from plan

None at registration.

## 16. Interpretation

### Observed

- Official documentation identifies public Polymarket market data, order-book, WebSocket, price-history, and fee surfaces.
- Official NOAA documentation identifies operational NBM distribution through NOMADS/AWS.
- Official ECMWF documentation describes Open Data as a rolling archive.

These are source-existence observations, not proof of usable historical coverage.

### Inferred

- Historical executable L2 reconstruction will likely require prospective capture because the documented price-history response does not include depth.
- Some operational weather products may require prospective archiving or an alternative historical/reforecast source.

These inferences must be verified in Phases 3 and 4.

### Unknown

- Exact active/recent weather-market discovery coverage.
- Historical L2 availability outside documented price history.
- Per-provider historical as-issued depth and first-availability semantics.
- Exact station/source consistency across market families.
- Recurring cost, storage and sustainable request rate.

## 17. Final decision

- Final status: Pending
- Primary gate outcome: Pending
- Complete city count: Pending
- Authorized downstream work: Only Phase 1 read-only discovery after registration commit
- Prohibited downstream work: Profitability claims, model training presented as valid, live orders
- Follow-up experiment: Pending

## 18. Artifact index

| Artifact | Path/run ID | Version/commit | Purpose |
|---|---|---|---|
| Experiment plan | `docs/experiments/EXP-20260830-data-source-feasibility/PLAN.md` | Registration commit in Git history | Pre-registration and project memory |
| Experiment index | `docs/experiments/README.md` | Registration commit in Git history | Experiment discoverability |
| Final feasibility report | `reports/research/data_source_feasibility.md` | Pending | Final source, cost and city decision |

## 19. Update Log — append only

### 2026-08-30 — Plan registered

- Previous status: None
- New status: `READY`
- Work completed: Primary hypothesis, sources, schemas, metrics, gates, seven execution phases, risks, candidate-city scoring, and commit points pre-registered.
- Evidence: Official source documentation listed in Section 6; root project charter and repository bootstrap.
- Deviations: None.
- Blockers: Endpoint-level coverage remains unknown by design.
- Next action: Commit registration, then begin Phase 1 public market-discovery spike.

### 2026-08-30 — Phase 1 schema reconnaissance completed

- Previous status: `READY`
- New status: `IN_PROGRESS`
- Work completed: Resolved live tag identities, compared broad/narrow tag coverage, measured first-page event/market counts, inspected keyset pagination and one nested market schema.
- Evidence: `reports/data_quality/EXP-20260830-phase1-schema-recon.md`.
- Deviations: None. Raw payloads remained temporary because the production immutable-envelope client is not yet implemented.
- Blockers: Full-page coverage and historical closed/resolved discovery remain unmeasured.
- Next action: Implement and test the production read-only market discovery client.

### 2026-08-30 — Phase 1 discovery client contract implemented

- Previous status: `IN_PROGRESS`
- New status: `IN_PROGRESS`
- Work completed: Implemented public keyset pagination, point-in-time raw envelope, atomic immutable persistence, strict event/market/outcome normalization, reason-code exclusions, sanitized fixtures and contract tests.
- Evidence: `src/weather_quant/ingestion/polymarket_markets.py`, `tests/test_polymarket_markets.py`, `tests/fixtures/gamma_highest_temperature_page.json`, `configs/polymarket_discovery.json`.
- Verification: 9/9 unit and smoke tests passed; JSON configs/fixtures parsed; Python compile and diff checks passed.
- Deviations: None. The implementation intentionally uses the Python standard library to avoid introducing a runtime dependency before dependency locking is finalized.
- Blockers: Full active and closed/resolved pagination has not yet been executed.
- Next action: Execute complete active keyset discovery and generate measured coverage artifacts.

### 2026-08-30 — Full active/not-closed inventory measured

- Previous status: `IN_PROGRESS`
- New status: `IN_PROGRESS`
- Work completed: Added the versioned discovery runner, traversed all active/not-closed keyset pages, persisted immutable raw envelopes, normalized events/markets/outcomes and summarized exclusions.
- Evidence: `reports/data_quality/EXP-20260830-phase1-active-inventory.md`; local run `20260829T214842Z`.
- Verification: 2 pages, 136 events, 0 duplicate IDs, 51 cities, 1,496 markets; 1,100 eligible and 396 excluded under the registered contract.
- Deviations: None. Raw and interim payloads remain Git-ignored as required.
- Blockers: Closed/resolved inventory and manual reconciliation remain pending.
- Next action: Execute and characterize the closed=true keyset inventory.

### 2026-08-30 — Closed inventory run exposed normalization coupling

- Previous status: `IN_PROGRESS`
- New status: `IN_PROGRESS`
- Work completed: Traversed 83 closed-history pages and measured 8,222 events, 54 cities, 89,536 markets, date coverage and 370 MB raw scale.
- Evidence: `reports/data_quality/EXP-20260830-phase1-closed-inventory-attempt.md`; local raw run `20260829T215025Z`.
- Invalidated result: Historical `outcome_count=0` from the first run must not be used; event/market/page/date/storage counts remain valid.
- Correction: Separated historical `identifier_complete` from current `eligible_for_book_collection`; added expired-market outcome retention regression test.
- Blockers: Corrected closed summary and full settlement-field coverage remain pending.
- Next action: Commit correction and rerun closed history to a new immutable run ID.

### 2026-08-30 — Corrected closed inventory and settlement coverage measured

- Previous status: `IN_PROGRESS`
- New status: `IN_PROGRESS`
- Work completed: Reran the complete closed history under the corrected contract and measured identifier plus settlement-field coverage.
- Evidence: `reports/data_quality/EXP-20260830-phase1-closed-inventory.md`; local raw run `20260829T215446Z`.
- Verification: 83 pages, 8,222 events, 89,536 markets and 0 duplicates reproduced; 89,514 identifier-complete markets generated 179,028 outcomes.
- Deviations: None. The earlier outcome metric remains invalidated and linked.
- Blockers: Missing source/status cohorts and ≥20 manual reconciliations remain pending.
- Next action: Generate anomaly cohorts and a stratified manual reconciliation sample.

### 2026-08-30 — Closed anomaly cohorts extracted and audit queue selected

- Previous status: `IN_PROGRESS`
- New status: `IN_PROGRESS`
- Work completed: Added deterministic closed-event classification, measured overlap-aware event/market cohorts and selected a fixed-seed 20-event manual reconciliation queue.
- Evidence: `reports/data_quality/EXP-20260830-phase1-closed-anomaly-cohorts.md`, `reports/data_quality/EXP-20260830-phase1-closed-audit-sample.json`.
- Verification: All 8,222 events classified; 20 unique sample IDs; every registered anomaly type represented; 13 tests pass.
- Deviations: The identifier-incomplete event cohort contains only two events, below its target of three; both were included and the remaining slot was filled deterministically. This is a population constraint, not a post-hoc threshold change.
- Blockers: The 20 selected records have not yet been manually reconciled.
- Next action: Reconcile the selected queue against source metadata and resolution pages.

### 2026-08-30 — Phase 1 manual reconciliation gate passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `PASSED`; Phase 2 is now `IN_PROGRESS`.
- Work completed: Retrieved fresh public Gamma and dated Wunderground snapshots for the fixed queue; checked identifier lineage, parsed rule/station/unit/date, identified exact terminal winners and compared them with displayed daily highs.
- Evidence: `reports/data_quality/EXP-20260830-phase1-manual-reconciliation.md`, `reports/data_quality/EXP-20260830-phase1-manual-reconciliation-v2.json`; local raw run `run=20260830T-reconciliation-v2`.
- Verification: 12/20 records reconciled across 12 cities, exceeding the ≥10/≥3 gate; 0 fetch failures; 0 critical identity mismatches among retained records; 18 tests pass.
- Exclusions: 3 missing source, 3 non-terminal/cancelled and 2 source/outcome mismatch records receive hard exclusion dispositions.
- Blockers: None for Phase 1. Historical forecast-as-issued, prospective L2 and the full experiment gate remain pending in later phases.
- Next action: Define the Phase 2 versioned resolution-rule/station registry schema.

### 2026-08-30 — Phase 2 resolution registry contract defined

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`
- Work completed: Added JSON Schema `0.1.0`, fail-closed semantic validation, sanitized record fixture and tests for rule hash, timezone, local-day semantics, identifier requirements and exhaustive discrete buckets.
- Evidence: `reports/data_quality/EXP-20260830-phase2-resolution-registry-contract.md`.
- Verification: 5 focused registry tests and 23 total repository tests pass; schema and fixture parse as JSON.
- Deviation/failure memory: First test run failed on an incorrect hand-written fixture hash and an insufficiently invalid timezone example; both test inputs were corrected without changing the contract or acceptance gate.
- Blockers: Sample population, independent timezone/station cross-check and city-family revision detection remain pending.
- Next action: Populate candidate registry records for the fixed 20-event sample.

### 2026-08-30 — Phase 2 candidate registry populated

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`
- Work completed: Implemented deterministic rule/bucket parsing, isolated station-timezone candidates in config and emitted all 20 fixed-sample records under schema `0.1.0`.
- Evidence: `reports/data_quality/EXP-20260830-phase2-resolution-registry-population.md`, `reports/data_quality/EXP-20260830-phase2-resolution-registry-candidate.jsonl`.
- Verification: 20 records, 161 buckets, 20 exact rule hashes, 12 structurally complete station-unverified candidates and 8 preserved hard exclusions; repeat output was byte-identical; 26 tests pass.
- Deviations: Initial implementation would have carried the 12 Phase 1 matches directly as `RECONCILED`; before commit this was tightened to `CANDIDATE_STATION_UNVERIFIED` because timezone values have not yet been independently sourced.
- Blockers: Authoritative station/timezone verification and city-family revision analysis remain pending.
- Next action: Verify the 12 candidate station/timezone mappings and promote only supported records.

### 2026-08-30 — Phase 2 station identity and timezone verification completed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`
- Work completed: Retrieved current AviationWeather metadata for 12 ICAO codes, resolved coordinates against Timezone Boundary Builder/IANA 2026c geometry and merged-name metadata, and applied a station-name/source-code semantic review.
- Evidence: `reports/data_quality/EXP-20260830-phase2-station-timezone-verification.md`, `reports/data_quality/EXP-20260830-phase2-station-timezone-evidence.json`.
- Verification: 12/12 ICAO records returned; 12/12 proposed timezones matched directly or through release-declared equivalence; 11/12 station identities passed; 11 records promoted and 9 total records remain hard excluded; 28 tests pass.
- Unexpected finding: Karachi rule text names Masroor Airbase while its source code OPKC identifies Karachi/Jinnah Intl; it was rejected despite valid code/timezone.
- Blockers: City-family rule/station revision analysis and DST/local-date tests remain pending.
- Next action: Complete revision and DST checks, then evaluate Phase 2 exit.

### 2026-08-30 — Phase 2 revision/DST gate passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `PASSED`; Phase 3 is now `IN_PROGRESS`.
- Work completed: Scanned all 8,222 closed events for station/unit/template revisions, corrected NWS query-parameter station parsing, and added IANA local-day DST duration tests.
- Evidence: `reports/data_quality/EXP-20260830-phase2-rule-family-dst.md`, `reports/data_quality/EXP-20260830-phase2-rule-family-revisions.json`.
- Verification: 7,321 complete parses, 901 explicit incomplete records, two station transitions, zero unit transitions, 52 multi-template cities; Toronto 23/25-hour and Kuala Lumpur 24-hour tests; 31 total tests pass.
- Invalidation: Initial 46-city station-change count was caused by parsing `timeseries` instead of NWS `site` query values. It was discarded and replaced by the corrected two-city result before commit.
- Gate: 11 retained cities exceed ≥3; retained critical completeness is 100%.
- Next action: Define Phase 3 CLOB order-book snapshot contract and measure public REST coverage.

### 2026-08-30 — Phase 3 public REST book coverage measured

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`
- Work completed: Added public read-only `/book` and dynamic tick clients, immutable envelopes, snapshot schema, level validation and a deterministic three-event/all-token runner.
- Evidence: `reports/data_quality/EXP-20260830-phase3-rest-orderbook-contract.md`, `reports/data_quality/EXP-20260830-phase3-rest-book-coverage.json`; local raw run `run=20260830T-phase3-rest-v3`.
- Verification: 66/66 tokens, 0 failures, 48 two-sided, 18 one-sided, 0 empty/crossed, 3,828 valid levels, 0 dynamic-tick violations; 35 tests pass.
- Invalidation: V1's 190 static-tick violations are invalid because Gamma metadata did not reflect dynamic CLOB tick changes. V2 fetched the current tick per token; 8/66 differed from Gamma.
- Blockers: WebSocket state/reconnect recovery and the 24-hour stability gate remain pending.
- Next action: Implement WebSocket capture and forced reconnect with REST reconciliation.

### 2026-08-30 — Phase 3 WebSocket forced reconnect passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`
- Pre-registered threshold: Full books for both assets on both connections; reconnect ≤15 seconds; no reconnect delta before base; fresh REST same hash or same best bid/ask.
- Work completed: Added public market-channel capture, immutable raw frame envelope/schema, fail-closed per-connection recovery state and an intentional disconnect/resubscribe probe.
- Evidence: `reports/data_quality/EXP-20260830-phase3-websocket-recovery.md`, `reports/data_quality/EXP-20260830-phase3-websocket-recovery.json`; local raw run `run=20260830T-phase3-reconnect-v1`.
- Verification: 2/2 initial books on both connections; 0.416/0.341-second recovery; zero base-before-delta; REST hash and top match 2/2; 39 tests pass.
- Limitation: No live delta or tick-change arrived during this short run, so delta replay and the 24-hour stability gate remain pending.
- Next action: Add heartbeat, delta application, REST anchoring and run a bounded shakeout before the 24-hour capture.

### 2026-08-30 — Phase 3 heartbeat/delta shakeout passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`
- Pre-registered threshold: 12/12 bases, ≥3 PING, ≥2 PONG, ≥1 applied change, zero delta-before-base/top mismatch and REST reconciliation ≥90%.
- Work completed: Added 10-second application heartbeat, Decimal price-level replay, atomic batch top validation, size-zero deletion, liquid-token selection and concurrent final REST anchors.
- Evidence: `reports/data_quality/EXP-20260830-phase3-websocket-shakeout.md`, `reports/data_quality/EXP-20260830-phase3-websocket-shakeout-v1.json`; local raw run `run=20260830T-phase3-shakeout-v1`.
- Verification: 12/12 bases, 3 PING/PONG, 39 delta events, 78 changes, zero contract violations, 12/12 exact REST hash/top matches and 43/43 valid frame checksums; 40 tests pass.
- Limitation: 35 seconds does not evaluate 24-hour uptime, long reconnects, stale state or daily storage; tick change was not observed.
- Next action: Build resumable stability runner and begin the registered 24-hour capture.

### 2026-08-30 — Phase 3 stability runner readiness passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`
- Work completed: Added restart-safe connection files, atomic summaries, 60-second-ready coverage, useful-uptime accounting, exponential reconnect, periodic concurrent REST anchors and storage/gap counters.
- Evidence: `reports/data_quality/EXP-20260830-phase3-stability-runner-smoke.md`; local ignored smoke and resume-smoke runs.
- Verification: 25-second probe produced 12/12 bases, 36 delta events, 24/24 REST matches and 4/4 ready checkpoints; a forced termination resumed with a new connection and 12 new bases. Both correctly failed the immutable 86,400-second gate due to duration.
- Metric lock: useful uptime ≥99%, ready checkpoint coverage ≥95%, elapsed ≥86,400 seconds and zero delta-before-base/replayed-top violations.
- Next action: Start the production 24-hour stability capture with 12 assets, 60-second checkpoints and 300-second anchors.

### 2026-08-30 — Phase 3 production 24-hour stability capture started

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`; capture status `RUNNING`.
- Run: `run=20260830T1145Z-phase3-stability-24h-v1`; start `2026-08-30T11:44:58Z`; target end `2026-08-31T11:44:58Z`.
- Locked parameters: 12 assets, 86,400 seconds, 60-second checkpoints, 300-second REST anchors, 15-second base timeout and 30-second maximum exponential reconnect backoff.
- First checkpoint: useful uptime 99.4699%, ready coverage 1/1, 82 price-change events, 164 applied changes, 5/5 PING/PONG and zero reconnect/error/contract violation.
- Local evidence: `data/raw/polymarket_ws/run=20260830T1145Z-phase3-stability-24h-v1`, `data/interim/polymarket_ws/stability-24h-v1.json`; raw/interim files remain git-ignored.
- Limitation: No gate decision is allowed before the target duration completes; first REST anchor was not yet due at this checkpoint.
- Next action: Monitor checkpoints/process health and evaluate the locked gate after completion.

### 2026-08-31 — Phase 3 first long run invalidated by host sleep

- Previous phase status: `IN_PROGRESS`; capture status `RUNNING`.
- New phase status: `IN_PROGRESS`; capture classification `HOST_SLEEP_CONTAMINATED_INTERRUPTED`.
- Evidence: macOS power log confirmed multiple sleep intervals during the run. At controlled interruption the snapshot had 37,015 elapsed seconds, 82.14% useful uptime, 98.64% observed-checkpoint coverage and 99.789% REST anchor match.
- Raw replay: 27 connection files, 69,461 frames and 16,936 advertised-top mismatches; concentration Toronto 11,394 and Panama City 5,542, with Mexico City zero.
- Metric invalidation: Observed-checkpoint coverage omitted wall-clock slots missed while the host was suspended and therefore cannot be used as the registered coverage metric.
- Additional failure: Late reconnects received only 6/12 full books, so fixed token lifecycle/availability must be checked separately from transport recovery.
- Evidence artifact: `reports/data_quality/EXP-20260830-phase3-stability-host-sleep-analysis.md`, `reports/data_quality/EXP-20260830-phase3-stability-host-sleep-analysis.json`.
- Next action: Collector remediation followed by 15-minute caffeinated regression and one-hour soak.

### 2026-08-31 — Phase 3 remediated 15-minute regression passed

- Previous phase status: `IN_PROGRESS`.
- New phase status: `IN_PROGRESS`; remediation regression `PASSED`.
- Remediation: Wall-clock slot denominator and final boundary accounting; missed-slot metric; non-blocking REST anchor tasks; market-end horizon guard; advertised-top mismatch marks state desynchronized and forces fresh-base recovery.
- Invalidation: v2 completed economically clean but reported 14 rather than 15 scheduled slots at 900 seconds. It was not accepted; v3 reran after final-slot correction.
- Evidence: `reports/data_quality/EXP-20260831-phase3-collector-regression-15m.md`; local run `run=20260830T2224Z-phase3-regression-15m-v3`.
- Verification: 900.068 seconds, useful uptime 99.9592%, 15/15 ready, 0 missed slot, 0 reconnect/error/base/top violation, 24/24 REST anchor match and 89/89 heartbeat/PONG.
- Next action: One-hour caffeinated soak on the same lifecycle-safe selection/code.

### 2026-08-31 — Phase 3 remediated one-hour soak passed with activity limitation

- Previous phase status: `IN_PROGRESS`.
- New phase status: `IN_PROGRESS`; one-hour soak `PASSED_WITH_ACTIVITY_LIMITATION`.
- Evidence: `reports/data_quality/EXP-20260831-phase3-collector-soak-1h.md`; local run `run=20260831T0045Z-phase3-soak-1h-v1`.
- Verification: 3,600.069 seconds, 99.9915% useful uptime, 60/60 ready slots, zero missed slot/error/reconnect/base/top violation, 132/132 REST anchor match and 359/359 heartbeat/PONG.
- Limitation: Zero price-change events occurred during this quiet selection/hour. Delta behavior is supported by the preceding remediated 15-minute run with 785 events and 1,570 changes, not by the soak alone.
- Decision: The combined active-delta regression and quiet-hour persistence soak authorize a replacement 24-hour gate; they do not pass Phase 3 themselves.
- Next action: Start a remediated caffeinated 24-hour capture with market-end horizon validation.

### 2026-08-31 — Phase 3 remediated replacement 24-hour capture started

- Previous phase status: `IN_PROGRESS`.
- New phase status: `IN_PROGRESS`; capture `RUNNING`.
- Run: `run=20260831T0820Z-phase3-stability-24h-v2`; start `2026-08-31T08:15:51Z`; target `2026-09-01T08:15:51Z`.
- Horizon contract: All 12 selected assets belong to markets ending `2026-09-01T12:00:00Z`, after the target end; runner enforces this before collection.
- Locked runtime: `caffeinate`, 86,400-second gate, 60-second wall-clock slots, 300-second non-blocking anchors, fresh base after any reconnect and fail-closed advertised-top mismatch.
- First six minutes: useful uptime 99.9057%, 6/6 ready, zero missed slot/error/reconnect/base/top violation and 12/12 first-anchor match.
- Limitation: No price changes in the first six minutes; final activity is reported separately and cannot be manufactured.
- Local evidence: `data/raw/polymarket_ws/run=20260831T0820Z-phase3-stability-24h-v2`, `data/interim/polymarket_ws/stability-24h-v2.json`.
- Next action: Evaluate only after the immutable target end.

### 2026-08-31 — Phase 3 replacement v2 invalidated by local network outage

- Previous phase status: `IN_PROGRESS`; capture `RUNNING`.
- New phase status: `IN_PROGRESS`; capture `NETWORK_OUTAGE_CONTAMINATED_INTERRUPTED`.
- Evidence: Local DNS failures began at `2026-08-31T10:26:00Z`. Stop snapshot had 11,463 seconds, 91.4008% useful uptime, 174/190 ready slots, 13 missed slots, 116 connection errors and 160 fail-closed top mismatches.
- Positive diagnostic: All 408 completed REST asset anchors matched; raw evidence spans 117 immutable connection files.
- New bug: Backoff resets immediately after socket connect, so repeated short-lived desync connections caused a reconnect storm after network restoration.
- Evidence artifact: `reports/data_quality/EXP-20260831-phase3-network-outage-v2.md`.
- Next action: Stable-grace backoff, circuit breaker, reason-specific metrics and forced-disconnect recovery regression.

### 2026-08-31 — Phase 3 long gate deferred to managed host

- Previous phase status: `IN_PROGRESS`.
- New phase status: `IN_PROGRESS`; 24-hour subgate `DEFERRED_UNTIL_MANAGED_HOST`.
- Decision: Preserve the registered 86,400-second thresholds and do not infer a pass from the 15-minute/one-hour runs. Further home-laptop reruns are deferred because host sleep and local internet dominate the measured failure surface.
- Available evidence: Active-delta regression and persistence soak passed their own bounded gates; two long attempts are explicitly contaminated and excluded.
- Consequence: No historical executable-L2 or live-readiness claim is authorized. Managed-host stability remains mandatory before paper/live execution work.
- Next action: Resume Phase 4 with locked 365-day operational GEFS coverage.

### 2026-08-30 — Phase 4 NBM/KORD initial archive spike conditionally passed

- Previous phase status: `NOT_STARTED`
- New phase status: `IN_PROGRESS`.
- Pre-registered threshold: Download current and ≥365-day-old actual objects; exact KORD station block must contain mean/SD and 10/25/50/75/90 MaxT-MinT markers with run identity and checksums.
- Work completed: Added immutable NOAA AWS retrieval, station-block/version inventory and checksum reanalysis; downloaded matched 01Z NBP files for 2026-08-30 and 2023-08-31.
- Evidence: `reports/research/EXP-20260830-phase4-nbm-initial-feasibility.md`, `reports/data_quality/EXP-20260830-phase4-nbm-archive-probe-cycle01-v2-analysis.json`; local raw run `run=20260830T-phase4-nbp-v2-cycle01`.
- Verification: Both actual files HTTP 200, 34.72/34.81 MB, distinct/reverified checksums, exactly one KORD block and seven required marker rows; 42 tests pass.
- Invalidation: Historical 00Z lacked KORD temperature rows, but documented/full 01Z carries them; cycle mismatch replaced the false archive-absence interpretation.
- Limitation: Point samples 1,095 days apart do not prove continuous coverage or historical first-publication time; NBM applies directly only to retained KORD/Chicago.
- Next action: Monthly/model-boundary coverage probe and fixed-width KORD probabilistic-value parser.

### 2026-08-30 — Phase 4 NBM sampled coverage and parser passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`; NBM/KORD remains `CONDITIONAL_PASS`.
- Work completed: Probed 37 month-start and 12 model-boundary 01Z objects, investigated the sole missing object across adjacent dates/cycles, and added an exact-station fixed-width MaxT parser/schema.
- Evidence: `reports/research/EXP-20260830-phase4-nbm-coverage-parser.md`, `reports/data_quality/EXP-20260830-phase4-nbm-monthly-boundary-coverage.json`, `reports/data_quality/EXP-20260830-phase4-nbm-kord-parsed-sample.json`.
- Verification: 48/49 HTTP 200, all 12 boundary dates present; 18 parsed MaxT records, zero missing values, monotonic percentiles and explicit run/valid/provenance; 43 tests pass.
- Missingness: 2026-06-01 01Z is 404 while same-day 00/07/13/19Z and adjacent 01Z objects exist; no silent fallback is authorized.
- Next action: Daily 365-day primary/fallback coverage and pre-registered KORD cycle-selection policy.

### 2026-08-30 — Phase 4 KORD 365-day run-selection policy passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`; NBM/KORD remains `CONDITIONAL_PASS`.
- Pre-registered gate: 365 completed dates, primary 01Z ≥99%, cascade coverage 100%, zero transient failures and actual fallback download/checksum/parse.
- Evidence: `reports/research/EXP-20260830-phase4-nbm-daily-policy.md`, `reports/data_quality/EXP-20260830-phase4-nbm-daily-coverage-365d.json`, `reports/data_quality/EXP-20260830-phase4-nbm-fallback-download.json`, `reports/data_quality/EXP-20260830-phase4-nbm-fallback-kord-parsed.json`.
- Verification: Primary 364/365, fallback 1, unavailable 0, zero transient failures; actual 07Z fallback yielded 9 KORD MaxT records with zero missing values; 45 tests pass.
- Policy: 01Z→07Z→13Z→19Z is fixed for object selection, but a fallback is eligible only after its own conservative availability timestamp and remains a separately scored segment.
- Next action: ECMWF Open Data global-provider and rolling-retention feasibility.

### 2026-08-30 — Phase 4 ECMWF Open Data measured

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`; ECMWF is `CONDITIONAL_PASS` prospective and `FAILED` as the direct historical source.
- Pre-registered gate: Three temperature fields, 1 deterministic record each, 50 perturbed records each with exact members 1–50, valid GRIB subsets, and at least 365 days retention for historical use.
- Evidence: `reports/research/EXP-20260830-phase4-ecmwf-open-data.md`, `reports/data_quality/EXP-20260830-phase4-ecmwf-open-data-probe.json`; local raw run `run=20260830T00Z-step24-v1`.
- Verification: Actual deterministic 3-message/1.94 MB and perturbed 150-message/97.50 MB subsets passed SHA-256 and GRIB boundaries; inventory contains all required fields and members. Actual `cf` control did not exist in this index.
- Retention: Date offsets 0/1/2 returned HTTP 200; 3/4/7/30/365 returned HTTP 404. The ≥365-day historical gate failed.
- Consequence: ECMWF Open Data may be collected prospectively, but cannot be backfilled as-issued from this surface and cannot be replaced by reanalysis.
- Next action: GEFS public historical archive feasibility under the same point-in-time contract.

### 2026-08-30 — Phase 4 GEFS initial operational archive gate passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`; GEFS operational archive is `CONDITIONAL_PASS`.
- Pre-registered gate: Current and ≥365-day-old operational runs; exact c00+p01–p30 set; one 2 m TMP/TMAX/TMIN record per member; real c00/p01/p30 range downloads with HTTP 206, GRIB integrity and SHA-256. Reforecast did not count.
- Evidence: `reports/research/EXP-20260830-phase4-gefs-initial-feasibility.md`, `reports/data_quality/EXP-20260830-phase4-gefs-operational-archive-probe.json`; local raw run `run=20260830T-phase4-gefs-v1`.
- Verification: Three run dates at ages 0/365/2,166 days each had 31/31 complete members. Nine actual subsets contained 27 valid GRIB messages. Full-member object availability was run+3.91–4.45 hours.
- Storage: One f024 run's three required fields totaled 54.31–65.18 MB versus 464.69–577.68 MB for full member objects.
- Limitation: Three point samples do not establish daily continuity, local-day multi-step MaxT construction or version-boundary stability.
- Next action: Locked 365-day daily coverage and local-day TMAX step semantics.

### 2026-08-31 — Phase 4 GEFS 365-day representative continuity passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`; GEFS remains `CONDITIONAL_PASS`.
- Pre-registered gate: Locked 2025-08-31–2026-08-30 window; 00Z/f024 c00/p01/p30; ≥99% of 1,095 indexes with exact 2 m TMP/TMAX/TMIN and zero terminal transport failures after bounded retry.
- Evidence: `reports/research/EXP-20260831-phase4-gefs-daily-coverage.md`, `reports/data_quality/EXP-20260831-phase4-gefs-daily-coverage-365d.json`.
- Verification: 365/365 complete dates and 1,095/1,095 complete indexes (%100). Three transient connection errors recovered on attempt two; terminal failures and missing dates were zero.
- Limitation: Representative members do not prove 31/31 daily coverage; local-day MaxT and model-version boundaries remain unresolved.
- Next action: Lock local-day TMAX step semantics for one DST and one non-DST city.

### 2026-08-31 — Phase 4 GEFS exact local-day TMAX gate failed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`; GEFS remains `CONDITIONAL_PASS` with a narrowed feature-only contract.
- Pre-registered gates: Every f003 step must be an independent `(step-3)-step` maximum; selected windows must exactly partition Toronto/CYYZ and Kuala Lumpur/WMKK local days with zero gap and outside-local seconds.
- Evidence: `reports/research/EXP-20260831-phase4-gefs-local-day-semantics.md`, `reports/data_quality/EXP-20260831-phase4-gefs-local-day-semantics.json`; local raw run `run=20260831T-local-day-v2`.
- Result: Gate A failed because metadata alternates 3h partial and 6h canonical windows. The f006/f012/... canonical series was consecutive. Gate B failed: both 24h local days had zero uncovered time but six hours outside-local contamination.
- Integrity: Ten actual TMAX ranges totaling 4,259,526 bytes passed HTTP 206, one-message and GRIB/7777 controls.
- Failure memory: The first probe mixed partial and canonical windows. It is preserved as `-attempt1`; canonical-only selection produced the final artifact without changing thresholds.
- Decision: Never use raw interval TMAX as a resolution-equivalent daily label. Permit only provenance-bearing interior/overlap predictors pending station-outcome calibration.
- Next action: Phase 5 CYYZ/WMKK observation coverage and revision semantics.

### 2026-08-31 — Phase 5 Wunderground observation spike passed

- Previous phase status: `NOT_STARTED`
- New phase status: `IN_PROGRESS`.
- Pre-registered gate: 24 fixed pages across CYYZ/WMKK; every HTTP, station/date/timezone, Celsius high, observation and repeatability check must pass with zero terminal transport failures.
- Evidence: `reports/research/EXP-20260831-phase5-wunderground-observation-spike.md`, `reports/data_quality/EXP-20260831-phase5-wunderground-observation-spike.json`; local raw `run=20260831T-phase5-spike-v1`.
- Verification: 24/24 complete and first-attempt responses; daily high equaled maximum parsed observation temperature on 24/24 pages. CYYZ had 24–41 and WMKK 41–50 observations/day.
- Evidence boundary: Pages are current/final historical views, not snapshots from the rule's next-day freeze time.
- Next action: Locked 365-day coverage for each station.

### 2026-08-31 — Phase 5 CYYZ/WMKK 365-day current/final coverage passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`.
- Pre-registered gate: 365 pages/station, ≥99% complete coverage, zero terminal transport failures, 100% identity among available pages and 100% daily-high/observation-max agreement.
- Evidence: `reports/research/EXP-20260831-phase5-wunderground-observation-coverage-365d.md`, `reports/data_quality/EXP-20260831-phase5-wunderground-observation-coverage-365d.json`; local raw `run=20260831T-phase5-coverage-365d-v1`.
- Verification: CYYZ and WMKK each passed 365/365 complete pages and identity/high reconstruction; six transient requests recovered on attempt two, terminal failures zero.
- Anomaly: CYYZ 2026-03-08 contains only two observations versus 44/24 on adjacent days. The registered gate remains passed, but this date is post-hoc flagged `SUBDAILY_INCOMPLETE_SUSPECTED` and cannot support a full intraday reconstruction claim.
- Evidence boundary: Current/final calibration labels passed; market-freeze-as-of settlement evidence did not.
- Next action: Investigate the CYYZ anomaly with an independent station source and market settlement.

### 2026-08-31 — Phase 5 CYYZ anomaly diagnostic v1 failed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`.
- Registered result: `FAILED`; ECCC `LOCAL_DATE` produced 24 rather than 23 civil-DST rows and maximum 12.1°C did not match the current Wunderground 9°C page.
- Unexpected settlement evidence: Structured scan found exact event 249630 and terminal winner `10°C or higher`; the current Wunderground page is inconsistent with settlement.
- Failure memory: `reports/data_quality/EXP-20260831-phase5-cyyz-20260308-anomaly-attempt1.json`.
- Next action: Correct only the ECCC time filter to IANA civil UTC boundaries and preserve all three source values in v2.

### 2026-08-31 — Phase 5 CYYZ corrective forensic diagnostic passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`; Wunderground label validity is downgraded.
- Correction: ECCC `UTC_DATE` was filtered through the event-effective `America/Toronto` half-open civil-day interval; no source values or original failed thresholds were rewritten.
- Evidence: `reports/research/EXP-20260831-phase5-cyyz-20260308-anomaly.md`, final and `-attempt1` JSON artifacts; local raw `run=20260831T-cyyz-anomaly-v2`.
- Result: 23/23 civil hours, official max 12.1°C, exact event 249630 and terminal winner `10°C or higher`. ECCC matched the winner; current Wunderground 9°C mismatched.
- Decision: Quarantine the date as `HISTORICAL_PAGE_DIVERGED_FROM_SETTLEMENT`; page availability can no longer imply label validity.
- Next action: Fixed ≥10-event/≥3-city divergence audit before Phase 5 exit.

### 2026-08-31 — Phase 5 fixed settlement-divergence audit passed

- Previous phase status: `IN_PROGRESS`
- New phase status: `IN_PROGRESS`; only the registered sample observation/settlement subgate passed.
- Primary evidence: Fixed 20-event cohort had 14 eligible records, 12 matches across 12 cities, two divergences across two cities, six ineligible records and zero unresolved eligible records. Divergence was 14.29% with Wilson 95% CI 4.01%–39.94%.
- Sensitivity: Adding the anomaly-selected CYYZ sentinel produced 3/15 divergence (20.00%, Wilson 95% CI 7.05%–45.19%); this is not a population estimate.
- Label result: Terminal Polymarket outcome was available for 14/14 eligible fixed records, but exact-temperature eligibility was 0/14 because no freeze-time page/version was preserved.
- Failure memory: `-attempt1` conflated bucket and temperature eligibility; `-attempt2` conflated page divergence with terminal-label availability. Both artifacts remain superseded and auditable.
- Evidence: `reports/research/EXP-20260831-phase5-wunderground-settlement-audit.md` and final plus two attempt JSON artifacts.
- Next action: Pre-register KORD/Chicago 365-day official observation, revision/final semantics and settlement join as the third-city evidence package.

### 2026-08-31 — KORD/LCDv2 observation package pre-registered

- Phase status remains `IN_PROGRESS`.
- Locked window: 2025-08-31–2026-08-30, 365 completed Chicago local dates.
- Locked source: NOAA NCEI LCDv2 annual files for GHCN `USW00094846`; KORD/O'Hare identity, response metadata and immutable checksums are mandatory.
- Acceptance: ≥99% exact-date and non-null daily-maximum coverage, zero duplicates, 100% admitted-row identity and zero terminal transport failures.
- Evidence boundary: LCDv2 is an independent official diagnostic, not the Wunderground settlement source. Current annual-object Last-Modified does not reconstruct the market's historical freeze-time version.
- Next action: Implement the smallest parser/probe, contract tests and immutable result artifact.

### 2026-08-31 — KORD/LCDv2 latest-365 coverage failed

- Phase status remains `IN_PROGRESS`.
- Registered result: `FAILED`; exact-date and non-null daily-maximum coverage were both 356/365 (97.53%), below ≥99%.
- Missingness: Nine consecutive trailing dates, 2026-08-22–2026-08-30. The observed 2026 object was last modified on 2026-08-26 but ended at SOD 2026-08-21, indicating publication lag rather than random station gaps.
- Passed checks: zero duplicate dates, zero identity failures, zero terminal transport failures; admitted maximum range −15.0°C to 35.6°C.
- Sentinel: Event 553903 LCDv2 maximum 27.2°C / 80.96°F was consistent with terminal `68°F or higher`; interpretation remains forensic only.
- Revision result: `HISTORICAL_FREEZE_AS_OF_UNRESOLVED`; annual-object metadata does not reconstruct historical versions.
- Evidence: final and `-attempt1` JSON artifacts, research report and local immutable raw v2 run; 69 tests passed.
- Next action: Pre-register lag-safe historical coverage with a ≥30-day as-of buffer and a publication-lag metric.

### 2026-08-31 — KORD/LCDv2 lag-safe coverage pre-registered

- Phase status remains `IN_PROGRESS`.
- Locked window: 2025-07-23–2026-07-22, exactly 365 dates and a 40-day analysis-time buffer.
- Parser, station identity and ≥99% thresholds are unchanged from the failed latest-window test.
- Passing is limited to final archive coverage; decision-time and settlement-freeze availability remain unresolved by construction.
- Next action: Extend only the artifact's publication-lag metadata, rerun under a new immutable raw run and apply the registered gate.

### 2026-08-31 — KORD/LCDv2 lag-safe final archive coverage passed

- Phase status remains `IN_PROGRESS`.
- Registered result: `PASSED` for final archive coverage; 365/365 exact dates and non-null maxima, zero duplicates, identity failures and terminal transport failures.
- Value range: −15.0°C–35.6°C; no missing values or imputation.
- Lag proxy: The observed 2026 annual object Last-Modified was five calendar days after its final SOD date. This is object-level freshness metadata, not row-level first-publication or revision history.
- Decision: Assign `FINAL_ARCHIVE_COVERAGE_PASS` and retain `INDEPENDENT_FINAL_DIAGNOSTIC_ONLY`; the failed latest-365 result remains unchanged.
- Evidence boundary: `HISTORICAL_FREEZE_AS_OF_UNRESOLVED`; final completeness does not prove decision-time availability.
- Evidence: JSON artifact, research report and local immutable raw run; 69 tests and Ruff passed.
- Next action: Build and test an append-only prospective KORD Wunderground freeze snapshot contract without launching a persistent collector.

### 2026-09-02 — Prospective Wunderground freeze snapshot contract pre-registered

- Phase status remains `IN_PROGRESS`.
- The exact qualification checks, immutable raw/manifest schema, idempotency and changed-content revision behavior were locked before implementation.
- The test cohort is synthetic KORD fixture data; no claim about live settlement reconstruction or uptime is authorized.
- Next action: Implement the smallest writer/verifier/replay module and exercise all fail-closed cases.

### 2026-09-02 — Prospective Wunderground freeze snapshot fixture contract passed

- Phase status remains `IN_PROGRESS`.
- Registered result: `PASSED`; all 12 valid, fail-closed, replay, append-only, idempotency, revision and tamper cases behaved as expected.
- Full suite: 76 tests and Ruff passed.
- Evidence: Module stores content-addressed target/trigger raw pages plus a canonical manifest with event/date/rule/parser/timestamp/checksum and qualification fields.
- Boundary: Synthetic fixture only; no live Wunderground behavior, uptime or historical settlement reconstruction claim. No persistent collector was started.
- Next action: Read-only discovery of one exact-rule upcoming KORD event, followed by a separately preregistered bounded live cohort if available.

### 2026-09-02 — Upcoming exact-rule KORD discovery pre-registered

- Phase status remains `IN_PROGRESS`.
- Complete public Gamma keyset universe, exact candidate gate, deterministic selection and `NOT_AVAILABLE` behavior were locked before retrieval.
- No broad-tag/city substitution, order action or background collector is permitted.
- Next action: Execute one read-only traversal and preserve the raw envelopes plus candidate audit.

### 2026-09-02 — Wunderground-primary KORD live cohort not available

- Phase status remains `IN_PROGRESS`.
- Inventory: two keyset pages, 150 events, zero duplicates and 51 cities; three Chicago events, two observed-future, all three identity-complete.
- Registered result: zero Wunderground-primary qualified KORD events, `NOT_AVAILABLE`; no event or city replacement occurred.
- Regime evidence: Events 940517, 946566 and 952456 use NOAA WRH KORD as primary; Wunderground appears only as fallback. Historical event 553903 was Wunderground-primary.
- Decision: Version the provider boundary and do not apply the Wunderground freeze collector as primary evidence to the current Chicago regime.
- Evidence: Discovery JSON, research report and ignored immutable raw run; 79 tests and scoped Ruff passed.
- Next action: Read-only NOAA WRH KORD surface discovery and preregistration of a source-specific prospective contract.

### 2026-09-02 — NOAA WRH KORD source discovery pre-registered

- Phase status remains `IN_PROGRESS`.
- Official-origin scope, two-request stability check, machine-readable semantic gate, following-date trigger requirement and revision boundary were locked before inspecting the live page/data calls.
- No polling, credentials, orders or third-party weather substitution are permitted.
- Next action: Retrieve the declared page twice, identify first-party data calls and apply the registered semantic gate.

### ED-0006 — 2026-08-30 — Separate historical identity from current book eligibility

- Decision: Historical outcome-token normalization depends on identifier integrity, not whether an event is currently eligible for book collection.
- Evidence available at decision time: The first closed run correctly found all events expired but incorrectly emitted zero historical outcome rows despite inspected records containing valid condition IDs and CLOB token mappings.
- Alternatives considered: Treat closed history only as event metadata; rejected because settlement and future historical-price joins require outcome-token identity.
- Consequence: Normalized market records expose both `identifier_complete` and `eligible_for_book_collection`; closed history is rerun before further coverage claims.
- Revisit condition: None; these concepts remain permanently distinct.

### ED-0007 — 2026-08-30 — Separate event-level and market-level anomaly prevalence

- Decision: Report status/identifier anomaly counts at their native grain and preserve cohort intersections; never add overlapping event cohorts or present market counts as event prevalence.
- Evidence available at decision time: 22 identifier-incomplete markets occur in only 2 events, and 80 non-UMA-resolved markets occur in 19 events; 54 events simultaneously lack close time and automatic resolution.
- Alternatives considered: Keep only raw market counts; rejected because it overstates independent event prevalence and obscures concentration.
- Consequence: Manual audit selection operates on unique events while retaining their anomalous market rows.
- Revisit condition: None; grain-aware reporting is a permanent integrity rule.

### ED-0008 — 2026-08-30 — Do not infer observed labels from terminal prices alone

- Decision: A terminal-looking Gamma outcome is not a valid weather label unless it reconciles with a declared resolution source and rule. Missing source, non-terminal/cancelled state and source/outcome mismatch are hard exclusion states.
- Evidence available at decision time: 12/20 sampled events reconciled; Dallas May 19 and Munich May 19 had exact terminal winners that materially contradicted the linked source daily high. Three events lacked a source and three lacked a sole exact terminal winner.
- Alternatives considered: Treat exact `[1,0]` outcome prices as ground truth; rejected because two sampled counterexamples would create mislabeled training/backtest rows.
- Consequence: Resolution registry and future datasets require independent source reconciliation and explicit disposition before a realized label is admitted.
- Revisit condition: Only a documented platform correction/re-resolution workflow that explains and versions these discrepancies.

### ED-0009 — 2026-08-30 — Make resolution eligibility a versioned fail-closed contract

- Decision: `RECONCILED` registry records require complete source/station/timezone/unit/window/rounding/rule-hash/bucket/provenance fields. Incomplete records remain representable only as explicit `NO_TRADE` dispositions.
- Evidence available at decision time: Phase 1 found missing sources, non-terminal records and source/outcome mismatches that would become silent label errors under a nullable best-effort table.
- Alternatives considered: Store a sparse registry and filter ad hoc in each analysis; rejected because filters could diverge and admit unsafe labels.
- Consequence: All downstream forecast joins/backtests must consume validated registry versions, not raw event metadata directly.
- Revisit condition: Schema version increments may add fields, but may not weaken fail-closed eligibility without a new documented decision.

### ED-0010 — 2026-08-30 — Separate structurally complete candidates from verified registry labels

- Decision: A record with a parsed IANA timezone proposal is `CANDIDATE_STATION_UNVERIFIED`, not final `RECONCILED`, until station identity/timezone evidence is independently recorded.
- Evidence available at decision time: The 12 Phase 1 matches parse cleanly, but their timezone mapping originated from a hand-maintained candidate config rather than an authoritative station metadata artifact.
- Alternatives considered: Promote immediately because all IANA names exist in `zoneinfo`; rejected because syntactic validity does not prove the station-to-timezone mapping.
- Consequence: Candidate records pass full structural validation but carry `STATION_TIMEZONE_UNVERIFIED` and remain excluded from backtests/trading.
- Revisit condition: Promotion occurs record-by-record after primary-source evidence is persisted.

### ED-0011 — 2026-08-30 — Require semantic station identity, not only a valid ICAO code

- Decision: Promotion requires rule station name and source ICAO identity to be semantically consistent in addition to metadata/timezone validity.
- Evidence available at decision time: Karachi rule text says Masroor Airbase, while source code OPKC resolves in current AviationWeather metadata to Karachi/Jinnah Intl.
- Alternatives considered: Trust the source URL code over prose; rejected because the resolution rule itself defines the intended station and ambiguity can change the realized maximum.
- Consequence: Karachi becomes `NO_TRADE_AMBIGUOUS_RULE`; 11 of 12 candidates are promoted.
- Revisit condition: A versioned Polymarket correction or authoritative resolution record explicitly disambiguates which station controlled that event.

### ED-0012 — 2026-08-30 — Version station/rule semantics per event, never per city

- Decision: City name is not a stable station/rule key. Every dataset join must use the event-effective station code and exact rule template/hash.
- Evidence available at decision time: Denver changed KDEN→KBKF, Paris changed LFPG→LFPB, and 52/54 city families contain multiple date-normalized rule templates; no unit transitions were observed.
- Alternatives considered: Maintain one current station/rule per city; rejected because it would retrospectively mislabel earlier events and hide provider wording changes.
- Consequence: Registry versions are event-scoped; unknown templates and incomplete parses remain excluded until reconciled.
- Revisit condition: None; historical point-in-time correctness permanently requires event-scoped versioning.

### ED-0013 — 2026-08-30 — Treat tick size as point-in-time dynamic state

- Decision: Validate order levels against the contemporaneous CLOB tick endpoint/WebSocket tick-size events, not Gamma's discovery-time tick metadata.
- Evidence available at decision time: V1 produced 190 apparent violations; public dynamic tick retrieval showed 28 tokens at `0.001`, 38 at `0.01`, and 8/66 values different from Gamma metadata. V2 had zero violations.
- Alternatives considered: Retain Gamma tick as authoritative; rejected because official WebSocket documentation defines tick-size-change events and live observations contradicted it.
- Consequence: Every book snapshot/capture state must version tick size; missing contemporaneous tick is a quality failure.
- Revisit condition: None while dynamic tick changes remain part of the official market protocol.

### ED-0014 — 2026-08-30 — Reset authoritative state at every WebSocket reconnect

- Decision: A reconnect starts with empty per-asset state; no delta becomes usable until that asset receives a new full `book` on the new connection.
- Evidence available at decision time: A forced disconnect recovered both sampled assets in 0.341 seconds, and both recovered hashes matched immediately fetched REST books exactly.
- Alternatives considered: Carry the previous socket's last state through reconnect; rejected because messages lost during disconnection would be undetectable without a sequence contract.
- Consequence: Production capture must persist connection IDs, local sequence and base-before-delta violations, and use REST only as a reconciliation anchor rather than inventing missing deltas.
- Revisit condition: Only a documented server resume/sequence protocol with independently validated gap recovery could relax this rule.

### ED-0015 — 2026-08-30 — Apply price-change batches atomically before top validation

- Decision: Apply every change in one `price_change` event before comparing reconstructed best bid/ask with the event-advertised values; use Decimal prices and delete size-zero levels.
- Evidence available at decision time: The 35-second shakeout applied 78 changes from 39 events with zero advertised-top mismatch and ended with exact REST hashes for all 12 assets.
- Alternatives considered: Validate advertised top after each item in a multi-change event; rejected because the advertised top represents the completed event and creates false intermediate mismatches.
- Consequence: Replay validation is event-batch granular while raw item order remains preserved for audit.
- Revisit condition: Official protocol semantics change or captured counterexamples demonstrate per-item rather than per-event top semantics.

### ED-0016 — 2026-08-30 — Define stability by authoritative-ready time

- Decision: Stability uptime counts only time when every selected asset has a full-book base on the current connection; a merely open socket is insufficient. Coverage is measured independently at scheduled 60-second checkpoints.
- Evidence available at decision time: The 25-second smoke had 25.072 connected seconds but only 24.741 authoritative-ready seconds, exposing startup time that socket-only uptime would hide.
- Alternatives considered: Process uptime or TCP/WebSocket connected time; rejected because both can report health before state is safe to replay or use.
- Consequence: The 24-hour gate requires useful uptime ≥99%, ready-checkpoint coverage ≥95%, elapsed ≥86,400 seconds and zero base/replay contract violations.
- Revisit condition: Only a more conservative metric may supersede this definition; the threshold cannot be relaxed post-hoc.

### ED-0022 — 2026-08-31 — Invalidate host-suspended runs and count scheduled slots

- Decision: Any run with confirmed host sleep is excluded from the stability gate. Coverage denominator is the number of wall-clock checkpoint slots that should have occurred, not only callbacks the process executed.
- Evidence available at decision time: macOS logs confirmed several sleep intervals during the first long run; useful uptime was 82.14% while callback-only ready coverage misleadingly reported 98.64%.
- Alternatives considered: Remove sleep intervals and score the remaining time; rejected post-hoc because the registered gate measures an operational collection system and missed market events cannot be reconstructed.
- Consequence: Future local gates run under `caffeinate`, record host monotonic/wall-clock discontinuities and mark missed slots not-ready. The contaminated raw data remains valid only for failure diagnosis.
- Revisit condition: A managed always-on host replaces laptop execution, with host health measured independently.

### ED-0023 — 2026-08-31 — Fail closed on event-level top disagreement

- Decision: An advertised-top mismatch invalidates the current connection state; do not prune or overwrite local levels to force agreement. Recovery requires a new connection and fresh full book.
- Evidence available at decision time: The contaminated capture produced 16,936 mismatches while most REST anchors matched. The exact missing/implicit delta semantics remain unproven, so silent state repair would fabricate depth.
- Alternatives considered: Trust advertised best bid/ask and delete every contradictory local level; rejected because it changes full depth without an explicit size-zero event and could invent executable liquidity. Ignore mismatch because anchors mostly match; rejected because event-time fills could still be wrong.
- Consequence: Regression/soak fails on any mismatch and reconnects fail closed. A future documented sequence/resume protocol or exact raw+REST proof may refine recovery, but cannot rewrite historical gaps.
- Revisit condition: Primary protocol documentation plus captured counterexamples establish a deterministic, replayable repair rule.

### ED-0024 — 2026-08-31 — Require combined activity and persistence evidence

- Decision: Treat the 15-minute active-delta regression and one-hour quiet persistence soak as complementary evidence; neither alone substitutes for the replacement 24-hour gate.
- Evidence available at decision time: The regression applied 1,570 changes with zero mismatch and 24/24 anchors; the soak maintained 60/60 scheduled slots and 132/132 anchors with zero reconnect/error but observed no price changes.
- Alternatives considered: Reject the soak because it had no deltas; rejected because transport/state persistence was its primary gate and actual market quietness is not collector failure. Declare Phase 3 passed from both short runs; rejected because the registered minimum remains 86,400 seconds.
- Consequence: Replacement 24-hour capture is authorized, while its report must separately show activity, uptime, checkpoint, anchor and lifecycle metrics.
- Revisit condition: The 24-hour run has insufficient activity or exposes a new protocol/lifecycle failure.

### ED-0025 — 2026-08-31 — Defer, do not relax, the long stability gate

- Decision: Move the unchanged 24-hour collector gate to an always-on managed host/VPS milestone; keep Phase 3 open and continue weather-source feasibility in parallel.
- Evidence available at decision time: Short active/persistence contracts passed, while both long local runs were invalidated by independently evidenced host sleep or DNS/internet loss rather than a clean collector-only experiment.
- Alternatives considered: Declare Phase 3 passed from short runs; rejected because it relaxes a pre-registered threshold after results. Keep rerunning on the laptop; rejected because it primarily remeasures host/network instability at low incremental research value.
- Consequence: GEFS/observation/model research may proceed, but execution backtests must expose missing prospective L2 coverage and no live/paper readiness can be claimed.
- Revisit condition: A managed always-on environment and stable network are available for a fresh immutable 24-hour run.

### ED-0017 — 2026-08-30 — Key NBM availability by cycle and version

- Decision: NBM records and coverage tests must key by run date, cycle, product and model version; a missing field in one cycle cannot be generalized to the date/provider.
- Evidence available at decision time: KORD's 2023-08-31 v4.1 00Z NBP block lacked temperature rows, while the same date's documented full 01Z block contained TXNMN, TXNSD and all five percentile rows. The 2026 01Z comparison used v5.0.
- Alternatives considered: Use one daily representative cycle without verifying its field schedule; rejected because it produced a false historical-unavailability conclusion.
- Consequence: Coverage and parser artifacts must segment model upgrades and cycle schedules; backtests cannot silently mix v4.1 and v5.0 as one stationary forecast product.
- Revisit condition: None; point-in-time forecast identity permanently requires run cycle and version.

### ED-0018 — 2026-08-30 — Treat NBM fallback cycles as different information sets

- Decision: A missing primary 01Z object may be replaced only by a pre-declared eligible cycle, with its own run/publication timestamps and a fallback flag; it is never silent imputation.
- Evidence available at decision time: 2026-06-01 01Z is absent while 00/07/13/19Z on the same day exist, and the earlier 00Z/01Z comparison showed that field availability can differ by cycle/version.
- Alternatives considered: Select the nearest available cycle retrospectively; rejected because it changes information time after observing missingness and can introduce selection bias.
- Consequence: A locked daily coverage experiment must quantify primary, fallback and unavailable rates before model scoring; analyses segment fallback records.
- Revisit condition: A provider-published canonical replacement policy can supersede the chosen fallback ordering, but historical timestamps remain mandatory.

### ED-0019 — 2026-08-30 — Freeze KORD canonical cycle order without backdating fallback

- Decision: Canonical daily object order is 01Z→07Z→13Z→19Z, selected without forecast-value inspection. A fallback never inherits the primary timestamp and is ineligible for earlier market snapshots.
- Evidence available at decision time: The locked 365-day window had 364 primary objects and one 07Z fallback; that fallback's object timestamp was 08:15:34Z and its KORD values parsed correctly.
- Alternatives considered: Drop the entire day; retained as a sensitivity baseline but rejected as the sole dataset policy because a valid later forecast exists. Backdate 07Z to primary time; rejected as look-ahead leakage.
- Consequence: Dataset rows carry `PRIMARY`/`FALLBACK`; forecast and EV reports segment them, and point-in-time joins enforce availability ≤ market snapshot.
- Revisit condition: Coverage in another locked regime violates the threshold or official product-cycle semantics change.

### ED-0020 — 2026-08-30 — Scope ECMWF Open Data to prospective collection

- Decision: Treat ECMWF Open Data as a current/prospective global forecast source, never as the direct source for the historical backtest unless a separately verified archive is introduced.
- Evidence available at decision time: Required deterministic and 50-member temperature fields were retrieved from the 2026-08-30 00Z run, but only offsets 0–2 existed and every probe from 3 through 365 days returned HTTP 404; `cf` control was absent from the actual step-24 index.
- Alternatives considered: Use reanalysis or current forecasts to reconstruct past information; rejected because neither proves what was issued and available at the historical decision time.
- Consequence: A global backtest requires another as-issued archive such as verified GEFS or a separately licensed ECMWF historical surface. Any prospective ECMWF collector must retain immutable run/cycle/step/availability provenance.
- Revisit condition: An actual historical ECMWF archive with ≥365-day coverage, access terms and point-in-time timestamps passes an independent probe.

### ED-0021 — 2026-08-30 — Select operational GEFS for the global historical candidate

- Decision: Advance the NOAA operational GEFS archive, not GEFS reforecast/replay, as the primary global historical ensemble candidate; status remains conditional until locked daily coverage and local-day aggregation pass.
- Evidence available at decision time: Operational 00Z f024 objects at ages 0, 365 and 2,166 days each contained c00 plus p01–p30 and one 2 m TMP/TMAX/TMIN field per member. Nine actual range subsets passed HTTP 206, GRIB boundary and checksum controls.
- Alternatives considered: ECMWF Open Data failed historical retention. GEFS reforecast/replay was rejected as a substitute because it was generated retrospectively rather than observed as issued at each historical market decision.
- Consequence: Historical global-source work proceeds with operational GEFS timestamps and immutable member provenance; reforecast may later be a separate climatology/model-development input but never masquerades as as-issued operational data.
- Revisit condition: Locked 365-day coverage fails materially, model boundaries cannot be versioned, or local-day MaxT cannot be reconstructed without leakage.

### ED-0026 — 2026-08-31 — Pass GEFS representative continuity without overclaiming membership

- Decision: Mark the locked 365-day c00/p01/p30 continuity subgate `PASSED`, while retaining GEFS provider status as `CONDITIONAL_PASS` until local-day semantics and broader membership stability are verified.
- Evidence available at decision time: All 1,095 representative 00Z/f024 indexes returned exact 2 m TMP/TMAX/TMIN across 365/365 dates. Three transient resets recovered on the second attempt and no terminal failure remained.
- Alternatives considered: Generalize three members to full 31-member daily completeness; rejected because it exceeds the sampled evidence. Fail the gate for recovered resets; rejected because the pre-registered failure metric was terminal failure after bounded retries.
- Consequence: Local-day valid-time/window semantics become the next smallest gate; historical modeling remains unauthorized until the joined-data gates pass.
- Revisit condition: Full-member sampling, a documented model boundary or local-day reconstruction contradicts the representative result.

### ED-0027 — 2026-08-31 — Restrict GEFS TMAX to contamination-aware features

- Decision: GEFS interval TMAX is not a station-local daily-MaxT label. Retain it only as two explicit predictors: the maximum across three fully contained 6h blocks and the maximum across five overlapping blocks with six outside-local hours recorded.
- Evidence available at decision time: Actual GEFS metadata alternated partial 3h and canonical 6h windows. The canonical series covered both CYYZ and WMKK local days without gaps but could not align their UTC boundaries, adding six outside-local hours. Ten GRIB ranges passed integrity checks.
- Alternatives considered: Call the five-window maximum “daily TMAX”; rejected because it includes another local date. Drop GEFS entirely; deferred because outcome calibration may extract incremental probabilistic value from explicitly tagged predictors.
- Consequence: Feature rows carry interval start/end, run/publish timestamps and outside-local seconds. Phase 5 observations are required before any forecast-skill or EV claim.
- Revisit condition: A provider field or transformation with exact station-local daily windows passes a separately pre-registered test.

### ED-0028 — 2026-08-31 — Separate current/final observations from settlement-as-of evidence

- Decision: Scale the exact Wunderground source to 365-day current/final observation coverage, but never label a page retrieved later as the value visible at Polymarket's next-day revision freeze.
- Evidence available at decision time: All 24 locked pages exposed exact station/date identity, daily high and observations, but retrieval occurred on 2026-08-31 rather than each event's historical freeze timestamp.
- Alternatives considered: Treat the current historical page as immutable settlement truth; rejected because the rule explicitly allows revisions until a defined next-day point. Reject the source entirely; deferred because it remains the exact resolution surface and a useful final calibration label.
- Consequence: Dataset rows carry an evidence class. Prospective next-day snapshots are required for exact settlement-as-of validation.
- Revisit condition: Versioned Wunderground history or another preserved source proves historical values at the applicable freeze timestamps.

### ED-0029 — 2026-08-31 — Pass daily labels while quarantining sub-daily incompleteness

- Decision: Accept CYYZ/WMKK Wunderground daily-high coverage for current/final calibration labels, but quarantine CYYZ 2026-03-08 from claims requiring complete intraday observations.
- Evidence available at decision time: All 730 daily pages passed the registered contract. The sole extreme count anomaly had two CYYZ observations, while adjacent days had 44 and 24; DST produces a 23-hour day but does not explain only two reports.
- Alternatives considered: Fail the entire daily gate; rejected because the source's daily high exists and matches its observed maximum under the pre-registered contract. Ignore the anomaly; rejected because it could bias feature comparison and confidence.
- Consequence: Daily-label and sub-daily-completeness flags remain separate. The anomaly is excluded in sensitivity analysis unless independent evidence resolves it.
- Revisit condition: Independent station records prove complete coverage/value or reveal that Wunderground's displayed high is incorrect.

### ED-0030 — 2026-08-31 — Do not treat ECCC LOCAL_DATE as civil DST time

- Decision: ECCC hourly rows used for Polymarket local-calendar days must be selected by UTC timestamps transformed through the event-effective IANA timezone, not by ECCC `LOCAL_DATE` alone.
- Evidence available at decision time: On Toronto's 2026 spring-forward date ECCC exposed local hours 0–23 with UTC offsets consistent with local standard-time labels, producing 24 rows rather than the civil day's 23 hours.
- Alternatives considered: Force-drop local hour 2; rejected because it edits source labels without an explicit civil-time transform. Use ECCC daily maximum; rejected because official climatological-day boundaries differ from the market's local day.
- Consequence: Corrective v2 filters the half-open civil UTC interval and preserves original ECCC local/UTC fields.
- Revisit condition: ECCC publishes an explicit DST-aware field or revised timestamp contract.

### ED-0031 — 2026-08-31 — Require settlement validation for historical page labels

- Decision: A Wunderground historical page retrieved after settlement is not an eligible model label solely because it has exact identity and a daily high. Eligibility requires terminal-bucket agreement or preserved freeze-time evidence.
- Evidence available at decision time: CYYZ 2026-03-08 current page showed 9°C and two rows, while ECCC civil-day maximum was 12.1°C and terminal Polymarket winner was `10°C or higher`.
- Alternatives considered: Keep 9°C as a current/final label; rejected because it contradicts both independent official data and settlement. Replace all Wunderground labels with ECCC; rejected because provider/time-window semantics differ and WMKK lacks the same source.
- Consequence: CYYZ anomaly is `NO_TRAIN_NO_BACKTEST`; all sampled historical labels undergo event-level settlement reconciliation. Page coverage and valid-label coverage are reported separately.
- Revisit condition: A preserved freeze-time Wunderground snapshot or version history proves the applicable historical value.

### ED-0032 — 2026-08-31 — Reuse the fixed sample and add only the anomaly sentinel

- Decision: Audit the original 20-event stratified cohort without replacement and add event 249630 only as a declared anomaly sentinel; report fixed-sample and sentinel roles explicitly.
- Evidence available at decision time: The original cohort already preserved 12 matches, two source/settlement mismatches and six structurally ineligible events. Event 249630 was discovered through a separately registered anomaly investigation.
- Alternatives considered: Select a fresh set of convenient matching events; rejected because outcome-aware replacement would bias divergence downward. Treat the sentinel as representative; rejected, so it is tagged separately.
- Consequence: Primary counts expose cohort composition and a sensitivity count excluding the sentinel. No divergence is silently dropped.
- Revisit condition: A broader probability sample is preregistered from the full event population.

### ED-0033 — 2026-08-31 — Separate terminal bucket outcomes from exact-temperature labels

- Decision: Treat the verified terminal Polymarket winner as the eligible market-outcome label, while requiring preserved freeze-time evidence before any current historical page can become an exact-temperature label.
- Evidence available at decision time: The fixed cohort produced 12 matches and two divergences among 14 eligible events; all 14 had terminal market labels but none had preserved freeze-time exact-temperature evidence. The anomaly sentinel added a third divergence.
- Alternatives considered: Discard terminal outcomes whenever the current page diverges; rejected because the terminal winner is the market's outcome and remains identified. Promote bucket-consistent current pages to exact temperatures; rejected because consistency within a bucket does not identify the settled numeric value.
- Consequence: The sample settlement subgate passes for bucket-outcome feasibility, Wunderground current pages fail as universal exact-temperature labels, and Phase 5 stays in progress pending third-city observation/revision evidence.
- Revisit condition: Immutable settlement-time snapshots or an authoritative version history reconstruct the exact applicable temperature.

### ED-0034 — 2026-08-31 — Use LCDv2 as an independent diagnostic, not a settlement substitute

- Decision: Test NOAA NCEI LCDv2 for KORD observation coverage and station-level forensic consistency, but never silently replace the event's declared Wunderground rule with NOAA values.
- Evidence available at decision time: NOAA documents LCDv2 as an official hourly/daily airport-station product derived from GHCN sources, while event 553903 explicitly names Wunderground KORD, whole °F and a next-day first-datapoint revision freeze.
- Alternatives considered: Use deprecated LCDv1/ISD files; rejected because NOAA states LCDv1 ended in August 2025 and the locked window crosses that boundary. Treat LCDv2 daily maximum as exact settlement truth; rejected because daily-window and historical version semantics are not yet equivalent.
- Consequence: Coverage can pass while historical freeze-as-of remains unresolved. Exact temperature labels stay ineligible unless version and window equivalence are proven.
- Revisit condition: NOAA/Wunderground provenance or preserved settlement-time snapshots prove exact equivalence.

### ED-0035 — 2026-08-31 — Separate final archive coverage from recent publication latency

- Decision: Treat the failed latest-365 gate as evidence of trailing publication lag, not as a reason to impute the nine missing outcomes or weaken the registered threshold. Test final research-label coverage only in a separately preregistered lag-safe window.
- Evidence available at decision time: KORD LCDv2 represented 356/365 dates with a single nine-day trailing missing block, no internal duplicates or identity failures, and a 2026 object whose last-modified date still preceded the requested window end.
- Alternatives considered: Shift the window post-hoc and report a pass; rejected because it changes the tested cohort after observing the result. Fill recent dates from Wunderground; rejected because that would mix providers and revision semantics.
- Consequence: The latest-365 result remains `FAILED`. A new ≥30-day-buffer experiment may test final archive completeness but cannot establish decision-time or settlement-freeze availability.
- Revisit condition: Prospective repeated retrievals estimate the actual publication-lag distribution or NOAA exposes versioned publication timestamps.

### ED-0036 — 2026-08-31 — Lock a separate 40-day-buffer cohort

- Decision: Evaluate final LCDv2 completeness on 2025-07-23–2026-07-22 as a new preregistered cohort, preserving the failed latest-window result unchanged.
- Evidence available at decision time: The first failure was a contiguous nine-day trailing block and all earlier dates in its window were complete, suggesting a testable publication-lag hypothesis.
- Alternatives considered: Re-label the original window after dropping recent dates; rejected as post-hoc cohort editing. Wait and silently rerun the same artifact; rejected because it would overwrite the observed failure state.
- Consequence: The new result answers only final archive completeness with a 40-day buffer and cannot satisfy point-in-time settlement evidence.
- Revisit condition: None; both cohort results remain in experiment memory.

### ED-0037 — 2026-08-31 — Accept final archive coverage without promoting point-in-time status

- Decision: Mark KORD LCDv2 as passing final archive coverage for the lag-safe cohort while keeping historical freeze-as-of unresolved and the latest-window gate failed.
- Evidence available at decision time: The preregistered lag-safe window had 365/365 observations and no quality failures; observed object metadata still lacked per-row publication/version history.
- Alternatives considered: Promote LCDv2 to historical settlement truth; rejected because the declared source is Wunderground and freeze-time versions are unavailable. Discard LCDv2 entirely; rejected because complete final observations remain useful for independent diagnostics and forecast verification.
- Consequence: Future datasets must distinguish `final_observation_available` from `available_at_decision_time` and `settlement_source_snapshot_available`.
- Revisit condition: Prospective append-only captures or authoritative version history resolve the missing point-in-time evidence.

### ED-0038 — 2026-09-02 — Require a two-page trigger/target evidence bundle

- Decision: A prospective freeze snapshot is eligible only when it preserves both the target-date value page and evidence that the following date has at least one observation; capture timestamp alone is insufficient.
- Evidence available at decision time: The KORD rule freezes revisions at the first following-date datapoint, not mechanically at midnight, while current historical pages can later diverge from settlement.
- Alternatives considered: Snapshot target page exactly at midnight; rejected because the trigger datapoint may not yet exist. Store only parsed temperature; rejected because parser changes and source disputes require original bytes.
- Consequence: Snapshot records are larger but independently replayable and fail closed when trigger evidence is absent.
- Revisit condition: The declared market rule changes or Wunderground exposes an authoritative version/freeze identifier.

### ED-0039 — 2026-09-02 — Keep fixture qualification separate from live evidence

- Decision: Passing the storage contract does not advance any event to settlement-as-of eligible; only a real exact-rule target/trigger capture can do so.
- Evidence available at decision time: All synthetic cases passed but no live event response was included, and historical current pages have already been shown to diverge from settlements.
- Alternatives considered: Treat contract tests as Phase 5 completion; rejected because they validate software behavior rather than data availability. Start an indefinite collector immediately; rejected because no event cohort or bounded runtime is registered.
- Consequence: Phase 5 remains in progress and next work is read-only event discovery plus bounded cohort registration.
- Revisit condition: At least one real event completes the registered prospective capture and later reconciles with terminal settlement.

### ED-0040 — 2026-09-02 — Select live KORD cohorts before observing their outcomes

- Decision: A prospective capture cohort must come from a complete current inventory and a deterministic earliest-end selection rule; absence is recorded without city substitution.
- Evidence available at decision time: Historical settlement mismatches make outcome-aware event replacement a material label-bias risk, while the snapshot contract itself does not select live events.
- Alternatives considered: Manually choose any convenient Chicago page; rejected because it may not correspond to a current market/rule. Switch cities if Chicago is absent; rejected because that expands scope after seeing availability.
- Consequence: The discovery result can be empty and still remain a valid feasibility finding.
- Revisit condition: A separately preregistered multi-city prospective cohort is approved.

### ED-0041 — 2026-09-02 — Treat current Chicago NOAA rules as a new provider regime

- Decision: Split historical Wunderground-primary and current NOAA-primary Chicago events at the rule/provider boundary; Wunderground fallback does not make a current event Wunderground-primary.
- Evidence available at decision time: All three discovered Chicago events named NOAA WRH KORD in `resolutionSource`, including both observed-future events, while the historical verified event 553903 named Wunderground KORD.
- Alternatives considered: Capture Wunderground anyway and label it settlement evidence; rejected because the primary source is NOAA unless the documented fallback condition occurs. Drop Chicago; deferred because NBM/KORD forecast and official observation coverage remain strong, and NOAA source feasibility can be tested.
- Consequence: Feature, label and backtest datasets require a versioned `resolution_provider_regime`; current prospective work pivots to NOAA WRH without merging labels across regimes.
- Revisit condition: A future event returns to Wunderground-primary or a verified fallback activation is observed.

### ED-0042 — 2026-09-02 — Require timestamped rows for NOAA trigger evidence

- Decision: NOAA WRH page availability or a displayed daily maximum alone cannot establish the next-day-first-datapoint trigger; eligibility requires timestamped station rows from which the first following-local-date observation is selected.
- Evidence available at decision time: Current Chicago rules define the freeze using the first following-date datapoint, and prior Wunderground current pages demonstrated that later display state can diverge from settlement.
- Alternatives considered: Use retrieval time as the trigger; rejected because a page may load before a following-date observation exists. Use only the final daily maximum; rejected because it omits the freeze event.
- Consequence: Source discovery can pass basic access yet remain conditional or fail trigger reconciliation.
- Revisit condition: NOAA exposes an authoritative explicit freeze/publication marker tied to the event rule.

## 20. Decision Log — append only

### ED-0001 — 2026-08-30 — Register feasibility before model development

- Decision: Do not build forecasting or trading models until at least three cities pass the point-in-time data join gate.
- Evidence available at decision time: Documented public market/order-book/weather-data surfaces exist, but historical L2, archive depth, station mapping and exact availability semantics remain unverified.
- Alternatives considered: Begin with a forecast model using current public data; rejected because it would not establish trustworthy historical execution or leakage controls.
- Consequence: Only read-only data discovery and feasibility collection are authorized.
- Revisit condition: Phase 7 applies the registered G0 decision gate.

### ED-0002 — 2026-08-30 — Treat price history as non-executable until proven otherwise

- Decision: Polymarket price-history data may be used for coverage diagnostics and benchmarks but not fill simulation.
- Evidence available at decision time: Official price-history response documents timestamp and price, while official book endpoints document bids, asks and sizes separately.
- Alternatives considered: Use historical price as an approximate fill; rejected due to unknown side, spread and depth.
- Consequence: Prospective L2 capture and reconnect validation are mandatory.
- Revisit condition: Only primary documentation or validated historical L2 data can change this rule.

### ED-0003 — 2026-08-30 — Require actual archive retrieval

- Decision: Provider statements about operational data do not count as historical feasibility; earliest/latest files must be retrieved and checksummed.
- Evidence available at decision time: NBM includes short-retention products and ECMWF Open Data is described as rolling.
- Alternatives considered: Infer archive depth from current product availability; rejected as point-in-time evidence risk.
- Consequence: Phase 4 must produce actual retrieval artifacts and measured retention.
- Revisit condition: None; this is a permanent provenance rule.

### ED-0004 — 2026-08-30 — Select the highest-temperature tag and keyset pagination

- Decision: Use tag slug `highest-temperature` (ID `104596`) as the primary daily MaxT discovery surface, keyset pagination for complete traversal, and broad Weather tag ID `84` only as a coverage cross-check.
- Evidence available at decision time: The narrow tag's first keyset page returned 100 titles all matching the intended family and a non-null cursor; the broad tag mixed multiple weather families; the generic temperature tag returned only two unrelated active events in the probe.
- Alternatives considered: Broad Weather filtering plus title regex; retained as cross-check but rejected as primary due to mixed contract families. Generic temperature tag; rejected for insufficient coverage.
- Consequence: Production normalization must still validate title structure, nested buckets, lifecycle dates and required identifiers; tag membership alone is insufficient.
- Revisit condition: Full pagination/manual reconciliation finds material false negatives or false positives.

### ED-0005 — 2026-08-30 — Do not equate active/not-closed with tradeable

- Decision: Preserve lifecycle flags but classify temporal relevance, identifier completeness and order-book eligibility separately.
- Evidence available at decision time: The 2026-08-30 response included active/not-closed May events and 44 nested market rows without condition/token identifiers.
- Alternatives considered: Filter only `active=true,closed=false`; rejected because it admits stale/incomplete records.
- Consequence: Excluded records remain in the inventory with explicit reason codes to avoid survivorship bias.
- Revisit condition: None; this is a permanent data-quality rule.
