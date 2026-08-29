# EXP-20260830-data-source-feasibility — Point-in-time market and weather data feasibility

**Status:** `IN_PROGRESS`
**Owner:** Abdullah Sezdi
**Created:** 2026-08-30
**Last updated:** 2026-08-30
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

**Status:** `IN_PROGRESS`

#### Objective

Convert market rule text into versioned, manually verified station, source, timezone, unit, daily-window, rounding, and bucket semantics.

#### Entry criteria

- Phase 1 identifier inventory passes.

#### Tasks

- [x] Define resolution registry schema. (`schemas/resolution_registry.schema.json` plus fail-closed Python semantic validator.)
- [x] Parse source URL/provider and station identity. (20 candidate records emitted; independent station verification pending.)
- [ ] Parse local date, timezone and observation window. (Local dates/windows parsed; timezones remain explicit unverified candidates.)
- [x] Parse temperature unit, bucket inclusivity and rounding. (161 buckets parsed; 128 belong to structurally valid candidates.)
- [x] Hash and version rule text. (20 exact SHA-256 rule versions.)
- [ ] Detect rule/station changes within a city family.
- [ ] Cross-check source station metadata.
- [ ] Manually reconcile minimum 20 market-events.
- [ ] Add DST, Celsius/Fahrenheit and boundary tests.

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

Registry schema version `0.1.0` binds event identity, disposition, source/station/timezone, unit/precision/rounding, explicit local-day window, exact rule hash/version, numeric bucket boundaries and source provenance. Candidate population produced 20 deterministic records and 161 buckets: 12 structurally complete station-unverified candidates and 8 preserved hard exclusions. Twenty exact rule hashes were retained; 26 tests pass.

#### Decision

Contract and candidate-population substeps passed; Phase 2 remains `IN_PROGRESS` until station/timezone metadata is independently verified and eligible records are promoted.

#### Next action

Verify station identity and timezone for the 12 structurally complete candidates against authoritative metadata, then promote only verified records.

### Phase 3 — Executable order-book capture feasibility

**Status:** `NOT_STARTED`

#### Objective

Demonstrate recoverable prospective L2 order-book capture and quantify why price history alone is insufficient for executable fills.

#### Entry criteria

- Phase 1 token identifiers pass.
- At least 3 active market-events are available.

#### Tasks

- [ ] Implement public REST `/book` client.
- [ ] Implement public market WebSocket client.
- [ ] Persist raw timestamps, receipt times, hashes and levels.
- [ ] Validate bid/ask sorting, bounds, tick size and empty-book behavior.
- [ ] Compare displayed/price-history values with executable book sides.
- [ ] Force reconnect and demonstrate full-book recovery.
- [ ] Run a minimum 24-hour stability capture.
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

Pending.

#### Decision

Pending.

#### Next action

Pending Phase 3 result.

### Phase 4 — Forecast-as-issued source feasibility

**Status:** `NOT_STARTED`

#### Objective

Verify actual retrievability, archive depth, timestamp semantics, parameters, licensing, cost and station applicability for candidate forecast providers.

#### Entry criteria

- Phase 2 final candidate station list exists.

#### Tasks

- [ ] Define required variables and lead times for daily MaxT reconstruction.
- [ ] Retrieve actual NBM core/QMD files for current and earliest available dates.
- [ ] Inspect NBM MaxT probabilistic/quantile fields and run cycles.
- [ ] Probe GFS/GEFS archive depth and ensemble structure.
- [ ] Probe HRRR archive depth and short-lead applicability.
- [ ] Probe ECMWF Open Data parameters, ensemble structure and rolling retention.
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

Pending.

#### Decision

Pending.

#### Next action

Pending Phase 4 result.

### Phase 5 — Observation and settlement reconciliation

**Status:** `NOT_STARTED`

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

Pending.

#### Decision

Pending.

#### Next action

Pending Phase 5 result.

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
